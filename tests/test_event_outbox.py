"""Fallas reales de frontera CORE/EVENT y recuperación con identidad estable."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from backend.db.core import EventOutbox, Evidencia, Visita
from backend.db.event import Event
from backend.services import visita_service
from backend.services.event_outbox import contexto_evento, enviar_pendientes, publicar_evento


@pytest.fixture
def audit():
    return contexto_evento(SimpleNamespace(usuario_id="guard"), "private-session-token")


@pytest.fixture
def pending(db_session, condominio_base, audit):
    data = SimpleNamespace(nombre_visitante="Test", tipo_visita="eventual", vigencia=None)
    visita = visita_service.crear_visita(db_session, data, condominio_base.condominio_id, auditoria=audit)
    return visita


def test_operacion_y_evento_misma_transaccion(db_session, pending, audit):
    visita_service.registrar_entrada(db_session, pending.visita_id, auditoria=audit)
    rows = db_session.query(EventOutbox).order_by(EventOutbox.created_at).all()
    assert len(rows) == 2
    assert rows[-1].payload["metadata_json"]["entrada_registrada_en"]
    assert rows[-1].payload["metadata_json"]["estado"] == "entrada_registrada"
    assert "private-session-token" not in str(rows[-1].payload)
    with pytest.raises(HTTPException):
        visita_service.registrar_entrada(db_session, pending.visita_id, auditoria=audit)
    assert db_session.query(EventOutbox).count() == 2


def test_falla_encolado_revierte_operacion(db_session, pending, audit, monkeypatch):
    def fail(*args):
        raise RuntimeError("outbox unavailable")
    monkeypatch.setattr(visita_service, "encolar_visita", fail)
    with pytest.raises(RuntimeError):
        visita_service.registrar_entrada(db_session, pending.visita_id, auditoria=audit)
    saved = db_session.query(Visita).filter_by(visita_id=pending.visita_id).one()
    assert saved.estado == "pendiente" and saved.entrada_registrada_en is None
    assert db_session.query(EventOutbox).count() == 1


def test_event_caido_no_borra_operacion_y_reintenta(db_session, pending, db_event_engine):
    def unavailable():
        raise ConnectionError("secret connection detail")
    now = datetime.utcnow() + timedelta(seconds=1)
    assert enviar_pendientes(db_session, pending.condominio_id, unavailable, now=now) == 0
    row = db_session.query(EventOutbox).one()
    assert row.attempts == 1 and row.delivered_at is None
    assert row.last_error == "ConnectionError" and row.next_attempt_at > now
    uid, payload = row.event_uid, dict(row.payload)
    factory = sessionmaker(bind=db_event_engine)
    assert enviar_pendientes(db_session, pending.condominio_id, factory, now=now) == 0
    assert enviar_pendientes(db_session, pending.condominio_id, factory, now=now + timedelta(minutes=5)) == 1
    with factory() as event_db:
        event = event_db.query(Event).one()
        assert event.event_uid == uid and event.hash_evento == payload["hash_evento"]
        assert event.timestamp.isoformat() == payload["timestamp"]
    assert db_session.query(Visita).filter_by(visita_id=pending.visita_id).one()


def test_event_confirmado_y_ack_perdido_recupera_sin_duplicar(db_session, pending, db_engine, db_event_engine, monkeypatch):
    core_factory = sessionmaker(bind=db_engine)
    event_factory = sessionmaker(bind=db_event_engine)
    now = datetime.utcnow() + timedelta(seconds=1)
    def lost_ack():
        raise ConnectionError("CORE acknowledgement lost")
    with core_factory() as first:
        monkeypatch.setattr(first, "commit", lost_ack)
        with pytest.raises(ConnectionError):
            enviar_pendientes(first, pending.condominio_id, event_factory, now=now)
        first.rollback()
    with event_factory() as event_db:
        assert event_db.query(Event).count() == 1
    with core_factory() as restarted:
        assert restarted.query(EventOutbox).one().delivered_at is None
        assert enviar_pendientes(restarted, pending.condominio_id, event_factory, now=now) == 1
    with event_factory() as event_db:
        assert event_db.query(Event).count() == 1


def test_conflicto_con_contenido_distinto_no_se_reconoce(db_session, pending, db_event_engine):
    factory = sessionmaker(bind=db_event_engine)
    row = db_session.query(EventOutbox).one()
    with factory() as event_db:
        publicar_evento(event_db, row.payload)
    changed = {**row.payload, "motivo": "different fact"}
    with factory() as event_db:
        with pytest.raises(ValueError):
            publicar_evento(event_db, changed)
    with factory() as event_db:
        assert event_db.query(Event).one().motivo == row.payload["motivo"]


def test_payload_de_otro_tenant_no_se_publica(db_session, pending, db_event_engine):
    row = db_session.query(EventOutbox).one()
    row.payload = {**row.payload, "tenant_id": "other"}
    db_session.commit()
    factory = sessionmaker(bind=db_event_engine)
    assert enviar_pendientes(db_session, pending.condominio_id, factory,
                            now=datetime.utcnow() + timedelta(seconds=1)) == 0
    assert row.last_error == "ValueError" and row.delivered_at is None
    with factory() as event_db:
        assert event_db.query(Event).count() == 0


def test_preregistro_qr_y_eventos_atomicos(db_session, usuario_base, audit):
    usuario_base.casa_unidad = "101"
    db_session.commit()
    data = SimpleNamespace(nombre_visitante="Test", tipo_visita="eventual", fecha_visita=datetime.utcnow(), notas="Test")
    visita = visita_service.crear_desde_preregistro(db_session, data, usuario_base, generar_qr=True, auditoria=audit)
    assert visita.qr_token and visita.qr_vigencia
    assert db_session.query(Evidencia).filter_by(visita_id=visita.visita_id).count() == 1
    rows = db_session.query(EventOutbox).all()
    assert len(rows) == 2 and {r.payload["entidad"] for r in rows} == {"visita", "qr"}
    assert all(r.payload["entidad_id"] == visita.visita_id for r in rows)


def test_preregistro_fallido_no_deja_visita_qr_o_eventos(db_session, usuario_base, audit, monkeypatch):
    from backend.services import qr_service
    usuario_base.casa_unidad = "101"
    db_session.commit()
    def fail(*args, **kwargs):
        raise RuntimeError("QR generation failed")
    monkeypatch.setattr(qr_service, "generar_qr_para_visita", fail)
    data = SimpleNamespace(nombre_visitante="Test", tipo_visita="eventual", fecha_visita=datetime.utcnow(), notas="Test")
    with pytest.raises(RuntimeError):
        visita_service.crear_desde_preregistro(db_session, data, usuario_base, generar_qr=True, auditoria=audit)
    assert db_session.query(Visita).count() == 0
    assert db_session.query(Evidencia).count() == 0
    assert db_session.query(EventOutbox).count() == 0
