"""AXS Corporativo: alta y habilitación del DIRECTORIO por Superadmin.

Este flujo no habilita visitantes, QR, biometría ni piloto real. Un usuario
con rol MSP_ADMIN pero sin autoridad GLOBAL no puede aprovisionar empresas.
"""
import uuid
from datetime import datetime
import hashlib
import json
from copy import deepcopy
import os
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import require_platform_operator
from backend.core.tenant.context import _set_postgres_tenant
from backend.db.core import (
    Condominio, CorporateMembership, CorporateOrganization, MSP, Usuario, get_core_db,
)
from backend.db.core.corporate_operations import CorporateProvisioningOperation
from backend.db.gov import Policy, PolicyScope, GovStatus, get_gov_db
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.services.corporate_provisioner_db import (
    get_provisioning_db, provisioning_enabled, require_provisioner_role,
)

def private_response(response: Response):
    """No almacenar respuestas administrativas, contactos ni configuración."""
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/plataforma/corporativo", tags=["Superadmin Corporativo"],
    dependencies=[Depends(provisioning_enabled), Depends(private_response)],
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
    request_id: uuid.UUID
    expected_revision: int = Field(ge=0, strict=True)
    max_sedes: int = Field(ge=1, le=1000, strict=True)
    max_destinos_por_sede: int = Field(ge=1, le=2000, strict=True)


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


def audit(db, tenant_id: str, actor: Usuario, request: Request, accion: str, *, metadata=None):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    return encolar_evento(db, tenant_id, tenant_id, contexto_evento(
        actor, token, entidad="empresa_corporativa", accion=accion,
        motivo="Cambio de aprovisionamiento autorizado"),
        metadata={"accion": accion, **(metadata or {})})


@router.get("/acceso")
def access_status(
    gov: Session = Depends(get_gov_db),
    actor: Usuario = Depends(get_current_user),
):
    # La navegación no confía en el rol MSP_ADMIN. Se controla AUP_GOV GLOBAL.
    require_global(gov, actor)
    return {"authorized": True, "provisioning_enabled": True,
            "credencial_configurada": bool(os.getenv("DATABASE_CORPORATE_PROVISIONING_URL", "").strip())}


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


def current_directory_limit(policy: Policy | None, action: str, now: datetime) -> int | None:
    """One definition of a usable quota for GET, PUT replay, and activation."""
    maximum = {"crear_sede_corporativa": 1000, "crear_destino_corporativo": 2000}.get(action)
    if (not policy or maximum is None or policy.estado != GovStatus.ACTIVO
            or not isinstance(policy.limites, dict)):
        return None
    value = policy.limites.get("max_count")
    if type(value) is not int or not 1 <= value <= maximum:
        return None
    if not isinstance(policy.valida_desde, datetime) or policy.valida_desde > now:
        return None
    if policy.valida_hasta is not None and (
            not isinstance(policy.valida_hasta, datetime) or policy.valida_hasta < now):
        return None
    return value


def has_tenant_policy(gov: Session, tenant_id: str, action: str) -> bool:
    _set_postgres_tenant(gov, tenant_id)
    now = datetime.utcnow()
    rows = gov.query(Policy).filter(
        Policy.ambito == PolicyScope.TENANT,
        Policy.target_tenant_id == tenant_id,
        Policy.accion_objetivo == action,
        Policy.estado == GovStatus.ACTIVO,
        Policy.valida_desde <= now,
        (Policy.valida_hasta.is_(None) | (Policy.valida_hasta >= now)),
    ).all()
    return bool(rows) and all(current_directory_limit(policy, action, now) is not None
                              for policy in rows)


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
    operation, confirmed = quota_operation_status(provisioner, tenant_id, quota_rows(gov, tenant_id))
    if not confirmed:
        raise HTTPException(409, "Las capacidades requieren conciliación confirmada CORE/GOV")
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


