"""
Missouri — Federal Reimbursement Allowance (FRA)
Source: RSMo §208.471
URL:    https://revisor.mo.gov/main/OneSection.aspx?section=208.471&bid=11092
Structure: percentage (5% hospital; SFY2027 emergency regulation)
Phase 1 confidence: likely — statute confirms FRA program; rate set by emergency reg.

MO FRA = 5% for SFY2027 per MO HealthNet emergency regulation.
Four provider taxes total ~$900M from hospitals in Missouri.
Actual rate is in administrative regulation, not the statute text.
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    STRUCTURE_PERCENTAGE, RateRow, StateScraperBase,
)

URL = "https://revisor.mo.gov/main/OneSection.aspx?section=208.471&bid=11092"
_FALLBACK_RATE = 5.0


class MissouriScraper(StateScraperBase):
    state = "Missouri"
    abbr = "MO"
    expansion = True

    def scrape(self) -> list[RateRow]:
        today = self._today()
        rate, confidence = self._parse_rate()

        return [
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="hospital",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=round(rate, 2),
                native_rate=f"{rate:.2f}% of net revenue (FRA, RSMo §208.471)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"SFY2027 rate {_FALLBACK_RATE}% per MO HealthNet emergency regulation. "
                    "Statute §208.471 confirms FRA program exists; rate set administratively. "
                    "Seek current MO HealthNet emergency reg for exact current rate. "
                    "Four hospital provider taxes total ~$900M/year."
                ),
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "208.471" in text or "reimbursement allowance" in text.lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:percent|%)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 3.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        if page_confirmed:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
