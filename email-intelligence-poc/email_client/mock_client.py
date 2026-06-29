"""Mock mailbox client for local development and demos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from email_client.base import BaseEmailClient, EmailMessage


class MockEmailClient(BaseEmailClient):
    """Email client that returns deterministic fake messages."""

    def __init__(self) -> None:
        """Create an in-memory mock client."""
        self._connected = False

    def connect(self) -> None:
        """Mark the mock mailbox as connected."""
        self._connected = True

    def fetch_emails(self, limit: int = 25, folder: str = "INBOX") -> list[EmailMessage]:
        """Return varied fake emails for local testing and visualization."""
        if not self._connected:
            raise RuntimeError("Mock client is not connected.")
        return self._build_messages(folder)[:limit]

    def disconnect(self) -> None:
        """Mark the mock mailbox as disconnected."""
        self._connected = False

    @staticmethod
    def _build_messages(folder: str) -> list[EmailMessage]:
        """Build deterministic messages covering multiple topics and tones."""
        now = datetime.now(timezone.utc)
        fixtures = [
            (
                "alex@customer.io",
                "Urgent: production login failures",
                "Customers are blocked from signing in. This is critical, negative, and needs immediate escalation.",
                0,
            ),
            (
                "maria@partner.dev",
                "Great launch feedback",
                "The launch went well and partner sentiment is positive. Users loved the onboarding flow.",
                1,
            ),
            (
                "billing@vendor.com",
                "Invoice due this week",
                "Monthly cloud invoice is ready. Please review the billing details before Friday.",
                2,
            ),
            (
                "security@example.org",
                "High priority security review",
                "A security audit found a risky dependency. Please prioritize remediation and review access logs.",
                3,
            ),
            (
                "newsletter@aiweekly.com",
                "AI market trends and research",
                "This week's newsletter covers artificial intelligence research, product trends, and funding updates.",
                4,
            ),
            (
                "jamie@company.com",
                "Neutral sync notes",
                "Sharing meeting notes from the product roadmap sync. No major blockers were reported.",
                5,
            ),
            (
                "support@saasapp.com",
                "Customer complaint about latency",
                "A key account is unhappy with slow dashboard performance and negative latency impact.",
                6,
            ),
            (
                "recruiting@company.com",
                "Interview panel schedule",
                "Please confirm availability for candidate interviews next week. Medium priority for hiring.",
                8,
            ),
            (
                "devops@company.com",
                "Deployment completed successfully",
                "The production deployment completed successfully with positive health checks and no alerts.",
                10,
            ),
            (
                "ceo@company.com",
                "Board prep: strategic priorities",
                "Need a concise update on revenue, customers, product roadmap, and high priority risks.",
                12,
            ),
            (
                "events@community.net",
                "Local data meetup invitation",
                "You are invited to a community event covering analytics, dashboards, and data visualization.",
                15,
            ),
            (
                "legal@company.com",
                "Contract review requested",
                "Please review the vendor contract terms. The request is medium priority and mostly neutral.",
                18,
            ),
        ]
        return [
            EmailMessage(
                message_id=f"mock-{idx + 1}",
                sender=sender,
                recipients=["you@example.com"],
                subject=subject,
                body=body,
                date=now - timedelta(days=days_ago),
                folder=folder,
            )
            for idx, (sender, subject, body, days_ago) in enumerate(fixtures)
        ]
