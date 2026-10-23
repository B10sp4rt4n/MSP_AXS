"""Initial AXS Agents observer: recommend reviews, never fabricate access facts.

The caller will eventually obtain a scoped snapshot through a trusted AXS
service identity. This module cannot authorize, mutate or persist anything.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from agents.contracts import AgentFinding, VisitSnapshot


def _finding_id(snapshot: VisitSnapshot, ref: str, category: str) -> str:
    # Stable across retries and subsequent snapshots of the same unresolved
    # condition; tenant and MSP prevent cross-tenant collisions.
    canonical = "\x1f".join(
        ("axs.reconciliation.observe.v1", snapshot.msp_id,
         snapshot.tenant_id, ref, category)
    )
    return "finding_" + sha256(canonical.encode("utf-8")).hexdigest()[:32]


def observe_visit_snapshot(
    snapshot: VisitSnapshot,
    *,
    as_of: datetime,
    review_after: timedelta = timedelta(hours=12),
) -> tuple[AgentFinding, ...]:
    """Observe a validated, already-authorized snapshot; return proposals only.

    A missing exit is an information inconsistency, NOT proof that someone
    remains inside a facility. Caller must revalidate AXS scope on delivery.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of requiere zona horaria")
    if review_after <= timedelta(0):
        raise ValueError("review_after debe ser positivo")
    if snapshot.generated_at > as_of + timedelta(minutes=5):
        raise ValueError("Snapshot del futuro")
    if snapshot.generated_at < as_of - timedelta(hours=24):
        raise ValueError("Snapshot desactualizado; no inferir estado operativo")

    output: list[AgentFinding] = []
    for record in snapshot.records:
        categories = []
        if record.salida_registrada_en is not None and record.entrada_registrada_en is None:
            categories.append("exit_without_entry")
        elif (record.salida_registrada_en is not None
              and record.entrada_registrada_en is not None
              and record.salida_registrada_en < record.entrada_registrada_en):
            categories.append("exit_before_entry")
        if record.estado == "completada" and record.salida_registrada_en is None:
            categories.append("completed_without_exit")
        elif (record.estado == "activa"
              and record.entrada_registrada_en is not None
              and record.salida_registrada_en is None
              and as_of - record.entrada_registrada_en >= review_after):
            categories.append("active_without_recent_exit")
        for category in categories:
            output.append(
                AgentFinding(
                    finding_id=_finding_id(snapshot, record.visit_ref, category),
                    msp_id=snapshot.msp_id,
                    tenant_id=snapshot.tenant_id,
                    source_snapshot_id=snapshot.snapshot_id,
                    visit_ref=record.visit_ref,
                    category=category,
                )
            )
    return tuple(output)
