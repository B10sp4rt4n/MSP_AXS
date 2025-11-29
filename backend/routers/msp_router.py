from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["msp"])
def list_msps():
    return {"msps": []}
