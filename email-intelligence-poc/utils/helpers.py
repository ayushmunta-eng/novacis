"""General helper functions for the email intelligence CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from email_client.base import EmailMessage


def ensure_directory(path: Path | str) -> Path:
    """Create a directory if needed and return it as a Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def truncate_text(value: str, max_length: int = 140) -> str:
    """Return a compact one-line text preview."""
    compact = " ".join(value.split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 3]}..."


def email_to_dict(email: EmailMessage) -> dict[str, Any]:
    """Serialize an EmailMessage into JSON-friendly primitives."""
    return {
        "message_id": email.message_id,
        "sender": email.sender,
        "recipients": email.recipients,
        "subject": email.subject,
        "body": email.body,
        "date": email.date.isoformat(),
        "folder": email.folder,
    }


def save_json(data: Any, path: Path | str) -> Path:
    """Write data to a JSON file and return the saved path."""
    output_path = Path(path)
    ensure_directory(output_path.parent)
    output_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return output_path
