"""
Wisconsin — Hospital Assessment (Wis. Stat. §50.38)
Source: Wisconsin Legislature statutes
URL:    https://docs.legis.wisconsin.gov/statutes/statutes/50/ii/38/7/c
Structure: percentage (6% of net patient revenues; 2025 Act 15)
Phase 1 confidence: likely — statute URL accessible; rate from 2025 Act 15.

Rate increased to 6% in 2025-27 budget (2025 Act 15, signed July 3, 2025 — just
before OBBBA freeze). Previously 1.8%; now generates ~$1.087B additional revenue/year.
Non-expansion state: zero phase-down exposure regardless of rate.
Seed shows 1.0% — significantly outdated.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://docs.legis.wisconsin.gov/statutes/statutes/50/ii/38/7/c"
_FALLBACK_RATE = 6.0


class WisconsinScraper(StateScraperBase):
    state = "Wisconsin"
    abbr = "WI"
    expansion = False   # non-expansion

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, confidence = self._parse_rate()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(rate, 2),
                native_rate=f"{rate:.2f}% net patient revenues (Wis. Stat. §50.38; 2025 Act 15)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"Rate increased from 1.8% to {_FALLBACK_RATE}% in 2025-27 budget "
                    "(2025 Act 15, signed July 3, 2025). Non-expansion state — "
                    "zero phase-down exposure. Generates ~$1.087B additional revenue/year. "
                    "Seed (1.0%) significantly outdated."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "50.38" in text or "hospital assessment" in text.lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,60}?(?:patient|revenue|net|assessment)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 4.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        if page_confirmed:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
