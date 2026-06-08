"""
Census American Community Survey (ACS) — api.census.gov.

Provides state-level Medicaid/public-coverage counts to cross-validate CMS
enrollment and to compute coverage context (uninsured rates, expansion-adult
populations). Uses ACS 1-year Subject Table S2704 (Public Health Insurance
Coverage by Type and Selected Characteristics).

API works without a key for light use; set CENSUS_API_KEY to raise rate limits.
Endpoint pattern:
    https://api.census.gov/data/{year}/acs/acs1/subject?get=NAME,{var}&for=state:*
"""

from __future__ import annotations

import os
import requests

BASE = "https://api.census.gov/data"


class FetchError(RuntimeError):
    pass


def fetch_acs_coverage(year: int = 2023, timeout: int = 30) -> list[dict]:
    """Pull state Medicaid coverage estimates from ACS S2704."""
    # S2704_C02_006E ~ number with Medicaid/means-tested public coverage (estimate).
    var = "S2704_C02_006E"
    url = f"{BASE}/{year}/acs/acs1/subject"
    params = {"get": f"NAME,{var}", "for": "state:*"}
    key = os.environ.get("CENSUS_API_KEY")
    if key:
        params["key"] = key
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        rows = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise FetchError(f"Census ACS fetch failed: {exc}") from exc

    header, *data = rows
    return [dict(zip(header, r)) for r in data]
