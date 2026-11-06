from fastapi import APIRouter

router = APIRouter()


@router.get("/settings")
async def get_settings() -> dict:
    return {}


@router.put("/settings")
async def update_settings() -> dict:
    return {"status": "updated"}
