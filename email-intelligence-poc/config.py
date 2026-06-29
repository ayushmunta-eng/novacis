"""Configuration helpers for the email intelligence proof of concept."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    email_provider: str = Field(default="imap")
    email_host: str = Field(default="imap.gmail.com")
    email_port: int = Field(default=993)
    email_user: Optional[str] = Field(default=None)
    email_password: Optional[str] = Field(default=None)
    email_use_ssl: bool = Field(default=True)
    groq_api_key: Optional[str] = Field(default=None)
    groq_model: str = Field(default="llama-3.1-8b-instant")
    gdrive_folder_id: Optional[str] = Field(default=None)
    output_dir: Path = Field(default=Path("output"))

    @property
    def groq_enabled(self) -> bool:
        """Return whether Groq-backed LangChain steps can be executed."""
        return bool(self.groq_api_key)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse a human-friendly boolean environment variable value."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings(env_file: str | Path = ".env") -> Settings:
    """Load application settings from a dotenv file and process environment."""
    load_dotenv(env_file)
    return Settings(
        email_provider=os.getenv("EMAIL_PROVIDER", "imap").strip().lower(),
        email_host=os.getenv("EMAIL_HOST", "imap.gmail.com"),
        email_port=int(os.getenv("EMAIL_PORT", "993")),
        email_user=os.getenv("EMAIL_USER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_use_ssl=_parse_bool(os.getenv("EMAIL_USE_SSL"), default=True),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        gdrive_folder_id=os.getenv("GDRIVE_FOLDER_ID"),
        output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
    )
