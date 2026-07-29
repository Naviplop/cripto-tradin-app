from pydantic import BaseModel


class ConfigResponse(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1m"
    binance_ws_url: str = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
    trading_app_data_dir: str | None = None


class ModelUpdateRequest(BaseModel):
    download_url: str
    expected_hash: str | None = None


class ModelStatusResponse(BaseModel):
    loaded: bool
    features: list[str] = []
    window_size: int = 30

