"""Synthetic-only retention lifecycle: real route auth and durable DB transactions."""
import hashlib
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker
from backend.db.core import IdentityRetention, Evidencia, Visita, EventOutbox
from backend.services import identificacion_conservacion as retention
from tests.test_identificaciones import setup, send
from tests.test_destinos_visitas import people, headers


@pytest.fixture
def lifecycle(client, setup, monkeypatch):
    db,store=setup
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('NEON_DEV_ENDPOINT','ep-withered-resonance-b59tusv3')
    monkeypatch.setenv('AXS_ID_RETENTION_SCHEMA_ENABLED','true')
    monkeypatch.setenv('AXS_ID_RETENTION_PILOT_ENABLED','true')
    monkeypatch.setattr(retention,'TENANTS',{'a1','b1'})
    visit=db.query(Visita).filter_by(visita_id='va').one()
    visit.nombre_visitante=retention.VISIT_PREFIX+'A'
    db.commit()
    from tests.test_identificaciones import jpeg
    from backend.services.identificacion_service import normalize_image
    import io
    from types import SimpleNamespace
    data=normalize_image(SimpleNamespace(file=io.BytesIO(jpeg())))
    monkeypatch.setattr(retention,'SYNTHETIC_HASH',hashlib.sha256(data).hexdigest())
    upload=send(client,name=retention.LABEL,front=jpeg())
    # send normally supplies a red back; synthetic pilot requires identical known blue sides.
    assert upload.status_code==503
    from tests.test_identificaciones import jpeg as image
    import uuid
    upload=client.post('/identificaciones/va?condominio_id=a1',headers=headers('guard','GUARDIA'),
        data={'nombre':retention.LABEL,'captura_id':str(uuid.uuid4())},
        files={side:(side+'.jpg',image(),'image/jpeg') for side in ('frente','reverso')})
    assert upload.status_code==200,upload.text
    def read(self,key):
        if key not in self.assets: raise HTTPException(404,'missing')
        return self.assets[key]
    store.read=read
    factory=sessionmaker(bind=db.get_bind())
    return db,store,factory,upload.json()['evidencias']


def listing(client):
    return client.get('/identificaciones/va?condominio_id=a1',headers=headers('guard','GUARDIA'))


def photo(client,eid):
    return client.get(f'/identificaciones/va/{eid}?condominio_id=a1',headers=headers('guard','GUARDIA'))


def hold(client,**changes):
    data={'hasta':(datetime.now(timezone.utc)+timedelta(days=3)).isoformat(),'responsable':'Operador de prueba','incidencia':'TEST-1','motivo':'Incidencia ficticia'}
    data.update(changes)
    return client.put('/identificaciones/va/conservacion/excepcion?condominio_id=a1',json=data,headers=headers('admin','ADMIN_CONDOMINIO'))


def expire(db):
    row=db.query(IdentityRetention).one()
    row.captured_at=row.base_at=datetime.utcnow()-timedelta(days=31)
    row.expires_at=row.next_attempt_at=datetime.utcnow()-timedelta(days=1)
    db.commit()
    return row


def test_boundary_and_stop_never_restore_access(client,lifecycle,monkeypatch):
    db,store,factory,rows=lifecycle
    row=db.query(IdentityRetention).one()
    cutoff=row.expires_at
    assert retention.state(row,cutoff-timedelta(microseconds=1))=='vigente'
    assert retention.state(row,cutoff)=='vencida'
    expire(db)
    assert listing(client).json()['estado']=='vencida'
    assert listing(client).json()['evidencias']==[]
    monkeypatch.setenv('AXS_ID_RETENTION_PILOT_ENABLED','false')
    assert photo(client,rows[0]['evidencia_id']).status_code==410
    assert hold(client).status_code==404
    assert store.assets


def test_hold_caducity_and_release(client,lifecycle):
    db,store,factory,rows=lifecycle
    expire(db)
    assert hold(client).status_code==200
    assert listing(client).json()['conservacion']['estado']=='excepcion'
    assert photo(client,rows[0]['evidencia_id']).status_code==200
    assert retention.claim(db,'a1')==[]
    row=db.query(IdentityRetention).one()
    row.hold_until=datetime.utcnow()-timedelta(seconds=1)
    db.commit()
    assert photo(client,rows[0]['evidencia_id']).status_code==410
    claims=retention.claim(db,'a1')
    assert len(claims)==1
    assert hold(client).status_code==409
    assert retention.process(factory,'a1',*claims[0],store=store())
    assert not store.assets


