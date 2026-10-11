"""Excel onboarding: preview, explicit confirmation and atomic audit."""
import base64
import binascii
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.db.core import (get_core_db, Usuario, Casa, Condominio, UserTenantScope,
                             AccessLevel, ScopeStatus)
from backend.db.gov import get_gov_db
from backend.core.auth.dependencies import get_current_user
from backend.core.scope.msp_boundary import require_condominio
from backend.core.tenant.context import _set_postgres_tenant
from backend.services.event_outbox import contexto_evento, encolar_evento
from backend.services.resident_import import parse_excel, plan_import

router = APIRouter(prefix="/condominios", tags=["importación residentes"])


class ImportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    archivo: str = Field(max_length=2800000)
    revision: str | None = Field(default=None, max_length=64)


@router.get("/{condominio_id}/residentes/plantilla")
def template(condominio_id: str, db: Session = Depends(get_core_db),
             gov: Session = Depends(get_gov_db), actor: Usuario = Depends(get_current_user)):
    require_condominio(db, gov, actor, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    return FileResponse(Path(__file__).parents[1] / "static" / "plantilla_residentes.xlsx",
        filename="AXS_residentes.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.post("/{condominio_id}/residentes/importar")
def import_residents(condominio_id: str, body: ImportBody, request: Request,
                     db: Session = Depends(get_core_db), gov: Session = Depends(get_gov_db),
                     actor: Usuario = Depends(get_current_user)):
    require_condominio(db, gov, actor, condominio_id, AccessLevel.ADMIN_CONDOMINIO)
    _set_postgres_tenant(db, condominio_id)
    # Shared with individual house/resident writes: serialize catalog changes.
    condo = db.query(Condominio).filter_by(condominio_id=condominio_id).with_for_update().one()
    try:
        raw = base64.b64decode(body.archivo, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(400, "Archivo inválido")
    plan = plan_import(db, condominio_id, parse_excel(raw))
    if body.revision is None:
        return {**plan, "confirmado": False}
    if body.revision != plan['revision']:
        raise HTTPException(409, "Los datos cambiaron; vuelve a validar el archivo")
    if plan['errores']:
        raise HTTPException(400, "Corrige las filas con errores antes de importar")
    batch = "imp_" + uuid.uuid4().hex
    created = []
    try:
        for row in plan['filas']:
            if row['estado'] == 'existente': continue
            house = db.query(Casa).filter_by(condominio_id=condominio_id, numero=row['vivienda']).first()
            if house is None:
                house = Casa(casa_id="casa_" + uuid.uuid4().hex, condominio_id=condominio_id,
                             numero=row['vivienda'], tipo=row['tipo'])
                db.add(house)
                db.flush()
            identity = Usuario(usuario_id="user_" + uuid.uuid4().hex, nombre=row['nombre'], email=row['correo'],
                rol="RESIDENTE", condominio_id=condominio_id, casa_id=house.casa_id,
                casa_unidad=house.numero, msp_id=condo.msp_id, password_hash=None)
            db.add(identity)
            db.flush()
            db.add(UserTenantScope(usuario_id=identity.usuario_id, tenant_id=condominio_id,
                access_level=AccessLevel.RESIDENTE, estado=ScopeStatus.ACTIVO,
                metadata_json={"source": "excel", "batch_id": batch, "grant_origin": {
                    "version": 1, "kind": "condominio", "recorded_by": actor.usuario_id,
                    "evidence_ref": "residencia:" + house.casa_id}}))
            created.append({"fila": row['fila'], "usuario_id": identity.usuario_id, "casa_id": house.casa_id})
            row['estado'] = 'creado'
        if created:
            encolar_evento(db, condominio_id, batch, contexto_evento(actor,
                request.headers.get("Authorization", "").removeprefix("Bearer "),
                entidad="resident_import", accion="importar", motivo="Alta por plantilla Excel"),
                metadata={"revision": body.revision, "altas": created})
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Los datos cambiaron; vuelve a validar. No se importó ninguna fila") from exc
    return {**plan, "confirmado": True, "lote": batch, "creados": len(created)}
