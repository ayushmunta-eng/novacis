"""Email client implementations for the email intelligence POC."""

from email_client.base import BaseEmailClient, EmailMessage
from email_client.imap_client import IMAPEmailClient
from email_client.mock_client import MockEmailClient

__all__ = ["BaseEmailClient", "EmailMessage", "IMAPEmailClient", "MockEmailClient"]
