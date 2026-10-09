"""Turno completo -> outbox -> EVENT -> consulta administrativa HTTP."""
from sqlalchemy.orm import sessionmaker
from backend.db.core import Visita, EventOutbox
from backend.db.event import Event
from backend.services.event_outbox import enviar_pendientes
from tests.test_reglas_acceso import setup, headers, rules
from tests.test_simulacion_reloj import reloj, crear


def test_turno_y_entrega_sin_duplicados(client, setup, reloj, db_event_engine):
    rules(client, exigir_autorizacion=True, exigir_proposito=True)
    visits = [crear(client, setup, reloj, t) for t in
              ['visita_personal', 'entrega', 'proveedor', 'visita_personal', 'entrega']]
    guard = headers('guard', 'GUARDIA')
    admin = headers('admin', 'ADMIN_CONDOMINIO')
    assert client.patch(f'/visitas/{visits[3][0].visita_id}/cancelar',
                        headers=headers('resident', 'RESIDENTE')).status_code == 200
    reloj.avanzar(minutes=30)
    for row, url in visits[:3]:
        assert client.get(url, headers=guard).status_code == 200
    assert client.get(visits[0][1], headers=guard).status_code == 400
    assert client.get(visits[3][1], headers=guard).status_code == 400
    reloj.avanzar(hours=2)
    assert client.get(visits[4][1], headers=guard).status_code == 400
    for row, _ in visits[:2]:
        assert client.patch(f'/visitas/{row.visita_id}/salida', headers=guard).status_code == 200
    listing = client.get('/visitas/condominio/a', headers=guard).json()
    assert sum(v['estado'] == 'entrada_registrada' for v in listing) == 1
    assert sum(v['estado'] == 'salida_registrada' for v in listing) == 2
    before = client.get('/bitacora/a', headers=admin).json()
    assert before['items'] == [] and before['pendientes_entrega_condominio'] > 0
    factory = sessionmaker(bind=db_event_engine)
    count = setup.query(EventOutbox).count()
    assert enviar_pendientes(setup, 'a', factory, now=reloj.utcnow(), limit=100) == count
    assert enviar_pendientes(setup, 'a', factory, now=reloj.utcnow(), limit=100) == 0
    with factory() as other:
        other.add(Event(event_uid="foreign", identity_id="foreign-guard", tenant_id="b",
                        tipo_evento="registrar", entidad="visita", entidad_id="foreign-visit",
                        accion="registrar", resultado="exito", timestamp=reloj.utcnow(), hash_evento="foreign-hash"))
        other.commit()
    result = client.get('/bitacora/a', headers=admin)
    assert result.status_code == 200
    data = result.json()
    assert data['pendientes_entrega_condominio'] == 0
    events = data['items']
    assert len({e['event_uid'] for e in events}) == len(events)
    for row, _ in visits[:2]:
        exits = [e for e in events if e['visita_id'] == row.visita_id and e['estado'] == 'salida_registrada']
        assert len(exits) == 1 and exits[0]['actor_id'] == 'guard'
        assert exits[0]['autorizada_por'] == 'resident'
    assert any(e['motivo'] == 'QR expirado' for e in events)
    assert any('cancelada' in (e['motivo'] or '').lower() for e in events)
    assert any(e['motivo'] == 'QR ya utilizado' for e in events)
    assert all(e['fecha'].endswith('Z') or e['fecha'].endswith('+00:00') for e in events)
    assert 'foreign' not in result.text
    assert 'session_hash' not in result.text and 'qr_token' not in result.text
    first = client.get('/bitacora/a?limite=2', headers=admin).json()
    second = client.get(f"/bitacora/a?limite=2&antes_id={first['siguiente']}", headers=admin).json()
    assert not {e['id'] for e in first['items']} & {e['id'] for e in second['items']}
    filtered = client.get(f'/bitacora/a?visita_id={visits[0][0].visita_id}', headers=admin).json()
    assert all(e['visita_id'] == visits[0][0].visita_id for e in filtered['items'])
    assert client.get('/bitacora/b', headers=admin).status_code == 403
    assert client.get('/bitacora/a', headers=guard).status_code == 403
    assert client.get('/bitacora/a', headers=headers('resident','RESIDENTE')).status_code == 403
    assert client.get('/bitacora/a?limite=101', headers=admin).status_code == 422
