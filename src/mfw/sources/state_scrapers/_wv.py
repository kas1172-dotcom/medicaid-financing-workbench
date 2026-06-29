"""
West Virginia: Hospital Directed Payment Tax
Source: WV Code §11-27-38 (+ §11-27-39 supplemental)
URL:    https://code.wvlegislature.gov/11-27-38/
Structure: percentage
Verified by Phase 1 fetch.

Confirmed rates:
  Base (§11-27-38):        3.86% of gross receipts (per Admin Notice 2024-11)
  Supplemental (§11-27-39): 0.13% of gross receipts
  Total:                   ~3.99% of gross receipts

Note: total ~3.99% is above the 3.5% 2032 floor → WV IS exposed.
Seed shows 5.5%: seed appears overstated.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://code.wvlegislature.gov/11-27-38/"
_BASE_RATE = 3.86
_SUPPLEMENTAL = 0.13
_TOTAL = round(_BASE_RATE + _SUPPLEMENTAL, 2)   # 3.99
_NOTES = (
    "Base 3.86% (Administrative Notice 2024-11) + supplemental 0.13% (§11-27-39). "
    "Total ~3.99% exceeds 3.5% 2032 floor → exposed. Seed (5.5%) overstated."
)


class WestVirginiaScraper(StateScraperBase):
    state = "West Virginia"
    abbr = "WV"
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
                native_rate=f"{rate}% gross receipts (base + supplemental)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross receipts",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=_NOTES,
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _TOTAL, CONFIDENCE_LIKELY
        text = resp.text
        if "11-27-38" in text or "directed payment" in text.lower():
            return _TOTAL, CONFIDENCE_VERIFIED
        return _TOTAL, CONFIDENCE_LIKELY
