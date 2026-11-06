from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    license_secret: str = Field(default="", alias="LICENSE_SECRET")
    admin_api_key: str = Field(default="", alias="ADMIN_API_KEY")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")
    extra_cors_origins: str = Field(default="", alias="EXTRA_CORS_ORIGINS")
    cors_regex: str = Field(default=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$|^null$", alias="CORS_REGEX")
    port: int = Field(default=8765, alias="PORT")
    host: str = Field(default="127.0.0.1", alias="HOST")
    symbol: str = Field(default="BTCUSDT", alias="SYMBOL")
    timeframe: str = Field(default="1m", alias="TIMEFRAME")
    binance_ws_url: str = Field(
        default="wss://stream.binance.com:9443/ws/btcusdt@kline_1m",
        alias="BINANCE_WS_URL",
    )
    trading_app_data_dir: Optional[str] = Field(default=None, alias="TRADING_APP_DATA_DIR")


def get_settings() -> Settings:
    return Settings()
