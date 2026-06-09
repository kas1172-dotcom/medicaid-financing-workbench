"""
Minnesota — Hospital Assessment (two-tier system)
Source: MN Statute 256.9657 + MinnesotaCare Tax (MN Stat. 295.52)
URL:    https://www.revisor.mn.gov/statutes/cite/256.9657
Structure: percentage (outpatient) + unit_based (inpatient)
Verified by Phase 1 fetch.

Confirmed rates (MN Stat. 256.9657):
  Outpatient: 5.96% of net outpatient revenue
  Inpatient:  $120.22 per patient day (unit_based)
  MinnesotaCare (MN Stat. 295.52): 1.8% gross revenues (separate tax)

For cap-exposure: outpatient 5.96% is a percentage above 3.5% → exposed.
Inpatient is unit_based → not_comparable for percentage cap.
We report outpatient as the effective subject rate (conservative: uses the
percentage component only; actual exposure may be higher if inpatient converts).
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, STRUCTURE_UNIT_BASED, RateRow, StateScraperBase,
)

URL = "https://www.revisor.mn.gov/statutes/cite/256.9657"
URL_CARE = "https://www.revisor.mn.gov/statutes/cite/295.52"

_OUTPATIENT_RATE = 5.96
_INPATIENT_PER_DAY = 120.22
_CARE_RATE = 1.8


class MinnesotaScraper(StateScraperBase):
    state = "Minnesota"
    abbr = "MN"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            # Outpatient: percentage component → contributes to cap exposure
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=_OUTPATIENT_RATE,
                native_rate=f"{_OUTPATIENT_RATE}% net outpatient revenue + ${_INPATIENT_PER_DAY}/patient-day inpatient",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used=(
                    "net outpatient revenue (% component); per-patient-day "
                    "inpatient component separately classified as unit_based"
                ),
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Two-tier: outpatient 5.96% (percentage, above 3.5% → exposed); "
                    f"inpatient ${_INPATIENT_PER_DAY}/day (unit_based, not_comparable "
                    "for % cap). Effective_rate_pct reflects outpatient component only."
                ),
            ),
            # MinnesotaCare: separate gross-receipts tax (not a Medicaid assessment)
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="other",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=_CARE_RATE,
                native_rate=f"{_CARE_RATE}% gross revenues (MinnesotaCare Tax, MN Stat. 295.52)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL_CARE,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MinnesotaCare Tax is a separate gross receipts tax, not a Medicaid provider assessment.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text
        if "5.96" in text or "256.9657" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
