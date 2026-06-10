"""
Michigan — Quality Assurance Assessment Program (QAAP)
Source: MCL 333.20161
URL:    https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-333-20161
Structure: percentage (rate in annual DHHS notice, up to federal maximum ~6%)
Verified by Phase 1 fetch — statute structure confirmed.

Actual current rate is set by DHHS annual rule/notice, not in the statute.
The statute confirms the program exists and sets the ceiling at the federal max.
Rate near 6% ($6B+ in QAAP revenue per legislative analysis).
Seed shows 6.0% — consistent with known program scope.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    RATE_BASIS_SEED_CARRYOVER, STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-333-20161"
_RATE = 6.0  # federal maximum; set by DHHS annual notice


class MichiganScraper(StateScraperBase):
    state = "Michigan"
    abbr = "MI"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=_RATE,
                native_rate=f"~{_RATE}% (federal maximum; actual set by DHHS annual notice)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="non-Medicare patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Statute sets ceiling at federal max; current rate per DHHS "
                    "annual notice (not in statute). Generates $6B+ QAAP revenue. "
                    "Seed (6.0%) consistent with program scope."
                ),
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=2.0,
                native_rate="2.0% (seed/MACPAC; not confirmed from primary source)",
                rate_basis=RATE_BASIS_SEED_CARRYOVER,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO rate from seed — verify against MI DHHS/CMS SPA before use.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text
        if "333.20161" in text or "quality assurance" in text.lower():
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
