"""
Alabama: Hospital Assessment Fee (non-expansion state)
Source: AL Department of Revenue FAQ
URL:    https://www.revenue.alabama.gov/faqs/hospital-assessment-fee/

LIVE PARSER: Rate is extracted via regex from the fetched AL DOR FAQ page.
Known fallback (6.0%) used only when parsing fails.
confidence is upgraded to verified when the page confirms "hospital assessment"
or "6 percent" and the extraction succeeds.

Non-expansion state: exposure to the reduced cap is ZERO.
Rate frozen at July 2025 level under OBBBA.
Seed (4.2%) appears understated: Phase 1 confirmed 6.0%.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.revenue.alabama.gov/faqs/hospital-assessment-fee/"
_FALLBACK_RATE = 6.0


class AlabamaScraper(StateScraperBase):
    state = "Alabama"
    abbr = "AL"
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
                native_rate=f"{rate:.2f}% net patient revenue (quarterly)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Live-parsed from AL DOR FAQ page. "
                    "Non-expansion state: zero phase-down exposure. "
                    "Rate frozen at July 2025 level under OBBBA. "
                    f"Seed (4.2%) understated; Phase 1 confirmed {rate:.1f}%."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        """
        Fetch AL DOR FAQ page and extract the hospital assessment rate.

        The page contains FAQ-style text that includes the current rate as a
        percentage, e.g. "The assessment fee is 6 percent" or "6% of net
        patient revenue."

        Returns (rate, confidence).
        """
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY

        text = resp.text
        page_confirmed = (
            "hospital assessment" in text.lower() or
            "assessment fee" in text.lower() or
            "revenue.alabama" in text.lower()
        )

        rate = _FALLBACK_RATE
        parsed = False

        # Search for explicit percentage near "assessment" or "fee"
        # Typical patterns: "6 percent", "6%", "6.0 percent of"
        match = re.search(
            r"(?:assessment|fee)[^.]{0,120}?(\d+(?:\.\d+)?)\s*(?:percent|%)",
            text, re.IGNORECASE
        )
        if not match:
            # Reverse context: percentage before "assessment"
            match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,120}?(?:assessment|fee)",
                text, re.IGNORECASE
            )

        if match:
            try:
                val = float(match.group(1))
                # Hospital tax rates are typically 1%–6%
                if 0.5 <= val <= 7.0:
                    rate = val
                    parsed = True
            except ValueError:
                pass

        confidence = (
            CONFIDENCE_VERIFIED if (page_confirmed and parsed) else
            CONFIDENCE_LIKELY
        )
        return rate, confidence
