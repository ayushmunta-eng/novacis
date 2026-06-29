"""CLI entrypoint for the LangChain email intelligence proof of concept."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from chains.analyzer import EmailAnalyzer
from chains.summarizer import EmailSummarizer
from config import Settings, load_settings
from email_client.base import BaseEmailClient, EmailMessage
from email_client.imap_client import IMAPEmailClient
from email_client.mock_client import MockEmailClient
from utils.helpers import email_to_dict, ensure_directory, save_json, truncate_text
from visualization.charts import ChartGenerator, EmailDataFrame


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Email intelligence POC powered by LangChain and Groq.")
    parser.add_argument("--mock", action="store_true", help="Use mock emails instead of a live IMAP mailbox.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of emails to fetch.")
    parser.add_argument("--folder", default="INBOX", help="Mailbox folder to read from.")
    return parser.parse_args()


def build_email_client(settings: Settings, use_mock: bool) -> BaseEmailClient:
    """Create the configured email client implementation."""
    if use_mock or settings.email_provider == "mock":
        return MockEmailClient()
    return IMAPEmailClient(settings)


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


def main() -> None:
    """Run the email intelligence command-line application."""
    args = parse_args()
    settings = load_settings()
    client = build_email_client(settings, use_mock=args.mock)
    result = run_pipeline(client, settings, limit=args.limit, folder=args.folder)
    print_report(result)


if __name__ == "__main__":
    main()
