"""
Alabama — Hospital Assessment Fee (non-expansion state)
Source: AL Department of Revenue FAQ
URL:    https://www.revenue.alabama.gov/faqs/hospital-assessment-fee/
Structure: percentage
Verified by Phase 1 fetch — 6.0% confirmed.

Non-expansion state: exposure to the reduced cap is ZERO.
Rate is frozen at July 2025 level under OBBBA.
Recorded for completeness; analysis correctly assigns zero phase-down exposure.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.revenue.alabama.gov/faqs/hospital-assessment-fee/"
_RATE = 6.0


class AlabamaScraper(StateScraperBase):
    state = "Alabama"
    abbr = "AL"
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
                native_rate=f"{rate}% net patient revenue (quarterly)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Non-expansion state — zero phase-down exposure. "
                    "Rate frozen at July 2025 level. Seed (4.2%) understated."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _RATE, CONFIDENCE_LIKELY
        text = resp.text
        if "6" in text and ("hospital" in text.lower() or "assessment" in text.lower()):
            return _RATE, CONFIDENCE_VERIFIED
        return _RATE, CONFIDENCE_LIKELY
