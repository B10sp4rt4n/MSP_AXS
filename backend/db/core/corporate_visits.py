"""Visit journal installed only by explicit migration, outside startup metadata."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.orm import declarative_base
from .models import CorporateDestination, CorporateMembership

CorporateVisitBase = declarative_base()


class CorporateVisit(CorporateVisitBase):
    __tablename__ = "corporate_visits"
    tenant_id = Column(String, primary_key=True)
    visit_id = Column(String(36), primary_key=True)
    site_id = Column(String(40), nullable=False)
    destination_id = Column(String(40), nullable=False)
    host_user_id = Column(String, nullable=False)
    visitor_ref = Column(String(80), nullable=False)
    state = Column(String(16), nullable=False, default="preregistrada")
    created_by = Column(String, nullable=False)
    authorized_by = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    authorized_at = Column(DateTime)
    entered_at = Column(DateTime)
    exited_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "site_id", "destination_id"],
                             [CorporateDestination.tenant_id, CorporateDestination.site_id,
                              CorporateDestination.destination_id]),
        ForeignKeyConstraint(["tenant_id", "host_user_id"],
                             [CorporateMembership.tenant_id, CorporateMembership.user_id]),
        CheckConstraint("state IN ('preregistrada','autorizada','dentro','cerrada','cancelada')",
                        name="ck_corporate_visit_state"),
        CheckConstraint("(state='preregistrada' AND authorized_at IS NULL AND authorized_by IS NULL AND entered_at IS NULL AND exited_at IS NULL AND cancelled_at IS NULL) OR "
                        "(state='autorizada' AND authorized_at IS NOT NULL AND authorized_by IS NOT NULL AND entered_at IS NULL AND exited_at IS NULL AND cancelled_at IS NULL) OR "
                        "(state='dentro' AND authorized_at IS NOT NULL AND authorized_by IS NOT NULL AND entered_at>=authorized_at AND entered_at IS NOT NULL AND exited_at IS NULL AND cancelled_at IS NULL) OR "
                        "(state='cerrada' AND authorized_at IS NOT NULL AND authorized_by IS NOT NULL AND entered_at>=authorized_at AND entered_at IS NOT NULL AND exited_at>=entered_at AND exited_at IS NOT NULL AND cancelled_at IS NULL) OR "
                        "(state='cancelada' AND entered_at IS NULL AND exited_at IS NULL AND cancelled_at IS NOT NULL)",
                        name="ck_corporate_visit_times"),
    )
