"""Offline emptiness certification and read-only runtime validation.

The certificate records initial emptiness and the approved schema/ACL snapshot.
It does not assert that later data is anonymous. Only offline synthetic seeding
is permitted; Clerk subjects must already be enrolled by the operator.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import create_engine, text
from scripts.corporate_sandbox_contract import (
    ACK, DATABASES, ROLES, TABLE_GRANTS, COLUMN_GRANTS, SEQUENCES,
)


def relations(conn):
    return conn.execute(text("""
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') ORDER BY c.relname
    """)).all()


def snapshot(conn):
    """Hash catalog metadata only: no application values, secrets or PII."""
    queries = (
        "SELECT c.relname,p.conname,pg_get_constraintdef(p.oid) FROM pg_constraint p JOIN pg_class c ON c.oid=p.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,p.conname",
        "SELECT c.relname,pg_get_indexdef(i.indexrelid) FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname",
        "SELECT c.relname,a.attname,pg_get_expr(d.adbin,d.adrelid) FROM pg_attrdef d JOIN pg_attribute a ON a.attrelid=d.adrelid AND a.attnum=d.adnum JOIN pg_class c ON c.oid=d.adrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY c.relname,a.attname",
        "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname",
        "SELECT p.proname,pg_get_functiondef(p.oid),coalesce(p.proacl::text,''),pg_get_userbyid(p.proowner) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind='f' ORDER BY p.proname,p.oid",
        """SELECT c.relname,c.relkind,c.relrowsecurity,c.relforcerowsecurity,
                  pg_get_userbyid(c.relowner),coalesce(c.relacl::text,'')
           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' ORDER BY c.relname""",
        """SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,
                  coalesce(a.attacl::text,'')
           FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
           JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND a.attnum>0 AND NOT a.attisdropped
           ORDER BY c.relname,a.attnum""",
        "SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname",
        "SELECT nspname,pg_get_userbyid(nspowner),coalesce(nspacl::text,'') FROM pg_namespace WHERE nspname='public'",
    )
    payload = [[list(row) for row in conn.execute(text(q)).all()] for q in queries]
    return hashlib.sha256(json.dumps(payload, default=str, separators=(",", ":")).encode()).hexdigest()


