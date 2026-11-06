from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


def problem_details(
    status_code: int,
    title: str,
    detail: str | None = None,
    instance: str | None = None,
    errors: list[str] | None = None,
) -> JSONResponse:
    payload = ProblemDetails(
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", by_alias=True),
        media_type="application/problem+json",
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return problem_details(status_code=500, title="Internal Server Error", detail="Internal server error")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, global_exception_handler)
