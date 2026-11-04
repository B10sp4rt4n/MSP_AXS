"""O2a: authenticated local protocol and transactional reconciliation experiment.

No AXS database imports. HTTP is restricted to loopback; remote TLS, real identity,
PostgreSQL/RLS and AUP outbox integration remain separate gates.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .journal import Denied, Scope, canonical, database, digest
from .packages import PackageTrust, PROOF_DOMAIN, decode, encode, finite

SEND_DOMAIN = b"AXS-CONTINGENCY-LAB-O2-SEND\0"
ACK_DOMAIN = b"AXS-CONTINGENCY-LAB-O2-ACK\0"
EVENT_FIELDS = {"schema", "synthetic", "event_uid", "scope", "seq", "visit", "action",
                "observed_at", "snapshot_id", "snapshot_expires_at", "policy_version",
                "intent_hash", "clock_suspect", "snapshot_expired", "authorization"}


def signed_request(scope, package, event, node_key):
    body = {"scope": scope.key, "package": package, "event": event}
    return {**body, "signature": encode(node_key.sign(SEND_DOMAIN + canonical(body).encode()))}


class AuthenticatedReceiver:
    def __init__(self, path, trust, receipt_key, clock=time.time):
        self.path, self.trust, self.receipt_key, self.clock = path, trust, receipt_key, clock
        with database(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS nodes (scope TEXT PRIMARY KEY, public_key TEXT NOT NULL, enabled INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS projection (scope TEXT PRIMARY KEY, visit TEXT NOT NULL, state TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS observations (
                uid TEXT PRIMARY KEY, scope TEXT NOT NULL, seq INTEGER NOT NULL, payload TEXT NOT NULL,
                package TEXT NOT NULL, ack TEXT NOT NULL, observed_at REAL NOT NULL,
                UNIQUE(scope,seq))""")
            db.execute("CREATE TABLE IF NOT EXISTS audit_outbox (uid TEXT PRIMARY KEY, scope TEXT NOT NULL, payload TEXT NOT NULL)")
            for table in ("observations", "audit_outbox"):
                for action in ("UPDATE", "DELETE"):
                    db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append only'); END")

    def enroll_fixture(self, scope, public_key, visit):
        with database(self.path) as db:
            db.execute("INSERT INTO nodes VALUES (?,?,1)", (scope.key, encode(public_key)))
            db.execute("INSERT INTO projection VALUES (?,?,?)", (scope.key, visit, "pendiente"))

    def disable_fixture(self, scope):
        with database(self.path) as db:
            db.execute("UPDATE nodes SET enabled=0 WHERE scope=?", (scope.key,))

    def cancel_fixture(self, scope):
        with database(self.path) as db:
            db.execute("UPDATE projection SET state='cancelada' WHERE scope=?", (scope.key,))

    def receive(self, request):
        try:
            if not isinstance(request, dict) or set(request) != {"scope", "package", "event", "signature"}:
                raise Denied("Contrato de entrega inválido")
            if len(canonical(request).encode()) > 32768 or not isinstance(request["scope"], str):
                raise Denied("Entrega demasiado grande o alcance inválido")
            with database(self.path) as db:
                node = db.execute("SELECT * FROM nodes WHERE scope=? AND enabled=1", (request["scope"],)).fetchone()
                if not node:
                    raise Denied("Nodo no habilitado en este receptor")
                body = {k: request[k] for k in ("scope", "package", "event")}
                key = Ed25519PublicKey.from_public_bytes(decode(node["public_key"], 32))
                key.verify(decode(request["signature"], 64), SEND_DOMAIN + canonical(body).encode())
                # Scope comes from the trusted registry AFTER signature verification.
                scope = Scope(*json.loads(node["scope"]))
                # Known lease revocation is a reconciliation conflict, not lost evidence.
                claims = PackageTrust(self.trust.keys).verify(request["package"], scope)
                if claims["node_public_key"] != node["public_key"]:
                    raise Denied("Clave del paquete distinta del nodo habilitado")
                event, snap = request["event"], claims["snapshot"]
                self._verify_event(event, request["package"], claims, key)
                old = db.execute("SELECT * FROM observations WHERE uid=?", (event["event_uid"],)).fetchone()
                if old:
                    if old["payload"] != canonical(event) or old["package"] != canonical(request["package"]):
                        raise Denied("UID existente con contenido distinto")
                    return json.loads(old["ack"])
                last = db.execute("SELECT seq,observed_at FROM observations WHERE scope=? ORDER BY seq DESC LIMIT 1", (scope.key,)).fetchone()
                if event["seq"] != (last["seq"] + 1 if last else 1):
                    raise Denied("Secuencia incompleta o colisión")
                projection = db.execute("SELECT * FROM projection WHERE scope=?", (scope.key,)).fetchone()
                now = self.clock()
                if not finite(now):
                    raise Denied("Reloj del receptor inválido")
                prior_conflict = db.execute("SELECT 1 FROM observations WHERE scope=? AND json_extract(ack,'$.receipt.status')='conflict'", (scope.key,)).fetchone()
                state_ok = (event["action"] == "entry" and projection["state"] == "pendiente") or (event["action"] == "exit" and projection["state"] == "entrada_registrada")
                time_ok = snap["issued_at"] <= event["observed_at"] < claims["lease_expires_at"] and event["observed_at"] <= now
                if event["action"] == "entry":
                    time_ok = time_ok and event["observed_at"] < snap["expires_at"] and snap["not_before"] <= event["observed_at"] < snap["valid_until"]
                revoked = claims["lease_id"] in self.trust.revoked_leases or node["public_key"] in self.trust.revoked_nodes
                conflict = (prior_conflict or not state_ok or not time_ok or revoked or event["clock_suspect"]
                            or event["snapshot_expired"] != (event["observed_at"] >= snap["expires_at"])
                            or event["visit"] != projection["visit"] or (last and event["observed_at"] < last["observed_at"]))
                status = "conflict" if conflict else "accepted"
                receipt = {"schema": 1, "receiver": "axs-lab-o2a", "scope": scope.key,
                           "event_uid": event["event_uid"], "payload_digest": digest(event),
                           "received_at": now, "status": status,
                           "reason": "Hecho recibido; requiere revisión" if conflict else "Hecho recibido y aplicado a proyección sintética"}
                ack = {"receipt": receipt, "signature": encode(self.receipt_key.sign(ACK_DOMAIN + canonical(receipt).encode()))}
                db.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?)", (event["event_uid"], scope.key, event["seq"], canonical(event), canonical(request["package"]), canonical(ack), event["observed_at"]))
                db.execute("INSERT INTO audit_outbox VALUES (?,?,?)", (event["event_uid"], scope.key, canonical({"event": event, "receipt": receipt})))
                if not conflict:
                    db.execute("UPDATE projection SET state=? WHERE scope=?", ("entrada_registrada" if event["action"] == "entry" else "salida_registrada", scope.key))
                return ack
        except (InvalidSignature, KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, Denied):
                raise
            raise Denied("Entrega o firma inválidas") from exc

    def _verify_event(self, event, package, claims, key):
        if not isinstance(event, dict) or set(event) != EVENT_FIELDS:
            raise Denied("Contrato de hecho inválido")
        if (type(event["schema"]) is not int or event["schema"] != 1 or event["synthetic"] is not True
                or type(event["seq"]) is not int or event["seq"] < 1 or not finite(event["observed_at"])
                or type(event["clock_suspect"]) is not bool or type(event["snapshot_expired"]) is not bool):
            raise Denied("Tipos de hecho inválidos")
        for field in ("event_uid", "visit", "intent_hash"):
            if not isinstance(event[field], str) or not 1 <= len(event[field]) <= 512:
                raise Denied("Identificador de hecho inválido")
        snap, auth = claims["snapshot"], event["authorization"]
        if not isinstance(auth, dict) or set(auth) != {"package_digest", "lease_id", "request_id", "node_signature"}:
            raise Denied("Prueba de captura inválida")
        if not isinstance(auth["request_id"], str) or not 1 <= len(auth["request_id"]) <= 100:
            raise Denied("Identificador de solicitud inválido")
        if (event["scope"] != claims["scope"] or event["visit"] != snap["visit"]
                or event["snapshot_id"] != snap["id"] or event["snapshot_expires_at"] != snap["expires_at"]
                or event["policy_version"] != snap["policy_version"] or event["action"] not in claims["actions"]
                or auth["lease_id"] != claims["lease_id"] or auth["package_digest"] != digest(package)):
            raise Denied("Hecho fuera del paquete autorizado")
        intent = {"visit": event["visit"], "action": event["action"], "credential": snap["credential"] if event["action"] == "entry" else ""}
        if event["intent_hash"] != digest(intent):
            raise Denied("Intención de captura alterada")
        proof = PROOF_DOMAIN + canonical({"package_digest": digest(package), "scope": event["scope"], "request_id": auth["request_id"], "intent_digest": event["intent_hash"]}).encode()
        key.verify(decode(auth["node_signature"], 64), proof)


