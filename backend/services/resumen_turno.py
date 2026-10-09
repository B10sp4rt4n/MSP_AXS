"""Proyección de solo lectura; no reescribe el estado ni el historial de visitas."""
from datetime import datetime
from backend.db.core import Visita, EventOutbox
from backend.services import qr_service


def permiso_temporal(visita, now):
    if visita.estado == 'cancelada':
        return 'cancelado'
    if visita.entrada_registrada_en or visita.salida_registrada_en:
        return 'utilizado'
    if visita.estado not in ('pendiente', 'activa'):
        return 'finalizado'
    ends = []
    start = None
    # Sólo proyectar permisos temporales existentes. No inventar vigencia para
    # accesos manuales sin QR ni autorización previa.
    if not visita.qr_token and not visita.autorizada_por:
        return 'sin_permiso_temporal'
    if visita.qr_token:
        if not visita.qr_vigencia:
            return 'sin_vigencia'
        ends.append(qr_service.as_utc(visita.qr_vigencia))
    if visita.vigencia:
        start, end = qr_service.ventana_visita(visita.vigencia)
        ends.append(end)
    if not ends:
        return 'sin_vigencia'
    if now >= min(ends):
        return 'vencido'
    if start and now < start:
        return 'por_iniciar'
    return 'vigente'


def resumir(db, tenant, inicio, fin):
    now = qr_service.utc_now()
    rows = db.query(Visita).filter(Visita.condominio_id == tenant).all()
    def before(dt, limit):
        return dt is not None and qr_service.as_utc(dt) < limit
    def during(dt):
        return dt is not None and inicio <= qr_service.as_utc(dt) < fin
    def inside_at(v, t):
        return before(v.entrada_registrada_en, t) and not before(v.salida_registrada_en, t)
    initial = sum(inside_at(v, inicio) for v in rows)
    entries = sum(during(v.entrada_registrada_en) for v in rows)
    exits = sum(during(v.salida_registrada_en) for v in rows)
    final = sum(inside_at(v, fin) for v in rows)
    invalid = [v.visita_id for v in rows if v.salida_registrada_en and (
        not v.entrada_registrada_en or v.salida_registrada_en < v.entrada_registrada_en)]
    rejects = cancellations = pending_delivery = 0
    # CORE outbox conserva tanto eventos entregados como pendientes. Contarlos
    # una sola vez aquí evita depender de la disponibilidad de EVENT.
    for event in db.query(EventOutbox).filter(EventOutbox.condominio_id == tenant).all():
        payload = event.payload
        if payload.get('entidad') not in ('visita', 'qr') or not during(event.created_at):
            continue
        rejects += payload.get('resultado') in ('denegado', 'fallo')
        cancellations += payload.get('accion') == 'revocar' and payload.get('resultado') == 'exito'
        pending_delivery += event.delivered_at is None
    pending = [v for v in rows if v.estado in ('pendiente', 'activa') and not v.entrada_registrada_en]
    permissions = {name: 0 for name in ('vigente','vencido','por_iniciar','sin_permiso_temporal','sin_vigencia')}
    for v in pending:
        permissions[permiso_temporal(v, now)] += 1
    return {'condominio_id': tenant, 'inicio': inicio, 'fin_exclusivo': fin, 'calculado_en': now,
            'turno': {'dentro_al_inicio': initial, 'entradas': entries, 'salidas': exits,
                      'dentro_al_cierre': final, 'reconciliado': not invalid and initial + entries - exits == final,
                      'cancelaciones_registradas': cancellations, 'rechazos_registrados': rejects,
                      'eventos_pendientes_entrega': pending_delivery},
            'actual': {'dentro': sum(bool(v.entrada_registrada_en) and not v.salida_registrada_en for v in rows),
                       'permisos_pendientes': permissions},
            'visitas_inconsistentes': invalid,
            'fuente_rechazos_cancelaciones': 'CORE EventOutbox; intentos fuera de scope pertenecen a seguridad global'}
