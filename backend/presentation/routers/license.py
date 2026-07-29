from fastapi import APIRouter

from presentation.schemas.license import LicenseRequest, LicenseResponse

router = APIRouter()


@router.options("/validate")
async def validate_license_options() -> dict:
    return {"detail": "OK"}


@router.post("/validate", response_model=LicenseResponse)
async def validate_license(request: LicenseRequest) -> dict:
    return {"valid": False, "message": "Disabled"}
