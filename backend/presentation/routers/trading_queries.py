from fastapi import APIRouter

router = APIRouter()


@router.get("/balance")
async def get_balance() -> dict:
    return {"balance": 10000.0, "initial_balance": 10000.0, "unrealized_pnl": 0.0, "total_equity": 10000.0, "positions_count": 0}


@router.get("/positions")
async def get_positions() -> dict:
    return {"positions": []}


@router.get("/history")
async def get_history() -> dict:
    return {"history": []}
