"""
CMS Medicaid enrollment: data.medicaid.gov.

Three datasets, all public (no key required):

1. Total Medicaid enrollment by year
   "Program Information for Medicaid and CHIP Beneficiaries by Year"
   ID: 5c267647-50e9-4a81-b2f2-8f23cec6631a
   → enrollment (averageenrollmentpermonth, Medicaid only, most recent year)

2. Enrollment by major eligibility group by year
   "Major Eligibility Group Information for Medicaid and CHIP Beneficiaries by Year"
   ID: bffd757a-3ae9-42fc-809a-820c2919496b
   → expansion_adults ("Adult expansion group" group, same year)

3. Dual-status enrollment by year
   "Dual Status Information for Medicaid and CHIP Beneficiaries by Year"
   ID: 93b36a8e-4dd5-4ff4-9a8b-8c6537684705
   → duals (Full + Partial dual eligibility, same year)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

ENROLLMENT_DATASET = "5c267647-50e9-4a81-b2f2-8f23cec6631a"
ELIGIBILITY_DATASET = "bffd757a-3ae9-42fc-809a-820c2919496b"
DUAL_DATASET = "93b36a8e-4dd5-4ff4-9a8b-8c6537684705"
BASE = "https://data.medicaid.gov/api/1/datastore/query"
RAW_DIR = Path("data/raw")
PAGE_SIZE = 5000


class FetchError(RuntimeError):
    pass


def _fetch_all(dataset_id: str, timeout: int = 60) -> list[dict]:
    url = f"{BASE}/{dataset_id}/0"
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
            raise FetchError(f"Fetch failed for {dataset_id} at offset {offset}: {exc}") from exc
        rows = payload.get("results", [])
        all_rows.extend(rows)
        total = payload.get("count", 0)
        offset += len(rows)
        if offset >= total or not rows:
            break
    return all_rows


def _parse_count(s: str) -> int:
    if not s or s.strip() in ("N/A", "", "null", "*"):
        return 0
    return int(s.replace(",", "").strip())


def _most_recent_year(rows: list[dict], year_field: str = "year") -> str:
    years = sorted({r.get(year_field, "") for r in rows if r.get(year_field)}, reverse=True)
    return years[0] if years else ""


def fetch_enrollment(timeout: int = 60) -> dict[str, dict]:
    """
    Fetch total Medicaid enrollment, expansion adults, and duals for each state.

    Returns dict keyed by CMS state name:
      { "California": {"enrollment": 14305237, "expansion_adults": 4923593, "duals": 1300000} }
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")

    # 1. Total enrollment
    enroll_rows = _fetch_all(ENROLLMENT_DATASET, timeout)
    (RAW_DIR / f"cms_enrollment_{stamp}.json").write_text(json.dumps(enroll_rows, indent=2))

    enroll_year = _most_recent_year(enroll_rows)
    total_by_state: dict[str, int] = {}
    for r in enroll_rows:
        if r.get("year") == enroll_year and r.get("programtype") == "Medicaid":
            state = r.get("state", "").strip()
            total_by_state[state] = _parse_count(r.get("averageenrollmentpermonth", "0"))

    # 2. Expansion adults by eligibility group
    elig_rows = _fetch_all(ELIGIBILITY_DATASET, timeout)
    (RAW_DIR / f"cms_eligibility_{stamp}.json").write_text(json.dumps(elig_rows, indent=2))

    elig_year = _most_recent_year(elig_rows)
    expansion_by_state: dict[str, int] = {}
    for r in elig_rows:
        if (
            r.get("year") == elig_year
            and r.get("majoreligibility_group") == "Adult expansion group"
        ):
            state = r.get("state", "").strip()
            expansion_by_state[state] = _parse_count(r.get("averageenrollmentpermonth", "0"))

    # 3. Dual eligibles (full + partial)
    dual_rows = _fetch_all(DUAL_DATASET, timeout)
    (RAW_DIR / f"cms_duals_{stamp}.json").write_text(json.dumps(dual_rows, indent=2))

    dual_year = _most_recent_year(dual_rows)
    duals_by_state: dict[str, int] = {}
    for r in dual_rows:
        if r.get("year") == dual_year and r.get("dualstatus") in (
            "Full dual eligibility",
            "Partial dual eligibility",
        ):
            state = r.get("state", "").strip()
            duals_by_state[state] = duals_by_state.get(state, 0) + _parse_count(
                r.get("averageenrollmentpermonth", "0")
            )

    # Merge
    all_states = set(total_by_state) | set(expansion_by_state) | set(duals_by_state)
    result: dict[str, dict] = {}
    for state in all_states:
        result[state] = {
            "enrollment": total_by_state.get(state, 0),
            "expansion_adults": expansion_by_state.get(state, 0),
            "duals": duals_by_state.get(state, 0),
            "enroll_year": enroll_year,
        }

    return result


def load_cached_enrollment() -> dict[str, dict] | None:
    """Return parsed enrollment from most recent cache, or None."""
    if not RAW_DIR.exists():
        return None
    files = sorted(RAW_DIR.glob("cms_enrollment_*.json"))
    if not files:
        return None
    try:
        enroll_rows = json.loads(files[-1].read_text())
        enroll_year = _most_recent_year(enroll_rows)
        result: dict[str, dict] = {}
        for r in enroll_rows:
            if r.get("year") == enroll_year and r.get("programtype") == "Medicaid":
                state = r.get("state", "").strip()
                result.setdefault(state, {"enrollment": 0, "expansion_adults": 0, "duals": 0,
                                          "enroll_year": enroll_year})
                result[state]["enrollment"] = _parse_count(r.get("averageenrollmentpermonth", "0"))
        # Try to add duals from cache
        dual_files = sorted(RAW_DIR.glob("cms_duals_*.json"))
        if dual_files:
            dual_rows = json.loads(dual_files[-1].read_text())
            dual_year = _most_recent_year(dual_rows)
            for r in dual_rows:
                if r.get("year") == dual_year and r.get("dualstatus") in (
                    "Full dual eligibility", "Partial dual eligibility"
                ):
                    state = r.get("state", "").strip()
                    if state in result:
                        result[state]["duals"] = result[state].get("duals", 0) + _parse_count(
                            r.get("averageenrollmentpermonth", "0")
                        )
        # Try to add expansion adults from cache
        elig_files = sorted(RAW_DIR.glob("cms_eligibility_*.json"))
        if elig_files:
            elig_rows = json.loads(elig_files[-1].read_text())
            elig_year = _most_recent_year(elig_rows)
            for r in elig_rows:
                if (
                    r.get("year") == elig_year
                    and r.get("majoreligibility_group") == "Adult expansion group"
                ):
                    state = r.get("state", "").strip()
                    if state in result:
                        result[state]["expansion_adults"] = _parse_count(
                            r.get("averageenrollmentpermonth", "0")
                        )
        return result
    except Exception:
        return None
