"""
District of Columbia: Hospital Provider Fee
Source: D.C. Code §44-664.13
URL:    https://code.dccouncil.gov/us/dc/council/code/sections/44-664.13
Structure: capped (dollar-capped total, not a % of revenue)
Verified by Phase 1 fetch.

The fee generates no more than $8,454,038/year total from all hospitals.
This is a dollar-cap structure: not_comparable to the standard % of NPR cap.
DC total hospital NPR is large enough that this is a tiny fraction of revenue.
Seed value of 5.5% for DC is almost certainly wrong; DC exposure is negligible.

MCO tax exists (1.5% per seed) but hospital fee is not a meaningful % rate.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    RATE_BASIS_REPORTED, RATE_BASIS_SEED_CARRYOVER, STRUCTURE_CAPPED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://code.dccouncil.gov/us/dc/council/code/sections/44-664.13"


class DCScraperScraper(StateScraperBase):
    state = "District of Columbia"
    abbr = "DC"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_CAPPED,
                effective_rate_pct=None,
                native_rate="$8,454,038/year total (dollar-capped program)",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Dollar-capped program: effective rate is trivially small "
                    "relative to DC hospital NPR. Seed (5.5%) is incorrect. "
                    "DC cap exposure should be effectively zero."
                ),
            ),
            # MCO tax: rate from seed, not confirmed from primary source URL.
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=1.5,
                native_rate="1.5% (seed/MACPAC; not confirmed from primary source)",
                rate_basis=RATE_BASIS_SEED_CARRYOVER,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO rate from seed (1.5%): below 3.5% floor. Verify against DC DHCF/CMS SPA.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text
        if "44-664" in text or "8,454,038" in text or "hospital provider" in text.lower():
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
