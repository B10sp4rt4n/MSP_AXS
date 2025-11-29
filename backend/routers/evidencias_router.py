from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["evidencias"])
def list_evidencias():
    return {"evidencias": []}
