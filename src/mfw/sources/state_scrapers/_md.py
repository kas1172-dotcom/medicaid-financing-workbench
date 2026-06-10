"""
Maryland — Hospital Quality Programs Assessment
Source: MDH OBBBA one-pager (July 2025)
URL:    https://health.maryland.gov/mmcp/Documents/OBBBA%20One-Pager_7.11.25.pdf
Structure: percentage (~5.5% NPR; seed value; primary source is PDF)
Phase 1 confidence: likely — PDF; specific hospital rate not confirmed from fetch.

MDH OBBBA one-pager confirms three provider taxes (hospital, NF, MCO); $1.17B at risk.
Specific hospital rate not extractable from PDF binary. Seed shows 5.5%.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://health.maryland.gov/mmcp/Documents/OBBBA%20One-Pager_7.11.25.pdf"
_FALLBACK_RATE = 5.5


class MarylandScraper(StateScraperBase):
    state = "Maryland"
    abbr = "MD"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(_FALLBACK_RATE, 2),
                native_rate=f"{_FALLBACK_RATE:.2f}% NPR (seed; MDH one-pager rate not directly extracted)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes=(
                    "MDH OBBBA one-pager (July 2025) confirms $1.17B at risk across "
                    "hospital + NF + MCO taxes. Hospital rate not extractable from PDF binary. "
                    "Seed (5.5%) used pending primary source extraction. "
                    "Seek current MDH hospital quality assessment documentation."
                ),
            ),
        ]
