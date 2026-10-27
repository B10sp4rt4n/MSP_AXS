"""Privileged CORE connection for corporate bootstrap; never reuse axs_core_app.

Fail-closed: no provisioner URL or a role with excessive powers means no writes.
The credential belongs only on the backend, not in frontend, repository or logs.
"""
import os
from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from fastapi import HTTPException


def provisioning_enabled() -> None:
    if (os.getenv("AXS_CORPORATE_PROVISIONING_ENABLED", "").lower() != "true"
            or os.getenv("AXS_CORPORATE_API_ENABLED", "").lower() != "true"):
        raise HTTPException(404, "Aprovisionamiento corporativo no disponible")


@lru_cache(maxsize=1)
def _session_factory(url: str):
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise RuntimeError("Aprovisionamiento exige PostgreSQL")
    return sessionmaker(bind=engine, autoflush=False)


def get_provisioning_db():
    provisioning_enabled()
    url = os.getenv("DATABASE_CORPORATE_PROVISIONING_URL", "").strip()
    if not url:
        raise HTTPException(503, "Aprovisionamiento sin credencial segregada")
    try:
        parsed = make_url(url)
        if parsed.get_backend_name() != "postgresql":
            raise ValueError("Motor no soportado")
        factory = _session_factory(url)
    except Exception as exc:
        raise HTTPException(503, "Configuración de aprovisionamiento inválida") from exc
    with factory() as db:
        yield db


def require_provisioner_role(db: Session):
    """No confiar en un URL apuntando por error a la conexión CORE global."""
    if db.bind.dialect.name == "sqlite":
        if os.getenv("TESTING") == "1":
            return  # Solo fixtures aislados; no habilitar SQLite en producción.
        raise HTTPException(503, "Aprovisionamiento requiere PostgreSQL")
    result = db.execute(text("""
        SELECT r.rolname,r.rolsuper,r.rolbypassrls,r.rolcreatedb,r.rolcreaterole,
               r.rolreplication, r.rolinherit,
               has_schema_privilege(current_user,'public','CREATE') AS can_create
        FROM pg_roles r WHERE r.rolname = current_user
    """)).mappings().one_or_none()
    if (not result or result["rolname"] != "axs_corporate_provisioner"
            or any(result[field] for field in (
                "rolsuper", "rolbypassrls", "rolcreatedb", "rolcreaterole",
                "rolreplication", "rolinherit", "can_create",
            ))):
        raise HTTPException(503, "La credencial de aprovisionamiento no cumple mínimos privilegios")
    memberships = db.execute(text("""
        SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
        WHERE r.rolname=current_user
    """)).scalar_one()
    if memberships:
        raise HTTPException(503, "La credencial de aprovisionamiento tiene roles heredables")
    owned = db.execute(text("""
        SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname IN
            ('condominios_exo','corporate_organizations','corporate_memberships','event_outbox',
             'corporate_provisioning_operations')
          AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname=current_user)
    """)).scalar_one()
    if owned:
        raise HTTPException(503, "La credencial de aprovisionamiento no debe ser dueña de tablas CORE")
