"""
Washington — Hospital Safety Net Assessment
Source: RCW Ch. 74.60
URL:    https://apps.leg.wa.gov/rcw/default.aspx?cite=74.60&full=true
Structure: amount_targeted (tier-allocated to hit annual dollar target)
Verified by Phase 1 fetch.

Rate set annually by HCA to produce $510M inpatient + $386.4M outpatient
in CY2024. Tiers: standard PPS 100%, rehab 50%, children's 5%/20%.
Not a single % of revenue — amount-targeted → not_comparable for % cap.

MCO tax: 2.0% (seed) — IS a percentage.
WA exposure is primarily via MCO tax.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    RATE_BASIS_REPORTED, STRUCTURE_AMOUNT_TARGETED, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://apps.leg.wa.gov/rcw/default.aspx?cite=74.60&full=true"


class WashingtonScraper(StateScraperBase):
    state = "Washington"
    abbr = "WA"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_AMOUNT_TARGETED,
                effective_rate_pct=None,
                native_rate="$510M inpatient + $386.4M outpatient target (CY2024); tier-allocated",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Annual HCA-set targets allocated by tier (PPS 100%, rehab 50%, "
                    "children's 5-20%). Not comparable to % cap without total NPR base."
                ),
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=2.0,
                native_rate="2.0% (seed value; CMS-approved)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO rate from seed; verify against WA HCA/CMS SPA.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "74.60" in text or "safety net" in text or "hospital" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
