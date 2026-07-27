import sqlite3
import json
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def get_base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()
DB_PATH = os.path.join(BASE_PATH, 'trading_app.db')


def get_db_connection(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_db(db_path: str = DB_PATH):
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            balance REAL NOT NULL,
            initial_balance REAL NOT NULL,
            total_equity REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            side TEXT NOT NULL,
            entry_price REAL NOT NULL,
            quantity REAL NOT NULL,
            tp REAL,
            sl REAL,
            unrealized_pnl REAL DEFAULT 0.0,
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            side TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            quantity REAL NOT NULL,
            pnl REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS license_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hwid TEXT NOT NULL UNIQUE,
            license_key TEXT,
            valid INTEGER DEFAULT 0,
            expiry TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            score REAL NOT NULL,
            signal TEXT NOT NULL,
            candles_used INTEGER NOT NULL,
            model_loaded INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized at %s", db_path)


class Storage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        if not os.path.exists(self.db_path):
            initialize_db()

    def get_connection(self):
        if not os.path.exists(self.db_path):
            initialize_db(self.db_path)
        return get_db_connection(self.db_path)

    def save_account_snapshot(self, balance: float, initial_balance: float, total_equity: float):
        conn = self.get_connection()
        try:
            conn.execute(
                "INSERT INTO account_snapshots (balance, initial_balance, total_equity, timestamp) VALUES (?, ?, ?, ?)",
                (balance, initial_balance, total_equity, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_latest_balance(self) -> Optional[dict]:
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT balance, initial_balance, total_equity FROM account_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                return {
                    "balance": row["balance"],
                    "initial_balance": row["initial_balance"],
                    "total_equity": row["total_equity"],
                }
            return None
        finally:
            conn.close()

    def save_position(self, side: str, entry_price: float, quantity: float, tp: Optional[float], sl: Optional[float]) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO positions (side, entry_price, quantity, tp, sl, unrealized_pnl, timestamp) VALUES (?, ?, ?, ?, ?, 0.0, ?)",
                (side, entry_price, quantity, tp, sl, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def delete_position(self, position_id: int):
        conn = self.get_connection()
        try:
            conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
            conn.commit()
        finally:
            conn.close()

    def save_prediction(self, score: float, signal: str, candles_used: int, model_loaded: bool):
        conn = self.get_connection()
        try:
            conn.execute(
                "INSERT INTO predictions (timestamp, score, signal, candles_used, model_loaded) VALUES (?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), score, signal, candles_used, 1 if model_loaded else 0)
            )
            conn.commit()
        finally:
            conn.close()

    def get_predictions(self, limit: int = 100) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "score": r["score"],
                    "signal": r["signal"],
                    "candles_used": r["candles_used"],
                    "model_loaded": bool(r["model_loaded"]),
                }
                for r in rows
            ]
        finally:
            conn.close()

    def update_position_unrealized_pnl(self, position_id: int, unrealized_pnl: float):
        conn = self.get_connection()
        try:
            conn.execute(
                "UPDATE positions SET unrealized_pnl = ? WHERE id = ?",
                (unrealized_pnl, position_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_open_positions(self) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute("SELECT * FROM positions WHERE 1=1").fetchall()
            return [
                {
                    "id": r["id"],
                    "side": r["side"],
                    "entry_price": r["entry_price"],
                    "quantity": r["quantity"],
                    "tp": r["tp"],
                    "sl": r["sl"],
                    "unrealized_pnl": r["unrealized_pnl"],
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def save_trade(self, side: str, entry_price: float, exit_price: float, quantity: float, pnl: float):
        conn = self.get_connection()
        try:
            conn.execute(
                "INSERT INTO trades (side, entry_price, exit_price, quantity, pnl, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (side, entry_price, exit_price, quantity, pnl, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_trade_history(self, limit: int = 100) -> list:
        conn = self.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "side": r["side"],
                    "entry_price": r["entry_price"],
                    "exit_price": r["exit_price"],
                    "quantity": r["quantity"],
                    "pnl": r["pnl"],
                    "timestamp": r["timestamp"],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def save_license_state(self, hwid: str, license_key: str, valid: bool, expiry: Optional[str]):
        conn = self.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO license_cache (hwid, license_key, valid, expiry, updated_at) VALUES (?, ?, ?, ?, ?)",
                (hwid, license_key, 1 if valid else 0, expiry, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def load_license_state(self, hwid: str) -> Optional[dict]:
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT license_key, valid, expiry FROM license_cache WHERE hwid = ?", (hwid,)
            ).fetchone()
            if row:
                return {
                    "license_key": row["license_key"],
                    "valid": bool(row["valid"]),
                    "expiry": row["expiry"],
                }
            return None
        finally:
            conn.close()

    def migrate_positions(self, positions_data: list):
        conn = self.get_connection()
        try:
            for pos in positions_data:
                conn.execute(
                    "INSERT OR IGNORE INTO positions (side, entry_price, quantity, tp, sl, unrealized_pnl, timestamp) VALUES (?, ?, ?, ?, ?, 0.0, ?)",
                    (
                        pos.get("side"),
                        pos.get("entry_price"),
                        pos.get("quantity"),
                        pos.get("tp"),
                        pos.get("sl"),
                        pos.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    )
                )
            conn.commit()
        finally:
            conn.close()

    def migrate_trades(self, trades_data: list):
        conn = self.get_connection()
        try:
            for trade in trades_data:
                conn.execute(
                    "INSERT OR IGNORE INTO trades (side, entry_price, exit_price, quantity, pnl, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        trade.get("side"),
                        trade.get("entry_price"),
                        trade.get("exit_price"),
                        trade.get("quantity"),
                        trade.get("pnl"),
                        trade.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    )
                )
            conn.commit()
        finally:
            conn.close()


_storage_instance: Optional[Storage] = None


def get_storage() -> Storage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = Storage()
    return _storage_instance