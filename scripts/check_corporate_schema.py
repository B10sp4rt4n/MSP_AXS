"""Read-only CORE schema gate. Never creates objects or imports backend engines.

Run after C0 -> C1 -> C2 -> C4, before starting the integrated backend.
This checks the corporate schema contract, not the whole privacy procedure or
all effective permissions; keep check_core_rls.py as a separate runtime gate.
"""
import json
import os
import re
import sys

from sqlalchemy import create_engine, text


TABLE_COLUMNS = {
    "corporate_organizations": "tenant_id modalidad created_at privacy_contact privacy_notice_url privacy_notice_version",
    "corporate_sites": "site_id tenant_id nombre zona_horaria activa created_at",
    "corporate_destinations": "destination_id tenant_id site_id nombre activa",
    "corporate_memberships": "membership_id tenant_id user_id rol estado created_at",
    "corporate_site_assignments": "assignment_id tenant_id site_id user_id estado",
    "corporate_provisioning_operations": "tenant_id request_id revision payload payload_hash requested_by expected_gov estado request_event_uid confirmation_event_uid created_at confirmed_at",
}
PRIMARY_KEYS = {
    "corporate_organizations": ("tenant_id",),
    "corporate_sites": ("site_id",),
    "corporate_destinations": ("destination_id",),
    "corporate_memberships": ("membership_id",),
    "corporate_site_assignments": ("assignment_id",),
    "corporate_provisioning_operations": ("tenant_id", "request_id"),
}
UNIQUES = {
    "condominios_exo": [("condominio_id", "modalidad")],
    "corporate_sites": [("tenant_id", "site_id")],
    "corporate_destinations": [("tenant_id", "site_id", "nombre")],
    "corporate_memberships": [("tenant_id", "user_id")],
    "corporate_site_assignments": [("tenant_id", "site_id", "user_id")],
    "corporate_provisioning_operations": [("tenant_id", "revision")],
}
FOREIGN_KEYS = {
    "corporate_organizations": [(('tenant_id', 'modalidad'), 'condominios_exo', ('condominio_id', 'modalidad'))],
    "corporate_sites": [(('tenant_id',), 'corporate_organizations', ('tenant_id',))],
    "corporate_destinations": [(('tenant_id', 'site_id'), 'corporate_sites', ('tenant_id', 'site_id'))],
    "corporate_memberships": [(('tenant_id',), 'corporate_organizations', ('tenant_id',)), (('user_id',), 'usuarios', ('usuario_id',))],
    "corporate_site_assignments": [(('tenant_id', 'site_id'), 'corporate_sites', ('tenant_id', 'site_id')), (('tenant_id', 'user_id'), 'corporate_memberships', ('tenant_id', 'user_id'))],
    "corporate_provisioning_operations": [(('tenant_id',), 'corporate_organizations', ('tenant_id',))],
}
CHECKS = {
    "condominios_exo": {"ck_condominios_modalidad", "ck_condominios_corporativo_habilitado"},
    "corporate_organizations": {"ck_corporate_org_mode"},
    "corporate_provisioning_operations": {"ck_corporate_operation_state", "ck_corporate_operation_confirmation"},
}


class SchemaGateError(RuntimeError):
    pass


def normalized(expression):
    # PostgreSQL emits equivalent varchar/text casts and redundant parentheses.
    value = re.sub(r"::(?:character varying|text)(?:\[\])?", "", expression or "", flags=re.I)
    return re.sub(r"[\s()]", "", value).lower()


