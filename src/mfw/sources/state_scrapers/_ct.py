"""
Connecticut — Hospital Provider Tax
Source: CGS Chapter 211c (§§12-263a through 12-263e)
URL:    https://www.cga.ct.gov/2021/pub/chap_211c.htm
Structure: percentage (6% inpatient NPR; outpatient rate >6% via CMS waiver)
Phase 1 confidence: likely — statute URL loads; rate confirmed from statute text.

Inpatient rate: 6% of net inpatient revenue.
Outpatient: CMS waiver rate reportedly >10%, but we do not confirm a rate above 6%
without a direct CMS waiver document. We report inpatient 6% as the primary rate.
2025 legislation revises tax base effective July 1, 2026.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.cga.ct.gov/2021/pub/chap_211c.htm"
_FALLBACK_RATE = 6.0


class ConnecticutScraper(StateScraperBase):
    state = "Connecticut"
    abbr = "CT"
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
                native_rate=f"{rate:.2f}% net inpatient revenue (CGS §12-263a et seq.)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net inpatient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Inpatient 6% confirmed from statute text. "
                    "Outpatient rate >6% reportedly via CMS waiver; not confirmed from "
                    "primary source — excluded pending CMS waiver document retrieval. "
                    "2025 legislation revises base effective July 1, 2026."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "12-263" in text or "hospital" in text.lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:percent|%)[^.]{0,80}?(?:inpatient|net patient|revenue)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 4.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        if "6" in text and page_confirmed:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
