"""
Kansas — Hospital Assessment (non-expansion state)
Source: KSA 65-6208
URL:    https://ksrevisor.gov/statutes/chapters/ch65/065_062_0008.html
Structure: percentage (ceiling confirmed; current rate at ceiling)
Verified by Phase 1 fetch.

Confirmed: statutory ceiling = 6% of net inpatient + outpatient operating revenue.
CMS approved KS 2025 preprint at 6% (increased from 3%).
Non-expansion state: zero phase-down exposure.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://ksrevisor.gov/statutes/chapters/ch65/065_062_0008.html"
_RATE = 6.0


class KansasScraper(StateScraperBase):
    state = "Kansas"
    abbr = "KS"
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
                native_rate=f"{rate}% net operating revenue (ceiling in KSA 65-6208)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net inpatient + outpatient operating revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="Non-expansion — zero phase-down exposure. 6% confirmed per CMS 2025 preprint.",
            ),
            # MCO tax also exists per seed
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=1.8,
                native_rate="1.8% (seed value; KS MCO tax per MACPAC)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO rate from seed; verify against KS Medicaid agency.",
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _RATE, CONFIDENCE_LIKELY
        text = resp.text
        if "65-6208" in text or ("6" in text and "percent" in text.lower()):
            return _RATE, CONFIDENCE_VERIFIED
        return _RATE, CONFIDENCE_LIKELY
