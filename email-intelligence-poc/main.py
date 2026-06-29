"""CLI entrypoint for the LangChain email intelligence proof of concept."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from chains.analyzer import EmailAnalyzer
from chains.summarizer import EmailSummarizer
from config import Settings, load_settings
from document_client.base import BaseDocumentClient
from document_client.gdrive_client import GoogleDriveDocumentClient
from document_client.mock_client import MockDocumentClient
from email_client.base import BaseEmailClient, EmailMessage
from email_client.imap_client import IMAPEmailClient
from email_client.mock_client import MockEmailClient
from utils.helpers import email_to_dict, ensure_directory, save_json, truncate_text
from visualization.charts import ChartGenerator, EmailDataFrame
from visualization.doc_charts import build_document_dataframe, generate_document_charts


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Email intelligence POC powered by LangChain and Groq.")
    parser.add_argument("--mock", action="store_true", help="Use mock emails instead of a live IMAP mailbox.")
    parser.add_argument("--docs", action="store_true", help="Analyze Google Drive documents instead of emails.")
    parser.add_argument("--docs-mock", action="store_true", help="Analyze mock documents without Google credentials.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of emails or documents to fetch.")
    parser.add_argument("--folder", default="INBOX", help="Mailbox folder to read from.")
    return parser.parse_args()


def build_email_client(settings: Settings, use_mock: bool) -> BaseEmailClient:
    """Create the configured email client implementation."""
    if use_mock or settings.email_provider == "mock":
        return MockEmailClient()
    return IMAPEmailClient(settings)


def build_document_client(settings: Settings, use_mock: bool) -> BaseDocumentClient:
    """Create the configured document client implementation."""
    if use_mock:
        return MockDocumentClient()
    return GoogleDriveDocumentClient(settings)


def run_pipeline(client: BaseEmailClient, settings: Settings, limit: int, folder: str) -> dict[str, Any]:
    """Fetch, analyze, summarize, visualize, and persist email intelligence outputs."""
    client.connect()
    try:
        emails = client.fetch_emails(limit=limit, folder=folder)
    finally:
        client.disconnect()

    analyzer = EmailAnalyzer(settings)
    analyses = analyzer.analyze_emails(emails)

    summarizer = EmailSummarizer(settings)
    summary = summarizer.summarize_emails(emails)

    output_dir = ensure_directory(settings.output_dir)
    charts_dir = output_dir / "charts"
    frame = EmailDataFrame(emails, analyses).build()
    chart_paths = ChartGenerator(charts_dir).generate_all(frame)

    raw_path = save_json([email_to_dict(email) for email in emails], output_dir / "raw_emails.json")
    analyzed_path = save_json(
        [
            {
                **email_to_dict(email),
                "analysis": analysis,
            }
            for email, analysis in zip(emails, analyses)
        ],
        output_dir / "analyzed_emails.json",
    )
    summary_path = save_json(summary, output_dir / "summary.json")

    return {
        "emails": emails,
        "analyses": analyses,
        "summary": summary,
        "chart_paths": chart_paths,
        "raw_path": raw_path,
        "analyzed_path": analyzed_path,
        "summary_path": summary_path,
    }


def run_document_pipeline(client: BaseDocumentClient, settings: Settings, limit: int) -> dict[str, Any]:
    """Fetch, analyze, visualize, and persist document intelligence outputs."""
    client.connect()
    try:
        documents = client.fetch_documents(limit=limit, folder_id=settings.gdrive_folder_id)
    finally:
        client.disconnect()

    analyzer = EmailAnalyzer(settings)
    summarizer = EmailSummarizer(settings)
    analyses: list[dict[str, Any]] = []
    for document in documents:
        analysis = analyzer.analyze_document(document)
        analysis["summary"] = summarizer.summarize_document(document)
        analyses.append(analysis)

    output_dir = ensure_directory(settings.output_dir)
    charts_dir = output_dir / "charts"
    frame = build_document_dataframe(documents, analyses)
    chart_paths = generate_document_charts(frame, charts_dir)

    raw_path = save_json(documents, output_dir / "raw_documents.json")
    analyzed_path = save_json(
        [
            {
                **document,
                "analysis": analysis,
            }
            for document, analysis in zip(documents, analyses)
        ],
        output_dir / "analyzed_documents.json",
    )

    return {
        "documents": documents,
        "analyses": analyses,
        "chart_paths": chart_paths,
        "raw_path": raw_path,
        "analyzed_path": analyzed_path,
    }


def print_report(result: dict[str, Any]) -> None:
    """Print a concise terminal report for the pipeline run."""
    emails: list[EmailMessage] = result["emails"]
    analyses: list[dict[str, Any]] = result["analyses"]
    summary: dict[str, Any] = result["summary"]
    chart_paths: list[Path] = result["chart_paths"]

    print("\nEmail Intelligence POC")
    print("=" * 24)
    print(f"Fetched emails: {len(emails)}")
    print(f"Summary source: {summary.get('summary_source')}")
    print(f"\nSummary:\n{summary.get('summary')}\n")

    print("Emails:")
    for email, analysis in zip(emails, analyses):
        topics = ", ".join(analysis.get("top_topics", []))
        print(
            f"- [{analysis.get('priority')}/{analysis.get('sentiment')}] "
            f"{email.date.date()} | {email.sender} | {email.subject} | topics: {topics}"
        )
        print(f"  {truncate_text(email.body)}")

    print("\nSaved outputs:")
    print(f"- Raw emails JSON: {result['raw_path']}")
    print(f"- Analyzed emails JSON: {result['analyzed_path']}")
    print(f"- Summary JSON: {result['summary_path']}")
    for path in chart_paths:
        print(f"- Chart: {path}")


def print_document_report(result: dict[str, Any]) -> None:
    """Print a concise terminal report for a document pipeline run."""
    documents: list[dict[str, Any]] = result["documents"]
    analyses: list[dict[str, Any]] = result["analyses"]
    chart_paths: list[Path] = result["chart_paths"]

    print("\nDocument Intelligence POC")
    print("=" * 25)
    print(f"Fetched documents: {len(documents)}")

    print("\nDocuments:")
    print(f"{'Type':<10} {'Words':>7} {'Owner':<20} {'Name'}")
    print("-" * 80)
    for document, analysis in zip(documents, analyses):
        print(
            f"{analysis.get('document_type', 'other'):<10} "
            f"{analysis.get('word_count', 0):>7} "
            f"{str(document.get('owner', 'Unknown owner'))[:20]:<20} "
            f"{document.get('name', 'Untitled')}"
        )
        topics = ", ".join(analysis.get("key_topics", []))
        print(f"  Topics: {topics}")
        print(f"  Summary: {truncate_text(str(analysis.get('summary', '')))}")

    print("\nSaved outputs:")
    print(f"- Raw documents JSON: {result['raw_path']}")
    print(f"- Analyzed documents JSON: {result['analyzed_path']}")
    for path in chart_paths:
        print(f"- Chart: {path}")


def main() -> None:
    """Run the email intelligence command-line application."""
    args = parse_args()
    settings = load_settings()
    if args.docs or args.docs_mock:
        document_client = build_document_client(settings, use_mock=args.docs_mock)
        document_result = run_document_pipeline(document_client, settings, limit=args.limit)
        print_document_report(document_result)
        return

    client = build_email_client(settings, use_mock=args.mock)
    result = run_pipeline(client, settings, limit=args.limit, folder=args.folder)
    print_report(result)


if __name__ == "__main__":
    main()
