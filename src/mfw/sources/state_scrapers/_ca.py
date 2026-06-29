"""
California: Hospital Quality Assurance Fee (HQAF)
Source: CA DHCS HQAF Program page
URL:    https://www.dhcs.ca.gov/provgovpart/Pages/HospitalQualityAssuranceFeeProgram.aspx
Structure: percentage (~5.03% of NPR; Prop 52 permanent program)
Phase 1 confidence: likely: rate confirmed from CHA secondary analysis, not page fetch.

Statutory authority: Prop 52 (2016) + SB 239 (2013). Rate ~5.03% of net patient revenue
per California Hospital Association analysis. DHCS page loads but does not display the
specific rate value. MCO tax also exists via CMS waiver (seed value ~4.5%; seed_carryover).
"""

from __future__ import annotations

import re

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_REPORTED,
    RATE_BASIS_SEED_CARRYOVER, STRUCTURE_PERCENTAGE,
    RateRow, StateScraperBase,
)

URL = "https://www.dhcs.ca.gov/provgovpart/Pages/HospitalQualityAssuranceFeeProgram.aspx"
_FALLBACK_RATE = 5.03


class CaliforniaScraper(StateScraperBase):
    state = "California"
    abbr = "CA"
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
                native_rate=f"{rate:.2f}% net patient revenue (HQAF, Prop 52)",
                rate_basis=RATE_BASIS_REPORTED,
                revenue_base_used="net patient revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    f"Rate ~{_FALLBACK_RATE}% per CHA analysis; DHCS page does not "
                    "display rate directly. Prop 52 made HQAF permanent (2016). "
                    "Seek current DHCS rate notice for exact figure."
                ),
            ),
            RateRow(
                state=self.state, abbr=self.abbr, expansion=self.expansion,
                provider_class="mco",
                structure=STRUCTURE_PERCENTAGE,
                effective_rate_pct=4.5,
                native_rate="~4.5% (seed/MACPAC; CMS waiver; not confirmed from primary source)",
                rate_basis=RATE_BASIS_SEED_CARRYOVER,
                revenue_base_used="MCO capitation revenue",
                source_url=URL,
                retrieved_date=today,
                confidence=CONFIDENCE_LIKELY,
                notes="MCO tax from seed; verify against CA DHCS/CMS SPA.",
            ),
        ]

    def _parse_rate(self) -> tuple[float, str]:
        resp = self._fetch(URL)
        if resp is None:
            return _FALLBACK_RATE, CONFIDENCE_LIKELY
        text = resp.text
        page_confirmed = "quality assurance" in text.lower() or "hqaf" in text.lower()
        match = re.search(r"(\d+\.\d+)\s*(?:percent|%)[^.]{0,60}?(?:patient|revenue|net)", text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                if 3.0 <= val <= 7.0:
                    return round(val, 2), CONFIDENCE_VERIFIED if page_confirmed else CONFIDENCE_LIKELY
            except ValueError:
                pass
        return _FALLBACK_RATE, CONFIDENCE_LIKELY
