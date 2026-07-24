import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from logger import logger


def get_base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()
SECURE_DB_DIR = os.path.join(BASE_PATH, "userdata")
SECURE_DB_PATH = os.path.join(SECURE_DB_DIR, "lafm_secure.db")


def _get_hwid() -> str:
    from license_manager import LicenseManager
    return LicenseManager().get_hardware_id()


def _derive_aes_key(hwid: str) -> bytes:
    key_material = hwid.encode("utf-8")
    return key_material[:32].ljust(32, b"\x00")


def _encrypt(plaintext: str, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    return cipher.nonce + tag + ciphertext


def _decrypt(data: bytes, key: bytes) -> Optional[str]:
    try:
        nonce = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
    except Exception as exc:
        logger.error("Decryption failed: %s", exc)
        return None


def _get_connection():
    os.makedirs(SECURE_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(SECURE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS secure_store (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            api_key_enc BLOB,
            api_secret_enc BLOB,
            paper_mode INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_api_keys(api_key: str, api_secret: str, paper_mode: bool = True):
    hwid = _get_hwid()
    key = _derive_aes_key(hwid)
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO secure_store (id, api_key_enc, api_secret_enc, paper_mode, updated_at) VALUES (1, ?, ?, ?, ?)",
            (
                _encrypt(api_key, key) if api_key else None,
                _encrypt(api_secret, key) if api_secret else None,
                1 if paper_mode else 0,
                __import__("datetime").datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_api_keys() -> Optional[dict]:
    hwid = _get_hwid()
    key = _derive_aes_key(hwid)
    conn = _get_connection()
    try:
        row = conn.execute("SELECT api_key_enc, api_secret_enc, paper_mode FROM secure_store WHERE id = 1").fetchone()
        if not row:
            return None
        api_key = _decrypt(row["api_key_enc"], key) if row["api_key_enc"] else None
        api_secret = _decrypt(row["api_secret_enc"], key) if row["api_secret_enc"] else None
        return {
            "api_key": api_key,
            "api_secret": api_secret,
            "paper_mode": bool(row["paper_mode"]),
        }
    finally:
        conn.close()


def clear_api_keys():
    conn = _get_connection()
    try:
        conn.execute("UPDATE secure_store SET api_key_enc = NULL, api_secret_enc = NULL WHERE id = 1")
        conn.commit()
    finally:
        conn.close()
