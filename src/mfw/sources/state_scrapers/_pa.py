"""
Pennsylvania: Hospital Assessment Program
Source: PA Code and Bulletin (annual rate-setting bulletin)
URL:    https://www.pacodeandbulletin.gov/Display/pabull?file=/secure/pabulletin/data/vol51/51-27/1057.html
Structure: percentage (split inpatient + outpatient)
Verified by Phase 1 fetch.

Confirmed rates (FY2022–2023):
  Inpatient:  3.32% of net inpatient revenue
  Outpatient: 1.73% of net outpatient revenue

For cap-exposure, inpatient rate (3.32%) is below 3.5% and not exposed.
Outpatient rate (1.73%) is also below 3.5%.
Important: these rates are below the 3.5% floor: PA may have LESS exposure
than seed data (5.9%) suggests. Phase 2 should seek the current-year bulletin.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://www.pacodeandbulletin.gov/Display/pabull?file=/secure/pabulletin/data/vol51/51-27/1057.html"

_INPATIENT_RATE = 3.32
_OUTPATIENT_RATE = 1.73

# ⚠ STALENESS WARNING: these rates are from the PA Bulletin FY2022–23 edition.
# PA sets hospital assessment rates annually via a published bulletin in the
# PA Code and Bulletin. The FY2022-23 rates (3.32% inpatient, 1.73% outpatient)
# were the most recently confirmed values during Phase 1 research.
# Current-year (FY2025-26) bulletin must be located at:
#   https://www.pacodeandbulletin.gov/
# and ingested before these rates are used for publication-grade analysis.
_STALENESS_NOTE = (
    "⚠ STALE: Source is PA Bulletin FY2022-23 (Vol. 51, No. 27). "
    "PA resets rates annually; current-year bulletin required before use. "
    "Both 2022-23 rates (3.32% inpatient, 1.73% outpatient) are below the "
    "3.5% phase-down floor: PA may not be exposed, but this must be confirmed "
    "with the current bulletin. Seed (5.9%) is likely overstated."
)
_NOTES = _STALENESS_NOTE


class PennsylvaniaScraper(StateScraperBase):
    state = "Pennsylvania"
    abbr = "PA"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        inp_rate, out_rate, confidence = self._parse_rates()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=max(inp_rate, out_rate),
                native_rate=f"{inp_rate}% inpatient NPR + {out_rate}% outpatient NPR",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net inpatient + net outpatient revenue (split rates)",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=_NOTES,
            ),
        ]

    def _parse_rates(self) -> tuple[float, float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _INPATIENT_RATE, _OUTPATIENT_RATE, CONFIDENCE_LIKELY
        text = resp.text
        # Even when the page confirms these rates, they are FY2022-23 values.
        # We return CONFIDENCE_LIKELY (not verified) because the source is known-stale.
        # Upgrade to verified only after the current-year bulletin is ingested.
        if "3.32" in text and "1.73" in text:
            return _INPATIENT_RATE, _OUTPATIENT_RATE, CONFIDENCE_LIKELY
        return _INPATIENT_RATE, _OUTPATIENT_RATE, CONFIDENCE_LIKELY
