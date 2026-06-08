"""
CMS-64 Medicaid expenditures — data.medicaid.gov.

The CMS-64 is the authoritative record of what states actually spent and the
federal match they drew down. It is the backbone of any Medicaid financing
analysis. Published as the "Medicaid Financial Management Data" dataset.

Public API (no key required):
    https://data.medicaid.gov/api/1/datastore/query/{dataset_id}/0

This module fetches, caches the raw pull to data/raw/, and exposes a clean
state-year frame. On any network failure it raises FetchError; the ETL layer
catches that and falls back to seed data, tagging provenance accordingly.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

# "Medicaid Financial Management Data" — state-by-state CMS-64 expenditures.
# Resource id from the data.gov catalog (medicaid-financial-management-data.7kua-37xz).
DATASET_ID = "7kua-37xz"
BASE = "https://data.medicaid.gov/api/1/datastore/query"
RAW_DIR = Path("data/raw")


class FetchError(RuntimeError):
    pass


def fetch_cms64(limit: int = 5000, timeout: int = 30) -> list[dict]:
    """Pull CMS-64 rows from data.medicaid.gov, cache raw JSON, return records."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{BASE}/{DATASET_ID}/0"
    params = {"limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise FetchError(f"CMS-64 fetch failed: {exc}") from exc

    stamp = time.strftime("%Y%m%dT%H%M%S")
    (RAW_DIR / f"cms64_{stamp}.json").write_text(json.dumps(payload, indent=2))

    results = payload.get("results", payload.get("data", []))
    if not results:
        raise FetchError("CMS-64 response contained no rows")
    return results


def load_cached_cms64() -> list[dict] | None:
    """Return the most recent cached CMS-64 pull, or None if none exists."""
    if not RAW_DIR.exists():
        return None
    files = sorted(RAW_DIR.glob("cms64_*.json"))
    if not files:
        return None
    payload = json.loads(files[-1].read_text())
    return payload.get("results", payload.get("data", []))
