"""AXS Corporativo: alta y habilitación del DIRECTORIO por Superadmin.

Este flujo no habilita visitantes, QR, biometría ni piloto real. Un usuario
con rol MSP_ADMIN pero sin autoridad GLOBAL no puede aprovisionar empresas.
"""
import uuid
from datetime import datetime
import hashlib
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import require_platform_operator
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import (
    Condominio, CorporateMembership, CorporateOrganization, MSP, Usuario, get_core_db,
)
from backend.db.gov import Policy, PolicyScope, GovStatus, get_gov_db
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.services.corporate_provisioner_db import (
    get_provisioning_db, provisioning_enabled, require_provisioner_role,
)

router = APIRouter(
    prefix="/plataforma/corporativo", tags=["Superadmin Corporativo"],
    dependencies=[Depends(provisioning_enabled)],
)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateCompany(Input):
    request_id: uuid.UUID
    nombre: str = Field(min_length=3, max_length=120)
    msp_id: str = Field(min_length=1, max_length=100)
    owner_user_id: str = Field(min_length=1, max_length=100)
    privacy_contact: str = Field(min_length=5, max_length=254)
    privacy_notice_url: str = Field(min_length=12, max_length=500)
    privacy_notice_version: str = Field(min_length=1, max_length=80)

    @field_validator("privacy_contact")
    @classmethod
    def email_address(cls, value: str) -> str:
        if value.count("@") != 1 or "." not in value.split("@")[1] or any(c.isspace() for c in value):
            raise ValueError("Correo de privacidad inválido")
        return value.lower()

    @field_validator("privacy_notice_url")
    @classmethod
    def https_notice(cls, value: str) -> str:
        parts = urlsplit(value)
        if (parts.scheme != "https" or not parts.hostname or parts.username
                or parts.password or parts.fragment or parts.port):
            raise ValueError("El aviso requiere URL HTTPS pública sin credenciales ni fragmento")
        return value


class ActivateDirectory(Input):
    confirmacion: StrictBool


class DirectoryLimits(Input):
    max_sedes: int = Field(ge=1, le=1000)
    max_destinos_por_sede: int = Field(ge=1, le=2000)


def require_global(gov: Session, actor: Usuario):
    require_platform_operator(gov, actor)


def view(tenant: Condominio, org: CorporateOrganization, owner_id: str) -> dict:
    return {
        "tenant_id": tenant.condominio_id,
        "nombre": tenant.nombre,
        "msp_id": tenant.msp_id,
        "owner_user_id": owner_id,
        "modalidad": tenant.modalidad,
        "directorio_habilitado": tenant.corporativo_habilitado,
        "privacy_notice_version": org.privacy_notice_version,
        "privacy_contact": org.privacy_contact,
    }


def audit(db, tenant_id: str, actor: Usuario, request: Request, accion: str):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    encolar_evento(db, tenant_id, tenant_id, contexto_evento(
        actor, token, entidad="empresa_corporativa", accion=accion,
        motivo="Cambio de aprovisionamiento autorizado"),
        metadata={"accion": accion})


