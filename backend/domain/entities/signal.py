from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Signal:
    name: str
    value: float
    confidence: float = 1.0
