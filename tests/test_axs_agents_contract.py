"""A0: pure, synthetic tests, no database/API/network or physical access."""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agents.contracts import AgentFinding, RECONCILIATION_AGENT, VisitSnapshot
from agents.observers.reconciliation import observe_visit_snapshot


NOW = datetime(2026, 10, 23, 16, tzinfo=timezone.utc)


def snapshot(records, **overrides):
    data = dict(
        schema_version="1.0",
        snapshot_id="snap_20261023_001",
        msp_id="msp_demo",
        tenant_id="tenant_demo",
        source_system="axs-core",
        purpose="operational_reconciliation",
        generated_at=NOW,
        records=records,
    )
    data.update(overrides)
    return VisitSnapshot.model_validate(data)


def fact(ref="VIS-DEMO-00001", state="completada", entry=None, exit=None):
    return {
        "visit_ref": ref,
        "estado": state,
        "entrada_registrada_en": entry,
        "salida_registrada_en": exit,
    }


def test_completed_without_exit_is_only_review():
    source = snapshot([fact(entry=NOW-timedelta(hours=4))])
    findings = observe_visit_snapshot(source, as_of=NOW)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.category == "completed_without_exit"
    assert finding.mode == "observe"
    assert finding.recommendation == "review_record_without_changing_history"
    assert finding.tenant_id == "tenant_demo"
    assert finding.agent_id == RECONCILIATION_AGENT.agent_id
    assert RECONCILIATION_AGENT.actions == ()
    assert source.records[0].salida_registrada_en is None


def test_recent_active_visit_does_not_imply_incident():
    s = snapshot([fact(state="activa", entry=NOW-timedelta(hours=2))])
    assert observe_visit_snapshot(s, as_of=NOW) == ()


def test_old_active_visit_needs_human_review():
    s = snapshot([fact(state="activa", entry=NOW-timedelta(hours=13))])
    assert observe_visit_snapshot(s, as_of=NOW)[0].category == "active_without_recent_exit"


@pytest.mark.parametrize("row,category", [
    (fact(exit=NOW-timedelta(hours=2)), "exit_without_entry"),
    (fact(entry=NOW, exit=NOW-timedelta(hours=1)), "exit_before_entry"),
])
def test_temporal_inconsistencies(row, category):
    assert observe_visit_snapshot(snapshot([row]), as_of=NOW)[0].category == category


def test_valid_completed_visit_yields_no_finding():
    s = snapshot([fact(entry=NOW-timedelta(hours=3), exit=NOW-timedelta(hours=1))])
    assert observe_visit_snapshot(s, as_of=NOW) == ()


def test_idempotence_across_retry_and_snapshot_version():
    first = snapshot([fact(entry=NOW-timedelta(hours=4))])
    second = snapshot([fact(entry=NOW-timedelta(hours=4))], snapshot_id="snap_20261023_002")
    x = observe_visit_snapshot(first, as_of=NOW)[0]
    assert x.finding_id == observe_visit_snapshot(first, as_of=NOW)[0].finding_id
    y = observe_visit_snapshot(second, as_of=NOW)[0]
    assert x.finding_id == y.finding_id
    assert x.source_snapshot_id != y.source_snapshot_id


def test_same_ref_under_different_tenant_msp_cannot_collide():
    row = [fact(entry=NOW-timedelta(hours=4))]
    a = observe_visit_snapshot(snapshot(row), as_of=NOW)[0]
    b = observe_visit_snapshot(snapshot(row, tenant_id="tenant_other"), as_of=NOW)[0]
    c = observe_visit_snapshot(snapshot(row, msp_id="msp_other"), as_of=NOW)[0]
    assert len({a.finding_id, b.finding_id, c.finding_id}) == 3


@pytest.mark.parametrize("field", ["nombre_visitante", "email", "foto", "qr_token", "ine", "placas"])
def test_visit_snapshot_rejects_unexpected_pii_fields(field):
    row = {**fact(), field: "private"}
    with pytest.raises(ValidationError):
        snapshot([row])


def test_snapshot_rejects_unexpected_sensitive_top_level_fields():
    with pytest.raises(ValidationError):
        snapshot([fact()], token="sensitive")


def test_snapshot_rejects_duplicate_visit_refs():
    with pytest.raises(ValidationError):
        snapshot([fact(), fact()])


@pytest.mark.parametrize("override", [
    {"schema_version": "2.0"},
    {"source_system": "untrusted-erp"},
    {"msp_id": ""},
    {"tenant_id": ""},
    {"snapshot_id": "bad id"},
])
def test_snapshot_rejects_unsupported_scope_or_version(override):
    with pytest.raises(ValidationError):
        snapshot([fact()], **override)


def test_reject_naive_timestamps_and_stale_snapshots():
    with pytest.raises(ValidationError):
        snapshot([fact(entry=datetime(2026, 10, 23, 12))])
    with pytest.raises(ValidationError):
        snapshot([fact()], generated_at=datetime(2026, 10, 23, 12))
    old = snapshot([fact()], generated_at=NOW-timedelta(days=3))
    with pytest.raises(ValueError):
        observe_visit_snapshot(old, as_of=NOW)
    future = snapshot([fact()], generated_at=NOW+timedelta(hours=1))
    with pytest.raises(ValueError):
        observe_visit_snapshot(future, as_of=NOW)


def test_finding_is_immutable_and_does_not_authorize():
    result = observe_visit_snapshot(snapshot([fact()]), as_of=NOW)[0]
    with pytest.raises(ValidationError):
        AgentFinding.model_validate({**result.model_dump(), "action": "open_door"})
    with pytest.raises((ValidationError, AttributeError)):
        result.mode = "execute"


def test_empty_snapshot_does_not_infer_presence():
    assert observe_visit_snapshot(snapshot([]), as_of=NOW) == ()


def test_manifest_is_observer_only_and_no_self_authorization():
    assert RECONCILIATION_AGENT.mode == "observe"
    assert RECONCILIATION_AGENT.requires_enabled_tenant is True
    assert RECONCILIATION_AGENT.actions == ()
    with pytest.raises(ValidationError):
        RECONCILIATION_AGENT.model_copy(update={"mode":"execute"}).__class__.model_validate(
            {**RECONCILIATION_AGENT.model_dump(), "mode":"execute"}
        )
