from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from tests.test_personal_condominio import people, headers
from backend.db.core import Usuario, UserTenantScope, Casa
from backend.services.onboarding import incorporation_state


@pytest.mark.parametrize('registered,home,age,expected,eligible',[
    (False,True,None,'precargado',True),(True,True,None,'registrado',False),
    (False,False,None,'vivienda_pendiente',False),(True,False,None,'vivienda_pendiente',False),
    (False,True,1,'invitacion_solicitada',False),(False,True,8,'invitacion_vencida',True),
])
def test_states(registered,home,age,expected,eligible):
    identity=SimpleNamespace(email='a@example.com',clerk_id='clerk' if registered else None)
    metadata={} if age is None else {'clerk_invitation':{'email':identity.email,'sent_at':(datetime.now(timezone.utc)-timedelta(days=age)).isoformat()}}
    state=incorporation_state(identity,SimpleNamespace(metadata_json=metadata),home)
    assert state['estado']==expected and state['puede_invitar']==eligible
    assert state['registro_completo']==registered


def test_list_and_stale_email(client,people,monkeypatch):
    from backend.services import clerk_invitations
    calls=[]
    monkeypatch.setattr(clerk_invitations,'send_invitation',lambda email:calls.append(email) or 'inv_test')
    people.add(Casa(casa_id='house',condominio_id='a1',numero='001',tipo='casa'))
    resident=people.query(Usuario).filter_by(usuario_id='resident').one()
    resident.casa_id='house'; resident.casa_unidad='001';people.commit()
    auth=headers('admin','ADMIN_CONDOMINIO')
    result=client.get('/condominios/a1/usuarios',headers=auth).json()
    assert next(u for u in result if u['usuario_id']=='resident')['incorporacion']['estado']=='precargado'
    url='/condominios/a1/usuarios/resident/invitacion'
    assert client.post(url,headers=auth,json={'expected_email':'old@example.com'}).status_code==409
    assert not calls
    assert client.post(url,headers=auth,json={'expected_email':resident.email}).status_code==200
    result=client.get('/condominios/a1/usuarios',headers=auth).json()
    state=next(u for u in result if u['usuario_id']=='resident')['incorporacion']
    assert state['estado']=='invitacion_solicitada' and not state['puede_invitar']
    assert 'id' not in state['invitacion']
    resident.clerk_id='clerk';people.commit()
    result=client.get('/condominios/a1/usuarios',headers=auth).json()
    assert next(u for u in result if u['usuario_id']=='resident')['incorporacion']['estado']=='registrado'


def test_bad_invitation_metadata_blocks_resend(client,people,monkeypatch):
    from backend.services import clerk_invitations
    def forbidden(email): raise AssertionError('Unexpected send')
    monkeypatch.setattr(clerk_invitations,'send_invitation',forbidden)
    scope=people.query(UserTenantScope).filter_by(usuario_id='resident').one()
    scope.metadata_json={'clerk_invitation':{'email':'resident@test.local','sent_at':'invalid'}};people.commit()
    assert client.post('/condominios/a1/usuarios/resident/invitacion',headers=headers('admin','ADMIN_CONDOMINIO')).status_code==409