def verify_permissions(conn, domain):
    role = ROLES[domain]
    if conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname !~ '^pg_')")).scalar_one():
        raise RuntimeError("Sandbox: esquema adicional no aprobado")
    row = conn.execute(text("""
        SELECT rolname,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolinherit,
          has_schema_privilege(:role,'public','CREATE') AS ddl,
          has_database_privilege(:role,current_database(),'CREATE') AS dbddl,
          has_database_privilege(:role,current_database(),'TEMP') AS temp
        FROM pg_roles WHERE rolname=:role
    """), {"role": role}).mappings().one()
    if any(row[k] for k in row if k != "rolname"):
        raise RuntimeError("Sandbox: rol con privilegios incompatibles")
    if conn.execute(text("""
        SELECT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=:role))
         OR EXISTS(SELECT 1 FROM pg_class WHERE relowner=(SELECT oid FROM pg_roles WHERE rolname=:role))
         OR EXISTS(SELECT 1 FROM pg_database WHERE datdba=(SELECT oid FROM pg_roles WHERE rolname=:role))
         OR EXISTS(SELECT 1 FROM pg_namespace WHERE nspowner=(SELECT oid FROM pg_roles WHERE rolname=:role))
    """), {"role": role}).scalar_one():
        raise RuntimeError("Sandbox: rol con propiedad o membresías")
    functions = conn.execute(text("""
        SELECT p.proname,p.prosecdef,pg_get_userbyid(p.proowner),
               has_function_privilege(:role,p.oid,'EXECUTE') AS executable,
               has_function_privilege(:role,p.oid,'EXECUTE WITH GRANT OPTION') AS delegable
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public'
    """), {"role": role}).all()
    for name, definer, owner, executable, delegable in functions:
        allowed = domain == 'CORE' and name == 'corporate_sandbox_lock_company'
        if executable != allowed or delegable or (allowed and (not definer or owner == role)):
            raise RuntimeError("Sandbox: función fuera del contrato")
    if domain == 'CORE' and not any(f[0] == 'corporate_sandbox_lock_company' for f in functions):
        raise RuntimeError("Sandbox: falta capacidad de bloqueo")
    tables = relations(conn)
    if not set(TABLE_GRANTS[domain]).issubset({r[0] for r in tables}):
        raise RuntimeError("Sandbox: contrato incompleto")
    if any(not rls or not forced for _, rls, forced in tables):
        raise RuntimeError("Sandbox: RLS obligatorio")
    # Batch catalog inspection: avoid thousands of network round trips on Neon.
    table_acl = conn.execute(text("""
        SELECT c.relname,p.privilege,
          has_table_privilege(:role,c.oid,p.privilege),
          has_table_privilege(:role,c.oid,p.privilege || ' WITH GRANT OPTION')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),('TRIGGER')) p(privilege)
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
    """), {"role": role}).all()
    for table, privilege, actual, delegable in table_acl:
        if actual != (privilege in TABLE_GRANTS[domain].get(table, ())) or delegable:
            raise RuntimeError("Sandbox: permisos de tabla fuera del contrato")
    column_acl = conn.execute(text("""
        SELECT c.relname,a.attname,p.privilege,
          has_column_privilege(:role,c.oid,a.attnum,p.privilege),
          has_column_privilege(:role,c.oid,a.attnum,p.privilege || ' WITH GRANT OPTION')
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('REFERENCES')) p(privilege)
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') AND a.attnum>0 AND NOT a.attisdropped
    """), {"role": role}).all()
    for table, column, privilege, actual, delegable in column_acl:
        specified = COLUMN_GRANTS[domain].get(table, {}).get(privilege, ())
        if delegable or actual != (privilege in TABLE_GRANTS[domain].get(table, ()) or column in specified):
            raise RuntimeError("Sandbox: permisos de columna fuera del contrato")
    expected = {conn.execute(text("SELECT pg_get_serial_sequence(:table,'id')"), {"table": 'public.' + table}).scalar_one() for table in SEQUENCES[domain]}
    sequence_acl = conn.execute(text("""
        SELECT n.nspname || '.' || c.relname,p.privilege,
          has_sequence_privilege(:role,c.oid,p.privilege),
          has_sequence_privilege(:role,c.oid,p.privilege || ' WITH GRANT OPTION')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN (VALUES ('USAGE'),('SELECT'),('UPDATE')) p(privilege)
        WHERE n.nspname='public' AND c.relkind='S'
    """), {"role": role}).all()
    for sequence, privilege, actual, delegable in sequence_acl:
        if delegable or actual != (privilege == "USAGE" and sequence in expected):
            raise RuntimeError("Sandbox: permisos de secuencia fuera del contrato")


