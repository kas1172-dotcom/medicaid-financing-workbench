"""
Massachusetts — Hospital Assessment (MGL c.118E §63)
Source: MGL c.118E §63
URL:    https://www.mass.gov/info-details/mass-general-laws-c118e-ss-63
Structure: amount_targeted (per-patient-day + per-visit; not a simple % of revenue)
Phase 1 confidence: likely

2025 appropriation: $1.48B total assessment for SFY2025 (St.2025, c.9 §48).
Rate is per-patient-day + per-visit — complex structure not_comparable to % cap.
Seed value of 5.9% is an approximation based on total assessment ÷ estimated NPR.
"""

from __future__ import annotations

from ._base import (
    CONFIDENCE_LIKELY, CONFIDENCE_VERIFIED, RATE_BASIS_NOT_COMPARABLE,
    STRUCTURE_AMOUNT_TARGETED, RateRow, StateScraperBase,
)

URL = "https://www.mass.gov/info-details/mass-general-laws-c118e-ss-63"


class MassachusettsScraper(StateScraperBase):
    state = "Massachusetts"
    abbr = "MA"
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
                native_rate="$1.48B SFY2025 total assessment; per-patient-day + per-visit rates",
                rate_basis=RATE_BASIS_NOT_COMPARABLE,
                revenue_base_used=None,
                source_url=URL,
                retrieved_date=today,
                confidence=confidence,
                notes=(
                    "Complex per-unit structure (per-patient-day + per-visit) — "
                    "not comparable to % cap without per-unit volumes. "
                    "Total assessment ~$1.48B SFY2025; seed (5.9%) is an approximation. "
                    "Seek MA EOHHS rate schedule for current per-unit rates."
                ),
            ),
        ]

    def _check_page(self) -> str:
        resp = self._fetch(URL)
        if resp is None:
            return CONFIDENCE_LIKELY
        text = resp.text.lower()
        if "118e" in text or "hospital assessment" in text or "mass.gov" in text:
            return CONFIDENCE_VERIFIED
        return CONFIDENCE_LIKELY
