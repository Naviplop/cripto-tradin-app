from fastapi import APIRouter

from presentation.schemas.trading import ApiKeyRequest

router = APIRouter()


@router.post("/verify-keys")
async def verify_keys(request: ApiKeyRequest) -> dict:
    return {"valid": True}


@router.post("/api-keys")
async def save_keys(request: ApiKeyRequest) -> dict:
    return {"status": "saved"}


@router.get("/api-keys")
async def get_keys() -> dict:
    return {"api_key": None, "api_secret": None, "paper_mode": True}


@router.delete("/api-keys")
async def delete_keys() -> dict:
    return {"status": "cleared"}
