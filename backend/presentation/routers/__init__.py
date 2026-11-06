from presentation.routers.admin import router as admin_router
from presentation.routers.auth import router as auth_router
from presentation.routers.config import router as config_router
from presentation.routers.health import router as health_router
from presentation.routers.license import router as license_router
from presentation.routers.market import router as market_router
from presentation.routers.model import router as model_router
from presentation.routers.trading_commands import router as trading_commands_router
from presentation.routers.trading_queries import router as trading_queries_router

__all__ = [
    "admin_router",
    "auth_router",
    "config_router",
    "health_router",
    "license_router",
    "market_router",
    "model_router",
    "trading_commands_router",
    "trading_queries_router",
]
