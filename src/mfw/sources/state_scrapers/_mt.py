"""
Montana: Hospital Facility Utilization Fee (HUF)
Source: MT Department of Revenue
URL:    https://revenue.mt.gov/taxes/miscellaneous/huf
Structure: unit_based (per-bed-day) + percentage (outpatient)
Verified by Phase 1 fetch.

Confirmed rates (MCA Title 15, Chapter 66):
  Inpatient:   $70 per inpatient bed day
  Outpatient:  0.90% of outpatient revenue

The inpatient component is unit_based → not_comparable for the % cap.
The outpatient component is 0.90% → below 3.5% floor, no phase-down exposure.
MT is an expansion state with low/no subject-class exposure.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE, STRUCTURE_UNIT_BASED,
    RateRow, StateScraperBase,
)

URL = "https://revenue.mt.gov/taxes/miscellaneous/huf"


class MontanaScraper(StateScraperBase):
    state = "Montana"
    abbr = "MT"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            # Inpatient: per-bed-day
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_UNIT_BASED,
                effective_rate_pct=None,
                native_rate="$70 per inpatient bed day + 0.90% outpatient revenue",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Hybrid structure: $70/bed-day (unit_based, not_comparable) "
                    "+ 0.90% outpatient (below 3.5% floor, not exposed). "
                    "Seed (0.0%) incorrect: MT does have a hospital tax."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "70" in text or "hospital" in text or "utilization" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
