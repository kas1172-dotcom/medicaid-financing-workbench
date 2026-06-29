"""
Indiana: Hospital Assessment Fee (HAF)
Source: HB1004 (2025); IC 6-8 + IC 16-21
URL:    https://iga.in.gov/pdf-documents/124/2025/house/bills/HB1004/HB1004.02.COMH.pdf
Structure: percentage (~6% non-Medicare revenue; CMS-approved April 28, 2025)
Phase 1 confidence: likely: PDF binary-encoded on fetch; rate from bill analysis.

HB1004 (2025) redesigns HAF to capture full federal maximum (~6%) effective July 1, 2025.
CMS approved revised HAF on April 28, 2025 (retroactive). Also adds new MCO assessment.
Rate near 6% of non-Medicare revenue.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://iga.in.gov/pdf-documents/124/2025/house/bills/HB1004/HB1004.02.COMH.pdf"
_FALLBACK_RATE = 6.0


class IndianaScraper(StateScraperBase):
    state = "Indiana"
    abbr = "IN"
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
                native_rate=f"{rate:.2f}% non-Medicare revenue (HAF, HB1004 2025)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="non-Medicare patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"HB1004 (2025) redesigns HAF to {_FALLBACK_RATE}% federal maximum. "
                    "CMS approved April 28, 2025 (retroactive to July 1, 2025). "
                    "Source PDF binary-encoded on direct fetch; rate from bill analysis."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        # PDF content: check for text markers
        content = resp.content
        if b"HB1004" in content or b"hospital assessment" in content.lower():
            return _FALLBACK_RATE, CONFIDENCE_LIKELY   # confirmed program, rate from bill analysis
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
