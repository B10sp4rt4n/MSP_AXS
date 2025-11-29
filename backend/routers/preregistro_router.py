from fastapi import APIRouter

router = APIRouter()


@router.post("/", tags=["preregistro"])
def preregistro(payload: dict):
    # placeholder: validar y crear preregistro
    return {"status": "ok", "payload": payload}
