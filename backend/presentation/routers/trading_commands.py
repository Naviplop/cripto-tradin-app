from fastapi import APIRouter

from presentation.schemas.trading import OrderRequest, OrderResponse

router = APIRouter()


@router.post("/order", response_model=OrderResponse)
async def place_order(request: OrderRequest) -> dict:
    return {"success": True, "order": {"status": "PENDING"}}


@router.get("/signals")
async def get_signals() -> dict:
    return {"signals": {"signal": "NEUTRAL"}}
