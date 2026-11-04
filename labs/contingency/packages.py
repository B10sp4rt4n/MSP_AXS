"""O1 laboratory: pinned Ed25519 issuer, explicit enrollment and device proof.

No production credentials, routes, provisioning or hardware identity. Private issuer
keys belong to the caller's authority; nodes receive public keys and signed packages.
"""
import base64
import binascii
import json
import math

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .journal import Denied, Journal, canonical, database, digest

PACKAGE_DOMAIN = b"AXS-CONTINGENCY-LAB-PACKAGE-V1\0"
PROOF_DOMAIN = b"AXS-CONTINGENCY-LAB-NODE-PROOF-V1\0"
SNAPSHOT_FIELDS = {"id", "scope", "issued_at", "expires_at", "policy_version", "visit",
                   "destination", "credential", "not_before", "valid_until"}
CLAIM_FIELDS = {"schema", "audience", "synthetic", "kid", "lease_id", "scope", "version",
                "node_public_key", "actions", "lease_expires_at", "snapshot"}


def encode(value):
    return base64.b64encode(value).decode("ascii")


def decode(value, length):
    try:
        if not isinstance(value, str) or len(value) > 256:
            raise ValueError()
        raw = base64.b64decode(value, validate=True)
        if len(raw) != length:
            raise ValueError()
        return raw
    except (ValueError, binascii.Error) as exc:
        raise Denied("Codificación criptográfica inválida") from exc


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_claims(claims):
    if not isinstance(claims, dict) or set(claims) != CLAIM_FIELDS:
        raise Denied("Contrato de paquete inválido")
    if (type(claims["schema"]) is not int or claims["schema"] != 1
            or claims["audience"] != "axs-contingency-lab-o1" or claims["synthetic"] is not True):
        raise Denied("Versión, audiencia o entorno no admitido")
    if type(claims["version"]) is not int or claims["version"] < 1:
        raise Denied("Versión de copia inválida")
    if (not isinstance(claims["actions"], list) or not claims["actions"]
            or any(type(a) is not str or a not in ("entry", "exit") for a in claims["actions"])
            or len(set(claims["actions"])) != len(claims["actions"])):
        raise Denied("Permisos inválidos")
    for key in ("kid", "lease_id", "scope"):
        if not isinstance(claims[key], str) or not 1 <= len(claims[key]) <= 512:
            raise Denied("Identidad inválida")
    decode(claims["node_public_key"], 32)
    snap = claims["snapshot"]
    if not isinstance(snap, dict) or set(snap) != SNAPSHOT_FIELDS:
        raise Denied("Proyección de datos inválida")
    for key in SNAPSHOT_FIELDS - {"issued_at", "expires_at", "not_before", "valid_until"}:
        if not isinstance(snap[key], str) or not 1 <= len(snap[key]) <= 512:
            raise Denied("Campo de proyección inválido")
    if snap["scope"] != claims["scope"]:
        raise Denied("Alcance de copia y permiso diferente")
    if not all(finite(snap[k]) for k in ("issued_at", "expires_at", "not_before", "valid_until")) or not finite(claims["lease_expires_at"]):
        raise Denied("Tiempos inválidos")
    if not (snap["issued_at"] < snap["expires_at"] <= claims["lease_expires_at"]
            and snap["not_before"] < snap["valid_until"]):
        raise Denied("Ventanas de vigencia inválidas")


class LabAuthority:
    """Issuer-side synthetic roster. Not instantiated by the node or O0 web server."""
    def __init__(self, kid, private_key):
        self.kid, self.private_key, self.enrollments = kid, private_key, {}

    def enroll(self, scope, node_public_key):
        if len(node_public_key) != 32:
            raise Denied("Clave de nodo inválida")
        self.enrollments[scope.key] = bytes(node_public_key)

    def revoke(self, scope):
        self.enrollments.pop(scope.key, None)

    def issue(self, scope, node_public_key, snapshot, *, version=1, actions=("entry", "exit"), lease_expires_at):
        if self.enrollments.get(scope.key) != node_public_key:
            raise Denied("Nodo y guardia sin habilitación explícita para este inmueble")
        claims = {"schema": 1, "audience": "axs-contingency-lab-o1", "synthetic": True,
                  "kid": self.kid, "lease_id": "lease_" + digest([scope.key, version]),
                  "scope": scope.key, "version": version, "actions": list(actions),
                  "node_public_key": encode(node_public_key), "snapshot": snapshot,
                  "lease_expires_at": lease_expires_at}
        validate_claims(claims)
        # Round-trip detaches nested objects from mutable issuer input.
        claims = json.loads(canonical(claims))
        return {"claims": claims, "signature": encode(self.private_key.sign(PACKAGE_DOMAIN + canonical(claims).encode()))}


class PackageTrust:
    def __init__(self, pinned_keys, *, revoked_leases=(), revoked_nodes=()):
        self.keys = dict(pinned_keys)
        self.revoked_leases, self.revoked_nodes = frozenset(revoked_leases), frozenset(revoked_nodes)

    def verify(self, envelope, scope):
        try:
            if not isinstance(envelope, dict) or set(envelope) != {"claims", "signature"}:
                raise Denied("Sobre de paquete inválido")
            if len(canonical(envelope).encode()) > 16384:
                raise Denied("Paquete demasiado grande")
            claims = envelope["claims"]
            validate_claims(claims)
            key = self.keys.get(claims["kid"])
            if key is None:
                raise Denied("Emisor no confiable")
            Ed25519PublicKey.from_public_bytes(key).verify(decode(envelope["signature"], 64), PACKAGE_DOMAIN + canonical(claims).encode())
            if claims["scope"] != scope.key:
                raise Denied("Paquete de otro MSP, inmueble, caseta, nodo o guardia")
            if claims["lease_id"] in self.revoked_leases or claims["node_public_key"] in self.revoked_nodes:
                raise Denied("Permiso o nodo revocado conocido localmente")
            return claims
        except (InvalidSignature, TypeError, ValueError) as exc:
            if isinstance(exc, Denied):
                raise
            raise Denied("Paquete o firma inválidos") from exc


