"""
Oklahoma: Supplemental Hospital Offset Payment Program (SHOPP)
Source: Oklahoma Health Care Authority supplemental payments page
URL:    https://www.ohca.com/providers/financial-data/supplemental-payments/
Structure: percentage (4% of net revenue; SB1045, Title 63 §5020A)
Phase 1 confidence: likely: page not confirmed via fetch; rate from OHCA budget review.

SHOPP rate: 4% of net revenue per SB1045. Expansion state; 4% > 3.5% floor → exposed.
Seed shows 0.0% for hospital: significant discrepancy.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.ohca.com/providers/financial-data/supplemental-payments/"
_FALLBACK_RATE = 4.0


class OklahomaScraper(StateScraperBase):
    state = "Oklahoma"
    abbr = "OK"
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
                native_rate=f"{rate:.2f}% net revenue (SHOPP, SB1045/Title 63 §5020A)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"SHOPP {_FALLBACK_RATE}% > 3.5% floor: OK is exposed. "
                    "Seed (0.0%) significantly understated. "
                    "Rate from OHCA budget review documents; page not confirmed via fetch."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "supplemental" in text.lower() or "ohca" in text.lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,60}?(?:net|revenue|hospital)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 2.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
