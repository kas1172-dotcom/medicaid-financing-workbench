"""
New Hampshire: Medicaid Enhancement Tax (MET)
Source: NH DRA FAQ page
URL:    https://www.revenue.nh.gov/faq/medicaid-enhancement.htm
Structure: percentage (5.4% NPSV; RSA 84-A)
Phase 1 confidence: likely: URL returned 403; rate confirmed from NH Fiscal Policy Institute.

NH MET: 5.4% of net patient service revenue on all 26 acute care hospitals.
Generated ~$348M SFY2025. Will phase down to 3.5% by October 2031 under OBBBA.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.revenue.nh.gov/faq/medicaid-enhancement.htm"
_FALLBACK_RATE = 5.4


class NewHampshireScraper(StateScraperBase):
    state = "New Hampshire"
    abbr = "NH"
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
                native_rate=f"{rate:.2f}% net patient service revenue (MET, RSA 84-A)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient service revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"Rate {_FALLBACK_RATE}% confirmed from NH Fiscal Policy Institute; "
                    "DRA FAQ page returned 403 on fetch. "
                    "26 acute care hospitals; ~$348M SFY2025. "
                    "Phases to 3.5% by Oct 2031."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None or (hasattr(resp, "status_code") and resp.status_code == 403):
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "medicaid enhancement" in text.lower() or "84-a" in text.lower()
        match = re.search(r"(\d+\.\d+)\s*(?:percent|%)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 3.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
