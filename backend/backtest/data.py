from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from typing import List, Optional, Union

import numpy as np
import pandas as pd

from domain.entities.candle import Candle


class KlineDataLoader:
    @staticmethod
    def from_dataframe(
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        pair: str = "BTCUSDT",
    ) -> List[Candle]:
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
        candles: List[Candle] = []
        for _, row in df.iterrows():
            ts = pd.Timestamp(row[timestamp_col]).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            candles.append(
                Candle.from_raw(
                    timestamp=ts,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        return candles

    @staticmethod
    def load_csv(path: str, pair: str = "BTCUSDT") -> List[Candle]:
        df = pd.read_csv(path)
        return KlineDataLoader.from_dataframe(df, pair=pair)

    @staticmethod
    def load_json(path: str, pair: str = "BTCUSDT") -> List[Candle]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("klines") or data.get("candles") or data.get("data") or []
        else:
            raise ValueError("Unsupported JSON format")
        df = pd.DataFrame(records)
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            raise ValueError(f"Missing required columns: {required - set(df.columns)}")
        return KlineDataLoader.from_dataframe(df, pair=pair)

    @staticmethod
    def resample(candles: List[Candle], target_timeframe: str) -> List[Candle]:
        if not candles:
            return []
        rows = []
        for c in candles:
            rows.append(
                {
                    "timestamp": c.timestamp,
                    "open": float(c.open.amount),
                    "high": float(c.high.amount),
                    "low": float(c.low.amount),
                    "close": float(c.close.amount),
                    "volume": float(c.volume),
                }
            )
        df = pd.DataFrame(rows)
        df.set_index("timestamp", inplace=True)
        df = df.sort_index()
        rule = target_timeframe.lower()
        ohlcv = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        resampled = df.resample(rule).agg(ohlcv).dropna(subset=["open", "close"])
        out: List[Candle] = []
        for ts, row in resampled.iterrows():
            out.append(
                Candle.from_raw(
                    timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        return out

    @staticmethod
    def align_pairs(
        primary: List[Candle],
        secondary: List[Candle],
        target_timeframe: str,
    ) -> tuple[List[Candle], List[Candle]]:
        primary_idx = {c.timestamp: c for c in primary}
        secondary_idx = {c.timestamp: c for c in secondary}
        common_ts = sorted(set(primary_idx.keys()) & set(secondary_idx.keys()))
        return [primary_idx[t] for t in common_ts], [secondary_idx[t] for t in common_ts]

    @staticmethod
    def to_dataframe(candles: List[Candle]) -> pd.DataFrame:
        rows = []
        for c in candles:
            rows.append(
                {
                    "timestamp": c.timestamp,
                    "open": float(c.open.amount),
                    "high": float(c.high.amount),
                    "low": float(c.low.amount),
                    "close": float(c.close.amount),
                    "volume": float(c.volume),
                }
            )
        df = pd.DataFrame(rows)
        if not df.empty:
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
        return df
