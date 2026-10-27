"""Explicitly migrated corporate operation journal, never startup create_all.

Separate metadata deliberately prevents legacy CORE bootstrap from silently
creating an unprotected table. Only reviewed migration C4 installs this table.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, UniqueConstraint, String, DateTime, JSON, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.orm import declarative_base

from .models import CorporateOrganization

CorporateOperationBase = declarative_base()


class CorporateProvisioningOperation(CorporateOperationBase):
    __tablename__ = "corporate_provisioning_operations"
    tenant_id = Column(String, ForeignKey(CorporateOrganization.tenant_id), primary_key=True)
    request_id = Column(String(36), primary_key=True)
    revision = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    requested_by = Column(String, nullable=False)
    expected_gov = Column(JSON, nullable=False)
    estado = Column(String(16), nullable=False, default="pending")
    request_event_uid = Column(String, nullable=False)
    confirmation_event_uid = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    __table_args__ = (
        CheckConstraint("estado IN ('pending','confirmed','needs_review')", name="ck_corporate_operation_state"),
        CheckConstraint("(estado IN ('pending','needs_review') AND confirmed_at IS NULL AND confirmation_event_uid IS NULL) OR "
                        "(estado='confirmed' AND confirmed_at IS NOT NULL AND confirmation_event_uid IS NOT NULL)",
                        name="ck_corporate_operation_confirmation"),
        UniqueConstraint("tenant_id", "revision", name="uq_corporate_operation_revision"),
        CheckConstraint("revision > 0", name="ck_corporate_operation_revision"),
        Index("uq_corporate_operation_pending", "tenant_id", unique=True,
              postgresql_where=text("estado IN ('pending','needs_review')"), sqlite_where=text("estado IN ('pending','needs_review')")),
    )
