"""
Ohio — Hospital Franchise Fee
Source: OAC Rule 5160-2-30
URL:    https://codes.ohio.gov/ohio-administrative-code/rule-5160-2-30
Structure: percentage
Verified by Phase 1 fetch.

Rate confirmed from page:
  Base rate: 3.37% of total facility costs (through CY2025)
  Base rate: 4.37% starting CY2026
  Supplemental rate: +3.641923% starting CY2026
  Combined CY2026+: ~8.01% (above 6% — CMS non-uniformity waiver in effect for supplemental)
  For cap-exposure analysis, use the base franchise fee: 4.37% (subject to cap).
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://codes.ohio.gov/ohio-administrative-code/rule-5160-2-30"

# Phase 1-confirmed rates. Parser tries to confirm; falls back to these.
_KNOWN_BASE_RATE_2026 = 4.37
_KNOWN_SUPPLEMENTAL = 3.641923
_KNOWN_NOTES = (
    "Base franchise fee 4.37% of total facility costs (CY2026+); supplemental "
    "fee 3.641923% (CY2026+) operates under CMS non-uniformity waiver. "
    "Cap-exposure uses base rate only (4.37%)."
)


class OhioScraper(StateScraperBase):
    state = "Ohio"
    abbr = "OH"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, confidence = self._parse_rate()

        rows = [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=rate,
                native_rate=f"{rate}% of total facility costs",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="total facility costs (Ohio franchise fee base)",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=_KNOWN_NOTES,
            ),
        ]
        return rows

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _KNOWN_BASE_RATE_2026, CONFIDENCE_LIKELY

        text = resp.text
        # Look for "4.37" in the page text to confirm the CY2026+ rate
        if "4.37" in text:
            return _KNOWN_BASE_RATE_2026, CONFIDENCE_VERIFIED
        # Fallback to older 3.37% if the page structure changed
        m = re.search(r"(\d\.\d+)\s*(?:percent|%)", text)
        if m:
            try:
                r = float(m.group(1))
                if 1.0 <= r <= 10.0:
                    return r, CONFIDENCE_LIKELY
            except ValueError:
                pass
        return _KNOWN_BASE_RATE_2026, CONFIDENCE_LIKELY
