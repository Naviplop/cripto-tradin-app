from __future__ import annotations

from abc import ABC


class DomainEvent(ABC):
    @property
    def event_name(self) -> str:
        return self.__class__.__name__
