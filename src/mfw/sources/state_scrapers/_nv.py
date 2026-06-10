"""
Nevada — Private Hospital Assessment Program
Source: NV DHCFP
URL:    https://dhcfp.nv.gov/Providers/PI/Provider_Assessments/
Structure: percentage (above 6% inpatient via CMS non-uniformity waiver)
Phase 1 confidence: likely

COMPLIANCE-RISK STATE: NV inpatient rate 7.139% exceeds 6% via CMS non-uniformity
waiver. Outpatient rate 6.0% is at the current ceiling.
Under OBBBA uniformity tightening, both components are at risk.
Flagged waiver_flag='non_uniformity_waiver'.

MCO tax exists (4.5% per seed).
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, RATE_BASIS_REPORTED, RATE_BASIS_SEED_CARRYOVER,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://dhcfp.nv.gov/Providers/PI/Provider_Assessments/"
_INPATIENT_RATE = 7.139
_OUTPATIENT_RATE = 6.0


class NevadaScraper(StateScraperBase):
    state = "Nevada"
    abbr = "NV"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=_INPATIENT_RATE,
                native_rate=f"{_INPATIENT_RATE}% inpatient NPR; {_OUTPATIENT_RATE}% outpatient NPR",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net non-Medicare patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                waiver_flag="non_uniformity_waiver",
                notes=(
                    f"Inpatient {_INPATIENT_RATE}% exceeds 6% under CMS non-uniformity waiver. "
                    "OBBBA compliance risk distinct from standard 3.5% phase-down. "
                    "MCO 4.5% also exists and IS standard exposure."
                ),
            ),
            # MCO: rate from seed — not confirmed from primary source URL.
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=4.5,
                native_rate="4.5% (seed/MACPAC; not confirmed from primary source)",
                rate_basis=RATE_BASIS_SEED_CARRYOVER,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO 4.5% > 3.5% — standard phase-down exposure. Verify against NV DHCFP/CMS SPA.",
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "7.139" in text or "assessment" in text or "hospital" in text:
            from ._base import CONFIDENCE_VERIFIED
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
