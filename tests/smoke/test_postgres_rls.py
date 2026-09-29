"""Ensayo de RLS sobre el ORM real, en un esquema PostgreSQL desechable."""

import os
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, Condominio, MSP, Visita
from backend.services import visita_service


@pytest.mark.integration
def test_visitas_aisladas_tras_commit_y_refresh():
    url = os.getenv("AXS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Requiere AXS_TEST_POSTGRES_URL de una base PostgreSQL desechable")
    engine = create_engine(url)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.fail("AXS_TEST_POSTGRES_URL debe apuntar a PostgreSQL")

    with engine.connect() as connection:
        bypass = connection.execute(text(
            "SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user"
        )).scalar_one()
    if bypass:
        engine.dispose()
        pytest.fail("El rol de la prueba tiene BYPASSRLS o SUPERUSER; usar un rol sin bypass")

    schema = f"axs_rls_{uuid.uuid4().hex[:12]}"
    # Vincular cada Session al Engine permite que db.commit() cierre la
    # transacción real. Una Session ligada a Connection externa puede dejar
    # la transacción abierta y producir un falso positivo para set_config.
    tenant_engine = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(tenant_engine, tables=[
            MSP.__table__, Condominio.__table__, Visita.__table__,
        ])
        with Session(tenant_engine) as db:
            db.add_all([MSP(msp_id="a", nombre="A"), MSP(msp_id="b", nombre="B")])
            db.flush()
            db.add_all([
                Condominio(condominio_id="a1", msp_id="a", nombre="A1"),
                Condominio(condominio_id="b1", msp_id="b", nombre="B1"),
            ])
            db.flush()
            db.add(Visita(visita_id="vb", condominio_id="b1", nombre_visitante="B", estado="pendiente"))
            db.commit()

        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {schema}.visitas ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {schema}.visitas FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY tenant_visitas ON {schema}.visitas "
                "USING (condominio_id = current_setting('app.tenant_id', true)) "
                "WITH CHECK (condominio_id = current_setting('app.tenant_id', true))"
            ))

        with Session(tenant_engine) as db:
            _set_postgres_tenant(db, "a1")
            data = SimpleNamespace(nombre_visitante="A", tipo_visita="eventual", vigencia=None)
            visita = visita_service.crear_visita(db, data, condominio_id="a1", casa_unidad="101")
            assert visita.condominio_id == "a1"  # commit + refresh del servicio
            assert db.query(Visita).filter_by(visita_id="vb").first() is None
            assert db.query(Visita).filter_by(visita_id=visita.visita_id).one().estado == "pendiente"
            assert db.query(Visita).filter_by(visita_id="vb").update({"estado": "cancelada"}) == 0
            db.commit()
            assert db.query(Visita).filter_by(visita_id="vb").first() is None
        with Session(tenant_engine) as no_context:
            assert no_context.query(Visita).count() == 0

        with Session(tenant_engine) as other:
            _set_postgres_tenant(other, "b1")
            assert other.query(Visita).filter_by(visita_id="vb").one().estado == "pendiente"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
