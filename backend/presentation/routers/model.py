from fastapi import APIRouter

from presentation.schemas.model import ModelStatusResponse, ModelUpdateRequest

router = APIRouter()


@router.get("/status", response_model=ModelStatusResponse)
async def model_status() -> dict:
    return {"loaded": False, "features": [], "window_size": 30}


@router.post("/update")
async def update_model(request: ModelUpdateRequest) -> dict:
    return {"status": "updated", "path": "", "loaded": False}
