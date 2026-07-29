from pydantic import BaseModel


class LicenseRequest(BaseModel):
    license_key: str


class ApiKeyRequest(BaseModel):
    api_key: str
    api_secret: str
    paper_mode: bool = True


class OrderRequest(BaseModel):
    side: str
    order_type: str
    quantity: float
    price: float | None = None
    tp: float | None = None
    sl: float | None = None
    stop_price: float | None = None
    limit_price: float | None = None


class OrderResponse(BaseModel):
    success: bool
    order: dict


class ModelUpdateRequest(BaseModel):
    download_url: str
    version: str | None = None

