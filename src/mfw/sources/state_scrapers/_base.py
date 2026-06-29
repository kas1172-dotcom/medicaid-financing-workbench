"""
Base class and data types for state provider-tax scrapers.

Every state adapter:
  1. Inherits StateScraperBase.
  2. Implements scrape() -> list[RateRow].
  3. Returns one RateRow per (state, provider_class) that has data.

Rate rows carry provenance on every field:
  effective_rate_pct : % of revenue base; null for non-percentage structures
  native_rate        : rate in its published units ("5.96% outpatient NPR",
                        "$12.50/admission", "$70/bed-day + 0.9% outpatient")
  rate_basis         : reported | derived | not_comparable
  structure          : percentage | unit_based | capped | amount_targeted | none

For cap-exposure analysis, only rows where rate_basis != 'not_comparable'
contribute a numeric effective_rate_pct. States flagged not_comparable appear
in a separate "non-percentage structures" panel, never as a fabricated bar.

Compliance-risk states (RI, NV) operate above 6% via CMS non-uniformity
waivers and carry waiver_flag='non_uniformity_waiver'. They are NOT treated
as standard cap-exposure: they face a different compliance risk under OBBBA
(tightened uniformity requirements), tracked separately.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import requests

TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "MedicaidFinancingWorkbench/0.2 (public-interest policy research; "
        "contact kapilsharmapersonal99@gmail.com)"
    )
}

RATE_BASIS_REPORTED = "reported"
RATE_BASIS_DERIVED = "derived"
RATE_BASIS_NOT_COMPARABLE = "not_comparable"
# Seed-carryover: rate copied from seed/MACPAC/KFF secondary sources, not confirmed
# from a primary state source URL. Treated identically to seed everywhere downstream:
# the rate value is present but MUST NOT be labeled "scraped" in any UI element.
RATE_BASIS_SEED_CARRYOVER = "seed_carryover"

STRUCTURE_PERCENTAGE = "percentage"
STRUCTURE_UNIT_BASED = "unit_based"
STRUCTURE_CAPPED = "capped"
STRUCTURE_AMOUNT_TARGETED = "amount_targeted"
STRUCTURE_NONE = "none"

CONFIDENCE_VERIFIED = "verified"
CONFIDENCE_LIKELY = "likely"
CONFIDENCE_FAILED = "failed"

# Provider class constants: must match seed.py and analysis/provider_tax.py
EXEMPT_CLASSES = frozenset({"nursing_facility", "icf_iid"})
SUBJECT_CLASSES = frozenset({"hospital", "mco", "ambulance", "other"})


@dataclass
class RateRow:
    state: str
    abbr: str
    expansion: bool
    provider_class: str           # hospital | mco | ambulance | other | nursing_facility | icf_iid
    structure: str                # percentage | unit_based | capped | amount_targeted | none
    effective_rate_pct: Optional[float]  # None when not_comparable
    native_rate: str              # rate in published units, always non-null
    rate_basis: str               # reported | derived | not_comparable
    revenue_base_used: Optional[str]     # description of base for derived rates
    source_url: Optional[str]
    retrieved_date: str
    confidence: str               # verified | likely | failed
    waiver_flag: Optional[str] = field(default=None)  # non_uniformity_waiver | None
    notes: str = field(default="")

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "abbr": self.abbr,
            "expansion": self.expansion,
            "provider_class": self.provider_class,
            "structure": self.structure,
            "effective_rate_pct": self.effective_rate_pct,
            "native_rate": self.native_rate,
            "rate_basis": self.rate_basis,
            "revenue_base_used": self.revenue_base_used,
            "source_url": self.source_url,
            "retrieved_date": self.retrieved_date,
            "confidence": self.confidence,
            "waiver_flag": self.waiver_flag,
            "notes": self.notes,
        }


class StateScraperBase(ABC):
    """Abstract base for all state provider-tax scrapers."""

    state: str        # full state name
    abbr: str         # 2-letter abbreviation
    expansion: bool   # Medicaid expansion status

    @abstractmethod
    def scrape(self) -> list[RateRow]:
        """
        Fetch and parse the primary source for this state's provider-tax rates.

        Must NEVER raise an exception: failures must be caught internally and
        returned as RateRow entries with confidence=failed and null rates.

        Returns one RateRow per (state, provider_class) with data.
        Omit classes with no tax (rate=0); they fall back to seed implicitly.
        """

    def _fetch(self, url: str) -> requests.Response | None:
        """GET a URL; return None on any failure (never raises)."""
        try:
            time.sleep(0.5)  # polite crawl delay
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r
        except Exception:
            return None

    def _today(self) -> str:
        from datetime import date
        return date.today().isoformat()

    def _failed_row(
        self,
        provider_class: str,
        source_url: str | None,
        error: str,
    ) -> RateRow:
        return RateRow(
            state=self.state,
            abbr=self.abbr,
            expansion=self.expansion,
            provider_class=provider_class,
            structure=STRUCTURE_NONE,
            effective_rate_pct=None,
            native_rate="unknown",
            rate_basis=RATE_BASIS_NOT_COMPARABLE,
            revenue_base_used=None,
            source_url=source_url,
            retrieved_date=self._today(),
            confidence=CONFIDENCE_FAILED,
            notes=f"Scrape failed: {error}",
        )
