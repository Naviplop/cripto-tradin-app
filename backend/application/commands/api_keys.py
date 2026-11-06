from __future__ import annotations

from pydantic import BaseModel


class SaveApiKeysCommand(BaseModel):
    api_key: str
    api_secret: str
    paper_mode: bool = True


class GetApiKeysQuery(BaseModel):
    api_key: str | None = None
    api_secret: str | None = None
    paper_mode: bool = True
