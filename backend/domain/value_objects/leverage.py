from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Leverage:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError("Leverage value must be an integer")
        if self.value < 1:
            raise ValueError("Leverage must be >= 1")