"""Real logical backup/restore, synthetic CI data only; never production URLs."""
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta
from time import perf_counter
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.db.core import (Base_CORE, MSP, Condominio, Casa, Usuario, Visita,
    Evidencia, UserTenantScope, ScopeStatus, AccessLevel, MSPMembership)
from backend.db.event import Base_EVENT, Event
from backend.db.gov import (Base_GOV, Authority, AuthorityType, Delegation, GovStatus)
from backend.core.scope.msp_boundary import require_condominio
from backend.core.event.registry import verificar_integridad_evento
from backend.services.event_outbox import contexto_evento, encolar_visita, enviar_pendientes
from backend.services.visita_service import registrar_entrada


@pytest.mark.integration
def test_backup_restore_and_stale_authorization_quarantine(tmp_path, request):
    raw = os.getenv('AXS_TEST_POSTGRES_URL')
    if not raw:
        pytest.skip('Requires disposable PostgreSQL CI database')
    url = make_url(raw)
    # Deliberately narrow: no generic database URL or production override.
    assert url.host in ('localhost', '127.0.0.1') and url.database == 'axs_rls_ci'
    assert url.username == 'axs_rls_ci' and not url.query
    for executable in ('pg_dump', 'pg_restore'):
        assert shutil.which(executable), f'{executable} must be installed in CI'
    schema = 'axs_dr_' + uuid.uuid4().hex
    live = schema + '_live'
    admin = create_engine(raw)
    engine = create_engine(raw, connect_args={'options': f'-csearch_path={schema}'})
    archive = tmp_path / 'synthetic.dump'
    env = {**os.environ, 'PGHOST': url.host, 'PGPORT': str(url.port or 5432),
           'PGDATABASE': url.database, 'PGUSER': url.username,
           'PGPASSWORD': url.password or '', 'PGCONNECT_TIMEOUT': '5',
           'PGOPTIONS': '', 'PGSERVICE': ''}
    metadata = [Base_CORE.metadata, Base_GOV.metadata, Base_EVENT.metadata]
    table_names = sorted({t.name for m in metadata for t in m.tables.values()})

    def snapshot(namespace):
        with admin.connect() as conn:
            return {name: sorted(json.dumps(dict(row), default=str, sort_keys=True)
                for row in conn.execute(text(f'SELECT * FROM {namespace}.{name}')).mappings())
                for name in table_names}

    def command(args):
        start = perf_counter()
        result = subprocess.run(args, env=env, capture_output=True, timeout=60)
        # Do not leak connection credentials or row values in command output.
        assert result.returncode == 0, (args[0], result.returncode)
        return perf_counter() - start

    try:
        with admin.begin() as conn:
            assert not conn.execute(text('SELECT rolsuper OR rolbypassrls FROM pg_roles '
                                         'WHERE rolname=current_user')).scalar_one()
            conn.execute(text(f'CREATE SCHEMA {schema}'))
        for m in metadata:
            m.create_all(engine)
        now = datetime.utcnow()
        audit = contexto_evento(SimpleNamespace(usuario_id='guard'), 'synthetic-session')
        with Session(engine) as db:
            db.add(MSP(msp_id='m', nombre='Synthetic MSP')); db.flush()
            db.add(Condominio(condominio_id='a', msp_id='m', nombre='Synthetic condo')); db.flush()
            db.add(Casa(casa_id='home', condominio_id='a', numero='101')); db.flush()
            for uid, role in [('guard', 'GUARDIA'), ('provider', 'MSP_ADMIN'), ('platform', 'MSP_ADMIN')]:
                db.add(Usuario(usuario_id=uid, email=f'{uid}@example.invalid', rol=role,
                               condominio_id='a', casa_id='home'))
            db.flush()
            db.add(UserTenantScope(usuario_id='guard', tenant_id='a',
                access_level=AccessLevel.GUARDIA, estado=ScopeStatus.ACTIVO))
            db.add(MSPMembership(usuario_id='provider', msp_id='m', estado='activo'))
            db.add(Authority(authority_id='global', identity_id='platform',
                             tipo=AuthorityType.GLOBAL, estado=GovStatus.ACTIVO)); db.flush()
            db.add(Delegation(delegation_id='delegation', authority_id='global',
                target_identity_id='guard', permisos_delegados=['crear_tenant']))
            for vid, state in [('pending', 'pendiente'), ('inside', 'entrada_registrada')]:
                visit = Visita(visita_id=vid, condominio_id='a', destino_id='home',
                    nombre_visitante='Synthetic visitor', tipo_visita='eventual', estado=state,
                    vigencia=now, qr_token=f'qr-{vid}', qr_vigencia=now+timedelta(hours=1),
                    entrada_registrada_en=now if vid == 'inside' else None)
                db.add(visit); db.flush()
                encolar_visita(db, visit, audit)
            db.add(Evidencia(evidencia_id='evidence', visita_id='inside', guardia_id='guard',
                archivo_url='https://example.invalid/synthetic', hash_sha256='a'*64))
            db.commit()
            assert enviar_pendientes(db, 'a', lambda: Session(engine)) == 2
        before = snapshot(schema)
        dump_seconds = command(['pg_dump', '--format=custom', '--no-owner', '--no-acl',
                                f'--schema={schema}', f'--file={archive}'])
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        # Changes made AFTER the recovery point must not mysteriously appear in the restore.
        with Session(engine) as db:
            registrar_entrada(db, 'pending', qr_token='qr-pending', auditoria=audit)
            db.query(UserTenantScope).update({UserTenantScope.estado: ScopeStatus.REVOCADO})
            db.commit()
            assert enviar_pendientes(db, 'a', lambda: Session(engine)) == 1
        after = snapshot(schema)
        assert before != after
        engine.dispose()
        # Preserve the newer source; restore into a distinct, empty namespace.
        with admin.begin() as conn:
            conn.execute(text(f'ALTER SCHEMA {schema} RENAME TO {live}'))
        restore_seconds = command(['pg_restore', '--exit-on-error', '--single-transaction',
            '--no-owner', '--no-acl', '--dbname=axs_rls_ci', str(archive)])
        validation_started = perf_counter()
        assert snapshot(schema) == before
        assert snapshot(live) == after
        with Session(engine) as db:
            assert db.query(Event).count() == 2
            assert all(verificar_integridad_evento(row) for row in db.query(Event))
            for user in db.query(Usuario):
                require_condominio(db, db, user, 'a', AccessLevel.GUARDIA)
            assert db.query(Visita).filter_by(visita_id='pending').one().estado == 'pendiente'
            assert db.query(UserTenantScope).one().estado == ScopeStatus.ACTIVO
            # Demonstrate actual service acceptance on the stale restore, then roll it back.
            # registrar_entrada commits; an external transaction confines this probe.
        with engine.connect() as conn:
            transaction = conn.begin()
            with Session(bind=conn, join_transaction_mode='create_savepoint') as probe:
                assert registrar_entrada(probe, 'pending', qr_token='qr-pending').entrada_registrada_en
            transaction.rollback()
        assert snapshot(schema) == before
        # Rehearsal quarantine: restored data stays offline until reconciliation.
        with Session(engine) as db:
            db.query(UserTenantScope).update({UserTenantScope.estado: ScopeStatus.REVOCADO})
            db.query(MSPMembership).update({MSPMembership.estado: 'revocado'})
            db.query(Authority).update({Authority.estado: GovStatus.REVOCADO})
            db.query(Delegation).update({Delegation.estado: GovStatus.REVOCADO})
            db.query(Visita).filter(Visita.estado.in_(['pendiente', 'activa'])).update({
                Visita.estado: 'cancelada', Visita.qr_token: None, Visita.qr_vigencia: None})
            db.commit()
            for user in db.query(Usuario):
                with pytest.raises(HTTPException) as denied:
                    require_condominio(db, db, user, 'a', AccessLevel.GUARDIA)
                assert denied.value.status_code == 403
            with pytest.raises(HTTPException) as denied:
                registrar_entrada(db, 'pending', qr_token='qr-pending')
            assert denied.value.status_code == 400
            db.rollback()
            assert db.query(Visita).filter_by(visita_id='inside').one().entrada_registrada_en == now
            assert all(verificar_integridad_evento(row) for row in db.query(Event))
            # Serial sequences also survive the archive.
            old_max = max(u.id for u in db.query(Usuario))
            new = Usuario(usuario_id='new', email='new@example.invalid')
            db.add(new); db.flush()
            assert new.id > old_max
            db.rollback()
        restored = snapshot(schema)
        for name in ('events_aup', 'evidencias', 'event_outbox'):
            assert restored[name] == before[name]
        assert snapshot(live) == after
        validation_seconds = perf_counter()-validation_started
        request.config.pluginmanager.get_plugin('terminalreporter').write_line(
            f'AXS_RESTORE tables={len(table_names)} rows={sum(map(len, before.values()))} '
            f'dump_s={dump_seconds:.3f} restore_s={restore_seconds:.3f} '
            f'validate_quarantine_s={validation_seconds:.3f} bytes={archive.stat().st_size} '
            f'sha256={digest} stale_qr_proven=true stale_scope_proven=true quarantine_denied=true')
    finally:
        engine.dispose()
        with admin.begin() as conn:
            for namespace in (schema, live):
                conn.execute(text(f'DROP SCHEMA IF EXISTS {namespace} CASCADE'))
        admin.dispose()
