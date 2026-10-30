"""C0: full HTTP matrix over real ORM tables with forced PostgreSQL RLS.

Only localhost/CI is accepted. No Neon, credentials or operational data.
"""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.core.auth.jwt import create_access_token
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import (
    Base_CORE, Condominio, Evidencia, EventOutbox, SecurityOutbox, Usuario, Visita, get_core_db,
)
from backend.db.gov import get_gov_db
from backend.main import app
from backend.services import security_outbox
from tests.test_tenant_modalidad_http import boundary, CASES, TENANT, VISIT, MODE_DENIED


@pytest.fixture
def db_engine():
    raw = os.getenv("AXS_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Requires disposable PostgreSQL CI database")
    url = make_url(raw)
    assert (url.host in {"localhost", "127.0.0.1"} and url.database == "axs_rls_ci"
            and url.username == "axs_rls_ci"), "Only disposable local CI is allowed"
    engine = create_engine(raw)
    schema = "axs_c0_http_" + uuid4().hex[:12]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        with engine.begin() as conn:
            assert not conn.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )).scalar_one()
            conn.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(scoped)
        yield scoped
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        engine.dispose()


@pytest.mark.integration
def test_full_corporate_denial_matrix_and_rls(boundary, db_engine, db_gov_session, monkeypatch):
    schema = db_engine.get_execution_options()["schema_translate_map"][None]
    factory = sessionmaker(bind=db_engine)
    # Synthetic legacy rows already exist before FORCE RLS, as in a migration.
    with db_engine.begin() as conn:
        for name in ("visitas", "event_outbox", "evidencias"):
            conn.execute(text(f"ALTER TABLE {schema}.{name} ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {schema}.{name} FORCE ROW LEVEL SECURITY"))
            expression = ("condominio_id=current_setting('app.tenant_id',true)" if name != "evidencias"
                          else f"EXISTS (SELECT 1 FROM {schema}.visitas v WHERE "
                               "v.visita_id=evidencias.visita_id AND "
                               "v.condominio_id=current_setting('app.tenant_id',true))")
            conn.execute(text(f"CREATE POLICY tenant ON {schema}.{name} "
                              f"USING ({expression}) WITH CHECK ({expression})"))
    # Add a second corporate tenant to exercise cross-company RLS independently
    # of the API guard, plus the residential tenant already seeded by boundary.
    with factory() as db:
        db.add(Condominio(condominio_id="corp-other", msp_id="provider-matrix",
                         modalidad="corporativo", nombre="Synthetic other company"))
        _set_postgres_tenant(db, "corp-other")
        db.add(Visita(visita_id="other-visit", condominio_id="corp-other", estado="pendiente"))
        db.commit()
    with factory() as db:
        assert db.query(Visita).count() == 0
        assert db.query(Evidencia).count() == 0
        assert db.query(EventOutbox).count() == 0
        _set_postgres_tenant(db, TENANT)
        assert {v.visita_id for v in db.query(Visita)} == {VISIT}
        assert db.query(Evidencia).count() == 2
        assert db.query(Visita).filter_by(visita_id="other-visit").update({"estado": "cancelada"}) == 0
        db.commit()
    with factory() as db:
        _set_postgres_tenant(db, "corp-other")
        assert db.query(Visita).one().estado == "pendiente"
        assert db.query(Evidencia).count() == 0
        assert db.query(Visita).filter_by(visita_id=VISIT).update({"estado": "cancelada"}) == 0
        db.rollback()
    with factory() as db:
        # A new request/session must not inherit tenant context after commit.
        assert db.query(Visita).count() == 0

    def fresh_core():
        with factory() as db:
            yield db

    def snapshot():
        result = {}
        with factory() as db:
            for tenant in (TENANT, "corp-other", "res-matrix"):
                _set_postgres_tenant(db, tenant)
                for table in Base_CORE.metadata.sorted_tables:
                    if table is SecurityOutbox.__table__:
                        continue
                    rows = db.execute(select(table).order_by(*table.primary_key.columns)).mappings()
                    result[(tenant, table.name)] = [dict(row) for row in rows]
        return result

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db] = fresh_core
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    monkeypatch.setattr(security_outbox, "SessionFactory", factory)
    try:
        with TestClient(app) as client:
            for enabled in (False, True):
                for actor in ("global-matrix", "msp-matrix", "local", "outsider-matrix"):
                    for item in CASES:
                        method, path, role, kwargs = item.values
                        with factory() as db:
                            db.query(Condominio).filter_by(condominio_id=TENANT).one().corporativo_habilitado = enabled
                            user = db.query(Usuario).filter_by(usuario_id=actor).one()
                            user.rol = "MSP_ADMIN" if actor == "msp-matrix" else role
                            token = create_access_token(actor, user.rol)
                            db.commit()
                            count = db.query(SecurityOutbox).count()
                        before = snapshot()
                        opts = {**kwargs, "params": {"condominio_id": TENANT, **kwargs.get("params", {})}}
                        response = client.request(method, path.format(tenant=TENANT, visit=VISIT),
                                                  headers={"Authorization": "Bearer " + token}, **opts)
                        context = (enabled, actor, method, path, response.text)
                        assert response.status_code == 403, context
                        if actor == "global-matrix":
                            assert response.json()["detail"] == MODE_DENIED, context
                        assert "PRIVATE_" not in response.text, context
                        assert snapshot() == before, context
                        with factory() as db:
                            assert db.query(SecurityOutbox).count() == count + 1, context
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
