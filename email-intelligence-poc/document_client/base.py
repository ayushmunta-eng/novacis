"""Base interfaces for document clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


DocumentRecord = dict[str, Any]


class BaseDocumentClient(ABC):
    """Abstract document source client used by the application."""

    @abstractmethod
    def connect(self) -> None:
        """Open a connection to the configured document provider."""

    @abstractmethod
    def fetch_documents(self, limit: int, folder_id: str | None = None) -> list[DocumentRecord]:
        """Fetch plain-text document records from a source folder."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close any active document provider connection and release resources."""
