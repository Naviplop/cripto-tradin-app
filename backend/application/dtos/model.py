from pydantic import BaseModel


class ModelUpdateRequestDTO(BaseModel):
    download_url: str
    version: str | None = None


class ModelStatusDTO(BaseModel):
    loaded: bool
    features: list[str] = []
    window_size: int = 30
