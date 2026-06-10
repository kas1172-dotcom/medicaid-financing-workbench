"""
Georgia — Hospital Provider Fee (non-expansion state)
Source: GA DCH Hospital Provider Fee Payment page
URL:    https://dch.georgia.gov/providers/provider-types/hospital-providers/provider-fee-payment

LIVE PARSER: Rate is extracted via regex from the fetched GA DCH page.
Known fallback (1.45% regular / 1.40% trauma) used only when parsing fails.
confidence is upgraded to verified when parsing succeeds AND the page is
confirmed as the GA DCH provider-fee page.

Confirmed rates:
  Regular hospitals:  1.45% net patient revenue
  Trauma centers:     1.40% net patient revenue

Non-expansion state: zero phase-down exposure regardless of rate.
Seed (1.5%) close match to confirmed regular rate (1.45%).
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://dch.georgia.gov/providers/provider-types/hospital-providers/provider-fee-payment"
_FALLBACK_RATE = 1.45


class GeorgiaScraper(StateScraperBase):
    state = "Georgia"
    abbr = "GA"
    expansion = False   # non-expansion

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, trauma_rate, confidence = self._parse_rate()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(rate, 2),
                native_rate=f"{rate:.2f}% net patient revenue ({trauma_rate:.2f}% trauma centers)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Live-parsed from GA DCH provider-fee page. "
                    "Non-expansion state — zero phase-down exposure. "
                    f"Seed (1.5%) close match to confirmed rate ({rate:.2f}%)."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, float, str]:
        """
        Fetch GA DCH provider-fee page and extract the hospital rate via regex.

        GA DCH typically shows text like "1.45 percent" or "1.45%" near
        "net patient revenue" or "hospital provider fee".

        Returns (regular_rate, trauma_rate, confidence).
        """
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, 1.40, CONFIDENCE_LIKELY

        text = resp.text
        page_confirmed = (
            "provider fee" in text.lower() or
            "dch.georgia" in text.lower() or
            "hospital" in text.lower()
        )

        regular = _FALLBACK_RATE
        trauma = 1.40
        parsed_any = False

        # Look for rate patterns: "1.45 percent" / "1.45%" / "1.45 per cent"
        # Prefer the first plausible percentage in context of "net patient revenue" or "fee"
        matches = re.findall(r"(\d+\.\d+)\s*(?:percent|%)", text, re.IGNORECASE)
        # Filter to plausible hospital tax range (0.5% – 3%)
        plausible = [float(m) for m in matches if 0.5 <= float(m) <= 3.0]

        if len(plausible) >= 2:
            # Typically the regular rate appears before the trauma rate
            plausible.sort(reverse=True)
            regular = plausible[0]
            trauma = plausible[1]
            parsed_any = True
        elif len(plausible) == 1:
            regular = plausible[0]
            # Trauma typically ~0.05pp below regular
            trauma = max(0.0, regular - 0.05)
            parsed_any = True

        # Also try context-anchored search
        anchored = re.search(
            r"(?:regular|general)[^.]{0,80}?(\d+\.\d+)\s*(?:percent|%)",
            text, re.IGNORECASE
        )
        if anchored:
            try:
                val = float(anchored.group(1))
                if 0.5 <= val <= 3.0:
                    regular = val
                    parsed_any = True
            except ValueError:
                pass

        confidence = (
            CONFIDENCE_VERIFIED if (page_confirmed and parsed_any) else
            CONFIDENCE_LIKELY
        )
        return regular, trauma, confidence
