"""HTTP replay of exact synthetic Neon development snapshots, not live Clerk."""
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import DateTime
from backend.db.core import Base_CORE
from backend.core.auth.jwt import create_access_token


def test_centinela_handover_and_provider_exit(client, db_session):
    stages=json.loads((Path(__file__).parent/'fixtures/centinela_lifecycle.json').read_text())
    # Fixture correction applied to all historical replay stages: seeded visits
    # initially omitted vigencia, which the API response contract requires.
    for stage in stages:
        for visit in stage['data']['visitas']:
            visit['vigencia']=visit['vigencia'] or visit['created_at']
    roles={'director':'MSP_ADMIN','admin':'ADMIN_CONDOMINIO','guardia1':'GUARDIA',
           'guardia2':'GUARDIA','residente':'RESIDENTE','admincontrol':'ADMIN_CONDOMINIO'}
    # These exact tokens are retained for the entire lifecycle.
    headers={k:{'Authorization':'Bearer '+create_access_token('lab261009_'+k,r)} for k,r in roles.items()}
    expected={'baseline':[200,200,200,403,200], 'handover':[200,200,403,200,200],
              'membership_only':[403,200,403,200,200], 'offboarding':[403,200,403,403,200]}
    actors=['director','admin','guardia1','guardia2','residente']
    baseline=stages[0]['data']
    ordered=['msps_exo','condominios_exo','casas','usuarios','msp_memberships','user_tenant_scope','visitas','evidencias']
    def values(table,row):
        return {k:datetime.fromisoformat(v) if v is not None and isinstance(table.c[k].type,DateTime) else v for k,v in row.items()}
    for name in ordered:
        table=Base_CORE.metadata.tables[name]
        for row in baseline[name]:
            db_session.execute(table.insert().values(**values(table,row)))
    db_session.commit()
    for stage in stages:
        data=stage['data']
        for name in ['visitas','evidencias','usuarios','casas']:
            assert data[name]==baseline[name], (stage['stage'],name)
        for name in ['condominios_exo','user_tenant_scope','msp_memberships']:
            table=Base_CORE.metadata.tables[name]
            for row in data[name]:
                db_session.execute(table.update().where(table.c.id==row['id']).values(**values(table,row)))
        db_session.commit();db_session.expire_all()
        for actor,status in zip(actors,expected[stage['stage']]):
            path='/visitas/lab261009_pendiente' if actor=='residente' else '/condominios/lab261009_ensayo/casas'
            r=client.get(path,headers=headers[actor])
            assert r.status_code==status,(stage['stage'],actor,r.status_code)
        assert client.get('/condominios/lab261009_control_condo/casas',headers=headers['admincontrol']).status_code==200
        assert client.get('/condominios/lab261009_control_condo/casas',headers=headers['admin']).status_code==403
        # Every preserved visit remains accessible to the retained condo admin.
        for visit in data['visitas']:
            r=client.get('/visitas/'+visit['visita_id'],headers=headers['admin'])
            assert r.status_code==200
            assert r.json()['estado']==visit['estado']
    # Independent condo scopes are deliberately retained; no provider grants remain.
    final=stages[-1]['data']
    assert next(c for c in final['condominios_exo'] if c['condominio_id']=='lab261009_ensayo')['msp_id'] is None
    assert next(m for m in final['msp_memberships'] if m['usuario_id']=='lab261009_director')['estado']=='revocado'
