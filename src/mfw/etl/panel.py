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
SCRAPED_TAXES_FILE = CURRENT_DIR / "state_provider_taxes.csv"

_SUBJECT_CLASSES = frozenset({"hospital", "mco", "ambulance", "other"})


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


def _load_scraped_taxes() -> dict[str, dict] | None:
    """
    Load state_provider_taxes.csv (written by the state scraper runner).

    Returns a dict keyed by abbr. Each value contains:
      provider_taxes_by_class  — {class: effective_rate_pct} for comparable rows only
      provider_tax_rate        — max subject-class rate (or None if all not_comparable)
      provider_tax_waiver_flag — 'non_uniformity_waiver' for RI/NV, else None
      provider_tax_data_source — 'scraped' (provenance tag for dashboard)

    States with confidence=failed or all rows not_comparable are omitted so the
    caller falls back to seed. Never fabricates a percentage.
    """
    if not SCRAPED_TAXES_FILE.exists():
        return None
    df = pd.read_csv(SCRAPED_TAXES_FILE)
    if df.empty:
        return None

    result: dict[str, dict] = {}
    for abbr, group in df.groupby("abbr"):
        abbr = str(abbr).strip().upper()

        # Non-failed rows with a usable effective_rate_pct.
        usable = group[group["confidence"] != "failed"]
        if usable.empty:
            continue

        # Comparable rows: rate_basis != not_comparable and effective_rate_pct present.
        comparable = usable[
            (usable["rate_basis"] != "not_comparable") &
            usable["effective_rate_pct"].notna()
        ]

        taxes: dict[str, float] = {}
        for _, row in comparable.iterrows():
            pclass = str(row.get("provider_class", "")).strip().lower()
            try:
                taxes[pclass] = float(row["effective_rate_pct"])
            except (ValueError, TypeError):
                pass

        # Waiver flag from any row.
        waiver_rows = usable[usable["waiver_flag"].notna()]
        waiver_flag = str(waiver_rows["waiver_flag"].iloc[0]) if not waiver_rows.empty else None

        # Provider_tax_rate: max subject-class comparable rate.
        subject_rates = [v for k, v in taxes.items() if k in _SUBJECT_CLASSES]
        provider_tax_rate = max(subject_rates) if subject_rates else None

        # Only add entry if we have something useful.
        if taxes or waiver_flag:
            result[abbr] = {
                "provider_taxes_by_class": taxes,
                "provider_tax_rate": provider_tax_rate,
                "provider_tax_waiver_flag": waiver_flag,
                "provider_tax_data_source": "scraped",
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
    scraped_taxes   = _load_scraped_taxes()

    if not prefer_live or (live_spending is None and live_enrollment is None):
        rows = []
        for r in records:
            row = dict(r)
            abbr = str(row["abbr"]).strip().upper()
            if scraped_taxes and abbr in scraped_taxes:
                st = scraped_taxes[abbr]
                if st["provider_taxes_by_class"]:
                    row["provider_taxes_by_class"] = st["provider_taxes_by_class"]
                if st["provider_tax_rate"] is not None:
                    row["provider_tax_rate"] = st["provider_tax_rate"]
                row["provider_tax_waiver_flag"] = st["provider_tax_waiver_flag"]
                row["provider_tax_data_source"] = "scraped"
            else:
                row["provider_tax_waiver_flag"] = None
                row["provider_tax_data_source"] = "seed"
            row["data_provenance"] = "seed"
            row["work_req_status"] = _wr_status(abbr, row["expansion"])
            rows.append(row)
        return pd.DataFrame(rows)

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
        if scraped_taxes and abbr in scraped_taxes:
            st = scraped_taxes[abbr]
            if st["provider_taxes_by_class"]:
                row["provider_taxes_by_class"] = st["provider_taxes_by_class"]
            if st["provider_tax_rate"] is not None:
                row["provider_tax_rate"] = st["provider_tax_rate"]
            row["provider_tax_waiver_flag"] = st["provider_tax_waiver_flag"]
            row["provider_tax_data_source"] = "scraped"
        else:
            row["provider_tax_waiver_flag"] = None
            row["provider_tax_data_source"] = "seed"
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
