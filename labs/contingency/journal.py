"""Durable SQLite experiment. No AXS imports, credentials, network or physical access.

Synthetic scope is supplied by the fixture, NOT a production authentication mechanism.
The receiver is a second local SQLite file, NOT the AXS server.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


class Denied(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Scope:
    msp: str
    tenant: str
    node: str
    gate: str
    actor: str

    @property
    def key(self):
        return canonical([self.msp, self.tenant, self.node, self.gate, self.actor])


SCOPES = {
    name: Scope("msp_ficticio", "condominio_" + name, "nodo_" + name,
                "caseta_" + name, "guardia_ficticio_" + name)
    for name in ("A", "B")
}


@contextmanager
def database(path):
    # Caller owns the directory; no connection URLs and no remote database support.
    db = sqlite3.connect(str(path), timeout=5, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    try:
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


class Journal:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = Path(path), clock
        with database(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS snapshots (scope TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS visits (
                scope TEXT, visit TEXT, state TEXT NOT NULL,
                PRIMARY KEY(scope,visit), FOREIGN KEY(scope) REFERENCES snapshots(scope))""")
            db.execute("""CREATE TABLE IF NOT EXISTS journal (
                event_uid TEXT PRIMARY KEY, scope TEXT NOT NULL, request_id TEXT NOT NULL,
                seq INTEGER NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL,
                UNIQUE(scope,request_id), UNIQUE(scope,seq))""")
            db.execute("""CREATE TABLE IF NOT EXISTS receipts (
                event_uid TEXT PRIMARY KEY REFERENCES journal(event_uid),
                status TEXT NOT NULL CHECK(status IN ('accepted','conflict')), reason TEXT NOT NULL)""")
            db.execute("CREATE TABLE IF NOT EXISTS clocks (scope TEXT PRIMARY KEY, last_seen REAL NOT NULL)")
            db.execute("""CREATE TRIGGER IF NOT EXISTS journal_no_update BEFORE UPDATE ON journal
                BEGIN SELECT RAISE(ABORT, 'journal append only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS journal_no_delete BEFORE DELETE ON journal
                BEGIN SELECT RAISE(ABORT, 'journal append only'); END""")

    def prepare_fixture(self, scope):
        """Create once. Restart NEVER refreshes expiry, state or unacknowledged events."""
        now = self.clock()
        with database(self.path) as db:
            if db.execute("SELECT 1 FROM snapshots WHERE scope=?", (scope.key,)).fetchone():
                return
            snapshot = {"id": "snapshot_ficticio_" + uuid.uuid4().hex,
                        "issued_at": now, "expires_at": now + 3600,
                        "policy_version": "laboratorio-v1", "scope": scope.key,
                        "visit": "visita_" + scope.tenant, "destination": "Vivienda ficticia 101",
                        "credential": "PASE-FICTICIO-" + scope.tenant[-1],
                        "not_before": now - 60, "valid_until": now + 3600}
            db.execute("INSERT INTO snapshots VALUES (?,?)", (scope.key, canonical(snapshot)))
            db.execute("INSERT INTO visits VALUES (?,?,?)", (scope.key, snapshot["visit"], "pendiente"))
            db.execute("INSERT INTO clocks VALUES (?,?)", (scope.key, now))

    def state(self, scope):
        with database(self.path) as db:
            row = db.execute("SELECT payload FROM snapshots WHERE scope=?", (scope.key,)).fetchone()
            if not row:
                raise Denied("Dispositivo o condominio sin copia preparada")
            snapshot = json.loads(row[0])
            state = db.execute("SELECT state FROM visits WHERE scope=? AND visit=?",
                               (scope.key, snapshot["visit"])).fetchone()[0]
            events = [dict(r) for r in db.execute("""SELECT j.event_uid,j.seq,j.payload,
                COALESCE(r.status,'pending') status,COALESCE(r.reason,'') reason
                FROM journal j LEFT JOIN receipts r USING(event_uid)
                WHERE scope=? ORDER BY seq""", (scope.key,))]
            for event in events:
                event["payload"] = json.loads(event["payload"])
            return {"snapshot": snapshot, "state": state, "events": events,
                    "expired": self.clock() >= snapshot["expires_at"]}

    def record(self, scope, *, request_id, visit, action, credential=""):
        if (not isinstance(request_id, str) or not 1 <= len(request_id) <= 100
                or action not in ("entry", "exit")):
            raise Denied("Solicitud inválida")
        # A request retry must match the same intent, even after a lost response/restart.
        intent = {"visit": visit, "action": action, "credential": credential}
        now = self.clock()
        with database(self.path) as db:
            existing = db.execute("SELECT payload,checksum FROM journal WHERE scope=? AND request_id=?",
                                  (scope.key, request_id)).fetchone()
            if existing:
                payload = json.loads(existing[0])
                if digest(payload) != existing[1] or payload["intent_hash"] != digest(intent):
                    raise Denied("Reintento con contenido diferente o evento alterado")
                return payload
            row = db.execute("SELECT payload FROM snapshots WHERE scope=?", (scope.key,)).fetchone()
            if not row:
                raise Denied("Dispositivo o condominio sin copia preparada")
            snap = json.loads(row[0])
            if snap["scope"] != scope.key or visit != snap["visit"]:
                raise Denied("Visita fuera del condominio, caseta o dispositivo autorizado")
            last = db.execute("SELECT last_seen FROM clocks WHERE scope=?", (scope.key,)).fetchone()[0]
            current = db.execute("SELECT state FROM visits WHERE scope=? AND visit=?",
                                 (scope.key, visit)).fetchone()[0]
            if action == "entry":
                if now < last or now < snap["issued_at"]:
                    raise Denied("Reloj retrocedió: entrada bloqueada")
                if now >= snap["expires_at"]:
                    raise Denied("Copia vencida: nueva entrada bloqueada")
                if not snap["not_before"] <= now < snap["valid_until"]:
                    raise Denied("Autorización fuera de vigencia")
                if credential != snap["credential"]:
                    raise Denied("Pase ficticio inválido")
                if current != "pendiente":
                    raise Denied("La visita ya ingresó o finalizó")
                next_state = "entrada_registrada"
            else:
                if current != "entrada_registrada":
                    raise Denied("No existe una entrada abierta en esta copia")
                # An exit observation never grants permission or actuates a door.
                next_state = "salida_registrada"
            seq = db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM journal WHERE scope=?",
                             (scope.key,)).fetchone()[0]
            payload = {"schema": 1, "synthetic": True, "event_uid": "lab_" + uuid.uuid4().hex,
                       "scope": scope.key, "seq": seq, "visit": visit, "action": action,
                       "observed_at": now, "snapshot_id": snap["id"],
                       "snapshot_expires_at": snap["expires_at"],
                       "policy_version": snap["policy_version"], "intent_hash": digest(intent),
                       "clock_suspect": now < last,
                       "snapshot_expired": now >= snap["expires_at"]}
            db.execute("INSERT INTO journal VALUES (?,?,?,?,?,?)",
                       (payload["event_uid"], scope.key, request_id, seq, canonical(payload), digest(payload)))
            db.execute("UPDATE visits SET state=? WHERE scope=? AND visit=?", (next_state, scope.key, visit))
            db.execute("UPDATE clocks SET last_seen=? WHERE scope=?", (max(now, last), scope.key))
            return payload

    def sync(self, scope, receiver, *, lose_ack=False):
        """Sequential delivery; a simulated ACK loss leaves the same UID pending."""
        with database(self.path) as db:
            rows = [dict(r) for r in db.execute("""SELECT j.* FROM journal j
                LEFT JOIN receipts r USING(event_uid)
                WHERE j.scope=? AND r.event_uid IS NULL ORDER BY seq""", (scope.key,))]
        count = 0
        for row in rows:
            payload = json.loads(row["payload"])
            if digest(payload) != row["checksum"] or payload["scope"] != scope.key:
                raise Denied("Integridad o alcance del evento incorrecto")
            receipt = receiver.receive(scope, payload)
            if lose_ack:
                raise ConnectionError("Receptor ficticio guardó el evento; confirmación perdida")
            with database(self.path) as db:
                db.execute("INSERT OR IGNORE INTO receipts VALUES (?,?,?)",
                           (payload["event_uid"], receipt["status"], receipt["reason"]))
            count += 1
        return count


