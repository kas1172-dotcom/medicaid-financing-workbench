"""
KFF State Health Facts: Provider Taxes (manual_upload adapter).

This is a Tier-2 adapter: the user downloads the CSV from the KFF State Health
Facts indicator page and drops it in data/inbox/kff_provider_taxes.csv.
`mfw refresh` then ingests, validates, and promotes it to data/current/.

Source:
  https://www.kff.org/medicaid/state-indicator/provider-taxes/

The KFF table lists, for each state:
  - Whether a provider tax exists (Yes/No) by provider class
  - The tax rate (% of net patient revenue) where applicable
  - Which classes are subject to the new hold-harmless cap

Expected CSV columns (KFF export format as of 2025-2026):
  State, Hospital, Nursing_Facility, MCO, ICF_IID, Ambulance, Other, Notes
  (Column names may vary slightly; the adapter normalises them.)

Parse rules:
  1. Map column names case-insensitively to the canonical class names.
  2. Convert "N/A", "--", empty strings → 0.0.
  3. Strip "%" characters from rate fields.
  4. Mark exempt classes (nursing_facility, icf_iid) in output.
  5. Compute `max_subject_rate` = max of non-exempt class rates.

Validation:
  - At least 30 expansion states should have a non-exempt rate > 3.5%
    (KFF anchor: 31 states as of Feb 2026).
  - At least 25 states should have a hospital rate > 3.5%.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .base import SourceAdapter, FetchError, ParseError

EXEMPT_CLASSES = {"nursing_facility", "icf_iid"}
SUBJECT_CLASSES = ["hospital", "mco", "ambulance", "other"]

# Canonical name → list of raw CSV column name variations to try.
_COLUMN_ALIASES = {
    "state":            ["state", "location"],
    "hospital":         ["hospital"],
    "nursing_facility": ["nursing_facility", "nursing facility", "nf", "snf"],
    "mco":              ["mco", "managed care organization", "managed care", "mco/hmo"],
    "icf_iid":          ["icf_iid", "icf/iid", "icf", "idd"],
    "ambulance":        ["ambulance", "ems"],
    "other":            ["other", "other provider"],
}


def _clean_rate(val) -> float:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    s = str(val).strip().replace("%", "").replace(",", "")
    if s in ("", "N/A", "--", "n/a", "na", "No", "no"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_column(df_cols_lower: list[str], aliases: list[str]) -> str | None:
    for alias in aliases:
        for col in df_cols_lower:
            if alias.lower() == col.lower():
                return col
    return None


class KFFProviderTaxesAdapter(SourceAdapter):
    source_id = "kff_provider_taxes"
    source_name = "KFF State Health Facts: Provider Taxes by Class"
    tier = "manual_upload"
    method = "Manual download from KFF State Health Facts"
    url = "https://www.kff.org/medicaid/state-indicator/provider-taxes/"
    expected_filename = "kff_provider_taxes.csv"
    refresh_frequency = "quarterly"

    def fetch(self) -> Path:
        inbox_file = self.INBOX_DIR / self.expected_filename
        if not inbox_file.exists():
            raise FetchError(
                f"File not found in data/inbox/: {self.expected_filename}\n"
                f"  Download from: {self.url}\n"
                f"  Save as: data/inbox/{self.expected_filename}"
            )
        return inbox_file

    def parse(self, raw: Path) -> pd.DataFrame:
        try:
            df_raw = pd.read_csv(raw, skiprows=2)  # KFF CSVs have a 2-row header
        except Exception as exc:
            raise ParseError(f"Could not read {raw}: {exc}") from exc

        # Normalise column names.
        col_map = {}
        raw_cols_lower = [c.lower().strip() for c in df_raw.columns]
        for canonical, aliases in _COLUMN_ALIASES.items():
            matched = _find_column(raw_cols_lower, aliases)
            if matched is not None:
                actual_col = df_raw.columns[raw_cols_lower.index(matched.lower())]
                col_map[actual_col] = canonical

        if "state" not in col_map.values():
            raise ParseError(f"Could not find 'State' column in {raw}. Columns: {list(df_raw.columns)}")

        df = df_raw.rename(columns=col_map)

        # Drop footer rows (NaN state, metadata rows).
        df = df[df["state"].notna() & (df["state"].str.strip() != "")].copy()

        # Clean rate columns.
        rows = []
        for _, r in df.iterrows():
            state_name = str(r["state"]).strip()
            if not state_name or state_name.startswith("Note"):
                continue
            rec = {"state": state_name}
            for cls in ["hospital", "nursing_facility", "mco", "icf_iid", "ambulance", "other"]:
                rec[cls] = _clean_rate(r.get(cls, 0.0))
            rec["max_subject_rate"] = max(rec[c] for c in SUBJECT_CLASSES)
            rec["max_exempt_rate"] = max(rec[c] for c in EXEMPT_CLASSES)
            rows.append(rec)

        out = pd.DataFrame(rows)
        self._tag_df(out)
        return out

    def validate(self, df: pd.DataFrame, expansion_states: set[str]) -> dict:
        """
        Cross-check parsed data against known KFF anchors.
        Returns {status: 'pass'|'flag'|'error', notes: str}.
        """
        try:
            # Anchor 1: ≥30 expansion states with non-exempt rate > 3.5%.
            # (KFF reports 31 as of Feb 2026; allow for minor revision.)
            n_exposed = (
                df[df["state"].isin(expansion_states)]["max_subject_rate"] > 3.5
            ).sum()
            anchor1_ok = n_exposed >= 30

            # Anchor 2: ≥25 states with hospital rate > 3.5%.
            n_hospital = (
                df[df["state"].isin(expansion_states)]["hospital"] > 3.5
            ).sum()
            anchor2_ok = n_hospital >= 25

            if anchor1_ok and anchor2_ok:
                return {
                    "status": "pass",
                    "notes": (
                        f"{n_exposed} expansion states with non-exempt tax > 3.5%; "
                        f"{n_hospital} with hospital tax > 3.5%."
                    ),
                }
            flags = []
            if not anchor1_ok:
                flags.append(f"Only {n_exposed} expansion states have non-exempt tax > 3.5% (expected ≥30).")
            if not anchor2_ok:
                flags.append(f"Only {n_hospital} states have hospital tax > 3.5% (expected ≥25).")
            return {"status": "flag", "notes": " ".join(flags)}
        except Exception as exc:
            return {"status": "error", "notes": str(exc)}
