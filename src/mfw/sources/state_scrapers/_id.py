"""
Idaho — Hospital Assessment Act
Source: IC §56-1404
URL:    https://legislature.idaho.gov/statutesrules/idstat/Title56/T56CH14/SECT56-1404/
Structure: amount_targeted (formula-based, not a simple % of revenue)
Verified by Phase 1 fetch — statute structure confirmed.

Rate is formula-based: the department sets a rate equal to the percentage that,
when applied to the assessment base, produces an amount equal to the upper payment
limit payment. An additional 30% is assessed for general fund Medicaid starting
July 1, 2023. Not a published % of NPR → not_comparable.
Seed shows 0.0% — confirms no simple rate published.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    STRUCTURE_AMOUNT_TARGETED, RateRow, StateScraperBase,
)

URL = "https://legislature.idaho.gov/statutesrules/idstat/Title56/T56CH14/SECT56-1404/"


class IdahoScraper(StateScraperBase):
    state = "Idaho"
    abbr = "ID"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_AMOUNT_TARGETED,
                effective_rate_pct=None,
                native_rate="formula: rate × base = UPL payment (+ 30% GF add-on from July 2023)",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "No published % of NPR. Rate set by DHHS to produce UPL amounts. "
                    "Seed (0.0%) reflects absence of a standard published rate."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text
        if "56-1404" in text or "hospital assessment" in text.lower():
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
