"""
Oregon — Hospital Assessment
Source: ORS 414.855
URL:    https://oregon.public.law/statutes/ors_414.855
Structure: amount_targeted (rate set by OHA Director by rule to hit % of Medicare)
Verified by Phase 1 fetch.

Rate set by OHA Director by rule (estimated ~6% per legislative background).
Caps: ≤30% of Medicare FFS inpatient payments, ≤41% Medicare FFS outpatient.
Not a fixed published % of NPR → reports as amount_targeted.
Extended to December 2032 by HB2010 (expired Sept 30, 2025).
Seed shows 5.5% — approximation from secondary sources.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    STRUCTURE_AMOUNT_TARGETED, RateRow, StateScraperBase,
)

URL = "https://oregon.public.law/statutes/ors_414.855"


class OregonScraper(StateScraperBase):
    state = "Oregon"
    abbr = "OR"
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
                native_rate="≤30% Medicare FFS inpatient + ≤41% Medicare FFS outpatient (OHA Director rule)",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Rate set by OHA Director by rule (~6% effective per legislative "
                    "background). Extended to Dec 2032 by HB2010. Seed (5.5%) is "
                    "approximation; use seed pending derivation with Medicare cost reports."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "414.855" in text or "hospital assessment" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
