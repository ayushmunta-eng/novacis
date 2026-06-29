"""Base interfaces and data models for email clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    """Normalized representation of an email message."""

    message_id: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    subject: str
    body: str
    date: datetime
    folder: str = "INBOX"


class BaseEmailClient(ABC):
    """Abstract mailbox client used by the application."""

    @abstractmethod
    def connect(self) -> None:
        """Open a connection to the configured mailbox provider."""

    @abstractmethod
    def fetch_emails(self, limit: int = 25, folder: str = "INBOX") -> list[EmailMessage]:
        """Fetch normalized emails from a mailbox folder."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close any active mailbox connection and release resources."""
