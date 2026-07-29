from __future__ import annotations

import os
from typing import Optional


def _derive_key(hwid: str) -> bytes:
    key_material = hwid.encode("utf-8")
    return key_material[:32].ljust(32, b"\x00")


def encrypt(plaintext: str, hwid: str) -> bytes:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes

    key = _derive_key(hwid)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    return cipher.nonce + tag + ciphertext


def decrypt(data: bytes, hwid: str) -> Optional[str]:
    try:
        nonce = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        from Crypto.Cipher import AES

        key = _derive_key(hwid)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error("Decryption failed: %s", exc)
        return None


def zeroize(value: Optional[str]) -> None:
    if not value:
        return
    buf = bytearray(value, "utf-8")
    for i in range(len(buf)):
        buf[i] = 0
    del buf
