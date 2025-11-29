from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["condominios"])
def list_condominios():
    return {"condominios": []}
