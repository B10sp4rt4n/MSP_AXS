"""Explicit grant provenance and atomic, per-condominium provider offboarding."""
from datetime import datetime
from fastapi import HTTPException
from backend.db.core import Condominio, UserTenantScope, ScopeStatus, AccessLevel, EventOutbox, ProviderContract
from backend.core.scope.msp_boundary import require_platform_operator, active_msp_ids, is_platform_operator
from backend.core.tenant.context import _set_postgres_tenant
from backend.core.scope.provider_contract import current_contract
from backend.services.event_outbox import encolar_evento, contexto_evento


def lock_condo(db, tenant):
    row=db.query(Condominio).filter_by(condominio_id=tenant).populate_existing().with_for_update().one_or_none()
    if row is None:
        raise HTTPException(404, 'Condominio no encontrado')
    _set_postgres_tenant(db, tenant)
    return row


def grant_origin(db, gov, actor, condo):
    """Capture effective issuer authority, never infer ownership from target role."""
    contract=current_contract(db, condo.condominio_id)
    contract_tag={"contract_id":contract.contract_id} if contract else {}
    base={'version':1,'recorded_by':actor.usuario_id,'recorded_at':datetime.utcnow().isoformat()}
    if is_platform_operator(gov, actor):
        return {**base,'kind':'unknown'}
    if condo.msp_id and condo.msp_id in active_msp_ids(db, actor):
        return {**base,'kind':'msp','msp_id':condo.msp_id,**contract_tag}
    origins=[(s.metadata_json or {}).get('grant_origin', {}) for s in db.query(UserTenantScope).filter_by(
        usuario_id=actor.usuario_id,tenant_id=condo.condominio_id,estado=ScopeStatus.ACTIVO,
        access_level=AccessLevel.ADMIN_CONDOMINIO)]
    if any(o.get('kind')=='condominio' for o in origins):
        return {**base,'kind':'condominio'}
    if condo.msp_id and any(o.get('kind')=='msp' and o.get('msp_id')==condo.msp_id for o in origins):
        return {**base,'kind':'msp','msp_id':condo.msp_id,**contract_tag}
    return {**base,'kind':'unknown'}


def classify(db, gov, actor, tenant, scope_id, kind, msp_id, evidence_ref, token):
    require_platform_operator(gov,actor)
    condo=lock_condo(db,tenant)
    row=db.query(UserTenantScope).filter_by(id=scope_id,tenant_id=tenant).one_or_none()
    if row is None:
        raise HTTPException(404,'Permiso no encontrado')
    if kind=='msp' and (not msp_id or msp_id!=condo.msp_id):
        raise HTTPException(409,'El proveedor no coincide con la relación vigente')
    if kind=='condominio' and msp_id is not None:
        raise HTTPException(422,'Un permiso local no lleva proveedor')
    before=(row.metadata_json or {}).get('grant_origin',{})
    if before.get('kind') in ('msp','condominio'):
        if before.get('kind')==kind and before.get('msp_id')==msp_id:
            return {'scope_id':scope_id,'origin':before,'unchanged':True}
        raise HTTPException(409,'Procedencia ya registrada; revocar y otorgar un permiso nuevo para cambiarla')
    origin={'version':1,'kind':kind,'recorded_by':actor.usuario_id,
            'recorded_at':datetime.utcnow().isoformat(),'evidence_ref':evidence_ref}
    if msp_id:
        origin['msp_id']=msp_id
        contract=current_contract(db,tenant)
        if contract:
            origin['contract_id']=contract.contract_id
    row.metadata_json={**(row.metadata_json or {}),'grant_origin':origin}
    uid=encolar_evento(db,tenant,str(scope_id),contexto_evento(actor,token,entidad='scope',accion='registrar_procedencia'),
                      metadata={'before':before,'after':origin})
    db.commit()
    return {'scope_id':scope_id,'origin':origin,'event_uid':uid}


def inventory(db, gov, actor, tenant):
    require_platform_operator(gov,actor)
    condo=lock_condo(db,tenant)
    return {'condominio_id':tenant,'msp_id':condo.msp_id,'scopes':[
        {'scope_id':s.id,'usuario_id':s.usuario_id,'estado':s.estado.value,
         'origin':(s.metadata_json or {}).get('grant_origin',{'kind':'unknown'})}
        for s in db.query(UserTenantScope).filter_by(tenant_id=tenant).order_by(UserTenantScope.id)]}


def offboard(db, gov, actor, tenant, msp_id, reason, token, contract_id=None):
    require_platform_operator(gov,actor)
    condo=lock_condo(db,tenant)
    contract=current_contract(db,tenant)
    if contract_id:
        selected=db.query(ProviderContract).filter_by(contract_id=contract_id,condominio_id=tenant,msp_id=msp_id).first()
        if not selected:
            raise HTTPException(409,'Contrato esperado no coincide')
        if selected.closed_at is not None:
            return {**selected.close_receipt,'event_uid':selected.close_event_uid,'unchanged':True}
        if not contract or contract.contract_id!=contract_id:
            raise HTTPException(409,'Contrato esperado no está vigente')
    elif contract:
        raise HTTPException(409,'contract_id requerido para cerrar una relación versionada')
    else:
        previous=db.query(EventOutbox).filter(EventOutbox.condominio_id==tenant,
            EventOutbox.payload['entidad'].as_string()=='proveedor',
            EventOutbox.payload['accion'].as_string()=='baja_proveedor',
            EventOutbox.payload['entidad_id'].as_string()==msp_id).order_by(EventOutbox.created_at.desc()).first()
        if condo.msp_id is None and previous:
            return {**previous.payload['metadata_json'],'event_uid':previous.event_uid,'unchanged':True}
        if previous:
            raise HTTPException(409,'Relación reutilizada; abrir un contrato versionado')
    if condo.msp_id!=msp_id:
        raise HTTPException(409,'El proveedor esperado no coincide con el actual')
    scopes=db.query(UserTenantScope).filter(UserTenantScope.tenant_id==tenant,
                                           UserTenantScope.estado!=ScopeStatus.REVOCADO).all()
    unknown=[]; revoke=[]; preserve=[]
    for scope in scopes:
        origin=(scope.metadata_json or {}).get('grant_origin',{})
        if origin.get('kind')=='condominio':
            preserve.append(scope.id)
        elif (origin.get('kind')=='msp' and origin.get('msp_id')==msp_id
              and origin.get('contract_id')==(contract.contract_id if contract else None)):
            revoke.append(scope)
        else:
            unknown.append(scope.id)
    if unknown:
        raise HTTPException(409,{'message':'Resolver procedencia antes de la baja','scope_ids':unknown})
    now=datetime.utcnow()
    for scope in revoke:
        scope.estado=ScopeStatus.REVOCADO
        scope.revoked_at=now
    condo.msp_id=None
    result={'condominio_id':tenant,'msp_id':msp_id,'revoked_scope_ids':[s.id for s in revoke],
            'preserved_scope_ids':preserve,'reason':reason,'authorized_by':actor.usuario_id,'at':now.isoformat()}
    if contract:
        result.update(contract_id=contract.contract_id,version=contract.version)
        contract.closed_at=now
        contract.close_receipt=result
    # Business mutation and durable audit share ONE CORE transaction.
    uid=encolar_evento(db,tenant,msp_id,contexto_evento(actor,token,entidad='proveedor',accion='baja_proveedor'),metadata=result)
    if contract:
        contract.close_event_uid=uid
    db.commit()
    return {**result,'event_uid':uid,'unchanged':False}
