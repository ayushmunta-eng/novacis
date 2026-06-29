"""IMAP mailbox client implementation."""

from __future__ import annotations

import email
import imaplib
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from typing import Optional

from config import Settings
from email_client.base import BaseEmailClient, EmailMessage


class IMAPEmailClient(BaseEmailClient):
    """Email client that reads messages from any standard IMAP server."""

    def __init__(self, settings: Settings) -> None:
        """Create an IMAP client using application settings."""
        self.settings = settings
        self._mailbox: Optional[imaplib.IMAP4] = None

    def connect(self) -> None:
        """Connect and authenticate to the configured IMAP mailbox."""
        if not self.settings.email_user or not self.settings.email_password:
            raise ValueError("EMAIL_USER and EMAIL_PASSWORD are required for live mailbox access.")

        if self.settings.email_use_ssl:
            self._mailbox = imaplib.IMAP4_SSL(self.settings.email_host, self.settings.email_port)
        else:
            self._mailbox = imaplib.IMAP4(self.settings.email_host, self.settings.email_port)
        self._mailbox.login(self.settings.email_user, self.settings.email_password)

    def fetch_emails(self, limit: int = 25, folder: str = "INBOX") -> list[EmailMessage]:
        """Fetch recent emails from the selected IMAP folder."""
        mailbox = self._require_connection()
        status, _ = mailbox.select(folder, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Unable to select IMAP folder: {folder}")

        status, data = mailbox.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return []

        message_ids = data[0].split()
        recent_ids = list(reversed(message_ids))[:limit]
        emails: list[EmailMessage] = []

        for raw_id in recent_ids:
            status, message_data = mailbox.fetch(raw_id, "(RFC822)")
            if status != "OK" or not message_data:
                continue
            for part in message_data:
                if not isinstance(part, tuple):
                    continue
                parsed = email.message_from_bytes(part[1])
                emails.append(self._parse_message(parsed, raw_id.decode("utf-8"), folder))
        return emails

    def disconnect(self) -> None:
        """Close the active IMAP connection if one exists."""
        if not self._mailbox:
            return
        try:
            self._mailbox.close()
        except imaplib.IMAP4.error:
            pass
        finally:
            self._mailbox.logout()
            self._mailbox = None

    def _require_connection(self) -> imaplib.IMAP4:
        """Return the active IMAP connection or raise a useful error."""
        if not self._mailbox:
            raise RuntimeError("IMAP client is not connected.")
        return self._mailbox

    def _parse_message(self, message: Message, fallback_id: str, folder: str) -> EmailMessage:
        """Convert an RFC822 message into the normalized EmailMessage model."""
        message_id = message.get("Message-ID", fallback_id).strip()
        sender = self._decode_header_value(message.get("From", "Unknown sender"))
        recipients = [
            address
            for _, address in getaddresses(message.get_all("To", []))
            if address
        ]
        subject = self._decode_header_value(message.get("Subject", "(no subject)"))
        body = self._extract_body(message)
        date = self._parse_date(message.get("Date"))
        return EmailMessage(
            message_id=message_id,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body=body,
            date=date,
            folder=folder,
        )

    @staticmethod
    def _decode_header_value(value: str) -> str:
        """Decode MIME-encoded email headers into plain text."""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return value

    @staticmethod
    def _parse_date(value: str | None) -> datetime:
        """Parse an email Date header into a timezone-aware datetime."""
        if not value:
            return datetime.now(timezone.utc)
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    @classmethod
    def _extract_body(cls, message: Message) -> str:
        """Extract the best available plain text body from an email message."""
        if message.is_multipart():
            html_fallback = ""
            for part in message.walk():
                content_disposition = part.get_content_disposition()
                content_type = part.get_content_type()
                if content_disposition == "attachment":
                    continue
                if content_type == "text/plain":
                    return cls._decode_payload(part)
                if content_type == "text/html" and not html_fallback:
                    html_fallback = cls._decode_payload(part)
            return html_fallback
        return cls._decode_payload(message)

    @staticmethod
    def _decode_payload(part: Message) -> str:
        """Decode one email payload using the declared charset when available."""
        payload = part.get_payload(decode=True)
        if payload is None:
            raw_payload = part.get_payload()
            return raw_payload if isinstance(raw_payload, str) else ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
