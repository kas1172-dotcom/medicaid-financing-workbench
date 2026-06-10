"""
Vermont — Hospital Provider Tax (18 VSA §9410 area)
Source: VT Joint Fiscal Office Provider Tax Overview (Jan 2026)
URL:    https://legislature.vermont.gov/Documents/2026/Workgroups/House%20Health%20Care/Orientation/W~Nolan%20Langweil~Provider%20Tax%20Overview~1-7-2026.pdf
Structure: percentage (>5.5% NPR; hospital component is 93% of VT provider tax revenue)
Phase 1 confidence: likely — PDF binary-encoded; rate from JFO overview excerpt.

VT hospital provider tax >5.5% (VT among ~13 states above 5.5%). Hospital component is
93% of all VT provider tax revenue. OBBBA phases down from 6% to 3.5% by 2032.
Seed shows 0.0% — significant discrepancy.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://legislature.vermont.gov/Documents/2026/Workgroups/House%20Health%20Care/Orientation/W~Nolan%20Langweil~Provider%20Tax%20Overview~1-7-2026.pdf"
# JFO overview confirms >5.5%; use conservative lower-bound pending verification.
_FALLBACK_RATE = 5.75


class VermontScraper(StateScraperBase):
    state = "Vermont"
    abbr = "VT"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(_FALLBACK_RATE, 2),
                native_rate=f">5.5% NPR (JFO overview; exact rate pending verification)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes=(
                    "JFO Provider Tax Overview (Jan 2026) confirms hospital tax >5.5%; "
                    "hospital component = 93% of all VT provider tax revenue. "
                    "PDF binary-encoded on fetch. Seed (0.0%) is incorrect. "
                    f"Effective_rate_pct set to {_FALLBACK_RATE}% (conservative lower bound). "
                    "Seek current VT DVHA rate schedule for verified exact rate."
                ),
            ),
        ]