def sync_authenticated(journal, scope, send, *, node_key, receiver_public_key, lose_ack=False):
    """Use only an explicitly provided authenticated transport; never O0 sync."""
    with database(journal.path) as db:
        rows = [dict(r) for r in db.execute("SELECT j.* FROM journal j LEFT JOIN receipts r USING(event_uid) WHERE j.scope=? AND r.event_uid IS NULL ORDER BY seq", (scope.key,))]
        history = {r[0]: json.loads(r[1]) for r in db.execute("SELECT digest,envelope FROM package_history WHERE scope=?", (scope.key,))}
    delivered = 0
    for row in rows:
        event = json.loads(row["payload"])
        if event["scope"] != scope.key or event["event_uid"] != row["event_uid"] or digest(event) != row["checksum"]:
            raise Denied("Diario alterado")
        package = history.get(event["authorization"]["package_digest"])
        if package is None:
            raise Denied("Falta paquete histórico; conservar pendiente")
        ack = send(signed_request(scope, package, event, node_key))
        try:
            if not isinstance(ack, dict) or set(ack) != {"receipt", "signature"}:
                raise Denied("Acuse inválido")
            receipt = ack["receipt"]
            Ed25519PublicKey.from_public_bytes(receiver_public_key).verify(decode(ack["signature"], 64), ACK_DOMAIN + canonical(receipt).encode())
            if (receipt["schema"] != 1 or receipt["receiver"] != "axs-lab-o2a" or receipt["scope"] != scope.key
                    or receipt["event_uid"] != event["event_uid"] or receipt["payload_digest"] != digest(event)
                    or receipt["status"] not in ("accepted", "conflict")):
                raise Denied("Acuse no corresponde al hecho")
        except (InvalidSignature, KeyError, TypeError, ValueError) as exc:
            raise Denied("Acuse inválido; conservar pendiente") from exc
        if lose_ack:
            raise ConnectionError("Confirmación perdida después de recepción durable")
        with database(journal.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS verified_acknowledgments (uid TEXT PRIMARY KEY REFERENCES journal(event_uid), ack TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO receipts VALUES (?,?,?)", (event["event_uid"], receipt["status"], receipt["reason"]))
            db.execute("INSERT OR IGNORE INTO verified_acknowledgments VALUES (?,?)", (event["event_uid"], canonical(ack)))
        delivered += 1
    return delivered


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args):
        raise Denied("El transporte de laboratorio no admite redirecciones")


def loopback_sender(url):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/lab/o2/events" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise Denied("Solo transporte HTTP loopback de laboratorio")
    opener = build_opener(ProxyHandler({}), NoRedirect())  # Local-only; never bypass a remote network policy.
    def send(request):
        data = canonical(request).encode()
        with opener.open(Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=5) as response:
            raw = response.read(32769)
            if len(raw) > 32768:
                raise Denied("Acuse demasiado grande")
            return json.loads(raw)
    return send


def make_receiver_server(receiver, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass
        def do_POST(self):
            status, result = 200, None
            try:
                expected = f"127.0.0.1:{self.server.server_port}"
                if (self.path != "/lab/o2/events" or self.headers.get("Host") != expected
                        or self.headers.get("Origin") not in (None, "http://" + expected)
                        or self.headers.get("Content-Type") != "application/json"):
                    raise Denied("Ruta u origen no admitido")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 32768:
                    raise Denied("Tamaño inválido")
                result = receiver.receive(json.loads(self.rfile.read(size)))
            except (Denied, ValueError, TypeError):
                status, result = 403, {"error": "Entrega rechazada; conservar pendiente"}
            except Exception:
                status, result = 503, {"error": "Recepción incierta; reintentar mismo UID"}
            data = canonical(result).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
    return HTTPServer(("127.0.0.1", port), Handler)
