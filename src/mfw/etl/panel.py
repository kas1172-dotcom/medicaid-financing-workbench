"""
Panel builder — assembles one analysis-ready state-level DataFrame.

Live build path (prefer_live=True and live CSVs present in data/current/):
  1. Load spending from data/current/cms64.csv
     → total_medicaid_spend, total_medicaid_fed_spend, nonfederal_share
  2. Load enrollment from data/current/cms_enrollment.csv
     → enrollment, expansion_adults, duals
  3. Overlay seed for fields with no API source:
     → expansion (boolean), fmap, provider_taxes_by_class, hcbs_spend,
       work_req_status

Seed-only path (prefer_live=False or no live CSVs): identical to original
behaviour, tagged data_provenance="seed".

All downstream analyses read from the panel; they never touch raw sources.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..sources import seed
from ..sources._state_map import ANALYSIS_ABBRS

CURRENT_DIR = Path("data/current")


def _load_live_spending() -> dict[str, dict] | None:
    path = CURRENT_DIR / "cms64.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    result = {}
    for _, row in df.iterrows():
        abbr = str(row.get("abbr", "")).strip().upper()
        if abbr in ANALYSIS_ABBRS:
            result[abbr] = {
                "total_medicaid_spend":     float(row.get("total_medicaid_spend", 0)),
                "total_medicaid_fed_spend": float(row.get("total_medicaid_fed_spend", 0)),
                "nonfederal_share":         float(row.get("nonfederal_share", 0)),
            }
    return result if result else None


def _load_live_enrollment() -> dict[str, dict] | None:
    path = CURRENT_DIR / "cms_enrollment.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    result = {}
    for _, row in df.iterrows():
        abbr = str(row.get("abbr", "")).strip().upper()
        if abbr in ANALYSIS_ABBRS:
            result[abbr] = {
                "enrollment":       int(row.get("enrollment", 0)),
                "expansion_adults": int(row.get("expansion_adults", 0)),
                "duals":            int(row.get("duals", 0)),
            }
    return result if result else None


def _wr_status(abbr: str, expansion: bool) -> str:
    if abbr in seed.WORK_REQUIREMENT_STATUS:
        return seed.WORK_REQUIREMENT_STATUS[abbr]["status"]
    return "pending" if expansion else "not_applicable"


def build_panel(prefer_live: bool = False) -> pd.DataFrame:
    """
    Return the state panel as a DataFrame.

    prefer_live=True uses real CMS data for spending and enrollment (from
    data/current/ CSVs written by `mfw refresh`), overlaid on seed values for
    fields that have no public API source: FMAP, provider tax rates, expansion
    status, and HCBS spend.
    """
    records = seed.load_seed_records()
    seed_by_abbr = {r["abbr"]: r for r in records}

    live_spending   = _load_live_spending()   if prefer_live else None
    live_enrollment = _load_live_enrollment() if prefer_live else None

    if not prefer_live or (live_spending is None and live_enrollment is None):
        df = pd.DataFrame(records)
        df["data_provenance"] = "seed"
        df["work_req_status"] = [
            _wr_status(r["abbr"], r["expansion"]) for r in records
        ]
        return df

    parts = []
    if live_spending:
        parts.append("cms64")
    if live_enrollment:
        parts.append("cms_enrollment")
    provenance = "live:" + "+".join(parts)

    rows = []
    for abbr, seed_row in seed_by_abbr.items():
        row = dict(seed_row)
        if live_spending and abbr in live_spending:
            row.update(live_spending[abbr])
        if live_enrollment and abbr in live_enrollment:
            row.update(live_enrollment[abbr])
        row["data_provenance"] = provenance
        row["work_req_status"] = _wr_status(abbr, row["expansion"])
        rows.append(row)

    return pd.DataFrame(rows)


def panel_summary(df: pd.DataFrame) -> dict:
    return {
        "n_states":                     int(len(df)),
        "n_expansion":                  int(df["expansion"].sum()),
        "total_medicaid_spend_billion": round(df["total_medicaid_spend"].sum() / 1000, 1),
        "total_enrollment_million":     round(df["enrollment"].sum() / 1e6, 1),
        "data_provenance":              df["data_provenance"].iloc[0],
    }
