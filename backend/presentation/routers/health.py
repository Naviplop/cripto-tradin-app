from fastapi import APIRouter

from presentation.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> dict:
    return {
        "status": "ok",
        "license_valid": False,
        "hwid": "unknown",
    }
