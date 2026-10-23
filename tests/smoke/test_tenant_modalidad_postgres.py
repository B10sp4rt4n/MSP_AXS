"""C0: aplica SQL real dos veces y comprueba integridad/RLS en PostgreSQL desechable.

No apunta a Neon ni a bases operativas. Un runner diferente se omite sin URL.
"""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


@pytest.mark.integration
def test_tenant_mode_migration_is_idempotent_and_preserves_rls():
    raw = os.getenv("AXS_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Requiere PostgreSQL desechable de CI")
    url = make_url(raw)
    # Protección deliberada: no ejecutar este SQL contra un entorno remoto.
    assert (url.host in ("localhost", "127.0.0.1")
            and url.database == "axs_rls_ci"
            and url.username == "axs_rls_ci")
    engine = create_engine(raw)
    schema = "axs_modalidad_" + uuid4().hex[:12]
    try:
        with engine.begin() as c:
            assert not c.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )).scalar_one()
            c.execute(text(f"CREATE SCHEMA {schema}"))
            c.execute(text(f"CREATE TABLE {schema}.condominios_exo (condominio_id varchar PRIMARY KEY)"))
            c.execute(text(f"INSERT INTO {schema}.condominios_exo VALUES ('res'),('other')"))
            c.execute(text(f"ALTER TABLE {schema}.condominios_exo ENABLE ROW LEVEL SECURITY"))
            c.execute(text(f"ALTER TABLE {schema}.condominios_exo FORCE ROW LEVEL SECURITY"))
            c.execute(text(f"CREATE POLICY tenant_context ON {schema}.condominios_exo "
                           "USING (condominio_id=current_setting('app.tenant_id',true)) "
                           "WITH CHECK (condominio_id=current_setting('app.tenant_id',true))"))

        sql = Path("migrations/20261023_tenant_modalidad_c0.sql").read_text()
        sql = sql.replace("public.", schema + ".")
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
            c.exec_driver_sql(sql)
            c.exec_driver_sql(sql)

        with engine.begin() as c:
            meta = c.execute(text(
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE oid=to_regclass(:relation)"
            ), {"relation": f"{schema}.condominios_exo"}).one()
            assert meta == (True, True)
            assert c.execute(text(f"SELECT count(*) FROM {schema}.condominios_exo")).scalar_one() == 0
            c.execute(text("SELECT set_config('app.tenant_id','res',true)"))
            row = c.execute(text(f"SELECT modalidad,corporativo_habilitado "
                                 f"FROM {schema}.condominios_exo")).one()
            assert row == ("residencial", False)
            assert c.execute(text(f"UPDATE {schema}.condominios_exo "
                                  "SET corporativo_habilitado=true "
                                  "WHERE condominio_id='other'")).rowcount == 0

        # El CHECK protege incluso si una escritura evita la API.
        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','res',true)"))
            with pytest.raises(DBAPIError):
                c.execute(text(f"UPDATE {schema}.condominios_exo "
                               "SET corporativo_habilitado=true WHERE condominio_id='res'"))
            # PostgreSQL queda en transacción abortada tras un CHECK fallido.
            c.rollback()

        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','res',true)"))
            c.execute(text(f"UPDATE {schema}.condominios_exo "
                           "SET modalidad='corporativo',corporativo_habilitado=true "
                           "WHERE condominio_id='res'"))
            assert c.execute(text(f"SELECT modalidad,corporativo_habilitado "
                                  f"FROM {schema}.condominios_exo")).one() == ("corporativo", True)

        with engine.begin() as c:
            c.execute(text("SELECT set_config('app.tenant_id','other',true)"))
            assert c.execute(text(f"SELECT modalidad,corporativo_habilitado "
                                  f"FROM {schema}.condominios_exo")).one() == ("residencial", False)
    finally:
        with engine.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
