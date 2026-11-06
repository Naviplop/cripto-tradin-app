from pydantic import BaseModel


class ApiKeyRequestDTO(BaseModel):
    api_key: str
    api_secret: str
    paper_mode: bool = True


class ApiKeyResponseDTO(BaseModel):
    api_key: str | None = None
    api_secret: str | None = None
    paper_mode: bool = True


class SystemSettingsDTO(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1m"
    binance_ws_url: str = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
    trading_app_data_dir: str | None = None
