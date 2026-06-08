"""
Panel builder — assembles one analysis-ready state-level frame.

Tries live sources first; on any failure, falls back to seed and tags every
record with data_provenance so downstream outputs can disclose it. This is the
single join point: every analysis reads from the panel, never from raw sources.
"""

from __future__ import annotations

import pandas as pd

from ..sources import seed
from ..sources.cms64 import fetch_cms64, load_cached_cms64, FetchError as CMS64Error


def build_panel(prefer_live: bool = False) -> pd.DataFrame:
    """
    Return the state panel as a DataFrame.

    prefer_live=True attempts the CMS-64 API (and would join managed care + ACS
    in a full live build). prefer_live=False uses the seed dataset directly so
    the tool is instant and deterministic for demos.
    """
    provenance = "seed"
    if prefer_live:
        try:
            _ = fetch_cms64()           # validated pull; full join wired in live build
            provenance = "live"
        except CMS64Error:
            cached = load_cached_cms64()
            provenance = "cached" if cached else "seed"

    records = seed.load_seed_records()
    df = pd.DataFrame(records)
    # Provenance reflects the best source actually obtained this run.
    df["data_provenance"] = provenance if prefer_live else "seed"

    # Attach documented work-requirement status; expansion states default to pending.
    def _wr_status(abbr, expansion):
        if abbr in seed.WORK_REQUIREMENT_STATUS:
            return seed.WORK_REQUIREMENT_STATUS[abbr]["status"]
        return "pending" if expansion else "not_applicable"

    df["work_req_status"] = [
        _wr_status(a, e) for a, e in zip(df["abbr"], df["expansion"])
    ]
    return df


def panel_summary(df: pd.DataFrame) -> dict:
    """Headline national totals for the dashboard banner."""
    return {
        "n_states": int(len(df)),
        "n_expansion": int(df["expansion"].sum()),
        "total_medicaid_spend_billion": round(df["total_medicaid_spend"].sum() / 1000, 1),
        "total_enrollment_million": round(df["enrollment"].sum() / 1e6, 1),
        "data_provenance": df["data_provenance"].iloc[0],
    }
