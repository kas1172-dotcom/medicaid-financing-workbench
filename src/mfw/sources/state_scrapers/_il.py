"""
Illinois: Hospital Assessment Program (HAP)
Source: ILCS Art. V-A (305 ILCS 5)
URL:    https://www.ilga.gov/legislation/ilcs/ilcs4.asp?DocName=030500050HArt.+V-A&ActID=1413&ChapterID=0&SeqStart=35500000&SeqEnd=38200000
Structure: percentage (~5.9% NPR; set administratively by HFS)
Phase 1 confidence: likely: statute confirms program; rate set by HFS notice, not statute.

HB2771 (2025) amends HAP. Specific rate not in statute text; set by HFS annual notice.
Rate near 5.9% of net revenue per HFS annual notice. Seed shows 5.9%.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.ilga.gov/legislation/ilcs/ilcs4.asp?DocName=030500050HArt.+V-A&ActID=1413&ChapterID=0&SeqStart=35500000&SeqEnd=38200000"
_FALLBACK_RATE = 5.9


class IllinoisScraper(StateScraperBase):
    state = "Illinois"
    abbr = "IL"
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
                native_rate=f"{rate:.2f}% net revenue (HAP, 305 ILCS 5/Art. V-A)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"Rate ~{_FALLBACK_RATE}% set by HFS annual notice; not in statute text. "
                    "HB2771 (2025) amends HAP. "
                    "Seek current HFS notice (HFS.ProviderAssessmentUnit@illinois.gov) "
                    "for verified rate."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "305 ilcs 5" in text.lower() or "hospital assessment" in text.lower()
        match = re.search(r"(\d+\.\d+)\s*(?:percent|%)[^.]{0,80}?(?:patient|revenue|net)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 3.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
