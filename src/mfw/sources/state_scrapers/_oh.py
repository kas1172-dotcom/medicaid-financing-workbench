"""
Ohio — Hospital Franchise Fee
Source: OAC Rule 5160-2-30
URL:    https://codes.ohio.gov/ohio-administrative-code/rule-5160-2-30
Structure: percentage
Verified by Phase 1 fetch.

Two-tier rate schedule (CY-based, not FFY-based):
  CY2025 (through 12/31/2025):  base 3.37% of total facility costs
  CY2026+ (starting 1/1/2026):  base 4.37% of total facility costs
  Supplemental (CY2026+):        3.641923% (operates under CMS non-uniformity waiver)
  Combined CY2026+:              ~8.01% (above 6% for the supplemental component)

For cap-exposure analysis, the rate IN EFFECT at phase-down START (FFY2028 = Oct 2027)
is CY2026+ base = 4.37%. The supplemental fee operates under a waiver and is
analytically distinct; we report the base rate for the standard exposure ranking.

We emit two rows:
  1. effective_date=2026-01-01 (the exposure-era rate, used for analysis)
  2. effective_date=2025-01-01 (CY2025 transition rate, for historical record)
The analysis layer picks the primary row (provider_class='hospital'; latest effective date).
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://codes.ohio.gov/ohio-administrative-code/rule-5160-2-30"

_RATE_2026 = 4.37     # CY2026+ base (in effect at FFY2028 phase-down start)
_RATE_2025 = 3.37     # CY2025 base (current through Dec 31 2025)
_SUPPLEMENTAL = 3.641923   # waiver-based; excluded from standard exposure


class OhioScraper(StateScraperBase):
    state = "Ohio"
    abbr = "OH"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate_2026, rate_2025, confidence = self._parse_rates()

        notes_primary = (
            f"CY2026+ base franchise fee {rate_2026:.2f}% of total facility costs "
            f"(effective 2026-01-01; in force at FFY2028 phase-down start). "
            f"Supplemental fee {_SUPPLEMENTAL}% operates under CMS non-uniformity waiver "
            f"(combined ~{round(rate_2026 + _SUPPLEMENTAL, 2)}% exceeds 6%). "
            f"Exposure analysis uses base rate only."
        )
        notes_hist = (
            f"CY2025 base franchise fee {rate_2025:.2f}% of total facility costs "
            f"(through 2025-12-31; historical reference only). "
            f"Use the CY2026+ row for phase-down exposure analysis."
        )

        return [
            # Primary row: CY2026+ rate — the rate in effect when phase-down begins.
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(rate_2026, 2),
                native_rate=f"{rate_2026:.2f}% total facility costs (CY2026+ base; effective 2026-01-01)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="total facility costs (Ohio franchise fee base)",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=notes_primary,
            ),
            # Historical row: CY2025 rate for record.
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital_cy2025",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(rate_2025, 2),
                native_rate=f"{rate_2025:.2f}% total facility costs (CY2025 base; through 2025-12-31)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="total facility costs (Ohio franchise fee base)",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=notes_hist,
            ),
        ]

    def _parse_rates(self) -> tuple[float, float, str]:
        """
        Fetch OAC Rule 5160-2-30 and extract both the CY2025 (3.37%) and
        CY2026+ (4.37%) base franchise fee rates.

        Returns (rate_2026, rate_2025, confidence).
        """
        resp = self._fetch(URL)
        if resp is None:
            return _RATE_2026, _RATE_2025, CONFIDENCE_LIKELY

        text = resp.text
        page_confirmed = "5160-2-30" in text or "franchise fee" in text.lower()

        r_2026 = _RATE_2026
        r_2025 = _RATE_2025
        parsed_any = False

        # Look for "4.37" explicitly (CY2026+ rate)
        if "4.37" in text:
            r_2026 = 4.37
            parsed_any = True

        # Look for "3.37" explicitly (CY2025 rate)
        if "3.37" in text:
            r_2025 = 3.37
            parsed_any = True

        # Broader regex: any decimal percentage near "facility costs" or "franchise"
        if not parsed_any:
            matches = re.findall(
                r"(\d+\.\d+)\s*(?:percent|%)[^.]{0,60}?(?:facility|franchise)",
                text, re.IGNORECASE
            )
            rates = sorted(set(float(m) for m in matches if 2.0 <= float(m) <= 6.0))
            if len(rates) >= 2:
                r_2025 = rates[0]    # lower = older rate
                r_2026 = rates[-1]   # higher = current rate
                parsed_any = True
            elif len(rates) == 1:
                r_2026 = rates[0]
                parsed_any = True

        confidence = (
            CONFIDENCE_VERIFIED if (page_confirmed and parsed_any) else
            CONFIDENCE_LIKELY
        )
        return r_2026, r_2025, confidence
