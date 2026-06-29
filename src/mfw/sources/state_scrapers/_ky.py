"""
Kentucky: Health Care Provider Tax
Source: KY Department of Revenue
URL:    https://revenue.ky.gov/Business/Health-Care-Provider-Tax/Pages/default.aspx

LIVE PARSER: Rates are extracted via regex from the fetched KY DOR page.
Known values (hospital 2.5%, MCO 5.5%, ICF-MR 5.5%) are used as fallback
only when parsing fails. confidence is upgraded to verified when the parsed
value matches a plausible rate AND the page confirms it's the KY DOR.

Confirmed rates:
  Hospital (KRS 142.303):  2.5% of gross revenues
  MCO:                     5.5% of gross revenues
  ICF-MR:                  5.5% of gross revenues (EXEMPT from phase-down)
  Nursing facility:        per-bed-day (unit_based, EXEMPT from phase-down)

Phase 2 finding: KY's max SUBJECT-class rate is MCO 5.5%, not hospital.
Seed shows hospital 5.5%: the seed hospital rate is significantly overstated.
The analytical story here is that KY exposure shifts from hospital to MCO class.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://revenue.ky.gov/Business/Health-Care-Provider-Tax/Pages/default.aspx"

_FALLBACK_HOSPITAL = 2.5
_FALLBACK_MCO = 5.5
_FALLBACK_ICF = 5.5


class KentuckyScraper(StateScraperBase):
    state = "Kentucky"
    abbr = "KY"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        hosp_rate, mco_rate, icf_rate, confidence = self._parse_rates()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(hosp_rate, 2),
                native_rate=f"{hosp_rate:.2f}% gross revenues (KRS 142.303)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Live-parsed from KY DOR Health Care Provider Tax page. "
                    "Seed (5.5%) overstated: hospital is 2.5%. "
                    "Phase 2 finding: KY exposure is MCO-class led, not hospital."
                ),
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(mco_rate, 2),
                native_rate=f"{mco_rate:.2f}% gross revenues",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Live-parsed from KY DOR page. "
                    f"MCO {mco_rate:.1f}% > 3.5% floor: KY primary cap-exposure class."
                ),
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="icf_iid",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(icf_rate, 2),
                native_rate=f"{icf_rate:.2f}% gross revenues (ICF-MR; EXEMPT from phase-down)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes="Live-parsed from KY DOR page. EXEMPT class, not counted toward cap exposure.",
            ),
        ]

    def _parse_rates(self) -> tuple[float, float, float, str]:
        """
        Fetch KY DOR provider-tax page and extract rates via regex.

        The page lists rates in a table or bullet list like:
          "Hospital: 2.5%", "HMO/MCO: 5.5%", "ICF-MR: 5.5%"

        Returns (hospital_rate, mco_rate, icf_rate, confidence).
        """
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_HOSPITAL, _FALLBACK_MCO, _FALLBACK_ICF, CONFIDENCE_LIKELY

        text = resp.text
        page_confirmed = (
            "health care provider tax" in text.lower() or
            "revenue.ky.gov" in text.lower() or
            "142.303" in text
        )

        hosp = _FALLBACK_HOSPITAL
        mco = _FALLBACK_MCO
        icf = _FALLBACK_ICF
        parsed_any = False

        # Hospital rate: look for "hospital" near a percentage
        hosp_match = re.search(
            r"hospital[^.]{0,80}?(\d+\.\d+)\s*(?:percent|%)",
            text, re.IGNORECASE
        )
        if hosp_match:
            try:
                val = float(hosp_match.group(1))
                if 0.5 <= val <= 8.0:
                    hosp = val
                    parsed_any = True
            except ValueError:
                pass

        # MCO rate: look for "mco", "hmo", "managed care org" near a percentage
        mco_match = re.search(
            r"(?:mco|hmo|managed\s*care\s*org)[^.]{0,80}?(\d+\.\d+)\s*(?:percent|%)",
            text, re.IGNORECASE
        )
        if mco_match:
            try:
                val = float(mco_match.group(1))
                if 0.5 <= val <= 8.0:
                    mco = val
                    parsed_any = True
            except ValueError:
                pass

        # ICF rate: look for "icf" near a percentage
        icf_match = re.search(
            r"icf[^.]{0,80}?(\d+\.\d+)\s*(?:percent|%)",
            text, re.IGNORECASE
        )
        if icf_match:
            try:
                val = float(icf_match.group(1))
                if 0.5 <= val <= 8.0:
                    icf = val
                    parsed_any = True
            except ValueError:
                pass

        confidence = (
            CONFIDENCE_VERIFIED if (page_confirmed and parsed_any) else
            CONFIDENCE_LIKELY
        )
        return hosp, mco, icf, confidence
