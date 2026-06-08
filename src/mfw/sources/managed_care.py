"""
Medicaid managed care enrollment — data.medicaid.gov.

Provides MCO penetration and dual-eligible-by-plan counts by state, used by the
duals and managed-care analyses. Same public API pattern as cms64.py.

CAUTION (documented by CMS): a beneficiary can be enrolled in more than one
managed care program type (e.g. a comprehensive MCO and a behavioral health
organization). Counts must NOT be summed across program types or the same
person is counted twice. The ETL layer uses only the comprehensive-MCO and
total-enrollee columns to avoid this.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

DATASET_ID = "e2ce0d2f-07c5-5213-947a-31e19bc649f6"  # Managed Care Enrollment by Program and Population
BASE = "https://data.medicaid.gov/api/1/datastore/query"
RAW_DIR = Path("data/raw")


class FetchError(RuntimeError):
    pass


def fetch_managed_care(limit: int = 5000, timeout: int = 30) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{DATASET_ID}/0"
    try:
        resp = requests.get(url, params={"limit": limit}, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise FetchError(f"Managed care fetch failed: {exc}") from exc

    stamp = time.strftime("%Y%m%dT%H%M%S")
    (RAW_DIR / f"managedcare_{stamp}.json").write_text(json.dumps(payload, indent=2))
    results = payload.get("results", payload.get("data", []))
    if not results:
        raise FetchError("Managed care response contained no rows")
    return results
