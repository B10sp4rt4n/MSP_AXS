"""Integración de #30/#31, permisos vigentes y proveedores por HTTP."""
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from backend.db.core import MSP, Condominio, Usuario, MSPMembership, UserTenantScope, ScopeStatus
from backend.services.event_outbox import enviar_pendientes
from tests.test_reglas_acceso import setup, headers
from tests.test_simulacion_reloj import reloj, crear


def test_integracion_bitacora_resumen_y_revocacion(client, setup, reloj, db_event_engine):
    start = reloj.instant
    row, url = crear(client, setup, reloj)
    guard = headers('guard','GUARDIA')  # Se conserva exactamente el mismo JWT.
    admin = headers('admin','ADMIN_CONDOMINIO')
    reloj.avanzar(minutes=30)
    assert client.get(url, headers=guard).status_code == 200
    reloj.avanzar(minutes=10)
    assert client.patch(f'/visitas/{row.visita_id}/salida',headers=guard).status_code == 200
    reloj.avanzar(seconds=1)
    params={'inicio':start.isoformat(),'fin':reloj.instant.isoformat()}
    summary=client.get('/visitas/resumen-turno/a',params=params,headers=admin).json()
    assert summary['turno']['entradas'] == summary['turno']['salidas'] == 1
    assert summary['actual']['dentro'] == 0
    def outage():
        raise ConnectionError('simulated')
    assert enviar_pendientes(setup,'a',outage,now=reloj.utcnow(),limit=100) == 0
    before=client.get('/bitacora/a',headers=admin).json()
    assert before['pendientes_entrega_condominio'] > 0 and before['items'] == []
    reloj.avanzar(minutes=5)
    factory=sessionmaker(bind=db_event_engine)
    assert enviar_pendientes(setup,'a',factory,now=reloj.utcnow(),limit=100) > 0
    assert enviar_pendientes(setup,'a',factory,now=reloj.utcnow(),limit=100) == 0
    events=client.get('/bitacora/a',headers=admin).json()
    assert events['pendientes_entrega_condominio'] == 0
    assert sum(e['estado']=='entrada_registrada' for e in events['items']) == summary['turno']['entradas']
    assert sum(e['estado']=='salida_registrada' for e in events['items']) == summary['turno']['salidas']
    _, second_url=crear(client,setup,reloj)
    reloj.avanzar(minutes=30)
    scope=setup.query(UserTenantScope).filter_by(usuario_id='guard').one()
    scope.estado=ScopeStatus.REVOCADO
    setup.commit()
    assert client.get(second_url,headers=guard).status_code == 403
    assert client.get('/visitas/condominio/a',headers=guard).status_code == 403
    assert client.get('/visitas/resumen-turno/a',params=params,headers=guard).status_code == 403


def test_dos_proveedores_cuatro_condominios(client,setup,reloj):
    # a,b pertenecen al MSP m; c,d pertenecen al MSP n.
    setup.add(MSP(msp_id='n',nombre='Segundo proveedor'));setup.flush()
    setup.add_all([Condominio(condominio_id=t,msp_id='n',nombre=t) for t in ('c','d')])
    for actor,provider in [('provider_m','m'),('provider_n','n')]:
        setup.add(Usuario(usuario_id=actor,email=actor+'@test.local',rol='MSP_ADMIN'))
        setup.flush();setup.add(MSPMembership(usuario_id=actor,msp_id=provider))
    setup.commit()
    params={'inicio':(reloj.instant-timedelta(hours=1)).isoformat(),'fin':reloj.instant.isoformat()}
    for actor,allowed in [('provider_m',{'a','b'}),('provider_n',{'c','d'})]:
        token=headers(actor,'MSP_ADMIN')
        for tenant in ['a','b','c','d']:
            for url in [f'/visitas/condominio/{tenant}',f'/bitacora/{tenant}',f'/visitas/resumen-turno/{tenant}']:
                result=client.get(url,params=params,headers=token)
                assert result.status_code == (200 if tenant in allowed else 403), (actor,url,result.text)
    token=headers('provider_m','MSP_ADMIN')
    member=setup.query(MSPMembership).filter_by(usuario_id='provider_m').one()
    member.estado='revocado';setup.commit()
    for url in ['/visitas/condominio/a','/bitacora/a','/visitas/resumen-turno/a']:
        assert client.get(url,params=params,headers=token).status_code == 403
