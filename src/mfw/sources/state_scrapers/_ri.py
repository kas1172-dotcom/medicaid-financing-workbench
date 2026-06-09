"""
Rhode Island — Hospital Licensing Fee
Source: RI General Laws 23-17-38.1
URL:    https://webserver.rilegislature.gov/Statutes/TITLE23/23-17/23-17-38.1.htm
Structure: percentage (above 6% via CMS non-uniformity waiver)
Phase 1 confidence: likely

COMPLIANCE-RISK STATE: RI operates at 13.12% inpatient NPR under a CMS
non-uniformity waiver. This rate is above the 6% ceiling but is legally valid
because of the waiver. Under OBBBA's tightened uniformity requirements, this
waiver is at risk — RI faces a different compliance risk than standard exposure.

This state is flagged waiver_flag='non_uniformity_waiver' and should NOT be
ranked alongside standard 3.5%-cap-exposure states in the primary analysis.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://webserver.rilegislature.gov/Statutes/TITLE23/23-17/23-17-38.1.htm"
_TIER1_RATE = 13.12
_STATE_GOVT_RATE = 5.25


class RhodeIslandScraper(StateScraperBase):
    state = "Rhode Island"
    abbr = "RI"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=_TIER1_RATE,
                native_rate=f"{_TIER1_RATE}% inpatient NPR (Tier 1); {_STATE_GOVT_RATE}% state-govt hospital",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="inpatient net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                waiver_flag="non_uniformity_waiver",
                notes=(
                    "Rate 13.12% exceeds 6% ceiling under CMS non-uniformity waiver. "
                    "OBBBA tightens waiver rules — compliance risk distinct from standard "
                    "phase-down exposure. DO NOT rank alongside standard exposure states."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text
        if "23-17-38" in text or "13.12" in text or "licensing fee" in text.lower():
            from ._base import CONFIDENCE_VERIFIED
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