class SimulatedReceiver:
    """Second LOCAL database. The reconciliation policy is experimental, not AXS API."""
    def __init__(self, path):
        self.path = Path(path)
        with database(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS registry (scope TEXT PRIMARY KEY, visit TEXT, state TEXT)")
            db.execute("""CREATE TABLE IF NOT EXISTS received (
                event_uid TEXT PRIMARY KEY, scope TEXT, seq INTEGER, payload TEXT,
                status TEXT, reason TEXT, UNIQUE(scope,seq))""")

    def prepare_fixture(self, scope, visit):
        with database(self.path) as db:
            db.execute("INSERT OR IGNORE INTO registry VALUES (?,?,?)", (scope.key, visit, "pendiente"))

    def cancel_fixture(self, scope):
        with database(self.path) as db:
            db.execute("UPDATE registry SET state='cancelada' WHERE scope=?", (scope.key,))

    def receive(self, scope, payload):
        if payload.get("scope") != scope.key or payload.get("synthetic") is not True:
            raise Denied("Alcance ajeno o evento fuera del laboratorio")
        with database(self.path) as db:
            previous = db.execute("SELECT * FROM received WHERE event_uid=?", (payload["event_uid"],)).fetchone()
            if previous:
                if previous["payload"] != canonical(payload):
                    raise Denied("Identificador existente con contenido diferente")
                return {"status": previous["status"], "reason": previous["reason"]}
            registry = db.execute("SELECT * FROM registry WHERE scope=?", (scope.key,)).fetchone()
            if not registry or registry["visit"] != payload["visit"]:
                raise Denied("Visita o dispositivo ajeno al receptor")
            expected = db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM received WHERE scope=?",
                                  (scope.key,)).fetchone()[0]
            if payload["seq"] != expected:
                raise Denied("Secuencia incompleta o repetida con otro identificador")
            status, reason = "accepted", "Recibido por simulador local"
            conflicts = db.execute("SELECT 1 FROM received WHERE scope=? AND status='conflict'",
                                   (scope.key,)).fetchone()
            allowed = ((payload["action"] == "entry" and registry["state"] == "pendiente") or
                       (payload["action"] == "exit" and registry["state"] == "entrada_registrada"))
            if conflicts or not allowed or payload["clock_suspect"]:
                status, reason = "conflict", "Hecho conservado; requiere revisión por cambio de estado o reloj"
            else:
                state = "entrada_registrada" if payload["action"] == "entry" else "salida_registrada"
                db.execute("UPDATE registry SET state=? WHERE scope=?", (state, scope.key))
            db.execute("INSERT INTO received VALUES (?,?,?,?,?,?)",
                       (payload["event_uid"], scope.key, payload["seq"], canonical(payload), status, reason))
            return {"status": status, "reason": reason}

    def state(self, scope):
        with database(self.path) as db:
            state = db.execute("SELECT state FROM registry WHERE scope=?", (scope.key,)).fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM received WHERE scope=?", (scope.key,)).fetchone()[0]
            return {"state": state, "received": total}