@pytest.mark.parametrize('change',[{'responsable':' '},{'incidencia':''},{'motivo':''},{'hasta':'2020-01-01T00:00:00Z'},{'hasta':'2030-01-01T00:00:00'}])
def test_hold_requires_finite_explicit_details(client,lifecycle,change):
    assert hold(client,**change).status_code==422


@pytest.mark.parametrize('user,role,tenant',[('guard','GUARDIA','a1'),('admin','ADMIN_CONDOMINIO','b1'),('resident','RESIDENTE','a1')])
def test_hold_access_denied(client,lifecycle,user,role,tenant):
    data={'hasta':'2030-01-01T00:00:00Z','responsable':'Test','incidencia':'Test','motivo':'Test'}
    assert client.put(f'/identificaciones/va/conservacion/excepcion?condominio_id={tenant}',headers=headers(user,role),json=data).status_code==403


def test_complete_pair_no_duplicate_claim_or_audit(client,lifecycle):
    db,store,factory,rows=lifecycle
    expire(db)
    claims=retention.claim(db,'a1')
    assert retention.claim(db,'a1')==[]
    assert retention.process(factory,'a1',*claims[0],store=store())
    db.expire_all()
    row=db.query(IdentityRetention).one()
    assert row.state=='purged' and not row.snapshots
    assert not store.assets and retention.claim(db,'a1')==[]
    assert not retention.process(factory,'a1',*claims[0],store=store())
    events=[r.payload for r in db.query(EventOutbox).all()]
    assert sum(e['accion']=='eliminar_identificacion' for e in events)==1
    assert all(retention.LABEL not in str(e) and 'axs-identificaciones/' not in str(e) for e in events)
    for row in db.query(Evidencia).all():
        assert row.archivo_url is None and row.hash_sha256 is None and 'nombre' not in row.metadata_json
    assert db.query(Visita).filter_by(visita_id='va').one().estado == 'pendiente'


def test_partial_failure_retry_same_operation(client,lifecycle):
    db,store,factory,rows=lifecycle
    expire(db)
    claims=retention.claim(db,'a1')
    original=store.delete
    calls=[]
    def fail(self,key):
        calls.append(key)
        if len(calls)==2: raise RuntimeError('synthetic outage')
        original(self,key)
    store.delete=fail
    assert not retention.process(factory,'a1',*claims[0],store=store())
    db.expire_all()
    row=db.query(IdentityRetention).one()
    operation=row.operation_id
    assert row.state=='pending' and row.attempts==1 and len(store.assets)==1
    assert photo(client,rows[1]['evidencia_id']).status_code==410
    assert retention.claim(db,'a1')==[]
    store.delete=original
    future=row.next_attempt_at+timedelta(seconds=1)
    claims=retention.claim(db,'a1',now=future)
    assert retention.process(factory,'a1',*claims[0],now=future,store=store())
    db.expire_all()
    assert db.query(IdentityRetention).one().operation_id==operation
    assert not store.assets


def test_claim_loss_and_tamper_never_delete(client,lifecycle):
    db,store,factory,rows=lifecycle
    expire(db)
    claims=retention.claim(db,'a1')
    assert not retention.process(factory,'a1',claims[0][0],'wrong-token',store=store())
    before=dict(store.assets)
    store.assets[next(iter(store.assets))]=b'not a synthetic fixture'
    assert not retention.process(factory,'a1',*claims[0],store=store())
    assert len(store.assets)==len(before)


def test_completion_event_failure_retries_without_resurrection(client,lifecycle,monkeypatch):
    db,store,factory,rows=lifecycle
    expire(db)
    claims=retention.claim(db,'a1')
    original=retention.event
    def fail(db,row,action,**kwargs):
        if action=='eliminar_identificacion': raise RuntimeError('audit failure')
        return original(db,row,action,**kwargs)
    monkeypatch.setattr(retention,'event',fail)
    assert not retention.process(factory,'a1',*claims[0],store=store())
    assert not store.assets
    db.expire_all()
    row=db.query(IdentityRetention).one()
    assert row.state=='pending'
    assert photo(client,rows[0]['evidencia_id']).status_code==410
    monkeypatch.setattr(retention,'event',original)
    future=row.next_attempt_at+timedelta(seconds=1)
    claims=retention.claim(db,'a1',now=future)
    assert retention.process(factory,'a1',*claims[0],now=future,store=store())


