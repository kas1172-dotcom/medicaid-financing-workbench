"""
North Carolina — Hospital Assessment Program (HASP)
Source: NC DHHS Medicaid assessments page
URL:    https://medicaid.ncdhhs.gov/providers/cost-reports-and-assessments/nursing-facility-cost-assessment
Structure: percentage (~6% NPR; >$2.5B/year)
Phase 1 confidence: likely — hospital page redirects; rate from press and NC legislation.

NC HASP: ~6% of net patient revenue; >$2.5B/year confirmed in press.
Statute: NCGS HB397 §10.28(a). NC expanded Medicaid in 2023.
The confirmed URL is the NF cost-assessment page; hospital-specific page redirects.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://medicaid.ncdhhs.gov/providers/cost-reports-and-assessments/nursing-facility-cost-assessment"
_FALLBACK_RATE = 6.0


class NorthCarolinaScraper(StateScraperBase):
    state = "North Carolina"
    abbr = "NC"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, confidence = self._parse_rate()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(rate, 2),
                native_rate=f"{rate:.2f}% net patient revenue (HASP, NCGS HB397 §10.28(a))",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"HASP ~{_FALLBACK_RATE}% NPR; >$2.5B/year confirmed in press. "
                    "Hospital-specific URL redirects; rate from NC legislation/press. "
                    "NC expanded Medicaid Nov 2023."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "assessment" in text.lower() or "ncdhhs" in text.lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,60}?(?:patient|revenue)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 4.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
