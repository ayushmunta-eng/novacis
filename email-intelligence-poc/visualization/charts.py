"""DataFrame creation and chart generation for analyzed emails."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from email_client.base import EmailMessage


class EmailDataFrame:
    """Build pandas DataFrames from fetched and analyzed emails."""

    def __init__(self, emails: list[EmailMessage], analyses: list[dict[str, Any]]) -> None:
        """Create a DataFrame builder from emails and parallel analyses."""
        self.emails = emails
        self.analyses = analyses

    def build(self) -> pd.DataFrame:
        """Return a pandas DataFrame suitable for reporting and charts."""
        records: list[dict[str, Any]] = []
        for email, analysis in zip(self.emails, self.analyses):
            records.append(
                {
                    "message_id": email.message_id,
                    "sender": email.sender,
                    "subject": email.subject,
                    "date": email.date,
                    "folder": email.folder,
                    "sentiment": analysis.get("sentiment", "unknown"),
                    "priority": analysis.get("priority", "unknown"),
                    "top_topics": analysis.get("top_topics", []),
                    "analysis_source": analysis.get("analysis_source", "unknown"),
                }
            )
        frame = pd.DataFrame.from_records(records)
        if not frame.empty:
            frame["date"] = pd.to_datetime(frame["date"], utc=True)
        return frame


class ChartGenerator:
    """Generate chart PNG files from an email intelligence DataFrame."""

    def __init__(self, output_dir: Path | str = Path("output/charts")) -> None:
        """Create a chart generator that writes to the given directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, frame: pd.DataFrame) -> list[Path]:
        """Generate every supported chart and return saved file paths."""
        return [
            self.sentiment_distribution(frame),
            self.priority_breakdown(frame),
            self.email_volume_over_time(frame),
            self.top_senders(frame),
        ]

    def sentiment_distribution(self, frame: pd.DataFrame) -> Path:
        """Save a sentiment distribution pie chart as a PNG."""
        path = self.output_dir / "sentiment_distribution.png"
        plt.figure(figsize=(7, 7))
        counts = self._value_counts(frame, "sentiment")
        counts.plot(kind="pie", autopct="%1.1f%%", startangle=90)
        plt.title("Sentiment Distribution")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        return path

    def priority_breakdown(self, frame: pd.DataFrame) -> Path:
        """Save a priority breakdown bar chart as a PNG."""
        path = self.output_dir / "priority_breakdown.png"
        plt.figure(figsize=(8, 5))
        counts = self._value_counts(frame, "priority").reindex(["high", "medium", "low", "unknown"]).dropna()
        counts.plot(kind="bar", color="#4C78A8")
        plt.title("Priority Breakdown")
        plt.xlabel("Priority")
        plt.ylabel("Email Count")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        return path

    def email_volume_over_time(self, frame: pd.DataFrame) -> Path:
        """Save an email volume over time line chart as a PNG."""
        path = self.output_dir / "email_volume_over_time.png"
        plt.figure(figsize=(10, 5))
        if frame.empty:
            series = pd.Series([0], index=pd.to_datetime(["today"]))
        else:
            series = frame.set_index("date").resample("D").size()
        series.plot(kind="line", marker="o", color="#59A14F")
        plt.title("Email Volume Over Time")
        plt.xlabel("Date")
        plt.ylabel("Email Count")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        return path

    def top_senders(self, frame: pd.DataFrame, limit: int = 10) -> Path:
        """Save a top senders bar chart as a PNG."""
        path = self.output_dir / "top_senders.png"
        plt.figure(figsize=(10, 6))
        counts = self._value_counts(frame, "sender").head(limit)
        counts.sort_values().plot(kind="barh", color="#F28E2B")
        plt.title("Top Senders")
        plt.xlabel("Email Count")
        plt.ylabel("Sender")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        return path

    @staticmethod
    def topic_counts(frame: pd.DataFrame) -> Counter[str]:
        """Return flattened topic counts from an email DataFrame."""
        counter: Counter[str] = Counter()
        if frame.empty or "top_topics" not in frame:
            return counter
        for topics in frame["top_topics"]:
            if isinstance(topics, list):
                counter.update(str(topic) for topic in topics)
        return counter

    @staticmethod
    def _value_counts(frame: pd.DataFrame, column: str) -> pd.Series:
        """Return value counts with a fallback row for empty data."""
        if frame.empty or column not in frame:
            return pd.Series({"unknown": 0})
        counts = frame[column].fillna("unknown").value_counts()
        return counts if not counts.empty else pd.Series({"unknown": 0})
