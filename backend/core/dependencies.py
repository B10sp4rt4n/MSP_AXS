from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.connection import SessionLocal
from ..db.models import Usuario


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_usuario_actual(
    x_user_id: str = Header(..., alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    usuario = db.query(Usuario).filter(Usuario.usuario_id == x_user_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return usuario
