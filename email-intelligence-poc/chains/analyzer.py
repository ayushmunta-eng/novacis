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
    VALID_DOCUMENT_TYPES = {"report", "memo", "proposal", "notes", "other"}

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

    def analyze_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single document and return structured Python data."""
        if not self.settings.groq_enabled:
            return self._heuristic_document_analysis(document)

        try:
            return self._groq_document_analysis(document)
        except Exception as exc:
            fallback = self._heuristic_document_analysis(document)
            fallback["llm_error"] = str(exc)
            return fallback

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

    def _groq_document_analysis(self, document: dict[str, Any]) -> dict[str, Any]:
        """Run ChatGroq extraction for a document and normalize the JSON response."""
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
                    "You analyze business documents. Return only valid JSON with keys: "
                    "summary, key_topics, document_type. key_topics must be a list of "
                    "short strings. document_type must be one of: report, memo, proposal, "
                    "notes, other.",
                ),
                (
                    "human",
                    "Name: {name}\nMime type: {mime_type}\nOwner: {owner}\nContent:\n{content}",
                ),
            ]
        )
        response = (prompt | self._llm).invoke(
            {
                "name": document.get("name", "Untitled"),
                "mime_type": document.get("mime_type", "unknown"),
                "owner": document.get("owner", "Unknown owner"),
                "content": str(document.get("content", ""))[:6000],
            }
        )
        content = getattr(response, "content", str(response))
        parsed = self._parse_json_response(content)
        return self._normalize_document_analysis(parsed, document, source="groq")

    def _heuristic_document_analysis(self, document: dict[str, Any]) -> dict[str, Any]:
        """Analyze a document locally when Groq is not configured or fails."""
        content = str(document.get("content", ""))
        text = f"{document.get('name', '')} {content}".lower()
        topic_terms = {
            "security": {"security", "incident", "audit", "logging", "escalation"},
            "finance": {"finance", "invoice", "revenue", "spend", "budget", "renewal"},
            "product": {"product", "roadmap", "prototype", "onboarding", "mobile"},
            "customer": {"customer", "customers", "churn", "support", "accounts"},
            "operations": {"operations", "workflow", "staffing", "process", "month-end"},
            "analytics": {"analytics", "dashboards", "instrumentation", "reporting"},
            "hiring": {"hiring", "interview", "engineering", "data science"},
        }

        key_topics = [
            topic
            for topic, terms in topic_terms.items()
            if any(self._contains_term(text, term) for term in terms)
        ]
        if not key_topics:
            key_topics = ["general"]

        return {
            "summary": self._short_summary(content),
            "key_topics": key_topics[:5],
            "document_type": self._infer_document_type(text),
            "word_count": len(content.split()),
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

    def _normalize_document_analysis(
        self,
        parsed: dict[str, Any],
        document: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        """Normalize document analysis output into stable chart-friendly values."""
        content = str(document.get("content", ""))
        summary = str(parsed.get("summary", "")).strip() or self._short_summary(content)
        topics = parsed.get("key_topics", [])
        document_type = str(parsed.get("document_type", "other")).strip().lower()
        if not isinstance(topics, list):
            topics = [str(topics)]
        clean_topics = [str(topic).strip().lower() for topic in topics if str(topic).strip()]
        if document_type not in self.VALID_DOCUMENT_TYPES:
            document_type = "other"
        return {
            "summary": summary,
            "key_topics": clean_topics[:5] or ["general"],
            "document_type": document_type,
            "word_count": len(content.split()),
            "analysis_source": source,
        }

    def _infer_document_type(self, text: str) -> str:
        """Infer a coarse business document type from a name and content."""
        if self._contains_term(text, "proposal"):
            return "proposal"
        if self._contains_term(text, "notes"):
            return "notes"
        if self._contains_term(text, "report") or self._contains_term(text, "review"):
            return "report"
        if self._contains_term(text, "memo"):
            return "memo"
        return "other"

    @staticmethod
    def _short_summary(content: str, max_length: int = 200) -> str:
        """Return a compact local summary from document content."""
        compact = " ".join(content.split())
        if not compact:
            return "No extractable document content was found."
        suffix = "..." if len(compact) > max_length else ""
        return f"{compact[:max_length]}{suffix}"
