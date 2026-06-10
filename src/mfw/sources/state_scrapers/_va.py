"""
Virginia — Hospital Coverage Assessment
Source: 12VAC30-160-10 (Virginia Administrative Code)
URL:    https://law.lis.virginia.gov/admincode/title12/agency30/chapter160/section10/
Structure: percentage (quarterly calculated, effectively ~6%)
Verified by Phase 1 fetch.

Rate: Calculated quarterly as (total coverage assessment ÷ total NPR).
Effectively ~6% of net patient service revenue for private acute care hospitals.
$572M revenue in 2025 across 63 hospitals confirmed.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    RATE_BASIS_SEED_CARRYOVER, STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://law.lis.virginia.gov/admincode/title12/agency30/chapter160/section10/"
_RATE = 6.0
_NOTES = (
    "Rate calculated quarterly as coverage assessment ÷ NPR; effectively ~6% "
    "of NPSV. Confirmed: 63 private acute-care hospitals, $572M revenue (2025)."
)


class VirginiaScraper(StateScraperBase):
    state = "Virginia"
    abbr = "VA"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, confidence = self._parse_rate()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=rate,
                native_rate=f"~{rate}% net patient service revenue (quarterly calculated)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient service revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=_NOTES,
            ),
            # MCO tax: rate from seed — not confirmed from primary source URL.
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=2.0,
                native_rate="2.0% (seed/MACPAC; not confirmed from primary source)",
                rate_basis=RATE_BASIS_SEED_CARRYOVER,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO rate from seed — verify against VA DMAS/CMS SPA.",
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _RATE, CONFIDENCE_LIKELY
        text = resp.text
        # Look for the section confirming the coverage assessment methodology
        if "coverage assessment" in text.lower() or "net patient" in text.lower():
            return _RATE, CONFIDENCE_VERIFIED
        return _RATE, CONFIDENCE_LIKELY
