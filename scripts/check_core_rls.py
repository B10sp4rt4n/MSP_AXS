"""Gate read-only de la conexión CORE efectiva; no imprime URL ni contraseña."""

import json
import os
import sys

from sqlalchemy import create_engine, text


def check(connection):
    role = connection.execute(text("""
        SELECT current_user AS role, rolsuper, rolbypassrls, rolcreatedb,
               rolcreaterole, rolreplication
        FROM pg_roles WHERE rolname = current_user
    """)).mappings().one()
    if any(role[k] for k in ("rolsuper", "rolbypassrls", "rolcreatedb", "rolcreaterole", "rolreplication")):
        raise RuntimeError("El rol CORE tiene privilegios elevados")
    memberships = connection.execute(text("""
        SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname=current_user
    """)).scalar_one()
    if memberships:
        raise RuntimeError("El rol CORE tiene membresías de rol; revisar posibilidad de SET ROLE")
    if connection.execute(text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")).scalar_one():
        raise RuntimeError("El rol CORE puede crear objetos en public")
    rows = connection.execute(text("""
        SELECT c.relname, c.relrowsecurity,
               pg_get_userbyid(c.relowner)=current_user AS owns_table,
               (has_table_privilege(current_user,c.oid,'SELECT') AND
                has_table_privilege(current_user,c.oid,'INSERT') AND
                has_table_privilege(current_user,c.oid,'UPDATE') AND
                has_table_privilege(current_user,c.oid,'DELETE')) AS has_crud,
               has_table_privilege(current_user,c.oid,'TRUNCATE') AS can_truncate,
               EXISTS(SELECT 1 FROM pg_policy p WHERE p.polrelid=c.oid) AS has_policy
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname IN ('visitas','casetas','evidencias')
    """)).mappings().all()
    if len(rows) != 3 or any(not r["relrowsecurity"] or r["owns_table"] or
                             not r["has_crud"] or r["can_truncate"] or not r["has_policy"] for r in rows):
        raise RuntimeError("CORE no tiene las tres tablas protegidas con RLS y permisos operativos")
    outbox = connection.execute(text("""
        SELECT c.relrowsecurity, c.relforcerowsecurity,
               pg_get_userbyid(c.relowner)=current_user AS owns_table,
               has_table_privilege(current_user,c.oid,'SELECT') AND
               has_table_privilege(current_user,c.oid,'INSERT') AS can_enqueue,
               has_table_privilege(current_user,c.oid,'DELETE') OR
               has_table_privilege(current_user,c.oid,'TRUNCATE') OR
               has_column_privilege(current_user,c.oid,'payload','UPDATE') OR
               has_column_privilege(current_user,c.oid,'event_uid','UPDATE') OR
               has_column_privilege(current_user,c.oid,'condominio_id','UPDATE') OR
               has_column_privilege(current_user,c.oid,'created_at','UPDATE') AS can_alter_fact,
               has_column_privilege(current_user,c.oid,'delivered_at','UPDATE') AND
               has_column_privilege(current_user,c.oid,'attempts','UPDATE') AND
               has_column_privilege(current_user,c.oid,'next_attempt_at','UPDATE') AND
               has_column_privilege(current_user,c.oid,'last_error','UPDATE') AS can_ack,
               EXISTS(SELECT 1 FROM pg_policy p WHERE p.polrelid=c.oid) AS has_policy
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='event_outbox'
    """)).mappings().one_or_none()
    if not outbox or not outbox["relrowsecurity"] or not outbox["relforcerowsecurity"] or \
            outbox["owns_table"] or not outbox["can_enqueue"] or outbox["can_alter_fact"] or \
            not outbox["can_ack"] or not outbox["has_policy"]:
        raise RuntimeError("La bandeja de auditoría no tiene RLS forzado y permisos limitados")
    return {"role": role["role"], "tables": sorted([r["relname"] for r in rows] + ["event_outbox"]), "gate": "PASS"}


def main():
    url = os.getenv("DATABASE_CORE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_CORE_URL")
    engine = create_engine(url)
    try:
        if engine.dialect.name != "postgresql":
            raise RuntimeError("CORE debe ser PostgreSQL")
        with engine.connect() as connection:
            print(json.dumps(check(connection)))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"FAIL: no se pudo verificar CORE ({type(exc).__name__})", file=sys.stderr)
        sys.exit(1)

