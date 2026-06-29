"""
New Mexico: Health Care Delivery and Access Assessment (HDAA)
Source: NM Taxation & Revenue HDAA page
URL:    https://www.tax.newmexico.gov/businesses/health-care-delivery-and-access-assessment/
Structure: amount_targeted (rate set annually by HCA; tiered rural reductions)
Phase 1 confidence: likely

Rate set annually by Health Care Authority prior to Nov 1; current CY2025 rate not
shown on public page. Tiered reductions: rural/frontier 50%, small urban 90%.
Statute: NMSA 7-9B (SB17, 2024 session). Rate not comparable without annual HCA notice.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    STRUCTURE_AMOUNT_TARGETED, RateRow, StateScraperBase,
)

URL = "https://www.tax.newmexico.gov/businesses/health-care-delivery-and-access-assessment/"


class NewMexicoScraper(StateScraperBase):
    state = "New Mexico"
    abbr = "NM"
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
                native_rate="annual rate set by HCA prior to Nov 1; tiered rural reductions (50%/90%)",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Rate not available on public page. Statute: NMSA 7-9B (SB17, 2024). "
                    "Rate set annually by HCA; rural/frontier hospitals assessed at 50% of standard, "
                    "small urban at 90%. Current rate not_comparable without annual HCA notice."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "health care delivery" in text or "7-9b" in text or "assessment" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
