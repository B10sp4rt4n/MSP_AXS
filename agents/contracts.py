"""AXS Agents A0: pure, offline contracts. Never import AXS DB engines here."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentMode(str, Enum):
    OBSERVE = "observe"
    PROPOSE = "propose"
    EXECUTE = "execute"  # Reserved for a separately authorized future phase.


class VisitFact(BaseModel):
    """A minimal, PII-free fact projection; not a copy of the visit row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    visit_ref: str = Field(pattern=r"^VIS-[A-Za-z0-9-]{4,64}$", max_length=68)
    estado: Literal["pendiente", "activa", "completada", "cancelada"]
    entrada_registrada_en: datetime | None = None
    salida_registrada_en: datetime | None = None

    @field_validator("entrada_registrada_en", "salida_registrada_en")
    @classmethod
    def timestamp_is_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Un timestamp requiere zona horaria")
        return value


class VisitSnapshot(BaseModel):
    """Snapshot supplied by a FUTURE trusted adapter, after AXS scope check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,100}$")
    msp_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    tenant_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    source_system: Literal["axs-core"] = "axs-core"
    purpose: Literal["operational_reconciliation"] = "operational_reconciliation"
    generated_at: datetime
    records: tuple[VisitFact, ...] = Field(max_length=500)

    @field_validator("generated_at")
    @classmethod
    def generated_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Snapshot sin zona horaria")
        return value

    @model_validator(mode="after")
    def unique_visit_refs(self):
        refs = [item.visit_ref for item in self.records]
        if len(refs) != len(set(refs)):
            raise ValueError("Snapshot con referencia duplicada")
        return self


class AgentFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str
    agent_id: Literal["axs.reconciliation.observe.v1"] = "axs.reconciliation.observe.v1"
    mode: Literal["observe"] = "observe"
    msp_id: str
    tenant_id: str
    source_snapshot_id: str
    visit_ref: str
    category: Literal[
        "completed_without_exit",
        "active_without_recent_exit",
        "exit_without_entry",
        "exit_before_entry",
    ]
    severity: Literal["review"] = "review"
    recommendation: Literal["review_record_without_changing_history"] = (
        "review_record_without_changing_history"
    )


class AgentManifest(BaseModel):
    """A declarative registry descriptor, never a source of authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    version: Literal["0.1"] = "0.1"
    mode: Literal["observe"] = "observe"
    consumes: tuple[Literal["visit_snapshot.v1"], ...] = ("visit_snapshot.v1",)
    actions: tuple[()] = ()  # No write-action capability in A0.
    requires_enabled_tenant: bool = True


RECONCILIATION_AGENT = AgentManifest(agent_id="axs.reconciliation.observe.v1")
