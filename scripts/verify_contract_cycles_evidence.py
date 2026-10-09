"""Offline cross-check of captured HTTP/CORE/EVENT evidence; never connects to a DB."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys


def verify(data):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    checks = [json.loads(row['message'].removeprefix('AXS_CYCLES_CHECK '))
              for row in data['logs'] if row['message'].startswith('AXS_CYCLES_CHECK ')]
    results = [json.loads(row['message'].removeprefix('AXS_CYCLES_RESULT '))
               for row in data['logs'] if row['message'].startswith('AXS_CYCLES_RESULT ')]
    require(len(results) == 1 and results[0]['status'] == 'PASS', 'Explicit unique PASS required')
    result = results[0]
    require(len(checks) == result['checks'] == 40, 'Incomplete HTTP evidence')
    require(all(row['actual'] == row['expected'] for row in checks), 'HTTP mismatch')
    require(result['reusedTokens'] and not data['clerk_tested'], 'Authentication scope mismatch')
    require(data['before'] == data['after'], 'Historical visit/evidence changed')

    contracts = data['contracts']
    require([c['version'] for c in contracts] == [1, 2], 'Contract versions mismatch')
    require([c['contract_id'] for c in contracts] == result['contracts'], 'Contract IDs mismatch')
    require(len({c['msp_id'] for c in contracts}) == 1, 'Different providers')
    require(all(c['closed_at'] for c in contracts), 'Open contract remains')
    require(all(c['msp_id'] is None for c in data['condominios']), 'Provider remains linked')

    scopes = {s['id']: s for s in data['scopes']}
    revoked = [s for s in scopes.values() if s['estado'] == 'REVOCADO']
    local = [s for s in scopes.values() if s['metadata_json']['grant_origin']['kind'] == 'condominio']
    require(len(scopes) == 5 and len(revoked) == 3 and len(local) == 2, 'Scope count mismatch')
    require(all(s['estado'] == 'ACTIVO' and s['revoked_at'] is None for s in local), 'Local/control scope changed')
    require({s['id'] for s in revoked} == set(result['scopes']), 'Wrong scopes revoked')
    require(all(s['revoked_at'] for s in revoked), 'Revocation timestamp missing')

    events = {e['event_uid']: e for e in data['events']}
    outbox = {e['event_uid']: e for e in data['outbox']}
    require(len(events) == len(data['events']) == len(outbox) == len(data['outbox']) == 7, 'Duplicate/missing audit')
    require(set(events) == set(outbox) == set(result['events']), 'Audit UID mismatch')
    require(Counter(e['accion'] for e in events.values()) == {
        'abrir_contrato': 2, 'otorgar_permiso_contrato': 3, 'baja_proveedor': 2}, 'Audit actions mismatch')
    require(len({e['session_hash'] for e in events.values()}) == 1, 'Operator JWT changed')
    for uid, row in outbox.items():
        require(row['delivered_at'] and row['attempts'] == 1 and row['last_error'] is None, 'Undelivered/retried event')
        payload = row['payload']
        require(events[uid] == payload, f'CORE/EVENT content mismatch: {uid}')
        values = [payload[key] for key in ('event_uid', 'identity_id', 'session_hash', 'tenant_id',
                  'entidad', 'entidad_id', 'accion', 'resultado', 'timestamp')]
        require(hashlib.sha256('|'.join(values).encode()).hexdigest() == payload['hash_evento'], f'Invalid audit hash: {uid}')
    for contract in contracts:
        receipt = contract['close_receipt']
        require(events[contract['close_event_uid']]['metadata_json'] == receipt, 'Receipt/audit mismatch')
        require(events[contract['open_event_uid']]['metadata_json']['contract_id'] == contract['contract_id'], 'Opening mismatch')
        for sid in receipt['revoked_scope_ids']:
            require(scopes[sid]['metadata_json']['grant_origin']['contract_id'] == contract['contract_id'], 'Cross-contract revocation')
        require(len(receipt['preserved_scope_ids']) == 1 and scopes[receipt['preserved_scope_ids'][0]] in local, 'Preserved scope mismatch')
    require(len(data['authority_cleanup']) == 1 and data['authority_cleanup'][0]['estado'] == 'REVOCADO'
            and data['authority_cleanup'][0]['revoked_at'], 'Temporary authority still active')
    require(data['runner_secret_cleared'], 'Runner secret not cleared')
    return {'status': 'PASS', 'http_checks': len(checks), 'closed_contracts': len(contracts),
            'revoked_scopes': len(revoked), 'matched_events': len(events), 'historical_rows_unchanged': True,
            'clerk_tested': False}


if __name__ == '__main__':
    default = Path(__file__).resolve().parents[1] / 'docs/operacion/evidencias/contract-cycles-20261009.json'
    try:
        print(json.dumps(verify(json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else default).read_text()))))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise SystemExit(f'FAIL: {exc}')
