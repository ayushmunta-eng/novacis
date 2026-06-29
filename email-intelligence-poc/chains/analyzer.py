"""LangChain-backed email analysis utilities."""

from __future__ import annotations

import json
import re
from typing import Any

from config import Settings
from email_client.base import EmailMessage


class EmailAnalyzer:
    """Extract sentiment, priority, and topics from email messages."""

    VALID_SENTIMENTS = {"positive", "negative", "neutral"}
    VALID_PRIORITIES = {"high", "medium", "low"}

    def __init__(self, settings: Settings) -> None:
        """Create an analyzer configured for Groq or local fallback mode."""
        self.settings = settings
        self._llm: Any | None = None

    def analyze_email(self, email: EmailMessage) -> dict[str, Any]:
        """Analyze a single email and return structured Python data."""
        if not self.settings.groq_enabled:
            return self._heuristic_analysis(email)

        try:
            return self._groq_analysis(email)
        except Exception as exc:
            fallback = self._heuristic_analysis(email)
            fallback["llm_error"] = str(exc)
            return fallback

    def analyze_emails(self, emails: list[EmailMessage]) -> list[dict[str, Any]]:
        """Analyze multiple emails and return one dict per message."""
        return [self.analyze_email(message) for message in emails]

    def _groq_analysis(self, email: EmailMessage) -> dict[str, Any]:
        """Run ChatGroq extraction and normalize the JSON response."""
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_groq import ChatGroq

        if self._llm is None:
            self._llm = ChatGroq(
                api_key=self.settings.groq_api_key,
                model=self.settings.groq_model,
                temperature=0,
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You analyze emails. Return only valid JSON with keys: "
                    "sentiment, priority, top_topics. Sentiment must be positive, "
                    "negative, or neutral. Priority must be high, medium, or low. "
                    "top_topics must be a list of short strings.",
                ),
                (
                    "human",
                    "Subject: {subject}\nSender: {sender}\nBody:\n{body}",
                ),
            ]
        )
        response = (prompt | self._llm).invoke(
            {"subject": email.subject, "sender": email.sender, "body": email.body[:6000]}
        )
        content = getattr(response, "content", str(response))
        parsed = self._parse_json_response(content)
        return self._normalize_analysis(parsed, source="groq")

    def _heuristic_analysis(self, email: EmailMessage) -> dict[str, Any]:
        """Analyze an email locally when Groq is not configured or fails."""
        text = f"{email.subject} {email.body}".lower()
        positive_terms = {"great", "loved", "success", "successfully", "positive", "well"}
        negative_terms = {"urgent", "blocked", "critical", "risky", "complaint", "unhappy", "negative", "slow"}
        high_terms = {"urgent", "critical", "immediate", "security", "high priority", "blocked", "ceo"}
        medium_terms = {"review", "due", "confirm", "medium priority", "schedule", "contract"}
        topic_terms = {
            "security": {"security", "audit", "access", "dependency"},
            "billing": {"invoice", "billing", "vendor"},
            "product": {"product", "roadmap", "launch", "onboarding"},
            "customer": {"customer", "customers", "account", "support"},
            "operations": {"deployment", "production", "devops", "alerts"},
            "analytics": {"analytics", "dashboard", "dashboards", "visualization", "data"},
            "hiring": {"recruiting", "interview", "candidate", "hiring"},
            "legal": {"legal", "contract", "terms"},
            "ai": {"ai", "artificial intelligence", "research"},
        }

        positive_score = sum(self._contains_term(text, term) for term in positive_terms)
        negative_score = sum(self._contains_term(text, term) for term in negative_terms)
        if positive_score > negative_score:
            sentiment = "positive"
        elif negative_score > positive_score:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        if any(self._contains_term(text, term) for term in high_terms):
            priority = "high"
        elif any(self._contains_term(text, term) for term in medium_terms):
            priority = "medium"
        else:
            priority = "low"

        topics = [
            topic
            for topic, terms in topic_terms.items()
            if any(self._contains_term(text, term) for term in terms)
        ]
        if not topics:
            topics = ["general"]

        return {
            "sentiment": sentiment,
            "priority": priority,
            "top_topics": topics[:5],
            "analysis_source": "heuristic",
        }

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        """Return whether text contains a whole-word term or phrase."""
        return re.search(rf"\b{re.escape(term)}\b", text) is not None

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse a model response that should contain JSON."""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if not match:
                raise ValueError(f"Model did not return JSON: {content}")
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("Model JSON response must be an object.")
        return parsed

    def _normalize_analysis(self, parsed: dict[str, Any], source: str) -> dict[str, Any]:
        """Normalize model output into stable chart-friendly values."""
        sentiment = str(parsed.get("sentiment", "neutral")).strip().lower()
        priority = str(parsed.get("priority", "medium")).strip().lower()
        topics = parsed.get("top_topics", [])
        if sentiment not in self.VALID_SENTIMENTS:
            sentiment = "neutral"
        if priority not in self.VALID_PRIORITIES:
            priority = "medium"
        if not isinstance(topics, list):
            topics = [str(topics)]
        clean_topics = [str(topic).strip().lower() for topic in topics if str(topic).strip()]
        return {
            "sentiment": sentiment,
            "priority": priority,
            "top_topics": clean_topics[:5] or ["general"],
            "analysis_source": source,
        }
