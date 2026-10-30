"""Serialize tenant operations without granting sandbox CORE root UPDATE."""
import os
from sqlalchemy import text


def lock_company_query(db, query, tenant_id):
    if os.getenv("AXS_CORPORATE_SANDBOX_ONLY", "").lower() == "true":
        db.execute(text("SELECT public.corporate_sandbox_lock_company(:tenant)"), {"tenant": tenant_id})
        return query
    return query.with_for_update()
