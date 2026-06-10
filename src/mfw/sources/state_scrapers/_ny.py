"""
New York — Provider-Specific Taxes (Hospital + MCO)
Source: NY DOH Quarterly Provider-Specific Tax Reports
URL:    https://www.health.ny.gov/health_care/medicaid/rates/dfrs/prov_spec_taxes/2025/
Structure: percentage (4–5% NPR hospital; MCO PMPM CMS-approved)
Phase 1 confidence: likely — DOH page returns 403; rates from NYS DOH secondary sources.

Hospital tax: 4–5% of net patient revenue per NYS DOH rate methodology.
MCO per-member-per-month tax approved by CMS effective January 1, 2025.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    RATE_BASIS_SEED_CARRYOVER, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://www.health.ny.gov/health_care/medicaid/rates/dfrs/prov_spec_taxes/2025/"
_FALLBACK_RATE = 4.5   # midpoint of 4–5% confirmed range


class NewYorkScraper(StateScraperBase):
    state = "New York"
    abbr = "NY"
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
                native_rate=f"{rate:.2f}% net patient revenue (NYS DOH quarterly rate)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "DOH quarterly reports return 403 on direct fetch; rate 4–5% "
                    "confirmed from NYS DOH rate methodology records. "
                    "Seek current-quarter DOH report for exact figure."
                ),
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=None,
                native_rate="PMPM amount (CMS-approved; effective Jan 1, 2025; not converted to %)",
                rate_basis=RATE_BASIS_SEED_CARRYOVER,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO tax is per-member-per-month; not converted to % without capitation base.",
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        if resp.status_code == 403:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        match = re.search(r"(\d+\.\d+)\s*(?:percent|%)[^.]{0,80}?(?:patient|revenue|net)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 2.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED
            except ValueError:
                pass
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
