"""Offline recovery operations. No public endpoint and no automatic grants."""
import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import text

from backend.core.recovery_gate import incident_id
from backend.core.event.registry import verificar_integridad_evento
from backend.db.core import (Condominio, Usuario, UserTenantScope, MSPMembership,
    Visita, EventOutbox, SecurityOutbox, ScopeStatus, AccessLevel)
from backend.db.core.models import RecoveryCheckpoint
from backend.db.gov import Authority, Delegation, GovStatus
from backend.db.gov.models import RecoveryGovCheckpoint
from backend.db.event import Event
from backend.services.event_outbox import publicar_evento


def _incident(expected):
    if not expected or incident_id() != expected:
        raise ValueError('Configure this fresh recovery incident before connecting the restored app')


def _visible(db):
    """Do not silently reconcile a subset hidden by RLS. Offline recovery role only."""
    if db.get_bind().dialect.name == 'postgresql':
        hidden = db.execute(text("""
            SELECT count(*) FROM pg_class c JOIN pg_roles r ON r.rolname=current_user
            WHERE c.relnamespace=current_schema()::regnamespace AND c.relrowsecurity
            AND NOT (r.rolsuper OR r.rolbypassrls OR
                     (c.relowner=r.oid AND NOT c.relforcerowsecurity))
        """)).scalar_one()
        if hidden:
            raise ValueError('Recovery requires complete visibility; runtime RLS role cannot be used')


def _markers(core, gov, incident):
    _incident(incident)
    for db in (core, gov):
        _visible(db)
    c = core.get(RecoveryCheckpoint, incident, with_for_update=True, populate_existing=True)
    g = gov.get(RecoveryGovCheckpoint, incident, with_for_update=True, populate_existing=True)
    if not c or not g or c.phase == 'released' or g.phase == 'released':
        raise ValueError('Incident missing or already released; do not reuse incidents')
    return c, g


def _assert_quarantined(core, gov):
    if (core.query(UserTenantScope).filter(UserTenantScope.estado == ScopeStatus.ACTIVO).count()
        or core.query(MSPMembership).filter(MSPMembership.estado == 'activo').count()
        or gov.query(Authority).filter(Authority.estado == GovStatus.ACTIVO).count()
        or gov.query(Delegation).filter(Delegation.estado == GovStatus.ACTIVO).count()
        or core.query(Visita).filter(Visita.estado.in_(['pendiente', 'activa'])).count()
        or core.query(Visita).filter(Visita.qr_token.is_not(None)).count()):
        raise ValueError('Quarantine incomplete or permissions changed; keep recovery locked')


def _fingerprint(core, gov, event):
    # Full database content of the three domains, except mutable recovery markers.
    # Includes evidence, identity, policy and occupancy changes after reconciliation.
    from backend.db.core import Base_CORE
    from backend.db.gov import Base_GOV
    from backend.db.event import Base_EVENT
    digest = hashlib.sha256()
    for db, metadata in ((core, Base_CORE.metadata), (gov, Base_GOV.metadata), (event, Base_EVENT.metadata)):
        for table in sorted(metadata.tables.values(), key=lambda t: t.name):
            if table.name.startswith('recovery_'):
                continue
            rows = sorted(json.dumps(dict(r), sort_keys=True, default=str)
                          for r in db.execute(table.select()).mappings())
            digest.update(json.dumps([table.name, rows]).encode())
    return digest.hexdigest()


def quarantine(core, gov, incident, *, actor):
    _incident(incident)
    if not actor.strip():
        raise ValueError('Recovery operator required')
    for db in (core, gov):
        _visible(db)
    c = core.get(RecoveryCheckpoint, incident, with_for_update=True, populate_existing=True)
    g = gov.get(RecoveryGovCheckpoint, incident, with_for_update=True, populate_existing=True)
    if (c and c.phase == 'released') or (g and g.phase == 'released'):
        raise ValueError('Use a fresh incident for each restoration')
    if c is None:
        c = RecoveryCheckpoint(incident_id=incident, phase='locked', report={})
        core.add(c)
    c.phase, c.release_nonce = 'locked', None
    core.commit()  # Close CORE first. A later GOV failure never opens the gate.
    if g is None:
        g = RecoveryGovCheckpoint(incident_id=incident)
        gov.add(g)
    g.phase, g.release_nonce = 'locked', None
    now = datetime.utcnow()
    counts = {
        'authorities_revoked': gov.query(Authority).filter(Authority.estado == GovStatus.ACTIVO).update(
            {Authority.estado: GovStatus.REVOCADO, Authority.revoked_at: now}),
        'delegations_revoked': gov.query(Delegation).filter(Delegation.estado == GovStatus.ACTIVO).update(
            {Delegation.estado: GovStatus.REVOCADO, Delegation.revoked_at: now}),
    }
    gov.commit()
    counts.update({
        'scopes_revoked': core.query(UserTenantScope).filter(UserTenantScope.estado == ScopeStatus.ACTIVO).update(
            {UserTenantScope.estado: ScopeStatus.REVOCADO, UserTenantScope.revoked_at: now}),
        'memberships_revoked': core.query(MSPMembership).filter(MSPMembership.estado == 'activo').update(
            {MSPMembership.estado: 'revocado', MSPMembership.revoked_at: now}),
        'visits_cancelled': core.query(Visita).filter(Visita.estado.in_(['pendiente', 'activa'])).update(
            {Visita.estado: 'cancelada'}),
        'qr_invalidated': core.query(Visita).filter(Visita.qr_token.is_not(None)).update(
            {Visita.qr_token: None, Visita.qr_vigencia: None}),
    })
    entry = {'action': 'quarantine', 'actor': actor, 'at': now.isoformat(), 'counts': counts}
    c.report = {**c.report, 'history': [*c.report.get('history', []), entry]}
    c.phase = 'quarantined'
    core.commit()
    g.phase = 'quarantined'
    gov.commit()
    _assert_quarantined(core, gov)
    return counts