def proof_message(envelope, scope, *, request_id, visit, action, credential=""):
    return PROOF_DOMAIN + canonical({"package_digest": digest(envelope), "scope": scope.key,
        "request_id": request_id, "intent_digest": digest({"visit": visit, "action": action, "credential": credential})}).encode()


class VerifiedJournal(Journal):
    """O1 adapter. O0 fixture server remains separate and explicitly unsigned."""
    def __init__(self, path, trust, **kwargs):
        super().__init__(path, **kwargs)
        self.trust = trust
        with database(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS packages (scope TEXT PRIMARY KEY, version INTEGER NOT NULL, envelope TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS package_history (digest TEXT PRIMARY KEY, scope TEXT NOT NULL, envelope TEXT NOT NULL)")
            for row in db.execute("SELECT scope,envelope FROM packages").fetchall():
                db.execute("INSERT OR IGNORE INTO package_history VALUES (?,?,?)",
                           (digest(json.loads(row[1])), row[0], row[1]))

    def prepare_fixture(self, scope):
        raise Denied("O1 requiere paquete firmado; no admite habilitación por fixture")

    def sync(self, *_args, **_kwargs):
        raise Denied("El adaptador O1 espera un receptor autenticado O2; no usar el receptor O0")

    def install(self, scope, envelope):
        claims = self.trust.verify(envelope, scope)
        now, snap = self.clock(), claims["snapshot"]
        if not finite(now) or not snap["issued_at"] <= now < snap["expires_at"]:
            raise Denied("Copia futura o vencida")
        with database(self.path) as db:
            current = db.execute("SELECT * FROM packages WHERE scope=?", (scope.key,)).fetchone()
            if not current and db.execute("SELECT 1 FROM snapshots WHERE scope=?", (scope.key,)).fetchone():
                raise Denied("No mezclar base O0 sin firma con el adaptador O1")
            if current:
                last = db.execute("SELECT last_seen FROM clocks WHERE scope=?", (scope.key,)).fetchone()[0]
                if now < last:
                    raise Denied("Reloj retrocedió")
                if current["envelope"] == canonical(envelope):
                    return  # Idempotent: never resets consumption, clocks or expiry.
                if claims["version"] <= current["version"]:
                    raise Denied("Copia antigua o versión reutilizada con otro contenido")
                old = json.loads(db.execute("SELECT payload FROM snapshots WHERE scope=?", (scope.key,)).fetchone()[0])
                if old["visit"] != snap["visit"]:
                    raise Denied("O1 conserva una visita por escenario; no reemplazar su historial")
            db.execute("INSERT INTO packages VALUES (?,?,?) ON CONFLICT(scope) DO UPDATE SET version=excluded.version,envelope=excluded.envelope",
                       (scope.key, claims["version"], canonical(envelope)))
            db.execute("INSERT OR IGNORE INTO package_history VALUES (?,?,?)",
                       (digest(envelope), scope.key, canonical(envelope)))
            db.execute("INSERT INTO snapshots VALUES (?,?) ON CONFLICT(scope) DO UPDATE SET payload=excluded.payload", (scope.key, canonical(snap)))
            db.execute("INSERT OR IGNORE INTO visits VALUES (?,?,?)", (scope.key, snap["visit"], "pendiente"))
            db.execute("INSERT INTO clocks VALUES (?,?) ON CONFLICT(scope) DO UPDATE SET last_seen=MAX(last_seen,excluded.last_seen)", (scope.key, now))

    def record(self, scope, *, request_id, visit, action, credential="", proof):
        def guard(db, now):
            row = db.execute("SELECT envelope FROM packages WHERE scope=?", (scope.key,)).fetchone()
            if not row:
                raise Denied("Nodo y guardia sin paquete instalado")
            env = json.loads(row[0])
            claims = self.trust.verify(env, scope)
            if not finite(now) or not claims["snapshot"]["issued_at"] <= now < claims["lease_expires_at"]:
                raise Denied("Habilitación temporal vencida o futura")
            if action not in claims["actions"]:
                raise Denied("Acción fuera del permiso temporal")
            stored = db.execute("SELECT payload FROM snapshots WHERE scope=?", (scope.key,)).fetchone()[0]
            if stored != canonical(claims["snapshot"]):
                raise Denied("La copia local difiere de la firmada")
            msg = proof_message(env, scope, request_id=request_id, visit=visit, action=action, credential=credential)
            try:
                Ed25519PublicKey.from_public_bytes(decode(claims["node_public_key"], 32)).verify(decode(proof, 64), msg)
            except InvalidSignature as exc:
                raise Denied("Nodo sin prueba válida de posesión de clave") from exc
            return {"package_digest": digest(env), "lease_id": claims["lease_id"],
                    "request_id": request_id, "node_signature": proof}
        return super().record(scope, request_id=request_id, visit=visit, action=action,
                              credential=credential, _guard=guard)
