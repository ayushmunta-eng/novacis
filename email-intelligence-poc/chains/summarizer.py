"""LangChain-backed email summarization utilities."""

from __future__ import annotations

from typing import Any

from config import Settings
from email_client.base import EmailMessage


class EmailSummarizer:
    """Summarize batches of emails with ChatGroq when configured."""

    def __init__(self, settings: Settings) -> None:
        """Create a summarizer using application settings."""
        self.settings = settings
        self._llm: Any | None = None

    def summarize_emails(self, emails: list[EmailMessage]) -> dict[str, Any]:
        """Return an executive summary for a list of emails."""
        if not emails:
            return {
                "summary": "No emails found.",
                "llm_enabled": False,
                "summary_source": "empty",
            }
        if not self.settings.groq_enabled:
            return {
                "summary": "GROQ_API_KEY is not set, so LLM summarization was skipped.",
                "llm_enabled": False,
                "summary_source": "skipped",
            }

        try:
            return {
                "summary": self._groq_summary(emails),
                "llm_enabled": True,
                "summary_source": "groq",
            }
        except Exception as exc:
            return {
                "summary": f"Groq summarization failed and was skipped: {exc}",
                "llm_enabled": False,
                "summary_source": "error",
            }

    def _groq_summary(self, emails: list[EmailMessage]) -> str:
        """Run the ChatGroq summarization chain."""
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_groq import ChatGroq

        if self._llm is None:
            self._llm = ChatGroq(
                api_key=self.settings.groq_api_key,
                model=self.settings.groq_model,
                temperature=0.2,
            )

        email_digest = "\n\n".join(
            f"From: {email.sender}\nDate: {email.date.isoformat()}\n"
            f"Subject: {email.subject}\nBody: {email.body[:1200]}"
            for email in emails
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an email intelligence assistant. Summarize the mailbox "
                    "for a busy operator. Include urgent items, recurring themes, "
                    "notable senders, and suggested next actions.",
                ),
                ("human", "Summarize these emails:\n\n{email_digest}"),
            ]
        )
        chain = prompt | self._llm | StrOutputParser()
        return chain.invoke({"email_digest": email_digest})
