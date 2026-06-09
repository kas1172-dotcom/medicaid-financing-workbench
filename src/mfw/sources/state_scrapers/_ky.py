"""
Kentucky — Health Care Provider Tax
Source: KY Department of Revenue
URL:    https://revenue.ky.gov/Business/Health-Care-Provider-Tax/Pages/default.aspx
Structure: percentage
Verified by Phase 1 fetch.

Confirmed rates:
  Hospital (KRS 142.303):  2.5% of gross revenues
  MCO:                     5.5% of gross revenues
  ICF-MR:                  5.5% of gross revenues (EXEMPT from phase-down)
  Nursing facility:        per-bed-day (unit_based, EXEMPT from phase-down)

For cap-exposure: MCO 5.5% is the max subject rate (hospital only 2.5%).
Seed shows hospital 5.5% — seed hospital rate is significantly overstated.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, STRUCTURE_UNIT_BASED, RateRow, StateScraperBase,
)

URL = "https://revenue.ky.gov/Business/Health-Care-Provider-Tax/Pages/default.aspx"


class KentuckyScraper(StateScraperBase):
    state = "Kentucky"
    abbr = "KY"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=2.5,
                native_rate="2.5% gross revenues (KRS 142.303)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="Hospital rate confirmed from KY DOR page. Seed (5.5%) overstated.",
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=5.5,
                native_rate="5.5% gross revenues",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="MCO rate confirmed from KY DOR page.",
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="icf_iid",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=5.5,
                native_rate="5.5% gross revenues (ICF-MR; EXEMPT from phase-down)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="EXEMPT class — not counted toward cap exposure.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "health care provider tax" in text or "2.5" in text or "5.5" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
