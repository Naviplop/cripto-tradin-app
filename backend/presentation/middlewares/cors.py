from __future__ import annotations

import os
import re
from typing import Iterable, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI, allowed_origins: Iterable[str], regex_pattern: str = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$|^null$") -> None:
    combined = list(allowed_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=regex_pattern,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )
