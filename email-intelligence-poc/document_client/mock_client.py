"""Mock document client for local development and demos."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from document_client.base import BaseDocumentClient, DocumentRecord


class MockDocumentClient(BaseDocumentClient):
    """Document client that returns deterministic fake documents."""

    def __init__(self) -> None:
        """Create an in-memory mock document client."""
        self._connected = False

    def connect(self) -> None:
        """Mark the mock document source as connected."""
        self._connected = True

    def fetch_documents(self, limit: int, folder_id: str | None = None) -> list[DocumentRecord]:
        """Return varied fake documents for local testing and visualization."""
        if not self._connected:
            raise RuntimeError("Mock document client is not connected.")
        return self._build_documents(folder_id)[:limit]

    def disconnect(self) -> None:
        """Mark the mock document source as disconnected."""
        self._connected = False

    @staticmethod
    def _build_documents(folder_id: str | None) -> list[DocumentRecord]:
        """Build deterministic documents covering multiple business formats."""
        now = datetime.now(timezone.utc)
        folder_suffix = f" in folder {folder_id}" if folder_id else ""
        fixtures = [
            (
                "doc-proposal-platform",
                "Customer Intelligence Platform Proposal",
                "application/vnd.google-apps.document",
                "A proposal to build a customer intelligence platform with ingestion, entity resolution, dashboards, "
                "and executive reporting. The project includes phased delivery, security review, and revenue impact "
                "measurement for enterprise accounts.",
                "Priya Shah",
                30,
                2,
            ),
            (
                "doc-notes-roadmap",
                "Product Roadmap Meeting Notes",
                "text/plain",
                "Meeting notes from the roadmap planning session. The team discussed onboarding improvements, mobile "
                "experience gaps, analytics instrumentation, and follow-up owners for each milestone.",
                "Marcus Lee",
                12,
                1,
            ),
            (
                "doc-report-qbr",
                "QBR Revenue Performance Report",
                "application/pdf",
                "Quarterly business review report covering revenue growth, churn risk, account expansion, renewal "
                "pipeline, and recommendations for customer success engagement.",
                "Elena Garcia",
                45,
                5,
            ),
            (
                "doc-memo-security",
                "Security Incident Response Memo",
                "application/vnd.google-apps.document",
                "Internal memo describing a security incident response workflow, escalation matrix, audit logging "
                "requirements, and communications plan for affected customers.",
                "Andre Coleman",
                20,
                3,
            ),
            (
                "doc-proposal-automation",
                "Finance Automation Proposal",
                "application/vnd.google-apps.document",
                "Proposal for automating invoice reconciliation, vendor approvals, spend analytics, and exception "
                "handling. The business case emphasizes reduced manual review and faster month-end close.",
                "Nora Patel",
                18,
                4,
            ),
            (
                "doc-report-support",
                "Support Operations Monthly Report",
                "application/pdf",
                "Monthly report summarizing ticket volume, response time, backlog health, top customer pain points, "
                "and staffing recommendations for support operations.",
                "Jamie Chen",
                9,
                1,
            ),
            (
                "doc-notes-design",
                "Design Review Notes",
                "text/plain",
                "Notes from the design critique covering navigation hierarchy, accessibility issues, dashboard layout, "
                "and next steps for the prototype usability test.",
                "Sam Rivera",
                6,
                2,
            ),
            (
                "doc-memo-hiring",
                "Hiring Plan Memo",
                "application/vnd.google-apps.document",
                "Memo outlining hiring priorities for engineering, data science, product design, and customer success. "
                "Includes interview process updates and budget considerations.",
                "Taylor Brooks",
                3,
                1,
            ),
        ]
        return [
            {
                "id": document_id,
                "name": f"{name}{folder_suffix}",
                "mime_type": mime_type,
                "content": content,
                "created_time": (now - timedelta(days=created_days_ago)).isoformat(),
                "modified_time": (now - timedelta(days=modified_days_ago)).isoformat(),
                "owner": owner,
            }
            for document_id, name, mime_type, content, owner, created_days_ago, modified_days_ago in fixtures
        ]
