"""
New Jersey — Health Care Facility Assessments
Source: NJ DOH Health Care Facility Assessments
URL:    https://www.nj.gov/health/hcf/assessments/
Structure: unit_based (per-admission for hospitals)
Verified by Phase 1 fetch.

Confirmed rates (P.L.2025, c.70):
  Hospital:          $12.50 per adjusted admission
  Ambulatory care:    2.5% of gross receipts (percentage)
  Subacute:          $35.00 per admission

The hospital rate is per-admission, NOT a % of revenue → not_comparable for
the standard 3.5% phase-down cap test. Secondary sources suggest ~5.8%
effective rate, but we do NOT derive this without a confirmed revenue base.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE, STRUCTURE_UNIT_BASED,
    RateRow, StateScraperBase,
)

URL = "https://www.nj.gov/health/hcf/assessments/"


class NewJerseyScraper(StateScraperBase):
    state = "New Jersey"
    abbr = "NJ"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_UNIT_BASED,
                effective_rate_pct=None,   # not_comparable
                native_rate="$12.50 per adjusted admission (P.L.2025, c.70)",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Per-admission structure — not comparable to % cap without "
                    "volume data. Do NOT derive a % without confirmed NPR base. "
                    "Seed (5.8%) is an approximation; not used for phase-down calc."
                ),
            ),
            # Ambulatory (subsumed under 'other' class)
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="other",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=2.5,
                native_rate="2.5% gross receipts (ambulatory care)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross receipts",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="Ambulatory care assessment (below 3.5% floor — not exposed).",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "12.50" in text or "assessments" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