@router.post("/empresas", status_code=201)
def create_company(
    body: CreateCompany, request: Request,
    core: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
    provisioner: Session = Depends(get_provisioning_db),
    actor: Usuario = Depends(get_current_user),
):
    require_global(gov, actor)
    require_provisioner_role(provisioner)

    # No utilizar /condominios/ ni crear viviendas ficticias.
    if actor.usuario_id == body.owner_user_id:
        raise HTTPException(400, "Superadmin no puede asignarse a sí mismo como primer owner")
    if not core.query(MSP.msp_id).filter(MSP.msp_id == body.msp_id).first():
        raise HTTPException(404, "Proveedor inexistente")
    if not core.query(Usuario.usuario_id).filter(Usuario.usuario_id == body.owner_user_id).first():
        raise HTTPException(404, "El owner debe tener usuario AXS existente")

    tenant_id = "corp_" + body.request_id.hex
    _set_postgres_tenant(provisioner, tenant_id)
    existing = provisioner.query(Condominio).filter_by(condominio_id=tenant_id).with_for_update().first()
    if existing:
        org = provisioner.query(CorporateOrganization).filter_by(tenant_id=tenant_id).first()
        member = provisioner.query(CorporateMembership).filter_by(
            tenant_id=tenant_id, user_id=body.owner_user_id, rol="owner", estado="activo").first()
        if (not org or not member or existing.nombre != body.nombre or existing.msp_id != body.msp_id
                or existing.modalidad != "corporativo"
                or org.privacy_contact != body.privacy_contact
                or org.privacy_notice_url != body.privacy_notice_url
                or org.privacy_notice_version != body.privacy_notice_version):
            raise HTTPException(409, "Referencia de alta reutilizada con información distinta")
        return view(existing, org, body.owner_user_id)

    tenant = Condominio(
        condominio_id=tenant_id, msp_id=body.msp_id, nombre=body.nombre,
        modalidad="corporativo", corporativo_habilitado=False,
    )
    org = CorporateOrganization(
        tenant_id=tenant_id, privacy_contact=body.privacy_contact,
        privacy_notice_url=body.privacy_notice_url,
        privacy_notice_version=body.privacy_notice_version,
    )
    owner = CorporateMembership(
        membership_id="cpm_" + uuid.uuid4().hex, tenant_id=tenant_id,
        user_id=body.owner_user_id, rol="owner", estado="activo",
    )
    try:
        provisioner.add(tenant)
        provisioner.flush()
        provisioner.add(org)
        provisioner.flush()
        provisioner.add(owner)
        audit(provisioner, tenant_id, actor, request, "crear_empresa")
        provisioner.commit()
        return view(tenant, org, body.owner_user_id)
    except IntegrityError as exc:
        provisioner.rollback()
        raise HTTPException(409, "Alta concurrente o datos corporativos inconsistentes; consulta la referencia") from exc
    except Exception:
        provisioner.rollback()
        raise


def require_company(provisioner: Session, tenant_id: str):
    _set_postgres_tenant(provisioner, tenant_id)
    tenant = provisioner.query(Condominio).filter_by(
        condominio_id=tenant_id, modalidad="corporativo").with_for_update().first()
    org = provisioner.query(CorporateOrganization).filter_by(tenant_id=tenant_id).first()
    if not tenant or not org:
        raise HTTPException(404, "Empresa no encontrada")
    return tenant, org


def has_tenant_policy(gov: Session, tenant_id: str, action: str) -> bool:
    now = datetime.utcnow()
    rows = gov.query(Policy.limites).filter(
        Policy.ambito == PolicyScope.TENANT,
        Policy.target_tenant_id == tenant_id,
        Policy.accion_objetivo == action,
        Policy.estado == GovStatus.ACTIVO,
        Policy.valida_desde <= now,
        (Policy.valida_hasta.is_(None) | (Policy.valida_hasta >= now)),
    ).all()
    return bool(rows) and all(
        isinstance(limits.get("max_count"), int)
        and not isinstance(limits.get("max_count"), bool)
        and 1 <= limits["max_count"] <= 2000
        for (limits,) in rows
    )


@router.post("/empresas/{tenant_id}/habilitar-directorio")
def activate_directory(
    tenant_id: str, body: ActivateDirectory, request: Request,
    gov: Session = Depends(get_gov_db),
    provisioner: Session = Depends(get_provisioning_db),
    actor: Usuario = Depends(get_current_user),
):
    require_global(gov, actor)
    require_provisioner_role(provisioner)
    if body.confirmacion is not True:
        raise HTTPException(422, "Confirma explícitamente la habilitación del directorio")
    tenant, org = require_company(provisioner, tenant_id)
    if not org.privacy_contact or not org.privacy_notice_url or not org.privacy_notice_version:
        raise HTTPException(409, "Falta aviso y responsable de privacidad")
    owner = provisioner.query(CorporateMembership).filter_by(
        tenant_id=tenant_id, rol="owner", estado="activo").first()
    if not owner:
        raise HTTPException(409, "Empresa sin owner activo")
    for action in ("crear_sede_corporativa", "crear_destino_corporativo"):
        if not has_tenant_policy(gov, tenant_id, action):
            raise HTTPException(409, "Faltan políticas GOV específicas para directorio corporativo")
    if not tenant.corporativo_habilitado:
        try:
            tenant.corporativo_habilitado = True
            audit(provisioner, tenant_id, actor, request, "habilitar_directorio")
            provisioner.commit()
        except Exception:
            provisioner.rollback()
            raise
    return view(tenant, org, owner.user_id)


