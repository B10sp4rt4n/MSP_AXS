"""Explicit openings and new staff grants; closed contracts never reopen."""
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from backend.db.core import ProviderContract, MSP, Usuario, UserTenantScope, ScopeStatus, AccessLevel
from backend.core.scope.msp_boundary import require_platform_operator
from backend.core.scope.provider_contract import current_contract
from backend.services.provider_offboarding import lock_condo
from backend.services.event_outbox import encolar_evento, contexto_evento


def snapshot(row):
    return {key: getattr(row, key) for key in (
        'contract_id', 'condominio_id', 'msp_id', 'version', 'evidence_ref',
        'opened_by', 'opened_at', 'closed_at', 'open_event_uid', 'close_event_uid')}


def history(db, gov, actor, tenant):
    require_platform_operator(gov, actor)
    lock_condo(db, tenant)
    return [snapshot(row) for row in db.query(ProviderContract).filter_by(
        condominio_id=tenant).order_by(ProviderContract.version)]


def open_contract(db, gov, actor, tenant, contract_id, msp_id, evidence_ref, token):
    require_platform_operator(gov, actor)
    condo = lock_condo(db, tenant)
    previous = db.query(ProviderContract).filter_by(contract_id=contract_id).first()
    if previous:
        if (previous.condominio_id, previous.msp_id, previous.evidence_ref) != (tenant, msp_id, evidence_ref):
            raise HTTPException(409, 'Identificador utilizado con otros datos')
        return {**snapshot(previous), 'unchanged': True}
    if condo.msp_id is not None or current_contract(db, tenant):
        raise HTTPException(409, 'Cerrar la relación vigente antes de abrir otra')
    if not db.query(MSP).filter_by(msp_id=msp_id).first():
        raise HTTPException(404, 'Proveedor no encontrado')
    unresolved = [s.id for s in db.query(UserTenantScope).filter(
        UserTenantScope.tenant_id == tenant, UserTenantScope.estado != ScopeStatus.REVOCADO)
        if (s.metadata_json or {}).get('grant_origin', {}).get('kind') != 'condominio']
    if unresolved:
        raise HTTPException(409, {'message': 'Resolver permisos previos antes del alta', 'scope_ids': unresolved})
    version = (db.query(func.max(ProviderContract.version)).filter_by(condominio_id=tenant).scalar() or 0) + 1
    uid = encolar_evento(db, tenant, contract_id, contexto_evento(actor, token,
        entidad='contrato_proveedor', accion='abrir_contrato'), metadata={
            'contract_id': contract_id, 'msp_id': msp_id, 'version': version, 'evidence_ref': evidence_ref})
    row = ProviderContract(contract_id=contract_id, condominio_id=tenant, msp_id=msp_id,
        version=version, evidence_ref=evidence_ref, opened_by=actor.usuario_id, open_event_uid=uid)
    db.add(row)
    condo.msp_id = msp_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Identificador o relación ocupados por otra solicitud')
    return {**snapshot(row), 'unchanged': False}


def grant_staff(db, gov, actor, tenant, contract_id, user_id, evidence_ref, token):
    require_platform_operator(gov, actor)
    condo = lock_condo(db, tenant)
    contract = current_contract(db, tenant)
    if not contract or contract.contract_id != contract_id or contract.msp_id != condo.msp_id:
        raise HTTPException(409, 'Contrato no vigente')
    user = db.query(Usuario).filter_by(usuario_id=user_id).first()
    if not user or user.rol not in ('GUARDIA', 'ADMIN_CONDOMINIO') or user.condominio_id != tenant:
        raise HTTPException(409, 'Requiere personal existente de este condominio')
    for scope in db.query(UserTenantScope).filter_by(usuario_id=user_id, tenant_id=tenant, estado=ScopeStatus.ACTIVO):
        origin = (scope.metadata_json or {}).get('grant_origin', {})
        if origin.get('contract_id') == contract_id and scope.access_level == AccessLevel[user.rol]:
            return {'scope_id': scope.id, 'unchanged': True}
        raise HTTPException(409, 'La identidad ya tiene un permiso activo distinto')
    scope = UserTenantScope(usuario_id=user_id, tenant_id=tenant, access_level=AccessLevel[user.rol],
        metadata_json={'grant_origin': {'version': 2, 'kind': 'msp', 'msp_id': contract.msp_id,
            'contract_id': contract_id, 'recorded_by': actor.usuario_id, 'evidence_ref': evidence_ref}})
    db.add(scope)
    db.flush()
    uid = encolar_evento(db, tenant, str(scope.id), contexto_evento(actor, token,
        entidad='scope', accion='otorgar_permiso_contrato'), metadata=scope.metadata_json)
    db.commit()
    return {'scope_id': scope.id, 'event_uid': uid, 'unchanged': False}