def check_schema(connection, *, schema="public", provisioner_role="axs_corporate_provisioner"):
    if connection.dialect.name != "postgresql":
        raise SchemaGateError("CORE schema: PostgreSQL obligatorio")
    names = set(TABLE_COLUMNS) | {"condominios_exo"}
    tables = {r["name"]: r for r in connection.execute(text("""
        SELECT c.relname AS name,c.relkind,c.relrowsecurity,c.relforcerowsecurity
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=:schema AND c.relkind IN ('r','p')
    """), {"schema": schema}).mappings()}
    errors = []
    for name in names:
        row = tables.get(name)
        if row is None:
            errors.append("tabla ausente: " + name)
        elif name in TABLE_COLUMNS and not (row["relrowsecurity"] and row["relforcerowsecurity"]):
            errors.append("RLS no forzado: " + name)
    if errors:
        raise SchemaGateError("CORE schema incompatible: " + "; ".join(sorted(errors)))

    columns = {(r["table_name"], r["column_name"]): r for r in connection.execute(text("""
        SELECT c.relname AS table_name,a.attname AS column_name,a.attnotnull,
               format_type(a.atttypid,a.atttypmod) AS type_name,
               pg_get_expr(d.adbin,d.adrelid) AS default_expr
        FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
        JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
        WHERE n.nspname=:schema AND a.attnum>0 AND NOT a.attisdropped
    """), {"schema": schema}).mappings()}
    for name, fields in TABLE_COLUMNS.items():
        for field in fields.split():
            if (name, field) not in columns:
                errors.append("columna ausente: " + name + "." + field)
    for field, expected_type, default in (
        ("modalidad", "character varying(16)", "'residencial'"),
        ("corporativo_habilitado", "boolean", "false"),
    ):
        row = columns.get(("condominios_exo", field))
        if not row or not row["attnotnull"] or row["type_name"] != expected_type or normalized(row["default_expr"]) != default:
            errors.append("columna/default C0 incompatible: " + field)
    # Types involved in journal transitions must not silently accept stale DDL.
    for field, typ in {"revision": "integer", "payload": "json", "expected_gov": "json", "confirmed_at": "timestamp without time zone"}.items():
        row = columns.get(("corporate_provisioning_operations", field))
        if row and row["type_name"] != typ:
            errors.append("tipo C4 incompatible: " + field)

    constraints = list(connection.execute(text("""
        SELECT t.relname AS table_name,c.conname,c.contype,c.convalidated,
               ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num,ord)
                     JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num ORDER BY k.ord) AS columns,
               rt.relname AS ref_table,rn.nspname AS ref_schema,
               ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(num,ord)
                     JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.num ORDER BY k.ord) AS ref_columns
        FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace
        LEFT JOIN pg_class rt ON rt.oid=c.confrelid
        LEFT JOIN pg_namespace rn ON rn.oid=rt.relnamespace WHERE n.nspname=:schema
    """), {"schema": schema}).mappings())
    for name, fields in PRIMARY_KEYS.items():
        if not any(r["table_name"] == name and r["contype"] == "p" and tuple(r["columns"]) == fields for r in constraints):
            errors.append("clave primaria incompatible: " + name)
    for name, refs in FOREIGN_KEYS.items():
        for fields, ref_table, ref_fields in refs:
            if not any(r["table_name"] == name and r["contype"] == "f" and r["convalidated"]
                       and tuple(r["columns"]) == fields and r["ref_schema"] == schema
                       and r["ref_table"] == ref_table and tuple(r["ref_columns"]) == ref_fields for r in constraints):
                errors.append("FK incompatible: " + name + "." + ",".join(fields))
    for name, checks in CHECKS.items():
        found = {r["conname"] for r in constraints if r["table_name"] == name and r["contype"] == "c" and r["convalidated"]}
        for missing in checks - found:
            errors.append("CHECK ausente/no validado: " + missing)

    indexes = list(connection.execute(text("""
        SELECT t.relname AS table_name,i.indisvalid,i.indisunique,
               pg_get_expr(i.indpred,i.indrelid) AS predicate,
               ARRAY(SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY k(num,ord)
                     JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num
                     WHERE k.ord<=i.indnkeyatts ORDER BY k.ord) AS columns
        FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname=:schema
    """), {"schema": schema}).mappings())
    for name, uniques in UNIQUES.items():
        for fields in uniques:
            if not any(r["table_name"] == name and r["indisvalid"] and r["indisunique"]
                       and r["predicate"] is None and tuple(r["columns"]) == fields for r in indexes):
                errors.append("indice unico incompatible: " + name + "." + ",".join(fields))
    pending = "estado=anyarray['pending','needs_review']"
    if not any(r["table_name"] == "corporate_provisioning_operations" and r["indisvalid"] and r["indisunique"]
               and tuple(r["columns"]) == ("tenant_id",) and normalized(r["predicate"]) == pending for r in indexes):
        errors.append("indice de operacion pendiente incompatible")

    policies = list(connection.execute(text("""
        SELECT t.relname AS table_name,p.polcmd,p.polpermissive,
               pg_get_expr(p.polqual,p.polrelid) AS qual,
               pg_get_expr(p.polwithcheck,p.polrelid) AS with_check,
               ARRAY(SELECT CASE WHEN r=0 THEN 'public' ELSE pg_get_userbyid(r)::text END
                     FROM unnest(p.polroles) r) AS roles
        FROM pg_policy p JOIN pg_class t ON t.oid=p.polrelid
        JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname=:schema
    """), {"schema": schema}).mappings())
    tenant_expr = normalized("tenant_id=current_setting('app.tenant_id',true)")
    for name in TABLE_COLUMNS:
        rows = [r for r in policies if r["table_name"] == name]
        roles = {provisioner_role} if name == "corporate_provisioning_operations" else {"public"}
        if len(rows) != 1 or any(r["polcmd"] != "*" or not r["polpermissive"] or set(r["roles"]) != roles
                                or normalized(r["qual"]) != tenant_expr or normalized(r["with_check"]) != tenant_expr for r in rows):
            errors.append("politica tenant incompatible: " + name)
    if errors:
        raise SchemaGateError("CORE schema incompatible: " + "; ".join(sorted(errors)))
    return {"gate": "PASS", "schema": schema, "corporate_tables": len(TABLE_COLUMNS)}


def run_gate(engine, **kwargs):
    try:
        if engine.dialect.name != "postgresql":
            raise SchemaGateError("CORE schema: PostgreSQL obligatorio")
        with engine.connect() as connection, connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            return check_schema(connection, **kwargs)
    except SchemaGateError:
        raise
    except Exception as exc:
        # Never include SQLAlchemy messages, SQL parameters or connection strings.
        raise SchemaGateError("CORE schema: no se pudo verificar (" + type(exc).__name__ + ")") from None


def main():
    url = os.getenv("DATABASE_CORE_URL", "")
    if not url:
        raise SchemaGateError("CORE schema: falta DATABASE_CORE_URL")
    engine = None
    try:
        engine = create_engine(url)
        print(json.dumps(run_gate(engine)))
    except SchemaGateError:
        raise
    except Exception as exc:
        raise SchemaGateError("CORE schema: conexion invalida (" + type(exc).__name__ + ")") from None
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except SchemaGateError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
