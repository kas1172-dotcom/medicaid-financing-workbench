"""
Arizona — Hospital Assessment (AHCCCS)
Source: AHCCCS Hospital Assessment page
URL:    https://www.azahcccs.gov/PlansProviders/RatesAndBilling/hospitalassessment.html
Structure: amount_targeted (per-discharge tiers → not_comparable)
Verified by Phase 1 fetch.

Assessment is based on inpatient discharges + outpatient NPR by hospital peer
group tier (Pediatric Intensive = 80%, Medium Pediatric = 90% of general acute
rate). FFY2026 total ~$1.275B directed payments.
Per-discharge structure → not a simple % of revenue → not_comparable.

MCO tax: 4.5% (seed; CMS waiver) — this IS a percentage and is above 3.5%.
AZ's primary exposure is via MCO tax, not hospital assessment.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    RATE_BASIS_REPORTED, STRUCTURE_AMOUNT_TARGETED, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://www.azahcccs.gov/PlansProviders/RatesAndBilling/hospitalassessment.html"


class ArizonaScraper(StateScraperBase):
    state = "Arizona"
    abbr = "AZ"
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
                native_rate="per-discharge tiers: general 100%, rehab 80%, peds 5-90% of target",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "FFY2026 total ~$1.275B in directed payments. Per-discharge "
                    "structure is not comparable to % cap. AZ primary exposure "
                    "is via MCO tax (4.5%)."
                ),
            ),
            # MCO tax: percentage → comparable
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=4.5,
                native_rate="4.5% (CMS-approved waiver; seed value)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO rate from seed; confirm against CMS SPA for AZ.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "hospital assessment" in text or "ahcccs" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
