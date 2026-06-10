"""
Louisiana — Hospital Assessment (tiered NPR rates)
Source: LA Legislative Fiscal Note on HCR 363
URL:    https://www.legis.la.gov/Legis/ViewDocument.aspx?d=1417157
Structure: percentage (tiered; acute care above 6% via CMS preprint)
Phase 1 confidence: likely

FY2025/26 hospital assessment rates:
  Acute care hospitals:             6.49% inpatient + 6.74% outpatient NPR (cap: $125M)
  Rehabilitation/psych/LTACH:       1.38%
  Certain hospital service districts: 4.99%

CMS preprint submitted May 16, 2025. The acute care rate (6.49%/6.74%) exceeds the
current 6% ceiling — the state appears to be operating under a CMS non-uniformity waiver
or a pending preprint approval. We flag this and report the acute care rate with a note.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.legis.la.gov/Legis/ViewDocument.aspx?d=1417157"
_INPATIENT_RATE = 6.49
_OUTPATIENT_RATE = 6.74


class LouisianaScraper(StateScraperBase):
    state = "Louisiana"
    abbr = "LA"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        confidence = self._check_page()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(_INPATIENT_RATE, 2),
                native_rate=(
                    f"{_INPATIENT_RATE:.2f}% inpatient NPR + {_OUTPATIENT_RATE:.2f}% "
                    "outpatient NPR (acute care; cap $125M)"
                ),
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue (inpatient; primary component)",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"Acute care rates ({_INPATIENT_RATE:.2f}% inpatient, "
                    f"{_OUTPATIENT_RATE:.2f}% outpatient) exceed 6% ceiling. "
                    "CMS preprint submitted May 16, 2025. "
                    "Operating under CMS preprint or pending uniformity waiver approval. "
                    "Rehabilitation/psych/LTACH: 1.38%; hospital service districts: 4.99%. "
                    "Effective_rate_pct uses inpatient component as primary exposure measure."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        if "6.49" in resp.text or "6.74" in resp.text or "hospital" in resp.text.lower():
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
