"""Contract-aware scope validation, independent of HTTP and tenant data."""
from backend.db.core import ProviderContract, Condominio


def current_contract(db, tenant):
    return db.query(ProviderContract).filter_by(condominio_id=tenant, closed_at=None).first()


def origin_is_current(db, scope, condo=None):
    origin = (scope.metadata_json or {}).get('grant_origin', {})
    if origin.get('kind') != 'msp':
        return True
    condo = condo or db.query(Condominio).filter_by(condominio_id=scope.tenant_id).first()
    if not condo or condo.msp_id != origin.get('msp_id'):
        return False
    contract = current_contract(db, scope.tenant_id)
    return origin.get('contract_id') == (contract.contract_id if contract else None)
