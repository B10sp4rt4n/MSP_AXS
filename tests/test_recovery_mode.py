"""Recovery across separate domains: fail closed, reconcile, explicitly reopen."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from backend.db.core import (MSP, Condominio, Usuario, Visita, UserTenantScope,
    MSPMembership, ScopeStatus, AccessLevel, EventOutbox)
from backend.db.core.models import RecoveryCheckpoint
from backend.db.gov import Authority, AuthorityType, GovStatus
from backend.db.gov.models import RecoveryGovCheckpoint
from backend.db.event import Event
from backend.core import recovery_gate
from backend.core.scope.msp_boundary import require_condominio
from backend.services.recovery_service import quarantine, reconcile, release
from backend.services.event_outbox import contexto_evento, encolar_visita, enviar_ciclo
from backend.services.visita_service import registrar_entrada


# The same behavior suite also runs against three independent PostgreSQL schemas.
from contextlib import contextmanager
import os
from sqlalchemy import create_engine, text
from backend.db.core import Base_CORE
from backend.db.gov import Base_GOV
from backend.db.event import Base_EVENT


@contextmanager
def database_engine(fallback, metadata):
    url = os.getenv('AXS_TEST_POSTGRES_URL')
    if not url:
        yield fallback
        return
    schema = 'axs_recovery_mode_' + uuid.uuid4().hex
    admin = create_engine(url)
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    try:
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA {schema}'))
        metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        admin.dispose()


@pytest.fixture
def db_engine(db_engine):
    with database_engine(db_engine, Base_CORE.metadata) as engine:
        yield engine


@pytest.fixture
def db_gov_engine(db_gov_engine):
    with database_engine(db_gov_engine, Base_GOV.metadata) as engine:
        yield engine


@pytest.fixture
def db_event_engine(db_event_engine):
    with database_engine(db_event_engine, Base_EVENT.metadata) as engine:
        yield engine


@pytest.fixture
def recovery(db_session, db_gov_session, db_event_session, monkeypatch):
    core, gov, event = db_session, db_gov_session, db_event_session
    incident = str(uuid.uuid4())
    monkeypatch.setenv('AXS_RECOVERY_INCIDENT', incident)
    core.add(MSP(msp_id='m', nombre='Synthetic')); core.flush()
    core.add(Condominio(condominio_id='a', msp_id='m')); core.flush()
    for uid, role in [('guard', 'GUARDIA'), ('admin', 'ADMIN_CONDOMINIO'), ('provider', 'MSP_ADMIN')]:
        core.add(Usuario(usuario_id=uid, email=f'{uid}@example.invalid', rol=role, condominio_id='a'))
    core.flush()
    core.add(UserTenantScope(usuario_id='guard', tenant_id='a', access_level=AccessLevel.GUARDIA))
    core.add(MSPMembership(usuario_id='provider', msp_id='m'))
    now = datetime.utcnow()
    for vid, state in [('pending', 'pendiente'), ('inside', 'entrada_registrada')]:
        visit = Visita(visita_id=vid, condominio_id='a', estado=state, tipo_visita='eventual',
            vigencia=now, qr_token=f'old-{vid}', qr_vigencia=now+timedelta(hours=1),
            entrada_registrada_en=now if vid == 'inside' else None)
        core.add(visit); core.flush()
        encolar_visita(core, visit, contexto_evento(SimpleNamespace(usuario_id='guard'), 'test'))
    # Simulate CORE believing delivery happened, while EVENT was restored earlier.
    core.query(EventOutbox).update({EventOutbox.delivered_at: now})
    core.commit()
    gov.add(Authority(authority_id='old', identity_id='provider', tipo=AuthorityType.GLOBAL))
    gov.commit()
    cf, gf = sessionmaker(bind=core.get_bind()), sessionmaker(bind=gov.get_bind())
    original = recovery_gate.recovery_allowed
    monkeypatch.setattr(recovery_gate, 'recovery_allowed',
        lambda **kwargs: original(core_factory=cf, gov_factory=gf))
    return core, gov, event, incident


def reconcile_it(state):
    core, gov, event, incident = state
    return reconcile(core, gov, event, incident,
        backup_cutoff=datetime.now(timezone.utc)-timedelta(hours=1))


def release_it(state, **kwargs):
    core, gov, event, incident = state
    args = dict(actor='operator', evidence_ref='exercise/occupancy-checked',
                occupancy_verified=True, admin_id='admin', tenant_id='a')
    args.update(kwargs)
    return release(core, gov, event, incident, **args)


def test_recovery_blocks_all_paths_and_worker(client, recovery):
    core, gov, event, incident = recovery
    for method, path in [('GET', '/qr/validar/pending/old-pending'),
                         ('POST', '/auth/login'), ('POST', '/webhooks/clerk'),
                         ('PATCH', '/visitas/pending/entrada'), ('GET', '/debug/db'),
                         ('GET', '/bitacora/a'), ('GET', '/ready')]:
        assert client.request(method, path).status_code == 503
    assert client.get('/health').json()['ready'] is False
    def forbidden():
        raise AssertionError('Worker must not open EVENT during recovery')
    enviar_ciclo(lambda: core, forbidden)
    assert event.query(Event).count() == 0
    assert core.query(Visita).filter_by(visita_id='pending').one().estado == 'pendiente'


def test_quarantine_reconcile_release_old_denied_new_allowed(client, recovery):
    core, gov, event, incident = recovery
    counts = quarantine(core, gov, incident, actor='operator')
    assert counts['qr_invalidated'] == 2 and counts['scopes_revoked'] == 1
    assert not recovery_gate.recovery_allowed()
    inside = core.query(Visita).filter_by(visita_id='inside').one().entrada_registrada_en
    report = reconcile_it(recovery)
    assert len(report['repaired_event_uids']) == 2
    assert len(report['events_after_cutoff']) == 2
    assert reconcile_it(recovery)['repaired_event_uids'] == []
    assert event.query(Event).count() == 2
    release_it(recovery)
    assert recovery_gate.recovery_allowed()
    assert client.get('/ready').status_code == 200
    from backend.core.auth.jwt import create_access_token
    def headers(uid, role):
        return {'Authorization': 'Bearer '+create_access_token(uid, role)}
    # Old QR remains rejected even to the newly approved administrator.
    assert client.get('/qr/validar/pending/old-pending',
        headers=headers('admin', 'ADMIN_CONDOMINIO')).status_code == 400
    assert client.get('/visitas/a', headers=headers('guard', 'GUARDIA')).status_code == 403
    admin = core.query(Usuario).filter_by(usuario_id='admin').one()
    require_condominio(core, gov, admin, 'a', AccessLevel.ADMIN_CONDOMINIO)
    for uid in ('guard', 'provider'):
        with pytest.raises(HTTPException) as denied:
            require_condominio(core, gov, core.query(Usuario).filter_by(usuario_id=uid).one(),
                               'a', AccessLevel.GUARDIA)
        assert denied.value.status_code == 403
    now = datetime.utcnow()
    core.add(Visita(visita_id='new', condominio_id='a', tipo_visita='eventual', estado='pendiente',
        qr_token='new-qr', qr_vigencia=now+timedelta(hours=1), vigencia=now))
    core.commit()
    assert client.get('/qr/validar/new/new-qr', headers=headers('admin', 'ADMIN_CONDOMINIO')).status_code == 200
    assert core.query(Visita).filter_by(visita_id='inside').one().entrada_registrada_en == inside
    assert core.get(RecoveryCheckpoint, incident).report['release']['evidence_ref']


@pytest.mark.parametrize('fault', ['no_reconcile', 'no_occupancy', 'no_evidence', 'changed_data', 'corrupt_event'])
def test_release_requires_verified_unchanged_reconciliation(recovery, fault):
    core, gov, event, incident = recovery
    quarantine(core, gov, incident, actor='operator')
    if fault != 'no_reconcile':
        reconcile_it(recovery)
    if fault == 'changed_data':
        core.query(Usuario).filter_by(usuario_id='admin').update({Usuario.nombre: 'changed'})
        core.commit()
    if fault == 'corrupt_event':
        event.query(Event).first().hash_evento = 'invalid'
        event.commit()
    args = {'occupancy_verified': False} if fault == 'no_occupancy' else {}
    if fault == 'no_evidence':
        args['evidence_ref'] = ''
    with pytest.raises(ValueError):
        release_it(recovery, **args)
    assert not recovery_gate.recovery_allowed()


def test_mismatched_event_never_overwritten_or_released(recovery):
    core, gov, event, incident = recovery
    quarantine(core, gov, incident, actor='operator')
    reconcile_it(recovery)
    row = event.query(Event).first()
    row.metadata_json = {'tampered': True}
    event.commit()
    with pytest.raises(ValueError):
        reconcile_it(recovery)
    with pytest.raises(ValueError):
        release_it(recovery)
    event.refresh(row)
    assert row.metadata_json == {'tampered': True}


@pytest.mark.parametrize('fault', ['core_missing', 'gov_missing', 'nonce', 'new_incident', 'invalid_incident'])
def test_stale_domain_or_bad_external_incident_blocks(recovery, monkeypatch, fault):
    core, gov, event, incident = recovery
    quarantine(core, gov, incident, actor='operator')
    reconcile_it(recovery); release_it(recovery)
    if fault == 'core_missing':
        core.delete(core.get(RecoveryCheckpoint, incident)); core.commit()
    elif fault == 'gov_missing':
        gov.delete(gov.get(RecoveryGovCheckpoint, incident)); gov.commit()
    elif fault == 'nonce':
        gov.get(RecoveryGovCheckpoint, incident).release_nonce = 'stale'; gov.commit()
    else:
        monkeypatch.setenv('AXS_RECOVERY_INCIDENT', str(uuid.uuid4()) if fault == 'new_incident' else '')
    assert not recovery_gate.recovery_allowed()


def test_partial_gov_failure_stays_locked_and_retryable(recovery, monkeypatch):
    core, gov, event, incident = recovery
    original = gov.commit
    def failure():
        raise RuntimeError('GOV offline')
    monkeypatch.setattr(gov, 'commit', failure)
    with pytest.raises(RuntimeError):
        quarantine(core, gov, incident, actor='operator')
    gov.rollback()
    assert not recovery_gate.recovery_allowed()
    monkeypatch.setattr(gov, 'commit', original)
    quarantine(core, gov, incident, actor='operator')
    reconcile_it(recovery); release_it(recovery)
    assert recovery_gate.recovery_allowed()


def test_release_core_commit_failure_never_opens_gate(recovery, monkeypatch):
    core, gov, event, incident = recovery
    quarantine(core, gov, incident, actor='operator'); reconcile_it(recovery)
    def failure():
        raise RuntimeError('CORE commit unavailable')
    monkeypatch.setattr(core, 'commit', failure)
    with pytest.raises(RuntimeError):
        release_it(recovery)
    core.rollback()
    assert not recovery_gate.recovery_allowed()


def test_incomplete_rls_visibility_rejected(recovery):
    core, gov, event, incident = recovery
    if core.get_bind().dialect.name != 'postgresql':
        pytest.skip('Requires real PostgreSQL RLS')
    core.execute(text('ALTER TABLE visitas ENABLE ROW LEVEL SECURITY'))
    core.execute(text('ALTER TABLE visitas FORCE ROW LEVEL SECURITY'))
    core.commit()
    with pytest.raises(ValueError, match='complete visibility'):
        quarantine(core, gov, incident, actor='operator')
    assert not recovery_gate.recovery_allowed()
