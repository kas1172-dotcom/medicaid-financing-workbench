"""
CMS-64 Medicaid expenditures: data.medicaid.gov.

Uses the "Medicaid CMS-64 New Adult Group Expenditures" dataset which has
quarterly state-level totals back to 2014 and is the most current available.

Dataset: Medicaid CMS-64 New Adult Group Expenditures
ID:      00505e90-f8ac-5921-b12f-5e23ba7ffcf3
Fields used:
  state                                                       : state name (CMS format)
  quarter_end_date                                            : YYYY-MM-DD
  total_computable_all_medical_assistance_expenditures        : total Medicaid spend ($)
  total_federal_share_all_medical_assistance_expenditures     : federal share ($)

We sum the four quarters of the most recent complete federal fiscal year
(FFY = Oct 1 – Sep 30, so quarters ending Dec, Mar, Jun, Sep of the same FFY).
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import requests

DATASET_ID = "00505e90-f8ac-5921-b12f-5e23ba7ffcf3"
BASE = "https://data.medicaid.gov/api/1/datastore/query"
RAW_DIR = Path("data/raw")
PAGE_SIZE = 5000


class FetchError(RuntimeError):
    pass


def _parse_dollars(s: str) -> int:
    if not s or s.strip() in ("N/A", "", "null"):
        return 0
    return int(s.replace(",", "").replace("$", "").strip())


def fetch_cms64(timeout: int = 60) -> list[dict]:
    """
    Pull all rows from the CMS-64 quarterly dataset, cache raw JSON, return records.
    Raises FetchError on network or empty-response errors.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{DATASET_ID}/0"
    all_rows: list[dict] = []
    offset = 0
    while True:
        try:
            resp = requests.get(
                url, params={"limit": PAGE_SIZE, "offset": offset}, timeout=timeout
            )
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise FetchError(f"CMS-64 fetch failed at offset {offset}: {exc}") from exc

        rows = payload.get("results", payload.get("data", []))
        all_rows.extend(rows)
        total = payload.get("count", 0)
        offset += len(rows)
        if offset >= total or not rows:
            break

    if not all_rows:
        raise FetchError("CMS-64 response contained no rows")

    stamp = time.strftime("%Y%m%dT%H%M%S")
    (RAW_DIR / f"cms64_{stamp}.json").write_text(json.dumps(all_rows, indent=2))
    return all_rows


def parse_provider_tax_revenue_by_state(rows: list[dict]) -> dict[str, float] | None:
    """
    Extract provider-tax revenue from CMS-64 T-19 supplemental data, if present.

    The standard CMS-64 expenditure dataset (00505e90-...) does not include the
    T-19 "Sources of Nonfederal Share" schedule, which is where states report
    provider-tax revenue as a dollar amount. If a future dataset exposes T-19
    fields (column names containing "provider_tax" or "provider_related_donation"),
    this function will extract them automatically.

    Returns dict keyed by state name: {state: revenue_millions} or None if the
    column is not present in the dataset.
    """
    if not rows:
        return None
    # Look for T-19 provider-tax revenue columns in the first row.
    sample = rows[0]
    pt_col = next(
        (k for k in sample if "provider_tax" in k.lower() or "provider_related" in k.lower()),
        None,
    )
    if pt_col is None:
        return None  # Column not present in this dataset: caller falls back to rate model.

    by_state: dict[str, float] = {}
    for r in rows:
        state = r.get("state", "").strip()
        if not state or state == "National Totals":
            continue
        try:
            val = _parse_dollars(str(r.get(pt_col, "0")))
            by_state[state] = by_state.get(state, 0.0) + val / 1_000_000
        except (ValueError, TypeError):
            pass
    return by_state if by_state else None


def parse_spending_by_state(rows: list[dict]) -> dict[str, dict]:
    """
    Aggregate rows to most-recent complete FFY state totals.

    Returns dict keyed by CMS state name:
      { "California": {"total_millions": 143780, "fed_millions": 87931,
                       "nonfed_millions": 55849, "ffy": 2024} }
    """
    # Build per (state, quarter_end_date) sums
    by_state_quarter: dict[tuple, dict] = {}
    for r in rows:
        state = r.get("state", "").strip()
        qdate = r.get("quarter_end_date", "")
        if not state or not qdate or state == "National Totals":
            continue
        key = (state, qdate)
        if key not in by_state_quarter:
            by_state_quarter[key] = {"total": 0, "federal": 0}
        by_state_quarter[key]["total"] += _parse_dollars(
            r.get("total_computable_all_medical_assistance_expenditures", "0")
        )
        by_state_quarter[key]["federal"] += _parse_dollars(
            r.get("total_federal_share_all_medical_assistance_expenditures", "0")
        )

    # A quarter belongs to FFY Y if it ends in Dec(Y-1), Mar(Y), Jun(Y), or Sep(Y)
    def quarter_to_ffy(qdate: str) -> int:
        year, month = int(qdate[:4]), int(qdate[5:7])
        return year if month <= 9 else year + 1

    state_ffy_quarters: dict[str, dict[int, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    for state, qdate in by_state_quarter:
        state_ffy_quarters[state][quarter_to_ffy(qdate)].append(qdate)

    # Find the latest FFY where >= 40 states have all 4 quarters
    all_ffys = sorted(
        {ffy for s in state_ffy_quarters.values() for ffy in s}, reverse=True
    )
    target_ffy = None
    for ffy in all_ffys:
        complete = sum(
            1
            for s in state_ffy_quarters
            if len(state_ffy_quarters[s].get(ffy, [])) == 4
        )
        if complete >= 40:
            target_ffy = ffy
            break

    if target_ffy is None:
        raise FetchError("Could not identify a complete FFY in CMS-64 data")

    result: dict[str, dict] = {}
    for state, ffy_map in state_ffy_quarters.items():
        quarters = ffy_map.get(target_ffy, [])
        if not quarters:
            continue
        total = sum(by_state_quarter[(state, q)]["total"] for q in quarters)
        fed = sum(by_state_quarter[(state, q)]["federal"] for q in quarters)
        result[state] = {
            "total_millions": round(total / 1_000_000),
            "fed_millions": round(fed / 1_000_000),
            "nonfed_millions": round((total - fed) / 1_000_000),
            "ffy": target_ffy,
            "quarters_used": len(quarters),
        }

    return result


def load_cached_cms64() -> list[dict] | None:
    """Return the most recent cached pull, or None."""
    if not RAW_DIR.exists():
        return None
    files = sorted(RAW_DIR.glob("cms64_*.json"))
    if not files:
        return None
    raw = json.loads(files[-1].read_text())
    # Handle both old format (dict with results key) and new format (list)
    if isinstance(raw, list):
        return raw
    return raw.get("results", raw.get("data", []))
