from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["visitas"])
def list_visitas():
    return {"visitas": []}
