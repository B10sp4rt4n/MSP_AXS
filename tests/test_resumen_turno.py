from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from backend.db.core import Visita, EventOutbox
from backend.db.event import Event
from backend.services.resumen_turno import permiso_temporal
from backend.services.event_outbox import enviar_pendientes
from tests.test_reglas_acceso import setup, headers
from tests.test_simulacion_reloj import reloj, crear


def test_turno_vencimiento_y_recuperacion(client, setup, reloj, db_event_engine):
    start = reloj.instant
    visits = [crear(client, setup, reloj, kind) for kind in
              ['visita_personal','entrega','proveedor','visita_personal','entrega']]
    guard = headers('guard','GUARDIA')
    assert permiso_temporal(visits[0][0], reloj.instant) == 'por_iniciar'
    assert client.patch(f'/visitas/{visits[3][0].visita_id}/cancelar',
                        headers=headers('resident','RESIDENTE')).status_code == 200
    reloj.avanzar(minutes=30)
    assert permiso_temporal(visits[0][0], reloj.instant) == 'vigente'
    for _, url in visits[:3]:
        assert client.get(url, headers=guard).status_code == 200
    assert client.get(visits[0][1], headers=guard).status_code == 400
    reloj.avanzar(hours=2)
    assert client.get(visits[4][1], headers=guard).status_code == 400
    for row, _ in visits[:2]:
        assert client.patch(f'/visitas/{row.visita_id}/salida', headers=guard).status_code == 200
    reloj.avanzar(seconds=1)
    params = {'inicio':start.isoformat(), 'fin':reloj.instant.isoformat()}
    url = '/visitas/resumen-turno/a'
    response = client.get(url, params=params, headers=guard)
    assert response.status_code == 200, response.text
    data = response.json()
    turn = data['turno']
    assert (turn['dentro_al_inicio'],turn['entradas'],turn['salidas'],turn['dentro_al_cierre']) == (0,3,2,1)
    assert turn['reconciliado'] is True
    assert turn['cancelaciones_registradas'] == 1 and turn['rechazos_registrados'] == 2
    assert data['actual']['permisos_pendientes']['vencido'] == 1
    setup.refresh(visits[4][0])
    assert visits[4][0].estado == 'pendiente'  # historial intacto
    def unavailable():
        raise ConnectionError('simulated outage')
    count = setup.query(EventOutbox).count()
    assert enviar_pendientes(setup, 'a', unavailable, limit=100, now=reloj.utcnow()) == 0
    after_failure = client.get(url, params=params, headers=guard).json()
    assert after_failure['turno'] == turn
    reloj.avanzar(minutes=5)
    factory = sessionmaker(bind=db_event_engine)
    assert enviar_pendientes(setup, 'a', factory, limit=100, now=reloj.utcnow()) == count
    assert enviar_pendientes(setup, 'a', factory, limit=100, now=reloj.utcnow()) == 0
    with factory() as db:
        uids = [r.event_uid for r in setup.query(EventOutbox).all()]
        assert db.query(Event).filter(Event.event_uid.in_(uids)).count() == count
    restored = client.get(url, params=params, headers=guard).json()['turno']
    assert restored == {**turn, 'eventos_pendientes_entrega':0}
    assert client.get('/visitas/resumen-turno/b', params=params, headers=guard).status_code == 403
    assert client.get(url, params=params, headers=headers('resident','RESIDENTE')).status_code == 403
    assert client.get(url, params={'inicio':'2030-01-15T18:00:00','fin':params['fin']}, headers=guard).status_code == 422
    assert client.get(url, params={'inicio':params['fin'],'fin':params['inicio']}, headers=guard).status_code == 422


def test_arrastre_y_limite_exclusivo(client, setup, reloj):
    start = reloj.utcnow()
    setup.add_all([
        Visita(visita_id='previous',condominio_id='a',nombre_visitante='Anterior',estado='salida_registrada',
               entrada_registrada_en=start-timedelta(hours=1),salida_registrada_en=start+timedelta(minutes=10)),
        Visita(visita_id='boundary',condominio_id='a',nombre_visitante='Límite',estado='entrada_registrada',
               entrada_registrada_en=start+timedelta(hours=1)),
        Visita(visita_id='foreign',condominio_id='b',nombre_visitante='Otro',estado='entrada_registrada',
               entrada_registrada_en=start-timedelta(hours=1)),
    ])
    setup.commit()
    begin = reloj.instant
    reloj.avanzar(hours=1)
    data = client.get('/visitas/resumen-turno/a',params={'inicio':begin.isoformat(),'fin':reloj.instant.isoformat()},
                      headers=headers('guard','GUARDIA')).json()
    assert data['turno']['dentro_al_inicio'] == 1
    assert data['turno']['entradas'] == 0  # entrada exactamente al fin corresponde al turno siguiente
    assert data['turno']['salidas'] == 1
    assert data['turno']['dentro_al_cierre'] == 0
    assert data['turno']['reconciliado'] is True
    assert data['actual']['dentro'] == 1


def test_limites_permiso_y_estados_terminales(reloj):
    from types import SimpleNamespace
    v = SimpleNamespace(estado='pendiente',entrada_registrada_en=None,salida_registrada_en=None,
                        qr_token='test',qr_vigencia=reloj.utcnow()+timedelta(hours=2),
                        vigencia=reloj.utcnow()+timedelta(hours=1),autorizada_por='resident')
    assert permiso_temporal(v,reloj.instant+timedelta(minutes=30)-timedelta(microseconds=1)) == 'por_iniciar'
    assert permiso_temporal(v,reloj.instant+timedelta(minutes=30)) == 'vigente'
    assert permiso_temporal(v,reloj.instant+timedelta(hours=2)-timedelta(microseconds=1)) == 'vigente'
    assert permiso_temporal(v,reloj.instant+timedelta(hours=2)) == 'vencido'
    v.estado='cancelada'
    assert permiso_temporal(v,reloj.instant+timedelta(days=1)) == 'cancelado'
    v.estado='entrada_registrada';v.entrada_registrada_en=reloj.utcnow()
    assert permiso_temporal(v,reloj.instant+timedelta(days=1)) == 'utilizado'
    v.estado='pendiente';v.entrada_registrada_en=None;v.qr_token=None;v.autorizada_por=None
    assert permiso_temporal(v,reloj.instant) == 'sin_permiso_temporal'