def policy_key(tenant_id: str, action: str) -> str:
    # La clave estable permite reintentos sin políticas duplicadas.
    return "cpg_" + hashlib.sha256(f"{tenant_id}:{action}".encode()).hexdigest()[:32]


@router.put("/empresas/{tenant_id}/capacidades")
def configure_directory_limits(
    tenant_id: str, body: DirectoryLimits, request: Request,
    gov: Session = Depends(get_gov_db),
    provisioner: Session = Depends(get_provisioning_db),
    actor: Usuario = Depends(get_current_user),
):
    """Dos cuotas de catálogo, no tarifas ni autorización de ingreso de visitas.

    CORE y GOV viven en bases independientes: se registra primero la solicitud
    en la outbox CORE. Si GOV falla, no se declara una actualización completada.
    """
    require_global(gov, actor)
    require_provisioner_role(provisioner)
    require_company(provisioner, tenant_id)
    specifications = (
        ("crear_sede_corporativa", body.max_sedes),
        ("crear_destino_corporativo", body.max_destinos_por_sede),
    )
    # Permisos explícitos desde Superadmin: no copiar una política GLOBAL
    # de otro cliente y no cambiar reglas de un condominio residencial.
    keys = [policy_key(tenant_id, name) for name, _ in specifications]
    rows = gov.query(Policy).filter(Policy.policy_id.in_(keys)).with_for_update().all()
    mapped = {p.policy_id: p for p in rows}
    for name, limit in specifications:
        key = policy_key(tenant_id, name)
        found = mapped.get(key)
        if found and (found.target_tenant_id != tenant_id
                      or found.accion_objetivo != name
                      or found.ambito != PolicyScope.TENANT):
            raise HTTPException(409, "Identificador de política ocupado")
    if all(
        mapped.get(policy_key(tenant_id, name)) is not None
        and mapped[policy_key(tenant_id, name)].estado == GovStatus.ACTIVO
        and mapped[policy_key(tenant_id, name)].limites == {"max_count": limit}
        for name, limit in specifications
    ):
        return {"tenant_id": tenant_id, "max_sedes": body.max_sedes,
                "max_destinos_por_sede": body.max_destinos_por_sede}
    try:
        audit(provisioner, tenant_id, actor, request, "solicitar_capacidades_directorio")
        provisioner.commit()
        for name, limit in specifications:
            key = policy_key(tenant_id, name)
            existing = mapped.get(key)
            if existing:
                existing.limites = {"max_count": limit}
                existing.estado = GovStatus.ACTIVO
                existing.valida_desde = datetime.utcnow()
                existing.valida_hasta = None
            else:
                gov.add(Policy(
                    policy_id=key, nombre="Cupo " + name,
                    ambito=PolicyScope.TENANT, target_tenant_id=tenant_id,
                    accion_objetivo=name, limites={"max_count": limit},
                    estado=GovStatus.ACTIVO,
                ))
        gov.commit()
        _set_postgres_tenant(provisioner, tenant_id)
        audit(provisioner, tenant_id, actor, request, "confirmar_capacidades_directorio")
        provisioner.commit()
    except IntegrityError as exc:
        gov.rollback()
        provisioner.rollback()
        raise HTTPException(409, "Conflicto de configuración; vuelve a consultar") from exc
    except Exception:
        gov.rollback()
        provisioner.rollback()
        raise
    return {"tenant_id": tenant_id, "max_sedes": body.max_sedes,
            "max_destinos_por_sede": body.max_destinos_por_sede}