def certify_empty(conn, domain, run_id, issuer, *, expected_db=None):
    """Owner-only, explicit transaction. All tables locked until certificate commit."""
    UUID(run_id)
    actual_db, bypass = conn.execute(text("SELECT current_database(),rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
    if actual_db != (expected_db or DATABASES[domain]) or not bypass:
        raise RuntimeError("Sandbox: certificación exige visibilidad completa y base exacta")
    tables = relations(conn)
    if ACK not in {r[0] for r in tables}:
        raise RuntimeError("Sandbox: falta migración de permisos")
    if domain == "CORE" and "corporate_provisioning_operations" not in {r[0] for r in tables}:
        raise RuntimeError("Sandbox: falta migración C4")
    # Identifiers originate only in PostgreSQL catalogs and are quoted by dialect.
    for table, _, _ in tables:
        quoted = conn.dialect.identifier_preparer.quote(table)
        conn.execute(text(f"LOCK TABLE public.{quoted} IN ACCESS EXCLUSIVE MODE"))
    # Scan every application table with full visibility, including the certificate.
    for table, _, _ in tables:
        quoted = conn.dialect.identifier_preparer.quote(table)
        if conn.execute(text(f"SELECT EXISTS(SELECT 1 FROM public.{quoted})")).scalar_one():
            raise RuntimeError("Sandbox: certificación inicial rechazada; base no vacía")
    verify_permissions(conn, domain)
    if domain == "CORE":
        verify_permissions(conn, "PROVISIONER")
    conn.execute(text(f"INSERT INTO public.{ACK}(singleton,run_id,domain,database_name,clerk_issuer,catalog_hash,certified_at,expires_at) VALUES (true,:run,:domain,:db,:issuer,:digest,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP + interval '24 hours')"),
        {"run": run_id, "domain": domain, "db": actual_db, "issuer": issuer, "digest": snapshot(conn)})


def verify_attestation(conn, domain, run_id, issuer, *, expected_db=None):
    source_domain = "CORE" if domain == "PROVISIONER" else domain
    db, role = conn.execute(text("SELECT current_database(),current_user")).one()
    if db != (expected_db or DATABASES[source_domain]) or role != ROLES[domain]:
        raise RuntimeError("Sandbox: rol o base incorrectos")
    verify_permissions(conn, domain)
    row = conn.execute(text(f"SELECT run_id,domain,database_name,clerk_issuer,catalog_hash,certified_at,expires_at FROM public.{ACK} WHERE singleton=true")).mappings().one()
    now = datetime.now(timezone.utc)
    source_domain = "CORE" if domain == "PROVISIONER" else domain
    if (str(row['run_id']) != run_id or row['domain'] != source_domain or row['database_name'] != db
            or row['clerk_issuer'] != issuer or row['catalog_hash'] != snapshot(conn)
            or not row['certified_at'] <= now < row['expires_at']
            or row['expires_at'] - row['certified_at'] > timedelta(hours=24)):
        raise RuntimeError("Sandbox: constancia ausente, vencida o incompatible")


def check_runtime(values):
    for domain in ("CORE", "GOV", "EVENT", "PROVISIONER"):
        key = "DATABASE_CORPORATE_PROVISIONING_URL" if domain == "PROVISIONER" else f"DATABASE_{domain}_URL"
        engine = None
        try:
            engine = create_engine(values[key], pool_pre_ping=True)
            with engine.connect() as conn:
                verify_attestation(conn, domain, values['AXS_CORPORATE_SANDBOX_RUN_ID'], values['CLERK_JWT_ISSUER'])
        except Exception as exc:
            raise RuntimeError(f"Sandbox: arranque no verificable ({domain})") from exc
        finally:
            if engine is not None:
                engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--certify-empty', action='store_true', required=True)
    parser.add_argument('--run-id', required=True, type=UUID)
    parser.add_argument('--clerk-issuer', required=True)
    args = parser.parse_args()
    # Deliberately absent from backend runtime environment. No owner credentials there.
    from scripts.bootstrap_corporate_sandbox_schemas import check_bootstrap_url
    if not __import__('re').fullmatch(r'https://[a-z0-9-]+[.]clerk[.]accounts[.]dev', args.clerk_issuer):
        raise RuntimeError('Sandbox: instancia Clerk de prueba requerida')
    urls = {d: os.environ[f'AXS_CORPORATE_BOOTSTRAP_{d}_URL'] for d in DATABASES}
    for domain, url in urls.items():
        check_bootstrap_url(url, DATABASES[domain])
    for domain, url in urls.items():
        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                certify_empty(conn, domain, str(args.run_id), args.clerk_issuer)
        finally:
            engine.dispose()
    print('AXS sandbox: initial emptiness certified; valid for 24 hours')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('FAIL: certificación inicial incompleta; inspección requerida', file=sys.stderr)
        sys.exit(1)