def reconcile(core, gov, event, incident, *, backup_cutoff):
    c, g = _markers(core, gov, incident)
    _visible(event)
    _assert_quarantined(core, gov)
    if backup_cutoff.tzinfo is None:
        raise ValueError('Backup cutoff must include a UTC offset')
    from datetime import timezone
    cutoff = backup_cutoff.astimezone(timezone.utc).replace(tzinfo=None)
    if cutoff > datetime.utcnow():
        raise ValueError('Backup cutoff cannot be in the future')
    repaired, later = [], []
    # Includes delivered rows: CORE and EVENT may have different recovery points.
    for model in (EventOutbox, SecurityOutbox):
        for row in core.query(model).all():
            if row.payload.get('event_uid') != row.event_uid:
                raise ValueError('Outbox identifier mismatch')
            if model is EventOutbox and row.payload.get('tenant_id') != row.condominio_id:
                raise ValueError('Outbox tenant mismatch')
            if model is SecurityOutbox and row.payload.get('tenant_id') != 'PLATFORM_SECURITY':
                raise ValueError('Security outbox domain mismatch')
            missing = event.query(Event).filter_by(event_uid=row.event_uid).first() is None
            # Existing mismatched payload fails; missing payload is inserted idempotently.
            publicar_evento(event, row.payload)
            if missing:
                repaired.append(row.event_uid)
            row.delivered_at = row.delivered_at or datetime.utcnow()
            row.last_error = None
    core.commit()
    for row in event.query(Event).all():
        if not verificar_integridad_evento(row):
            raise ValueError('Event integrity mismatch')
        if row.timestamp > cutoff:
            later.append({'event_uid': row.event_uid, 'tenant_id': row.tenant_id,
                          'entity': row.entidad, 'entity_id': row.entidad_id,
                          'action': row.accion, 'result': row.resultado})
    report = {'backup_cutoff_utc': cutoff.isoformat(), 'events_after_cutoff': later,
              'repaired_event_uids': repaired, 'unknown_post_backup_access': 'all_prior_grants_revoked',
              'occupancy_requires_verification': True, 'fingerprint': _fingerprint(core, gov, event)}
    c.report = {**c.report, 'reconciliation': report}
    c.phase, g.phase = 'reconciled', 'reconciled'
    gov.commit()
    core.commit()
    return report


def release(core, gov, event, incident, *, actor, evidence_ref, occupancy_verified,
            admin_id, tenant_id):
    c, g = _markers(core, gov, incident)
    _visible(event)
    _assert_quarantined(core, gov)
    if c.phase != 'reconciled' or g.phase != 'reconciled':
        raise ValueError('Reconciliation required')
    if not actor.strip() or not evidence_ref.strip() or occupancy_verified is not True:
        raise ValueError('Operator, evidence reference and occupancy verification required')
    if _fingerprint(core, gov, event) != c.report['reconciliation']['fingerprint']:
        raise ValueError('Data changed after reconciliation; reconcile again')
    user = core.query(Usuario).filter_by(usuario_id=admin_id).one_or_none()
    tenant = core.query(Condominio).filter_by(condominio_id=tenant_id).one_or_none()
    if not user or user.rol != 'ADMIN_CONDOMINIO' or not tenant or user.condominio_id != tenant_id:
        raise ValueError('Explicit administrator must belong to the selected tenant')
    # Only this newly approved scope returns. Prior grants stay revoked.
    core.add(UserTenantScope(usuario_id=admin_id, tenant_id=tenant_id,
        access_level=AccessLevel.ADMIN_CONDOMINIO, estado=ScopeStatus.ACTIVO,
        metadata_json={'recovery_incident': incident, 'approved_by': actor}))
    nonce = uuid.uuid4().hex
    c.report = {**c.report, 'release': {'actor': actor, 'evidence_ref': evidence_ref,
        'occupancy_verified': True, 'admin_id': admin_id, 'tenant_id': tenant_id,
        'at': datetime.utcnow().isoformat()}}
    c.phase = g.phase = 'released'
    c.release_nonce = g.release_nonce = nonce
    # If CORE commit fails after GOV, phase/nonce mismatch keeps runtime closed.
    gov.commit()
    core.commit()
    return {'incident_id': incident, 'phase': 'released', 'admin_id': admin_id, 'tenant_id': tenant_id}
