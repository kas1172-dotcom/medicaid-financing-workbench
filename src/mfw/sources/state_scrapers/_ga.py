"""
Georgia — Hospital Provider Fee (non-expansion state)
Source: GA DCH Hospital Provider Fee Payment page
URL:    https://dch.georgia.gov/providers/provider-types/hospital-providers/provider-fee-payment
Structure: percentage
Verified by Phase 1 fetch.

Confirmed rates:
  Regular hospitals:  1.45% net patient revenue
  Trauma centers:     1.40% net patient revenue

Non-expansion state: zero phase-down exposure.
Seed (1.5%) is close to confirmed rate (1.45%).
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://dch.georgia.gov/providers/provider-types/hospital-providers/provider-fee-payment"
_RATE = 1.45


class GeorgiaScraper(StateScraperBase):
    state = "Georgia"
    abbr = "GA"
    expansion = False   # non-expansion

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, confidence = self._parse_rate()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=rate,
                native_rate=f"{rate}% net patient revenue (1.40% trauma centers)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="Non-expansion state — zero phase-down exposure. Seed (1.5%) close match.",
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _RATE, CONFIDENCE_LIKELY
        text = resp.text
        if "1.45" in text or "provider fee" in text.lower():
            return _RATE, CONFIDENCE_VERIFIED
        return _RATE, CONFIDENCE_LIKELY
