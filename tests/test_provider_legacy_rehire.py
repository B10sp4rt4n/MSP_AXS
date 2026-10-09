"""Reproduces PR #37's guardrail with synthetic in-memory relationships only."""
from backend.db.core import Condominio, EventOutbox, UserTenantScope, ScopeStatus
from tests.test_provider_offboarding import scenario, classify_all, leave
from tests.test_recovery_mode import db_engine, db_gov_engine, db_event_engine


def test_unversioned_rehire_second_exit_is_rejected(client, db_session, scenario):
    classify_all(client, db_session, scenario['operator'])
    first = leave(client, scenario['operator'])
    assert first.status_code == 200, first.text
    # Reproduce the unsupported legacy relink, exclusively in the test database.
    condo = db_session.query(Condominio).filter_by(condominio_id='ensayo').one()
    condo.msp_id = 'centinela'
    db_session.commit()
    second = leave(client, scenario['operator'])
    assert second.status_code == 409, second.text
    assert 'Relación reutilizada' in second.json()['detail']
    assert condo.msp_id == 'centinela'
    assert all(db_session.get(UserTenantScope, sid).estado == ScopeStatus.REVOCADO
               for sid in first.json()['revoked_scope_ids'])
    assert len([e for e in db_session.query(EventOutbox)
                if e.payload['accion'] == 'baja_proveedor']) == 1
