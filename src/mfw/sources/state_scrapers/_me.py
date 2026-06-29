"""
Maine: Health Care Provider Tax (MRS Title 36, Chapter 373)
Source: Maine Legislature
URL:    https://www.mainelegislature.org/legis/statutes/36/title36ch373.pdf
Structure: percentage (6% of net patient revenues; MRS Title 36 Ch. 373)
Phase 1 confidence: likely: PDF binary-encoded on fetch; rate confirmed from statute excerpts.

Hospital rate: 6% of net patient revenues (increased from 5.5% effective Oct 1, 2011).
Seed shows 0.0%: significant discrepancy; Phase 2 verification required.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://www.mainelegislature.org/legis/statutes/36/title36ch373.pdf"
_FALLBACK_RATE = 6.0


class MaineScraper(StateScraperBase):
    state = "Maine"
    abbr = "ME"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(_FALLBACK_RATE, 2),
                native_rate=f"{_FALLBACK_RATE:.2f}% net patient revenues (MRS Title 36, Ch. 373)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes=(
                    f"Rate {_FALLBACK_RATE}% confirmed from statute text excerpts. "
                    "PDF binary-encoded on direct fetch. "
                    "Increased from 5.5% effective Oct 1, 2011. "
                    "Seed (0.0%) is incorrect: ME does have a hospital provider tax."
                ),
            ),
        ]
