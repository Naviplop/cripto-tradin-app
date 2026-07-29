from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from presentation.middlewares.cors import setup_cors
from presentation.middlewares.exception_handlers import problem_details
from presentation.middlewares.request_id import RequestIdMiddleware


def setup_rate_limit(app: FastAPI) -> None:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _rate_limit_exceeded_handler(request: Any, exc: RateLimitExceeded) -> Any:
    return problem_details(
        status_code=429,
        title="Rate Limit Exceeded",
        detail=str(exc.detail),
    )


def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
    setup_cors(
        app,
        allowed_origins=[],
        regex_pattern=os.environ.get("CORS_REGEX", r"^http://(localhost|127\.0\.0\.1)(:\d+)?$|^null$"),
    )
    setup_rate_limit(app)
