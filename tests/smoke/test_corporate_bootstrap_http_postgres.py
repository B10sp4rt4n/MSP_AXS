"""C3: HTTP real con aprovisionamiento PostgreSQL segregado en CI efímero.

Nunca usar contra Neon ni datos productivos; limita host, DB y superuser a CI local.
Clerk/GOV/Event se simulan exclusivamente con fixtures, CORE provisioner y RLS son reales.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import DBAPIError

from backend.main import app
from backend.core.auth.jwt import create_access_token
from backend.db.core import (
    Base_CORE, Condominio, CorporateOrganization, CorporateMembership,
    CorporateSite, EventOutbox, MSP, Usuario, Casa, get_core_db,
)
from backend.db.event import get_event_db
from backend.db.gov import Authority, AuthorityType, GovStatus, Policy, get_gov_db
from backend.services.corporate_provisioner_db import get_provisioning_db
from backend.services import security_outbox


@pytest.mark.integration
def test_corporate_http_bootstrap_with_restricted_postgres_and_rls(
    db_core_session, db_gov_session, db_event_session, monkeypatch,
):
    normal, admin = os.getenv("AXS_TEST_POSTGRES_URL"), os.getenv("AXS_TEST_POSTGRES_ADMIN_URL")
    if not normal or not admin:
        pytest.skip("Solo CI PostgreSQL descartable")
    a, b = make_url(normal), make_url(admin)
    assert a.host in ("localhost", "127.0.0.1") and a.database == "axs_rls_ci"
    assert b.host in ("localhost", "127.0.0.1") and b.database == "axs_rls_ci"
    assert b.username == "postgres"
    root = create_engine(admin)
    schema = "axs_c3_" + uuid4().hex[:12]
    scoped = root.execution_options(schema_translate_map={None: schema})
    previous = app.dependency_overrides.copy()
    provisioner_created = False
    class RestrictedSession(Session):
        pass

    @event.listens_for(RestrictedSession, "after_begin")
    def _set_role(session, transaction, connection):
        connection.exec_driver_sql("SET LOCAL ROLE axs_corporate_provisioner")

    factory = sessionmaker(bind=scoped, class_=RestrictedSession, autoflush=False)
    def restricted():
        with factory() as db:
            yield db

    try:
        with root.begin() as c:
            c.execute(text(f"CREATE SCHEMA {schema}"))
        Base_CORE.metadata.create_all(scoped)
        with Session(scoped) as db:
            db.add(MSP(msp_id="provider", nombre="Proveedor sintetico"))
            db.add_all([
                Usuario(usuario_id="owner", email="owner@example.test", rol="RESIDENTE"),
                Usuario(usuario_id="super", email="super@example.test", rol="MSP_ADMIN"),
            ])
            db.commit()
        # Apply schema DDL/migrations with owner, never with app/provisioner role.
        statements = [
            "migrations/20261023_corporate_directory_c1.sql",
            "migrations/20261023_corporate_superadmin_c2.sql",
            "migrations/20261023_corporate_reconciliation_c4.sql",
        ]
        for file in statements:
            sql = Path(file).read_text()
            sql = (sql.replace("public.", schema + ".")
                   .replace("GRANT USAGE ON SCHEMA public TO", f"GRANT USAGE ON SCHEMA {schema} TO")
                   .replace("TO axs_core_app", "TO axs_rls_ci")
                   .replace("schemaname='public'", "schemaname='" + schema + "'")
                   .replace("%I", "%%I").replace("%s", "%%s"))
            with root.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
                c.exec_driver_sql(sql)
                if "reconciliation_c4" not in file:
                    c.exec_driver_sql(sql)
        provisioner_created = True
        with root.begin() as c:
            c.execute(text(f"ALTER TABLE {schema}.event_outbox ENABLE ROW LEVEL SECURITY"))
            c.execute(text(f"ALTER TABLE {schema}.event_outbox FORCE ROW LEVEL SECURITY"))
            c.execute(text(f"CREATE POLICY tenant ON {schema}.event_outbox "
                           "USING (condominio_id=current_setting('app.tenant_id',true)) "
                           "WITH CHECK (condominio_id=current_setting('app.tenant_id',true))"))

        db_core_session.add(MSP(msp_id="provider", nombre="MSP demo"))
        db_core_session.add_all([
            Usuario(usuario_id="super", email="super@example.test", rol="MSP_ADMIN"),
            Usuario(usuario_id="owner", email="owner@example.test", rol="RESIDENTE"),
            Usuario(usuario_id="unprivileged", email="msp@example.test", rol="MSP_ADMIN"),
        ])
        db_core_session.commit()
        db_gov_session.add(Authority(
            authority_id="global_c3", identity_id="super",
            tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO))
        db_gov_session.commit()
        monkeypatch.setenv("AXS_CORPORATE_API_ENABLED", "true")
        monkeypatch.setenv("AXS_CORPORATE_PROVISIONING_ENABLED", "true")
        monkeypatch.setenv("TESTING", "1")
        monkeypatch.setattr(security_outbox, "SessionFactory",
                            sessionmaker(bind=db_core_session.bind))
        app.dependency_overrides[get_core_db] = lambda: db_core_session
        app.dependency_overrides[get_gov_db] = lambda: db_gov_session
        app.dependency_overrides[get_event_db] = lambda: db_event_session
        app.dependency_overrides[get_provisioning_db] = restricted
        base = "/plataforma/corporativo"
        auth = lambda who: {"Authorization": "Bearer " + create_access_token(who, "MSP_ADMIN")}
        data = {
            "request_id": str(uuid4()), "nombre": "Empresa ficticia E2E",
            "msp_id": "provider", "owner_user_id": "owner",
            "privacy_contact": "privacidad@example.test",
            "privacy_notice_url": "https://example.test/privacidad",
            "privacy_notice_version": "synthetic-v1",
        }
        with TestClient(app) as client:
            denied = client.post(base + "/empresas", headers=auth("unprivileged"), json=data)
            assert denied.status_code == 403
            assert client.get(base + "/acceso", headers=auth("unprivileged")).status_code == 403
            assert client.get(base + "/acceso", headers=auth("super")).status_code == 200
            created = client.post(base + "/empresas", headers=auth("super"), json=data)
            assert created.status_code == 201, created.text
            tenant = created.json()["tenant_id"]
            assert not created.json()["directorio_habilitado"]
            assert client.post(base + "/empresas", headers=auth("super"), json=data).json()["tenant_id"] == tenant
            assert client.post(base + "/empresas", headers=auth("super"),
                json={**data,"nombre":"Otro nombre"}).status_code == 409
            caps_url = base + "/empresas/" + tenant + "/capacidades"
            on_url = base + "/empresas/" + tenant + "/habilitar-directorio"
            assert client.post(on_url, headers=auth("super"), json={"confirmacion":True}).status_code == 409
            quota = {"max_sedes":2, "max_destinos_por_sede":4,
                     "request_id":str(uuid4()), "expected_revision":0}
            assert client.put(caps_url, headers=auth("unprivileged"), json=quota).status_code == 403
            stored = client.put(caps_url, headers=auth("super"), json=quota)
            assert stored.status_code == 200,stored.text
            assert db_gov_session.query(Policy).filter_by(target_tenant_id=tenant).count() == 2
            # Real restricted CORE session/RLS, synthetic GOV: an identical PUT
            # must repair an ineffective time window, not silently succeed.
            for invalid_window in ("expired", "future"):
                now = datetime.utcnow()
                for policy in db_gov_session.query(Policy).filter_by(target_tenant_id=tenant).all():
                    if invalid_window == "expired":
                        policy.valida_hasta = now - timedelta(days=1)
                    else:
                        policy.valida_desde = now + timedelta(days=1)
                db_gov_session.commit()
                status = client.get(base + "/empresas/" + tenant, headers=auth("super"))
                assert status.status_code == 200, status.text
                assert status.json()["capacidades"] == {"max_sedes": None, "max_destinos_por_sede": None}
                assert client.post(on_url, headers=auth("super"), json={"confirmacion": True}).status_code == 409
                quota = {**quota, "request_id":str(uuid4()), "expected_revision":quota["expected_revision"] + 1}
                repaired = client.put(caps_url, headers=auth("super"), json=quota)
                assert repaired.status_code == 200, repaired.text
                assert client.get(base + "/empresas/" + tenant, headers=auth("super")).json()["capacidades"] == {k:quota[k] for k in ("max_sedes", "max_destinos_por_sede")}
            active = client.post(on_url, headers=auth("super"), json={"confirmacion":True})
            assert active.status_code == 200,active.text
            assert active.json()["directorio_habilitado"]
            assert client.post(on_url, headers=auth("super"),json={"confirmacion":True}).status_code == 200
        with Session(scoped) as verify:
            assert verify.query(Condominio).filter_by(condominio_id=tenant, modalidad="corporativo").one().corporativo_habilitado
            assert verify.query(CorporateOrganization).filter_by(tenant_id=tenant).count()==1
            assert verify.query(CorporateMembership).filter_by(tenant_id=tenant, rol="owner").count()==1
            assert verify.query(Casa).count()==0
            assert verify.query(CorporateSite).count()==0
            # Creation + initial quota pair + two repairs (two events each) + activation.
            assert verify.query(EventOutbox).filter_by(condominio_id=tenant).count()==8

        with factory() as isolated:
            # No tenant context: must not expose private corporate membership/outbox.
            assert isolated.query(CorporateMembership).count()==0
            assert isolated.query(CorporateOrganization).count()==0
            # Este rol sólo puede INSERTar en auditoría; SELECT está denegado.
            with pytest.raises(DBAPIError):
                isolated.query(EventOutbox).count()
            isolated.rollback()

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        with root.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            if provisioner_created:
                c.execute(text("DROP OWNED BY axs_corporate_provisioner"))
                c.execute(text("DROP ROLE IF EXISTS axs_corporate_provisioner"))
        root.dispose()
