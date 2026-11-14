"""Read-only EVENT/GOV and Clerk predeploy gate; no app startup or DDL imports."""
import base64
import json
import os
import re
import sys
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text

ROLES = {"EVENT": "axs_event_app", "GOV": "axs_gov_app"}
WRITABLE_QUOTA = {"limites", "metadata_json", "estado", "valida_desde", "valida_hasta"}
TENANT = "tenant_id::text=current_setting('app.tenant_id',true)"
EVENT_INSERT = TENANT + " AND (tenant_id::text<>'PLATFORM_SECURITY' OR (accion::text='denegar' AND resultado::text='denegado' AND entidad::text=ANY(ARRAY['session','scope']::text[])))"
QUOTA = "ambito::text='TENANT' AND target_tenant_id::text=current_setting('app.tenant_id',true) AND accion_objetivo::text=ANY(ARRAY['crear_sede_corporativa','crear_destino_corporativo']::text[])"
POLICIES = {
    "EVENT": {"events_aup": {
        "event_runtime_read": ("SELECT", TENANT, None),
        "event_runtime_insert": ("INSERT", None, EVENT_INSERT),
    }},
    "GOV": {
        "authorities_gov": {"gov_runtime_authority_read": ("SELECT", "true", None)},
        "delegations_gov": {"gov_runtime_delegation_read": ("SELECT", "true", None)},
        "recovery_gov_checkpoints": {"gov_runtime_checkpoint_read": ("SELECT", "true", None)},
        "policies_gov": {
            "gov_runtime_policy_read": ("SELECT", "true", None),
            "gov_runtime_quota_insert": ("INSERT", None, QUOTA),
            "gov_runtime_quota_update": ("UPDATE", QUOTA, QUOTA),
        },
    },
}


class RuntimeGateError(RuntimeError):
    pass


def normalized(value):
    if value is None:
        return None
    value = re.sub(r"::(?:text|character varying|policyscope)(?:\[\])?", "", value, flags=re.I)
    return re.sub(r"[\s()]", "", value).lower()


def check_connection(conn, domain, *, expected_role=None):
    expected_role = expected_role or ROLES[domain]
    if conn.dialect.name != "postgresql":
        raise RuntimeGateError(domain + ": PostgreSQL required")
    role = conn.execute(text("""
        SELECT r.rolname,r.rolsuper,r.rolbypassrls,r.rolcreatedb,r.rolcreaterole,
               r.rolreplication,r.rolinherit,
               has_schema_privilege(current_user,'public','CREATE') AS ddl,
               has_database_privilege(current_user,current_database(),'CREATE') AS db_create,
               has_database_privilege(current_user,current_database(),'TEMP') AS db_temp,
               EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid) AS memberships,
               EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                      WHERE n.nspname='public' AND c.relowner=r.oid) AS ownership
        FROM pg_roles r WHERE r.rolname=current_user
    """)).mappings().one()
    if role["rolname"] != expected_role or any(v for k, v in role.items() if k != "rolname"):
        raise RuntimeGateError(domain + ": runtime role has unexpected authority")
    for table, expected in POLICIES[domain].items():
        row = conn.execute(text("""
            SELECT c.relrowsecurity,c.relforcerowsecurity,
              has_table_privilege(current_user,c.oid,'SELECT') AS can_read,
              has_table_privilege(current_user,c.oid,'INSERT') AS can_insert,
              has_any_column_privilege(current_user,c.oid,'UPDATE') AS can_update,
              has_table_privilege(current_user,c.oid,'DELETE') OR
              has_table_privilege(current_user,c.oid,'TRUNCATE') OR
              has_table_privilege(current_user,c.oid,'TRIGGER') OR
              has_any_column_privilege(current_user,c.oid,'REFERENCES') AS extra
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=:table
        """), {"table": table}).mappings().one_or_none()
        writable = domain == "GOV" and table == "policies_gov"
        insert = domain == "EVENT" or writable
        if (not row or not all(row[k] for k in ("relrowsecurity", "relforcerowsecurity", "can_read"))
                or row["can_insert"] != insert or row["can_update"] != writable or row["extra"]):
            raise RuntimeGateError(domain + ": unexpected table permissions: " + table)
        if writable:
            columns = conn.execute(text("""
                SELECT a.attname,has_column_privilege(current_user,c.oid,a.attname,'UPDATE') AS writable
                FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relname=:table AND a.attnum>0 AND NOT a.attisdropped
            """), {"table": table}).mappings()
            if {c["attname"] for c in columns if c["writable"]} != WRITABLE_QUOTA:
                raise RuntimeGateError("GOV: unexpected writable policy columns")
        policies = conn.execute(text("""
            SELECT policyname,cmd,roles,qual,with_check,permissive FROM pg_policies
            WHERE schemaname='public' AND tablename=:table
              AND (:role=ANY(roles::text[]) OR 'public'=ANY(roles::text[]))
        """), {"table": table, "role": expected_role}).mappings().all()
        actual = {p["policyname"]: (p["cmd"], normalized(p["qual"]), normalized(p["with_check"])) for p in policies}
        wanted = {name: (cmd, normalized(using), normalized(check)) for name, (cmd, using, check) in expected.items()}
        if actual != wanted or any(list(p["roles"]) != [expected_role] or p["permissive"] != "PERMISSIVE" for p in policies):
            raise RuntimeGateError(domain + ": unexpected RLS policy: " + table)
    if domain == "EVENT":
        sequence = conn.exec_driver_sql("SELECT pg_get_serial_sequence('public.events_aup','id')").scalar_one()
        ok = sequence and conn.execute(text("SELECT has_sequence_privilege(current_user,:seq,'USAGE') AND NOT has_sequence_privilege(current_user,:seq,'UPDATE')"), {"seq": sequence}).scalar_one()
        if not ok:
            raise RuntimeGateError("EVENT: unexpected sequence permissions")
    return {"gate": "PASS", "role": expected_role, "domain": domain}


def check_clerk(values):
    issuer = values.get("CLERK_JWT_ISSUER", "").rstrip("/")
    parsed = urlsplit(issuer)
    try:
        pk = values.get("CLERK_PUBLISHABLE_KEY") or values.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
        encoded = pk.split("_", 2)[2]
        domain = base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True).decode().rstrip("$")
        if (parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment
                or parsed.username or parsed.password or parsed.port or parsed.hostname != domain
                or values.get("CLERK_JWKS_URL") != issuer + "/.well-known/jwks.json"):
            raise ValueError("Clerk instance mismatch")
        if values.get("ENVIRONMENT", values.get("ENV", "")).lower() == "production" and not pk.startswith("pk_live_"):
            raise ValueError("Development key in production")
    except Exception:
        raise RuntimeGateError("Clerk: issuer, public instance and JWKS must agree") from None
    return {"gate": "PASS", "issuer": issuer,
            "pinned_public_key_present": bool(values.get("CLERK_JWT_PUBLIC_KEY", "").strip())}


def main():
    result = {"CLERK": check_clerk(os.environ)}
    for domain in ("EVENT", "GOV"):
        engine = None
        try:
            engine = create_engine(os.environ["DATABASE_" + domain + "_URL"])
            with engine.connect() as conn, conn.begin():
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                result[domain] = check_connection(conn, domain)
        except RuntimeGateError:
            raise
        except Exception as exc:
            raise RuntimeGateError(domain + ": verification failed (" + type(exc).__name__ + ")") from None
        finally:
            if engine is not None:
                engine.dispose()
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except RuntimeGateError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
