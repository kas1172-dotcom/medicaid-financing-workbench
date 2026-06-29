"""
Source-adapter interface for the three-tier ingestion system.

Tier 1 (api)          : auto-fetched via HTTP. fetch() hits the endpoint,
                          parse() returns a tidy DataFrame.
Tier 2 (manual_upload): user downloads a file and drops it in data/inbox/.
                          fetch() is a no-op (just validates the inbox file).
                          parse() reads and normalises the file.
Tier 3 (pdf)          : PDF table extraction via pdfplumber or camelot.
                          fetch() validates the PDF in data/inbox/.
                          parse() extracts and normalises the table.

Every adapter must:
  1. Implement fetch() and parse().
  2. Return DataFrames with a `_source`, `_method`, and `_retrieved_date`
     column on every row (provenance tags).
  3. Raise FetchError on retrieval failure, ParseError on parse failure.

The `mfw refresh` command calls each adapter in sequence; the panel builder
reads from data/current/ which is populated by the adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class FetchError(RuntimeError):
    pass


class ParseError(RuntimeError):
    pass


@dataclass
class ProvenanceRecord:
    source_id: str
    source_name: str
    tier: str                     # api | manual_upload | pdf
    method: str
    retrieved_date: str           # ISO-8601 date string
    filename: str | None = None
    row_count: int = 0
    validation_status: str = "pending"   # pending | pass | flag | error
    validation_notes: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "tier": self.tier,
            "method": self.method,
            "retrieved_date": self.retrieved_date,
            "filename": self.filename,
            "row_count": self.row_count,
            "validation_status": self.validation_status,
            "validation_notes": self.validation_notes,
            **self.extra,
        }


class SourceAdapter(ABC):
    """Abstract base for all source adapters."""

    source_id: str
    source_name: str
    tier: str            # api | manual_upload | pdf
    method: str
    url: str
    expected_filename: str | None = None
    refresh_frequency: str = "weekly"

    CURRENT_DIR = Path("data/current")
    RAW_DIR = Path("data/raw")
    INBOX_DIR = Path("data/inbox")

    @abstractmethod
    def fetch(self) -> Any:
        """
        Retrieve raw data.
        - api tier: HTTP request → cache to data/raw/ → return raw payload
        - manual_upload/pdf: validate inbox file exists → return Path
        Raises FetchError on any failure.
        """

    @abstractmethod
    def parse(self, raw: Any) -> pd.DataFrame:
        """
        Parse raw payload into a tidy DataFrame.
        Every returned row must have _source, _method, _retrieved_date columns.
        Raises ParseError on any failure.
        """

    def run(self) -> tuple[pd.DataFrame, ProvenanceRecord]:
        """
        Full fetch + parse cycle. Promotes the cleaned DataFrame to
        data/current/ and writes the provenance sidecar.
        Returns (df, provenance_record).
        """
        raw = self.fetch()
        df = self.parse(raw)
        self._promote(df)
        prov = ProvenanceRecord(
            source_id=self.source_id,
            source_name=self.source_name,
            tier=self.tier,
            method=self.method,
            retrieved_date=datetime.utcnow().date().isoformat(),
            filename=self.expected_filename,
            row_count=len(df),
        )
        self._write_provenance(prov)
        return df, prov

    def _promote(self, df: pd.DataFrame) -> None:
        self.CURRENT_DIR.mkdir(parents=True, exist_ok=True)
        out = self.CURRENT_DIR / f"{self.source_id}.csv"
        df.to_csv(out, index=False)

    def _write_provenance(self, prov: ProvenanceRecord) -> None:
        import json
        self.CURRENT_DIR.mkdir(parents=True, exist_ok=True)
        out = self.CURRENT_DIR / f"{self.source_id}.provenance.json"
        out.write_text(json.dumps(prov.to_dict(), indent=2))

    def load_current(self) -> pd.DataFrame | None:
        """Load the last-good version from data/current/, or None."""
        path = self.CURRENT_DIR / f"{self.source_id}.csv"
        if not path.exists():
            return None
        return pd.read_csv(path)

    def provenance(self) -> dict | None:
        """Load the provenance sidecar from data/current/, or None."""
        import json
        path = self.CURRENT_DIR / f"{self.source_id}.provenance.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _tag_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attach provenance columns to a DataFrame in-place."""
        df["_source"] = self.source_id
        df["_method"] = self.method
        df["_retrieved_date"] = datetime.utcnow().date().isoformat()
        return df
