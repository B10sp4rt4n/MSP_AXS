"""Corporate privacy through HTTP and forced RLS in disposable local PG only."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import Base_CORE, CorporateMembership, EventOutbox, get_core_db
from backend.db.core.models import ArcoCase
from backend.db.gov import get_gov_db
from backend.main import app
from backend.services import security_outbox
from tests.test_corporate_arco import privacy_company, TENANT, headers, body


@pytest.fixture
def db_engine():
    raw = os.getenv("AXS_TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("Requires disposable PostgreSQL CI")
    url = make_url(raw)
    assert (url.host in {"localhost", "127.0.0.1"} and url.database == "axs_rls_ci"
            and url.username == "axs_rls_ci")
    engine = create_engine(raw)
    schema = "axs_corp_arco_" + uuid4().hex[:12]
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
def test_disabled_corporate_privacy_membership_revocation_and_rls(
    privacy_company, db_engine, db_gov_session, monkeypatch,
):
    schema = db_engine.get_execution_options()["schema_translate_map"][None]
    with db_engine.begin() as conn:
        for name, column in (("corporate_memberships", "tenant_id"), ("arco_cases", "condominio_id"),
                             ("event_outbox", "condominio_id")):
            conn.execute(text(f"ALTER TABLE {schema}.{name} ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {schema}.{name} FORCE ROW LEVEL SECURITY"))
            expr = f"{column}=current_setting('app.tenant_id',true)"
            conn.execute(text(f"CREATE POLICY tenant ON {schema}.{name} USING ({expr}) WITH CHECK ({expr})"))
    factory = sessionmaker(bind=db_engine)
    def fresh_core():
        with factory() as db:
            yield db
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_core_db] = fresh_core
    app.dependency_overrides[get_gov_db] = lambda: db_gov_session
    monkeypatch.setattr(security_outbox, "SessionFactory", factory)
    try:
        with TestClient(app) as client:
            payload = body()
            response = client.post("/arco/"+TENANT, headers=headers("owner"), json=payload)
            assert response.status_code == 200, response.text
            assert response.headers["cache-control"] == "private, no-store"
            assert len(client.get("/arco/"+TENANT, headers=headers("owner")).json()) == 1
            for actor in ("host", "reception", "scoped", "msp", "outsider"):
                response = client.get("/arco/"+TENANT, headers=headers(actor))
                assert response.status_code == 403 and "PRIVATE_" not in response.text
            monkeypatch.setenv("AXS_ARCO_OPERATORS", "privacy-owner:"+TENANT+",privacy-owner:arco-other")
            assert client.get("/arco/arco-other", headers=headers("owner")).status_code == 403
            response = client.post("/arco/"+TENANT+"/"+payload["request_id"]+"/estado", headers=headers("owner"),
                                   json={"version": 1, "state": "verificada", "reference": "SYNTHETIC"})
            assert response.status_code == 200, response.text
            with factory() as db:
                assert db.query(CorporateMembership).count() == 0
                assert db.query(ArcoCase).count() == 0
                assert db.query(EventOutbox).count() == 0
                _set_postgres_tenant(db, TENANT)
                assert db.query(ArcoCase).one().state == "verificada"
                assert "PRIVATE_" not in str([row.payload for row in db.query(EventOutbox)])
                db.query(CorporateMembership).filter_by(membership_id="member-owner").one().estado = "revocado"
                db.commit()
            # Fresh request with the identical JWT must see the revocation.
            assert client.get("/arco/"+TENANT, headers=headers("owner")).status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