def quota_rows(gov: Session, tenant_id: str, *, lock=False, validate=True):
    _set_postgres_tenant(gov, tenant_id)
    keys = [policy_key(tenant_id, action) for action in (
        "crear_sede_corporativa", "crear_destino_corporativo")]
    query = gov.query(Policy).filter(Policy.policy_id.in_(keys)).order_by(Policy.policy_id)
    if lock:
        query = query.with_for_update().populate_existing()
    rows = {row.policy_id: row for row in query.all()}
    for action in ("crear_sede_corporativa", "crear_destino_corporativo") if validate else ():
        row = rows.get(policy_key(tenant_id, action))
        if row and row.metadata_json is not None and not isinstance(row.metadata_json, dict):
            raise HTTPException(409, "Metadata GOV incompatible; requiere revisión")
        if row and (row.target_tenant_id != tenant_id or row.accion_objetivo != action
                    or row.ambito != PolicyScope.TENANT):
            raise HTTPException(409, "Identificador de política ocupado")
    return rows


def quota_snapshot(rows):
    """Compare the complete managed policy state, not just its quota."""
    snapshots = {key: {
        "policy_id": row.policy_id, "nombre": row.nombre, "descripcion": row.descripcion,
        "ambito": row.ambito.value, "target_tenant_id": row.target_tenant_id,
        "accion_objetivo": row.accion_objetivo, "limites": deepcopy(row.limites),
        "estado": row.estado.value,
        "valida_desde": row.valida_desde.isoformat() if row.valida_desde else None,
        "valida_hasta": row.valida_hasta.isoformat() if row.valida_hasta else None,
        "metadata_json": deepcopy(row.metadata_json),
    } for key, row in rows.items()}
    # Do not copy arbitrary GOV descriptions/metadata into CORE's journal.
    return {key: hashlib.sha256(json.dumps(value, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest() for key, value in snapshots.items()}


def operation_marker(operation):
    return {"request_id": operation.request_id, "payload_hash": operation.payload_hash,
            "revision": operation.revision}


def operation_matches_gov(operation, rows):
    now = datetime.utcnow()
    for action, field in (("crear_sede_corporativa", "max_sedes"),
                          ("crear_destino_corporativo", "max_destinos_por_sede")):
        row = rows.get(policy_key(operation.tenant_id, action))
        if (not row or row.target_tenant_id != operation.tenant_id
                or row.accion_objetivo != action or row.ambito != PolicyScope.TENANT
                or current_directory_limit(row, action, now) != operation.payload[field]
                or row.limites != {"max_count": operation.payload[field]}
                or not isinstance(row.metadata_json, dict)
                or row.metadata_json.get("axs_corporate_operation") != operation_marker(operation)):
            return False
    return True


def quota_operation_status(provisioner, tenant_id, rows):
    try:
        operation = provisioner.query(CorporateProvisioningOperation).filter_by(
            tenant_id=tenant_id).order_by(CorporateProvisioningOperation.revision.desc()).first()
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Registro de conciliación no disponible; operación bloqueada") from exc
    confirmed = bool(operation and operation.estado == "confirmed"
                     and operation_matches_gov(operation, rows))
    return operation, confirmed


def operation_view(operation):
    if not operation:
        return None
    return {"request_id": operation.request_id, "estado": operation.estado,
            "revision": operation.revision, "expected_revision": operation.revision - 1,
            **operation.payload}


def operation_response(operation):
    return {"tenant_id": operation.tenant_id, **operation_view(operation),
            "cuotas": dict(operation.payload)}


def rollback_quietly(*sessions):
    for session in sessions:
        try:
            session.rollback()
        except Exception:
            pass  # A broken connection cannot establish whether its commit happened.


@router.put("/empresas/{tenant_id}/capacidades")
def configure_directory_limits(
    tenant_id: str, body: DirectoryLimits, request: Request,
    gov: Session = Depends(get_gov_db),
    provisioner: Session = Depends(get_provisioning_db),
    actor: Usuario = Depends(get_current_user),
):
    """Durable CORE intent -> atomic GOV pair -> atomic CORE confirmation.

    Locks always follow CORE(company, operation) -> GOV(ordered policy keys).
    A retry never infers success from coincidentally equal numeric quotas.
    """
    require_global(gov, actor)
    require_provisioner_role(provisioner)
    tenant_id = validated_company_id(tenant_id)
    request_id = str(body.request_id)
    payload = {"max_sedes": body.max_sedes, "max_destinos_por_sede": body.max_destinos_por_sede}
    payload_hash = hashlib.sha256(json.dumps({"contract": "corporate-quota-v1",
        "tenant_id": tenant_id, "expected_revision": body.expected_revision,
        "payload": payload}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    try:
        require_company(provisioner, tenant_id)
        operation = provisioner.query(CorporateProvisioningOperation).filter_by(
            tenant_id=tenant_id, request_id=request_id).with_for_update().first()
        latest = provisioner.query(CorporateProvisioningOperation).filter_by(
            tenant_id=tenant_id).order_by(CorporateProvisioningOperation.revision.desc()).first()
        if operation and (operation.payload_hash != payload_hash or operation.payload != payload):
            raise HTTPException(409, "Referencia de capacidades reutilizada con información distinta")
        if latest and latest.request_id != request_id and latest.estado != "confirmed":
            raise HTTPException(409, "Hay una conciliación pendiente; consulta la empresa")
        if operation and operation.estado == "needs_review":
            raise HTTPException(409, "La conciliación requiere revisión de deriva GOV")
        if operation and latest.request_id != request_id:
            raise HTTPException(409, "Operación sustituida; consulta la revisión vigente")
        if not operation:
            revision = latest.revision if latest else 0
            if body.expected_revision != revision:
                raise HTTPException(409, "Revisión obsoleta; consulta la empresa antes de cambiar cuotas")
            expected_gov = quota_snapshot(quota_rows(gov, tenant_id))
            # Never carry a preliminary GOV transaction into a new CORE lock.
            gov.rollback()
            operation = CorporateProvisioningOperation(
                tenant_id=tenant_id, request_id=request_id, revision=revision + 1,
                payload=payload, payload_hash=payload_hash, requested_by=actor.usuario_id,
                expected_gov=expected_gov, estado="pending")
            operation.request_event_uid = audit(provisioner, tenant_id, actor, request,
                "solicitar_capacidades_directorio", metadata=operation_marker(operation))
            provisioner.add(operation)
            provisioner.commit()
            # Reacquire after durable preparation. Pending excludes other intentions.
            require_company(provisioner, tenant_id)
            operation = provisioner.query(CorporateProvisioningOperation).filter_by(
                tenant_id=tenant_id, request_id=request_id).populate_existing().with_for_update().one()
        # Another retry can finish or flag the operation during the prepare gap.
        latest = provisioner.query(CorporateProvisioningOperation).filter_by(
            tenant_id=tenant_id).order_by(CorporateProvisioningOperation.revision.desc()).populate_existing().first()
        if operation.estado == "needs_review":
            raise HTTPException(409, "La conciliación requiere revisión de deriva GOV")
        if latest.request_id != request_id:
            raise HTTPException(409, "Operación sustituida; consulta la revisión vigente")
        def locked_rows_or_review():
            try:
                return quota_rows(gov, tenant_id, lock=True)
            except HTTPException:
                if operation.estado == "pending":
                    operation.estado = "needs_review"
                    audit(provisioner, tenant_id, actor, request,
                          "conflicto_capacidades_directorio", metadata=operation_marker(operation))
                    provisioner.commit()
                raise
        rows = locked_rows_or_review()
        if operation.estado == "confirmed":
            if not operation_matches_gov(operation, rows):
                raise HTTPException(409, "La operación confirmada ya no representa GOV; consulta y crea otra")
            return operation_response(operation)
        if not operation_matches_gov(operation, rows):
            # An unchanged snapshot permits first apply, never a stale overwrite.
            if quota_snapshot(rows) != operation.expected_gov:
                operation.estado = "needs_review"
                audit(provisioner, tenant_id, actor, request,
                      "conflicto_capacidades_directorio", metadata=operation_marker(operation))
                provisioner.commit()
                raise HTTPException(409, "GOV cambió durante la conciliación; requiere revisión")
            for action, field in (("crear_sede_corporativa", "max_sedes"),
                                  ("crear_destino_corporativo", "max_destinos_por_sede")):
                key = policy_key(tenant_id, action)
                row = rows.get(key)
                if row is None:
                    row = Policy(policy_id=key, nombre="Cupo " + action,
                        ambito=PolicyScope.TENANT, target_tenant_id=tenant_id, accion_objetivo=action)
                    gov.add(row)
                row.limites = {"max_count": payload[field]}
                row.estado = GovStatus.ACTIVO
                row.valida_desde = datetime.utcnow()
                row.valida_hasta = None
                row.metadata_json = {**(row.metadata_json or {}),
                                     "axs_corporate_operation": operation_marker(operation)}
            gov.commit()
            # Check committed data under lock, not the expired ORM identity map.
            rows = locked_rows_or_review()
            if not operation_matches_gov(operation, rows):
                operation.estado = "needs_review"
                audit(provisioner, tenant_id, actor, request,
                      "conflicto_capacidades_directorio", metadata=operation_marker(operation))
                provisioner.commit()
                raise HTTPException(409, "GOV no conserva la operación aplicada; requiere revisión")
        operation.confirmation_event_uid = audit(provisioner, tenant_id, actor, request,
            "confirmar_capacidades_directorio", metadata={**operation_marker(operation),
                                                       "requested_by": operation.requested_by})
        operation.estado = "confirmed"
        operation.confirmed_at = datetime.utcnow()
        # Immutable response captured before commit can never trigger a late lazy SELECT.
        response = operation_response(operation)
        provisioner.commit()
        gov.rollback()
        return response
    except HTTPException:
        rollback_quietly(gov, provisioner)
        raise
    except Exception as exc:
        rollback_quietly(gov, provisioner)
        raise HTTPException(503, detail={"code": "CORPORATE_OPERATION_UNCERTAIN",
            "request_id": request_id, "message": "Resultado incierto; reintenta la misma referencia y datos"}) from exc


# Consulta y reanudación de operaciones existentes, importadas de C3 #99.
def validated_company_id(tenant_id: str) -> str:
    if not re.fullmatch(r"corp_[0-9a-f]{32}", tenant_id):
        raise HTTPException(404, "Empresa no encontrada")
    return tenant_id


@router.get("/usuarios/{user_id}")
def owner_preview(
    user_id: str, core: Session = Depends(get_core_db),
    gov: Session = Depends(get_gov_db),
    actor: Usuario = Depends(get_current_user),
):
    require_global(gov, actor)
    person = core.query(Usuario).filter(Usuario.usuario_id == user_id).first()
    if not person:
        raise HTTPException(404, "Usuario no encontrado")
    return {"usuario_id": person.usuario_id, "nombre": person.nombre or "",
            "email": person.email or ""}


@router.get("/empresas/{tenant_id}")
def company_status(
    tenant_id: str, gov: Session = Depends(get_gov_db),
    provisioner: Session = Depends(get_provisioning_db),
    actor: Usuario = Depends(get_current_user),
):
    """Consultar una empresa conocida, sin listado global que omita RLS."""
    require_global(gov, actor)
    require_provisioner_role(provisioner)
    tenant_id = validated_company_id(tenant_id)
    tenant, org = require_company(provisioner, tenant_id)
    owner = provisioner.query(CorporateMembership).filter_by(
        tenant_id=tenant_id, rol="owner", estado="activo").first()
    if not owner:
        raise HTTPException(409, "Empresa sin owner activo")
    details = view(tenant, org, owner.user_id)
    details["privacy_notice_url"] = org.privacy_notice_url
    details["capacidades"] = {}
    _set_postgres_tenant(gov, tenant_id)
    now = datetime.utcnow()
    for action, name in (("crear_sede_corporativa", "max_sedes"),
                         ("crear_destino_corporativo", "max_destinos_por_sede")):
        key = policy_key(tenant_id, action)
        policy = gov.query(Policy).filter(
            Policy.policy_id == key, Policy.ambito == PolicyScope.TENANT,
            Policy.target_tenant_id == tenant_id, Policy.accion_objetivo == action,
            Policy.estado == GovStatus.ACTIVO,
        ).first()
        details["capacidades"][name] = current_directory_limit(policy, action, now)
    operation, confirmed = quota_operation_status(
        provisioner, tenant_id, quota_rows(gov, tenant_id, validate=False))
    details["capacidades_operacion"] = operation_view(operation)
    details["capacidades_revision"] = operation.revision if operation else 0
    details["capacidades_confirmadas"] = confirmed
    return details