def test_late_exit_cannot_extend_and_early_exit_is_audited(client,lifecycle):
    db,store,factory,rows=lifecycle
    visit=db.query(Visita).filter_by(visita_id='va').one()
    visit.estado='salida_registrada';visit.salida_registrada_en=datetime.utcnow()+timedelta(seconds=1)
    db.commit()
    listing(client)
    row=db.query(IdentityRetention).one()
    assert row.base_at==visit.salida_registrada_en
    expire(db)
    previous=row.expires_at
    visit.salida_registrada_en=datetime.utcnow()
    db.commit()
    assert listing(client).json()['estado']=='vencida'
    assert row.expires_at==previous


def test_release_and_anonymous_denial(client,lifecycle):
    db,store,factory,rows=lifecycle
    expire(db)
    assert hold(client).status_code==200
    route='/identificaciones/va/conservacion/excepcion?condominio_id=a1'
    assert client.delete(route).status_code==401
    assert client.delete(route,headers=headers('admin','ADMIN_CONDOMINIO')).status_code==200
    assert photo(client,rows[0]['evidencia_id']).status_code==410
    event=db.query(EventOutbox).all()[-1].payload
    assert event['accion']=='liberar_conservacion_identificacion' and event['entidad']=='visita'
    assert event['metadata_json']['incidencia']=='TEST-1'


def test_expiry_rechecked_after_download(client,lifecycle,monkeypatch):
    db,store,factory,rows=lifecycle
    def read(self,key):
        expire(db)
        return self.assets[key]
    store.read=read
    response=photo(client,rows[0]['evidencia_id'])
    assert response.status_code==410 and not response.headers['content-type'].startswith('image/')


def test_intent_failure_never_calls_storage(client,lifecycle,monkeypatch):
    db,store,factory,rows=lifecycle
    expire(db)
    def fail(*args,**kwargs): raise RuntimeError('durable intent unavailable')
    monkeypatch.setattr(retention,'event',fail)
    with pytest.raises(RuntimeError): retention.claim(db,'a1')
    db.rollback()
    assert len(store.assets)==2 and db.query(IdentityRetention).one().state=='active'


def test_exit_updates_retention_in_exit_transaction(client,lifecycle):
    db,store,factory,rows=lifecycle
    from backend.services.visita_service import registrar_salida
    visit=db.query(Visita).filter_by(visita_id='va').one()
    visit.estado='entrada_registrada';visit.entrada_registrada_en=datetime.utcnow()-timedelta(minutes=1)
    db.commit()
    result=registrar_salida(db,'va')
    row=db.query(IdentityRetention).one()
    assert row.base_at==result.salida_registrada_en
    assert row.expires_at==result.salida_registrada_en+timedelta(days=30)


@pytest.mark.parametrize('env,value',[('APP_ENV','production'),('NEON_DEV_ENDPOINT','wrong'),('AXS_ID_RETENTION_PILOT_ENABLED','false')])
def test_worker_gate_never_deletes(client,lifecycle,monkeypatch,env,value):
    db,store,factory,rows=lifecycle
    expire(db)
    monkeypatch.setenv(env,value)
    with pytest.raises(HTTPException) as exc: retention.claim(db,'a1')
    assert exc.value.status_code==404 and len(store.assets)==2


def test_expired_capture_retry_does_not_return_transcribed_name(client,lifecycle):
    db,store,factory,rows=lifecycle
    expire(db)
    # An upload must not provide an alternate route to an expired identity.
    assert send(client,name=retention.LABEL).status_code==410


@pytest.mark.parametrize('status',[304,429,500,503])
def test_provider_uncertain_read_is_not_absence(monkeypatch,status):
    from types import SimpleNamespace
    from vercel import blob
    from backend.services.identificacion_service import PrivateIdentityStore
    monkeypatch.setenv('AXS_ID_PHOTOS_ENABLED','true');monkeypatch.setenv('BLOB_READ_WRITE_TOKEN','synthetic')
    monkeypatch.setattr(blob,'get',lambda *args,**kwargs: SimpleNamespace(status_code=status,content=b''))
    with pytest.raises(HTTPException) as exc: PrivateIdentityStore().read('fixture')
    assert exc.value.status_code==503
