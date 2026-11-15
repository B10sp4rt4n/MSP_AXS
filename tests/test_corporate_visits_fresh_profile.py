"""The fresh C5 run cannot reuse expired databases or broaden its role target."""
import pytest
from scripts.corporate_sandbox_targets import LEGACY, INTEGRATED, VISITS, render_sandbox_sql, sandbox_targets
from scripts.check_corporate_sandbox_config import check
from scripts.prepare_integrated_sandbox_bundle import permission_scripts
from tests.test_corporate_sandbox_runtime import runtime_config


def config():
    values=runtime_config()
    values['AXS_CORPORATE_SANDBOX_RUN_PROFILE']='visits-20261115'
    values['AXS_CORPORATE_VISITS_ENABLED']='true'
    for key in ('DATABASE_CORE_URL','DATABASE_URL','DATABASE_GOV_URL','DATABASE_EVENT_URL','DATABASE_CORPORATE_PROVISIONING_URL'):
        values[key]=render_sandbox_sql(values[key],VISITS)
    return values


def test_fixed_fresh_c5_targets_and_schema():
    check(config())
    assert sandbox_targets(config())==VISITS
    for older in (LEGACY,INTEGRATED):
        assert set(older.databases.values()).isdisjoint(VISITS.databases.values())
        assert set(older.roles.values()).isdisjoint(VISITS.roles.values())
    sql='\n'.join(permission_scripts('CORE',VISITS))
    assert 'CREATE TABLE public.corporate_visits' in sql
    assert "interval '24 hours'" in sql
    assert ' TO axs_core_app' not in sql
    assert VISITS.roles['CORE'] in sql


@pytest.mark.parametrize('key',('DATABASE_CORE_URL','DATABASE_URL','DATABASE_GOV_URL','DATABASE_EVENT_URL','DATABASE_CORPORATE_PROVISIONING_URL'))
def test_fresh_run_rejects_connection_to_prior_run(key):
    values=config()
    old=render_sandbox_sql(runtime_config()[key],INTEGRATED)
    values[key]=old
    with pytest.raises(RuntimeError):check(values)
