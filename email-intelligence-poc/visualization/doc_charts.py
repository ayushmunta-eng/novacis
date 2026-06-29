"""Document visualization helpers for Google Drive analysis outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def build_document_dataframe(documents: list[dict[str, Any]], analyses: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a pandas DataFrame from documents and parallel analysis records."""
    records: list[dict[str, Any]] = []
    for document, analysis in zip(documents, analyses):
        records.append(
            {
                "id": document.get("id"),
                "name": document.get("name"),
                "mime_type": document.get("mime_type"),
                "created_time": document.get("created_time"),
                "modified_time": document.get("modified_time"),
                "owner": document.get("owner", "Unknown owner"),
                "summary": analysis.get("summary", ""),
                "key_topics": analysis.get("key_topics", []),
                "document_type": analysis.get("document_type", "other"),
                "word_count": analysis.get("word_count", 0),
                "analysis_source": analysis.get("analysis_source", "unknown"),
            }
        )
    frame = pd.DataFrame.from_records(records)
    if not frame.empty:
        frame["created_time"] = pd.to_datetime(frame["created_time"], utc=True, errors="coerce")
        frame["modified_time"] = pd.to_datetime(frame["modified_time"], utc=True, errors="coerce")
    return frame


def generate_document_charts(frame: pd.DataFrame, output_dir: Path | str = Path("output/charts")) -> list[Path]:
    """Generate all supported document charts and return saved file paths."""
    chart_dir = Path(output_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    return [
        document_type_distribution(frame, chart_dir),
        top_document_owners(frame, chart_dir),
        document_activity_over_time(frame, chart_dir),
    ]


def document_type_distribution(frame: pd.DataFrame, output_dir: Path | str = Path("output/charts")) -> Path:
    """Save a document type distribution pie chart as a PNG."""
    chart_dir = Path(output_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    path = chart_dir / "document_type_distribution.png"
    plt.figure(figsize=(7, 7))
    counts = _value_counts(frame, "document_type")
    counts.plot(kind="pie", autopct="%1.1f%%", startangle=90)
    plt.title("Document Type Distribution")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def top_document_owners(frame: pd.DataFrame, output_dir: Path | str = Path("output/charts"), limit: int = 10) -> Path:
    """Save a top document owners bar chart as a PNG."""
    chart_dir = Path(output_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    path = chart_dir / "top_document_owners.png"
    plt.figure(figsize=(10, 6))
    counts = _value_counts(frame, "owner").head(limit)
    counts.sort_values().plot(kind="barh", color="#9C755F")
    plt.title("Top Document Owners")
    plt.xlabel("Document Count")
    plt.ylabel("Owner")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def document_activity_over_time(frame: pd.DataFrame, output_dir: Path | str = Path("output/charts")) -> Path:
    """Save a document created/modified activity line chart as a PNG."""
    chart_dir = Path(output_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    path = chart_dir / "document_activity_over_time.png"
    plt.figure(figsize=(10, 5))
    if frame.empty:
        activity = pd.DataFrame({"created": [0], "modified": [0]}, index=pd.to_datetime(["today"]))
    else:
        created = frame.dropna(subset=["created_time"]).set_index("created_time").resample("D").size()
        modified = frame.dropna(subset=["modified_time"]).set_index("modified_time").resample("D").size()
        activity = pd.DataFrame({"created": created, "modified": modified}).fillna(0)
    activity.plot(kind="line", marker="o", ax=plt.gca())
    plt.title("Document Activity Over Time")
    plt.xlabel("Date")
    plt.ylabel("Document Count")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def _value_counts(frame: pd.DataFrame, column: str) -> pd.Series:
    """Return value counts with a fallback row for empty data."""
    if frame.empty or column not in frame:
        return pd.Series({"unknown": 0})
    counts = frame[column].fillna("unknown").value_counts()
    return counts if not counts.empty else pd.Series({"unknown": 0})
