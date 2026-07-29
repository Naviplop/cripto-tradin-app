from fastapi import APIRouter

from application.dtos.admin import AdminIssueRequestDTO as AdminIssueRequest, AdminRevokeRequestDTO as AdminRevokeRequest

router = APIRouter()


@router.get("/licenses")
async def admin_list_licenses() -> dict:
    return {"licenses": [], "revoked": []}


@router.post("/issue")
async def admin_issue_license(request: AdminIssueRequest) -> dict:
    return {"license_key": "", "record": {}}


@router.post("/revoke")
async def admin_revoke_license(request: AdminRevokeRequest) -> dict:
    return {"status": "revoked", "hwid": request.target_hwid}


@router.delete("/licenses")
async def admin_delete_licenses() -> dict:
    return {"status": "cleared"}
