"""Rehearse the captured CORE public schema with synthetic rows on local PG18.

Never connects to Neon. Restores metadata, not production rows/sequence values.
Provider owner/memberships/default ACLs are deliberately not cloned.
"""
import copy
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, declarative_base

from scripts import check_corporate_schema as gate
from scripts.check_core_rls import check as check_core_rls


pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parents[1] / "fixtures" / "corporate_upgrade"
MIGRATIONS = ["20261023_tenant_modalidad_c0.sql", "20261023_corporate_directory_c1.sql",
              "20261023_corporate_superadmin_c2.sql", "20261023_corporate_reconciliation_c4.sql"]


def ident(value):
    return '"' + value.replace('"', '""') + '"'


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def restore_catalog(connection, catalog):
    """Only supports the object kinds actually present in the captured fixture."""
    def execute(sql):
        connection.execute(text(sql))
    for typ in catalog["types"]:
        assert typ["kind"] == "e"
        execute(f"CREATE TYPE public.{ident(typ['name'])} AS ENUM ({','.join(literal(v) for v in typ['labels'])})")
    for seq in catalog["sequences"]:
        execute(f"CREATE SEQUENCE public.{ident(seq['name'])} AS {seq['type']} START {seq['start']} INCREMENT {seq['increment']} MINVALUE {seq['min']} MAXVALUE {seq['max']} CACHE {seq['cache']} {'CYCLE' if seq['cycle'] else 'NO CYCLE'}")
    for table in catalog["tables"]:
        columns = []
        for col in table["columns"]:
            assert not col["identity"] and not col["generated"]
            declaration = ident(col["name"]) + " " + col["type"]
            if col["default"] is not None:
                declaration += " DEFAULT " + col["default"]
            if col["not_null"]:
                nn = next(c for c in table["constraints"] if c["type"] == "n" and c["definition"].replace('"', '') == "NOT NULL " + col["name"])
                declaration += " CONSTRAINT " + ident(nn["name"]) + " NOT NULL"
            columns.append(declaration)
        execute(f"CREATE TABLE public.{ident(table['name'])} ({','.join(columns)})")
    # Referenced unique indexes must exist before any FK (not all are constraints).
    for foreign in (False, True):
        for table in catalog["tables"]:
            for constraint in table["constraints"]:
                if constraint["type"] == "n" or (constraint["type"] == "f") != foreign:
                    continue
                execute(f"ALTER TABLE public.{ident(table['name'])} ADD CONSTRAINT {ident(constraint['name'])} {constraint['definition']}")
            if not foreign:
                for index in table["indexes"]:
                    assert index["valid"]
                    if not index["constraint"]:
                        execute(index["definition"])
    for seq in catalog["sequences"]:
        execute(f"ALTER SEQUENCE public.{ident(seq['name'])} OWNED BY public.{ident(seq['table'])}.{ident(seq['column'])}")
    for table in catalog["tables"]:
        qualified = "public." + ident(table["name"])
        if table["rls"]:
            execute(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
        if table["force"]:
            execute(f"ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY")
        for policy in table["policies"]:
            command = {"*": "ALL", "r": "SELECT", "a": "INSERT", "w": "UPDATE", "d": "DELETE"}[policy["command"]]
            roles = ",".join("PUBLIC" if r == "public" else ident(r) for r in policy["roles"])
            ddl = f"CREATE POLICY {ident(policy['name'])} ON {qualified} AS {'PERMISSIVE' if policy['permissive'] else 'RESTRICTIVE'} FOR {command} TO {roles}"
            if policy["using"] is not None:
                ddl += " USING (" + policy["using"] + ")"
            if policy["check"] is not None:
                ddl += " WITH CHECK (" + policy["check"] + ")"
            execute(ddl)
        assert not table["triggers"]
        for grant in table["acl"] + table["column_acl"]:
            privilege = grant["privilege"] + (" (" + ident(grant["column"]) + ")" if "column" in grant else "")
            role = "PUBLIC" if grant["grantee"] == "PUBLIC" else ident(grant["grantee"])
            execute(f"GRANT {privilege} ON {qualified} TO {role}" + (" WITH GRANT OPTION" if grant["grantable"] else ""))
    for seq in catalog["sequences"]:
        for grant in seq["acl"]:
            assert not grant["grantable"]
            execute(f"GRANT {grant['privilege']} ON SEQUENCE public.{ident(seq['name'])} TO {ident(grant['grantee'])}")


def canonical(catalog):
    # Re-parsing historical varchar-array casts on PG18 distributes the text
    # cast over literal elements. Normalize only that exact equivalent form.
    def sql_form(value):
        if isinstance(value, dict):
            return {k: sql_form(v) for k, v in value.items()}
        if isinstance(value, list):
            return [sql_form(v) for v in value]
        if isinstance(value, str):
            return re.sub(r"ARRAY\[((?:'(?:''|[^'])*'::character varying(?:,\s*)?)+)\]::text\[\]",
                          lambda m: "ARRAY[" + m[1].replace("::character varying", "::character varying::text") + "]", value)
        return value
    result = {k: copy.deepcopy(catalog[k]) for k in ("tables", "sequences", "types", "functions", "schemas", "extensions")}
    for table in result["tables"]:
        table.pop("owner")
    return sql_form(result)


def assert_same_catalog(actual, expected):
    differences = []
    def compare(a, b, path):
        if len(differences) >= 8:
            return
        if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
            for key in a:
                compare(a[key], b[key], path + "." + str(key))
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for index, (left, right) in enumerate(zip(a, b)):
                compare(left, right, path + f"[{index}]")
        elif a != b:
            differences.append(path + ": " + repr(a)[:180] + " != " + repr(b)[:180])
    compare(actual, expected, "catalog")
    if differences:
        pytest.fail("Catalog mismatch: " + "; ".join(differences), pytrace=False)


def capture(engine):
    with engine.connect() as connection:
        return connection.scalar(text((FIXTURES / "capture_core_catalog.sql").read_text()))


def rows(engine, catalog):
    with engine.connect() as connection:
        result = {}
        for table in catalog["tables"]:
            name = table["name"]
            data = connection.scalar(text(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM public.{ident(name)} t"))
            if name == "condominios_exo":
                for row in data:
                    row.pop("modalidad", None)
                    row.pop("corporativo_habilitado", None)
            result[name] = data
        return result


@pytest.fixture
def target():
    raw = os.getenv("AXS_TEST_TARGET_SCHEMA_ADMIN_URL")
    if not raw:
        pytest.skip("Requires isolated local PostgreSQL 18 target-catalog job")
    url = make_url(raw)
    assert url.get_backend_name() == "postgresql" and url.host in {"localhost", "127.0.0.1"}
    assert url.database == "postgres" and url.username == "postgres"
    admin = create_engine(raw, isolation_level="AUTOCOMMIT")
    suffix = uuid4().hex[:12]
    database, runtime, provisioner = "axs_target_" + suffix, "axs_app_" + suffix, "axs_prov_" + suffix
    catalog = json.loads((FIXTURES / "core_catalog_20261028.json").read_text().replace("axs_core_app", runtime))
    engine = None
    try:
        with admin.connect() as c:
            assert int(c.scalar(text("SHOW server_version_num"))) // 10000 == 18
            c.exec_driver_sql(f"CREATE ROLE {runtime} NOLOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
            c.exec_driver_sql(f"CREATE DATABASE {database}")
        engine = create_engine(url.set(database=database))
        with engine.begin() as c:
            c.exec_driver_sql("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            c.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {runtime}")
            restore_catalog(c, catalog)
        # Every test proves fidelity before seeding or migrating.
        assert_same_catalog(canonical(capture(engine)), canonical(catalog))
        with engine.begin() as c:
            c.exec_driver_sql("INSERT INTO msps_exo(msp_id,nombre) VALUES ('msp_synthetic','Synthetic MSP')")
            for tenant in ("res_a", "res_b"):
                c.execute(text("INSERT INTO condominios_exo(condominio_id,msp_id,nombre,reglas_acceso) VALUES (:t,'msp_synthetic',:t,'{}')"), {"t": tenant})
                c.execute(text("INSERT INTO casas(casa_id,condominio_id,numero) VALUES (:house,:t,'1')"), {"house": tenant + "_house", "t": tenant})
                c.execute(text("INSERT INTO usuarios(usuario_id,condominio_id,casa_id,nombre,rol) VALUES (:u,:t,:house,'Synthetic Resident','residente')"), {"u": tenant + "_user", "t": tenant, "house": tenant + "_house"})
                c.execute(text("INSERT INTO casetas(caseta_id,condominio_id,nombre) VALUES (:id,:t,'Synthetic Gate')"), {"id": tenant + "_gate", "t": tenant})
                c.execute(text("INSERT INTO visitas(visita_id,condominio_id,nombre_visitante,destino_id,estado) VALUES (:id,:t,'Synthetic Visitor',:house,'pendiente')"), {"id": tenant + "_visit", "t": tenant, "house": tenant + "_house"})
                c.execute(text("INSERT INTO evidencias(evidencia_id,visita_id,categoria) VALUES (:id,:visit,'synthetic')"), {"id": tenant + "_evidence", "visit": tenant + "_visit"})
                c.execute(text("INSERT INTO event_outbox(event_uid,condominio_id,payload,created_at,next_attempt_at) VALUES (:id,:t,'{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"id": tenant + "_event", "t": tenant})

        def apply(index, *, fail=False):
            sql = Path("migrations", MIGRATIONS[index]).read_text().replace("axs_core_app", runtime).replace("axs_corporate_provisioner", provisioner)
            if fail:
                sql = sql.replace("COMMIT;", "DO $$ BEGIN RAISE EXCEPTION 'synthetic interrupted C4'; END $$; COMMIT;")
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
                try:
                    c.exec_driver_sql(sql.replace("%", "%%"))
                except Exception:
                    c.exec_driver_sql("ROLLBACK")
                    raise
        yield engine, catalog, runtime, provisioner, apply
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as c:
            c.exec_driver_sql(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)")
            for role in (runtime, provisioner):
                if c.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=:r)"), {"r": role}):
                    c.exec_driver_sql(f"DROP ROLE {role}")
        admin.dispose()


def load_models(path):
    """Load exact model definitions on a fresh registry, without engine imports."""
    module = ModuleType("upgrade_models_" + uuid4().hex)
    module.Base_CORE = declarative_base()
    source = Path(path).read_text()
    assert source.count("from .engine import Base_CORE") == 1
    sys.modules[module.__name__] = module
    try:
        exec(compile(source.replace("from .engine import Base_CORE", ""), str(path), "exec"), module.__dict__)
    finally:
        sys.modules.pop(module.__name__)
    return module


def model_workload(engine, runtime, path, marker):
    models = load_models(path)
    with engine.begin() as c:
        c.exec_driver_sql(f"SET LOCAL ROLE {runtime}")
        c.execute(text("SELECT set_config('app.tenant_id','res_a',true)"))
        with Session(bind=c, join_transaction_mode="create_savepoint") as session:
            tenant = session.scalar(select(models.Condominio).where(models.Condominio.condominio_id == "res_a"))
            assert tenant.msp_id == "msp_synthetic"
            assert session.scalar(select(models.Usuario).where(models.Usuario.usuario_id == "res_a_user")).casa_id == "res_a_house"
            assert session.scalar(select(models.Casa).where(models.Casa.casa_id == "res_a_house")).numero == "1"
            assert {v.condominio_id for v in session.scalars(select(models.Visita))} == {"res_a"}
            assert {e.visita_id for e in session.scalars(select(models.Evidencia))} == {"res_a_visit"}
            session.add(models.Condominio(condominio_id=marker, msp_id="msp_synthetic", nombre=marker))
            tenant.nombre = marker
            session.commit()


def test_target_catalog_upgrade_and_legacy_model_rollback(target):
    engine, catalog, runtime, provisioner, apply = target
    legacy = os.environ["AXS_TEST_LEGACY_CORE_MODELS"]
    model_workload(engine, runtime, legacy, "legacy_before")
    before = rows(engine, catalog)
    for index in range(4):
        with pytest.raises(gate.SchemaGateError):
            gate.run_gate(engine, provisioner_role=provisioner)
        apply(index)
    assert gate.run_gate(engine, provisioner_role=provisioner)["gate"] == "PASS"
    assert rows(engine, catalog) == before
    # Every pre-existing table/control remains identical except the C0 additions.
    after = canonical(capture(engine))
    after["tables"] = [t for t in after["tables"] if not t["name"].startswith("corporate_")]
    root = next(t for t in after["tables"] if t["name"] == "condominios_exo")
    root["columns"] = [c for c in root["columns"] if c["name"] not in {"modalidad", "corporativo_habilitado"}]
    root["constraints"] = [c for c in root["constraints"] if c["name"] not in {"ck_condominios_modalidad", "ck_condominios_corporativo_habilitado", "condominios_exo_modalidad_not_null", "condominios_exo_corporativo_habilitado_not_null"}]
    root["indexes"] = [i for i in root["indexes"] if i["name"] != "uq_condominios_modalidad"]
    # New explicit provisioner grants are expected, not changes to runtime grants.
    for table in after["tables"]:
        table["acl"] = [a for a in table["acl"] if a["grantee"] != provisioner]
        table["column_acl"] = [a for a in table["column_acl"] if a["grantee"] != provisioner]
    for seq in after["sequences"]:
        seq["acl"] = [a for a in seq["acl"] if a["grantee"] != provisioner]
    assert_same_catalog(after, canonical(catalog))
    model_workload(engine, runtime, "backend/db/core/models.py", "integrated_after")
    model_workload(engine, runtime, legacy, "legacy_after_rollback")
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM condominios_exo WHERE modalidad<>'residencial' OR corporativo_habilitado")) == 0
        assert c.scalar(text("SELECT count(*) FROM condominios_exo")) == 5


def test_target_catalog_interrupted_c4_is_atomic_and_recoverable(target):
    engine, catalog, runtime, provisioner, apply = target
    for i in range(3):
        apply(i)
    before_catalog, before_rows = capture(engine), rows(engine, catalog)
    with pytest.raises(DBAPIError):
        apply(3, fail=True)
    assert capture(engine) == before_catalog
    assert rows(engine, catalog) == before_rows
    with pytest.raises(gate.SchemaGateError):
        gate.run_gate(engine, provisioner_role=provisioner)
    apply(3)
    assert gate.run_gate(engine, provisioner_role=provisioner)["gate"] == "PASS"
    with pytest.raises(DBAPIError) as error:
        apply(3)
    assert getattr(error.value.orig, "sqlstate", None) == "42P07"
    assert rows(engine, catalog) == before_rows


def test_target_catalog_runtime_gates_rls_and_outbox_grants(target, monkeypatch):
    engine, catalog, runtime, provisioner, apply = target
    monkeypatch.delenv("AXS_ALEXA_LINKING_ENABLED", raising=False)
    for i in range(4):
        apply(i)
    with engine.begin() as c:
        c.exec_driver_sql(f"SET LOCAL ROLE {runtime}")
        assert check_core_rls(c)["gate"] == "PASS"
        assert gate.check_schema(c, provisioner_role=provisioner)["gate"] == "PASS"
        assert c.scalar(text("SELECT count(*) FROM visitas")) == 0
        c.execute(text("SELECT set_config('app.tenant_id','res_a',true)"))
        for table in ("visitas", "casetas", "event_outbox"):
            assert c.execute(text(f"SELECT DISTINCT condominio_id FROM {table}")).scalars().all() == ["res_a"]
        assert c.execute(text("SELECT visita_id FROM evidencias")).scalars().all() == ["res_a_visit"]
        c.exec_driver_sql("UPDATE event_outbox SET attempts=attempts+1 WHERE event_uid='res_a_event'")
        assert c.scalar(text("SELECT attempts FROM event_outbox WHERE event_uid='res_a_event'")) == 1
        for sql in ("UPDATE event_outbox SET payload='{}' WHERE event_uid='res_a_event'",
                    "INSERT INTO visitas(visita_id,condominio_id) VALUES ('forbidden','res_b')",
                    "SELECT * FROM corporate_provisioning_operations",
                    "CREATE TABLE public.forbidden(id integer)"):
            with pytest.raises(DBAPIError):
                with c.begin_nested():
                    c.exec_driver_sql(sql)
        assert c.scalar(text("SELECT has_table_privilege(current_user,'corporate_memberships','INSERT')")) is False
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM visitas WHERE visita_id='forbidden'")) == 0
