"""Manual C5 upgrade of a still-valid, previously certified synthetic sandbox.

Preserves initial certification and its expiry; never recertifies nonempty data.
Not imported by backend startup. The caller owns the enclosing transaction.
"""
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text
from scripts.corporate_sandbox_contract import ACK
from scripts.corporate_sandbox_targets import LEGACY, INTEGRATED
from scripts.corporate_sandbox_attestation import snapshot, verify_permissions


def upgrade_catalog(conn, run_id, issuer, *, targets=INTEGRATED, expected_db=None):
    if targets not in (LEGACY, INTEGRATED):
        raise RuntimeError('C5: sandbox target not approved')
    database, owner, bypass = conn.execute(text(
        'SELECT current_database(),current_user,rolsuper OR rolbypassrls '
        'FROM pg_roles WHERE rolname=current_user')).one()
    if database != (expected_db or targets.databases['CORE']) or not bypass:
        raise RuntimeError('C5: exact sandbox and schema owner required')
    # Serialize upgrades and check the original certificate before any DDL.
    row = conn.execute(text(f'SELECT * FROM public.{ACK} WHERE singleton=true FOR UPDATE')).mappings().one()
    now = datetime.now(timezone.utc)
    if (str(row['run_id']) != run_id or row['domain'] != 'CORE'
            or row['database_name'] != database or row['clerk_issuer'] != issuer
            or row['catalog_hash'] != snapshot(conn)
            or not row['certified_at'] <= now < row['expires_at']
            or (row['expires_at'] - row['certified_at']).total_seconds() > 86400):
        raise RuntimeError('C5: original certificate expired or incompatible')
    for domain in ('CORE', 'PROVISIONER'):
        verify_permissions(conn, domain, targets=targets)
    if conn.execute(text("SELECT to_regclass('public.corporate_visits')")).scalar_one():
        raise RuntimeError('C5: visit table already exists; inspect before retry')
    source = (Path(__file__).resolve().parents[1] / 'migrations/20261115_corporate_visits_c5.sql').read_text()
    # Fixed, reviewed role substitution; transaction is owned by this caller.
    prefix, body = source.split('BEGIN;', 1)
    if not body.rstrip().endswith('COMMIT;'):
        raise RuntimeError('C5: migration transaction wrapper changed')
    body = body.rstrip()[:-len('COMMIT;')].replace('axs_core_app', targets.roles['CORE'])
    conn.exec_driver_sql(body)
    for domain in ('CORE', 'PROVISIONER'):
        verify_permissions(conn, domain, targets=targets, visits_enabled=True)
    from scripts.check_corporate_visit_schema import check_schema
    conn.exec_driver_sql('SET LOCAL ROLE ' + targets.roles['CORE'])
    try:
        check_schema(conn, role=targets.roles['CORE'])
    finally:
        conn.exec_driver_sql('SET LOCAL ROLE NONE')
    conn.execute(text(f'UPDATE public.{ACK} SET catalog_hash=:digest WHERE singleton=true'),
                 {'digest': snapshot(conn)})
    return {'migration': 'C5', 'expires_at': row['expires_at'].isoformat(),
            'initial_certification_preserved': True}
