"""Base connection interface for CIM-Loader database connectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

QueryResponse = Any


class ConnectionInterface(ABC):
    """Contract every database connection class must implement."""

    @abstractmethod
    def connect(self) -> None:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def execute(self, query: str) -> QueryResponse:
        ...
