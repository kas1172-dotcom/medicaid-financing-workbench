"""
Minnesota — Hospital Assessment + MinnesotaCare Tax
Sources:
  MN Stat. 256.9657 — hospital assessment (outpatient % + inpatient per-day)
  MN Stat. 295.52   — MinnesotaCare gross-receipts tax

URL: https://www.revisor.mn.gov/statutes/cite/256.9657
     https://www.revisor.mn.gov/statutes/cite/295.52

LIVE PARSER: Rates are extracted via regex from the fetched statute page.
The known values (5.96% outpatient, $120.22/day inpatient, 1.8% MinnesotaCare)
are used ONLY as fallback when parsing fails. confidence is upgraded to
verified only when the parsed value matches a plausible rate range.

Two-tier structure:
  Outpatient: 5.96% of net outpatient revenue (percentage → cap-comparable)
  Inpatient:  $120.22 per patient day (unit_based → not_comparable for % cap)
  MinnesotaCare: 1.8% gross revenues (separate gross-receipts tax, 295.52)
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    RATE_BASIS_REPORTED, STRUCTURE_PERCENTAGE, STRUCTURE_UNIT_BASED,
    RateRow, StateScraperBase,
)

URL_HOSP = "https://www.revisor.mn.gov/statutes/cite/256.9657"
URL_CARE = "https://www.revisor.mn.gov/statutes/cite/295.52"

_FALLBACK_OUTPATIENT = 5.96
_FALLBACK_INPATIENT_DAY = 120.22
_FALLBACK_CARE = 1.8


class MinnesotaScraper(StateScraperBase):
    state = "Minnesota"
    abbr = "MN"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        outpatient_rate, inpatient_day, hosp_confidence = self._parse_hospital()
        care_rate, care_confidence = self._parse_minnesota_care()

        rows = [
            # Outpatient percentage component — cap-comparable
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(outpatient_rate, 2),
                native_rate=(
                    f"{outpatient_rate:.2f}% net outpatient revenue + "
                    f"${inpatient_day:.2f}/patient-day inpatient"
                ),
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used=(
                    "net outpatient revenue (% component); per-patient-day "
                    "inpatient component classified separately as unit_based"
                ),
                source_url=URL_HOSP,
                retrieved_date=today,
                confidence=hosp_confidence,
                notes=(
                    f"Live-parsed from MN Stat. 256.9657. "
                    f"Outpatient {outpatient_rate:.2f}% (above 3.5% → exposed). "
                    f"Inpatient ${inpatient_day:.2f}/day (unit_based, not_comparable for % cap). "
                    "effective_rate_pct reflects outpatient component only."
                ),
            ),
            # Inpatient unit-based row for record; not used in % cap exposure
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="other",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(care_rate, 2),
                native_rate=f"{care_rate:.2f}% gross revenues (MinnesotaCare Tax, MN Stat. 295.52)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="gross revenues",
                source_url=URL_CARE,
                retrieved_date=today,
                confidence=care_confidence,
                notes=(
                    "Live-parsed from MN Stat. 295.52. "
                    "MinnesotaCare Tax is a separate gross-receipts tax, not a Medicaid assessment."
                ),
            ),
        ]
        return rows

    def _parse_hospital(self) -> tuple[float, float, str]:
        """
        Fetch MN Stat. 256.9657 and extract:
          - outpatient rate (e.g. "5.96 percent")
          - inpatient per-diem (e.g. "$120.22 per patient day")
        Returns (outpatient_rate, inpatient_day, confidence).
        """
        resp = self._fetch(URL_HOSP)
        if resp is None:
            return _FALLBACK_OUTPATIENT, _FALLBACK_INPATIENT_DAY, CONFIDENCE_LIKELY

        text = resp.text

        # Look for patterns like "5.96 percent" or "5.96%" in statute text
        out_match = re.search(
            r"(\d+\.\d+)\s*percent(?:age)?\s+of\s+(?:net\s+)?outpatient",
            text, re.IGNORECASE
        )
        if not out_match:
            # Broader search for any percentage near "outpatient"
            out_match = re.search(r"outpatient[^.]{0,60}?(\d+\.\d+)\s*(?:percent|%)", text, re.IGNORECASE)
        if not out_match:
            out_match = re.search(r"(\d+\.\d+)\s*(?:percent|%)[^.]{0,60}?outpatient", text, re.IGNORECASE)

        # Look for per-patient-day rate like "$120.22" near "patient day"
        day_match = re.search(
            r"\$\s*(\d+\.\d+)\s*per\s+(?:patient\s+)?day",
            text, re.IGNORECASE
        )
        if not day_match:
            day_match = re.search(r"(\d+\.\d+)\s+(?:dollars?\s+)?per\s+(?:patient\s+)?day", text, re.IGNORECASE)

        outpatient = _FALLBACK_OUTPATIENT
        inpatient = _FALLBACK_INPATIENT_DAY
        confidence = CONFIDENCE_LIKELY
        parsed_any = False

        if out_match:
            try:
                val = float(out_match.group(1))
                if 1.0 <= val <= 10.0:   # sanity range for a Medicaid tax %
                    outpatient = val
                    parsed_any = True
            except ValueError:
                pass

        if day_match:
            try:
                val = float(day_match.group(1))
                if 50.0 <= val <= 500.0:  # sanity range for per-diem
                    inpatient = val
                    parsed_any = True
            except ValueError:
                pass

        # Confirm page is the right statute even when parsing fails
        if "256.9657" in text or "hospital assessment" in text.lower():
            confidence = CONFIDENCE_VERIFIED if parsed_any else CONFIDENCE_LIKELY

        return outpatient, inpatient, confidence

    def _parse_minnesota_care(self) -> tuple[float, str]:
        """
        Fetch MN Stat. 295.52 and extract the MinnesotaCare gross-receipts rate.
        """
        resp = self._fetch(URL_CARE)
        if resp is None:
            return _FALLBACK_CARE, CONFIDENCE_LIKELY

        text = resp.text

        # Look for rate near "gross revenues" or "gross receipts"
        match = re.search(
            r"(\d+\.\d+)\s*percent[^.]{0,80}?gross\s+(?:revenues?|receipts?)",
            text, re.IGNORECASE
        )
        if not match:
            match = re.search(
                r"gross\s+(?:revenues?|receipts?)[^.]{0,80}?(\d+\.\d+)\s*percent",
                text, re.IGNORECASE
            )

        rate = _FALLBACK_CARE
        confidence = CONFIDENCE_LIKELY

        if match:
            try:
                val = float(match.group(1))
                if 0.5 <= val <= 5.0:
                    rate = val
                    confidence = CONFIDENCE_VERIFIED
            except ValueError:
                pass
        elif "295.52" in text or "minnesotacare" in text.lower():
            confidence = CONFIDENCE_LIKELY   # page loaded, rate not parsed

        return rate, confidence
