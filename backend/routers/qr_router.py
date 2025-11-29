from fastapi import APIRouter
from ..services.qr_service import generate_qr

router = APIRouter()


@router.get("/generate", tags=["qr"])
def generate(q: str):
    return {"qr": generate_qr(q)}
