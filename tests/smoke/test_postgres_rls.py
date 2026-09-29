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

    schema = f"axs_rls_{uuid.uuid4().hex[:12]}"
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        with engine.connect().execution_options(schema_translate_map={None: schema}) as connection:
            Base_CORE.metadata.create_all(connection, tables=[
                MSP.__table__, Condominio.__table__, Visita.__table__,
            ])
            with Session(bind=connection) as db:
                db.add_all([
                    MSP(msp_id="a", nombre="A"), MSP(msp_id="b", nombre="B"),
                    Condominio(condominio_id="a1", msp_id="a", nombre="A1"),
                    Condominio(condominio_id="b1", msp_id="b", nombre="B1"),
                    Visita(visita_id="vb", condominio_id="b1", nombre_visitante="B", estado="pendiente"),
                ])
                db.commit()

        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {schema}.visitas ENABLE ROW LEVEL SECURITY"))
            connection.execute(text(f"ALTER TABLE {schema}.visitas FORCE ROW LEVEL SECURITY"))
            connection.execute(text(
                f"CREATE POLICY tenant_visitas ON {schema}.visitas "
                "USING (condominio_id = current_setting('app.tenant_id', true)) "
                "WITH CHECK (condominio_id = current_setting('app.tenant_id', true))"
            ))

        with engine.connect().execution_options(schema_translate_map={None: schema}) as connection:
            with Session(bind=connection) as db:
                _set_postgres_tenant(db, "a1")
                data = SimpleNamespace(nombre_visitante="A", tipo_visita="eventual", vigencia=None)
                visita = visita_service.crear_visita(db, data, condominio_id="a1", casa_unidad="101")
                assert visita.condominio_id == "a1"  # commit + refresh del servicio
                assert db.query(Visita).filter_by(visita_id="vb").first() is None
                assert db.query(Visita).filter_by(visita_id=visita.visita_id).one().estado == "pendiente"
                assert db.query(Visita).filter_by(visita_id="vb").update({"estado": "cancelada"}) == 0
                db.commit()
                assert db.query(Visita).filter_by(visita_id="vb").first() is None
            with Session(bind=connection) as no_context:
                assert no_context.query(Visita).count() == 0

        with engine.connect().execution_options(schema_translate_map={None: schema}) as connection:
            with Session(bind=connection) as other:
                _set_postgres_tenant(other, "b1")
                assert other.query(Visita).filter_by(visita_id="vb").one().estado == "pendiente"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()
