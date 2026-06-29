"""
Analysis 1: Provider tax financing analysis (three-tier model).

Three tiers, each applicable to some or all of the 51 jurisdictions:

Tier 1: Budget dependence (all 51, headline metric)
   provider_tax_revenue ÷ nonfederal_spending
   Source: CMS-64 T-19 when available; KFF-anchor rate-model estimate when not.
   Answers: "How much of the state's non-federal Medicaid budget depends on
   provider-tax revenue that is now at risk or under new constraints?"

Tier 2: Rate-based exposure (expansion states with a real percentage rate)
   Distance above 3.5% floor → implied dollar gap → phase-down trajectory.
   Subject classes only: hospital, MCO, ambulance, other.
   Exempt classes: nursing_facility, icf_iid.
   Preserves known findings: PA below floor (3.32%), KY exposure via MCO 5.5%
   not hospital 2.5%, OH base 4.37% CY2026+, WV 3.99%.

Tier 3: Structural outliers (three sub-panels)
   a. Waiver states (RI 13.12%, NV 7.139%): CMS non-uniformity waiver; primary
      risk is waiver revocation, not the 3.5% phase-down.
   b. Non-percentage structures (NJ, WA, AZ-hospital, MT, ID, OR, DC):
      per-admission, per-bed-day, dollar-cap, amount-targeted.
      Shown in native units + Tier-1 dollar dependence; no derived percentage.
   c. No-tax expansion states (AK; per registry): confirmed absence of
      subject provider taxes.

Result schema: every state appears exactly once:
   tier                  int      Primary tier (1|2|3)
   dependence_share_pct  float?   % of nonfederal share from provider taxes
                                  (null = unavailable, NEVER rendered as zero)
   dependence_source     str      data source for dependence_share_pct
   rate_exposure         dict?    Tier-2 data; null for non-rate states
   structure             str      "percentage"|"non_percentage"|"waiver"|"none"|"mixed"
   waiver_flag           str?
   provenance            str      "scraped"|"seed"|"seed_carryover"|"unquantified"
   provider_tax_data_source  str  raw source tag from scraper
"""

from __future__ import annotations

import pandas as pd
import math


def _clean_str(val) -> str | None:
    """Return None for NaN/None/empty, else str(val)."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none") else None

EXEMPT_CLASSES = frozenset({"nursing_facility", "icf_iid"})
SUBJECT_CLASSES = ["hospital", "mco", "ambulance", "other"]

# KFF anchor: provider taxes fund a median ~18% of nonfederal share nationally,
# at a median subject rate of ~5.5%. Calibration constant = 18.0 / 5.5.
# Applied only when CMS-64 T-19 revenue data is unavailable.
_KFF_DEPENDENCE_MEDIAN_PCT = 18.0
_KFF_MEDIAN_RATE = 5.5
_RATE_TO_DEPENDENCE_CALIBRATION = _KFF_DEPENDENCE_MEDIAN_PCT / _KFF_MEDIAN_RATE

# Source labels for dependence_source field
_DEP_SRC_T19 = "cms64_t19_reported"
_DEP_SRC_RATE_EST = "rate_model_kff_anchor"
_DEP_SRC_NO_TAX = "no_subject_taxes_confirmed"
_DEP_SRC_UNAVAIL = "data_unavailable"
_DEP_SRC_NON_PCT = "non_percentage_structure"


def _estimate_dependence_from_rate(
    max_subject_rate: float,
    nonfederal_share: float,
    provider_tax_revenue_millions: float | None,
) -> tuple[float | None, str]:
    """
    Return (dependence_share_pct, source_label).

    Priority:
    1. Directly reported CMS-64 T-19 revenue.
    2. Rate-model KFF-anchor estimate (max subject rate rescaled from 18%@5.5%).
    3. Null (data unavailable).
    """
    if provider_tax_revenue_millions is not None and nonfederal_share > 0:
        pct = round(100.0 * provider_tax_revenue_millions / nonfederal_share, 1)
        return pct, _DEP_SRC_T19

    if max_subject_rate > 0 and nonfederal_share > 0:
        # Scale from the KFF median anchor. Capped at 40% to prevent outliers.
        est_pct = min(max_subject_rate * _RATE_TO_DEPENDENCE_CALIBRATION, 40.0)
        return round(est_pct, 1), _DEP_SRC_RATE_EST

    return None, _DEP_SRC_UNAVAIL


def _compute_state_gap(
    nonfederal_share: float,
    taxes: dict[str, float],
    cap: float,
) -> tuple[float, dict[str, float]]:
    """
    Return (gap_$M, class_breakdown_dict) for one state at a given cap level.

    gap_$M: total at-risk revenue across all subject classes.
    class_breakdown: {class: gap_$M} for per-class audit.
    """
    subject = {c: taxes.get(c, 0.0) for c in SUBJECT_CLASSES if taxes.get(c, 0.0) > 0.0}
    if not subject:
        return 0.0, {}

    total_subject_rate = sum(subject.values())
    gap = 0.0
    breakdown = {}
    for c, rate in subject.items():
        pts = max(0.0, rate - cap)
        if pts > 0:
            weight = rate / total_subject_rate
            class_gap = nonfederal_share * weight * (pts / rate)
            breakdown[c] = round(class_gap, 1)
            gap += class_gap
    return gap, breakdown


def _assign_tier(
    expansion: bool,
    waiver_flag: str | None,
    structure: str,
    max_subject_rate: float,
) -> int:
    """
    Assign primary tier.
    3 = waiver / structural-outlier / no-tax confirmed
    2 = expansion with rate above 3.5% floor
    1 = all others
    """
    if waiver_flag == "non_uniformity_waiver":
        return 3
    if structure in ("non_percentage", "none"):
        return 3
    if expansion and max_subject_rate > 3.5:
        return 2
    return 1


def run(df: pd.DataFrame, params: dict) -> dict:
    pt = params["provider_tax"]
    target = pt["target_cap_pct"]
    start = pt["phasedown_start_year"]
    end = pt["phasedown_end_year"]
    step = pt["phasedown_step_pct_per_year"]
    current = pt["current_cap_pct"]

    # Ceiling schedule by year (6.0 → 3.5 in 0.5-point steps).
    schedule: dict[int, float] = {}
    cap = current
    for yr in range(start, end + 1):
        cap = max(target, round(cap - step, 2))
        schedule[yr] = cap

    rows = []             # all 51 states, one row each
    waiver_rows = []      # Tier-3a: waiver states (also appear in rows with tier=3)
    t3_non_pct = []       # Tier-3b: non-percentage structures
    t3_no_tax = []        # Tier-3c: no-tax expansion states
    t2_exposed = []       # Tier-2: rate-states above 3.5%

    for _, r in df.iterrows():
        taxes = r.get("provider_taxes_by_class") or {}
        expansion = bool(r["expansion"])
        waiver_flag = _clean_str(r.get("provider_tax_waiver_flag"))
        data_source = _clean_str(r.get("provider_tax_data_source")) or "seed"
        unquantified = r.get("provider_tax_unquantified") or {}
        nonfed = float(r.get("nonfederal_share") or 0.0)
        pt_revenue = r.get("provider_tax_revenue_millions")  # from CMS-64 T-19 if available

        subject_rates = {c: taxes.get(c, 0.0) for c in SUBJECT_CLASSES}
        max_subject = max(subject_rates.values()) if subject_rates else 0.0

        # Determine subject-class structures for this state.
        has_pct_subject = any(
            taxes.get(c, 0.0) > 0 and c not in unquantified
            for c in SUBJECT_CLASSES
        )
        has_only_non_pct = (
            not has_pct_subject and
            any(c in unquantified for c in SUBJECT_CLASSES)
        )
        has_no_subject = (not has_pct_subject and not has_only_non_pct and max_subject == 0.0)

        # Structure classification
        if waiver_flag == "non_uniformity_waiver":
            structure = "waiver"
        elif has_only_non_pct:
            structure = "non_percentage"
        elif has_no_subject:
            structure = "none"
        elif unquantified:
            structure = "mixed"   # some pct, some non-pct
        else:
            structure = "percentage"

        # ── Tier 1: Budget dependence for all 51 ─────────────────────
        if has_no_subject and not unquantified:
            dependence_share_pct = 0.0
            dependence_source = _DEP_SRC_NO_TAX
        elif structure == "non_percentage" and pt_revenue is None:
            # Can't estimate from rate; T-19 revenue needed
            dependence_share_pct = None
            dependence_source = _DEP_SRC_NON_PCT
        elif structure == "mixed" and pt_revenue is None:
            # Has some pct classes: estimate from those
            dependence_share_pct, dependence_source = _estimate_dependence_from_rate(
                max_subject, nonfed, pt_revenue
            )
        else:
            dependence_share_pct, dependence_source = _estimate_dependence_from_rate(
                max_subject, nonfed, pt_revenue
            )

        # ── Tier 2: Rate-based exposure (expansion, percentage, > 3.5%) ─
        tier2_result = None
        exposed = False

        if expansion and not waiver_flag and max_subject > 0.0:
            exposed = max_subject > target
            if exposed:
                final_gap, class_breakdown = _compute_state_gap(nonfed, taxes, target)
                gap_share_of_nonfed = round(100 * final_gap / nonfed, 1) if nonfed else 0.0
                by_year = {}
                for yr, yr_cap in schedule.items():
                    yr_gap, _ = _compute_state_gap(nonfed, taxes, yr_cap)
                    by_year[yr] = round(yr_gap, 1)
                tier2_result = {
                    "max_subject_rate": max_subject,
                    "exposed": True,
                    "final_gap_millions": round(final_gap, 1),
                    "gap_share_of_nonfederal_pct": gap_share_of_nonfed,
                    "gap_by_year": by_year,
                    "gap_by_class": class_breakdown,
                }
            else:
                tier2_result = {
                    "max_subject_rate": max_subject,
                    "exposed": False,
                    "final_gap_millions": 0.0,
                    "gap_share_of_nonfederal_pct": 0.0,
                    "gap_by_year": {yr: 0.0 for yr in schedule},
                    "gap_by_class": {},
                }

        # ── Assign primary tier ──────────────────────────────────────
        tier = _assign_tier(expansion, waiver_flag, structure, max_subject)

        # ── Build the unified row ────────────────────────────────────
        row = {
            "state": r["state"],
            "abbr": r["abbr"],
            "expansion": expansion,
            "tier": tier,
            "structure": structure,
            "dependence_share_pct": dependence_share_pct,
            "dependence_source": dependence_source,
            "rate_exposure": tier2_result,
            # Flattened convenience fields for charts/tables
            "provider_tax_rate": r.get("provider_tax_rate") or max_subject,
            "provider_taxes_by_class": taxes,
            "exposed": exposed,
            "final_gap_millions": tier2_result["final_gap_millions"] if tier2_result else 0.0,
            "gap_share_of_nonfederal_pct": tier2_result["gap_share_of_nonfederal_pct"] if tier2_result else 0.0,
            "gap_by_year": tier2_result["gap_by_year"] if tier2_result else {yr: 0.0 for yr in schedule},
            "gap_by_class": tier2_result["gap_by_class"] if tier2_result else {},
            "unquantified_classes": {c: v for c, v in unquantified.items() if c in SUBJECT_CLASSES} or None,
            "waiver_flag": waiver_flag,
            "provider_tax_data_source": data_source,
            "note": None,
        }

        rows.append(row)

        # ── Tier panel cataloguing ───────────────────────────────────
        if tier == 3:
            if waiver_flag == "non_uniformity_waiver":
                waiver_rows.append({
                    **row,
                    "waiver_rate_pct": max_subject,
                    "note": (
                        "CMS non-uniformity waiver: rate exceeds 6% ceiling. "
                        "OBBBA compliance risk distinct from standard phase-down."
                    ),
                })
            elif structure in ("non_percentage", "mixed"):
                t3_non_pct.append({
                    **row,
                    "native_rates": unquantified,
                    "note": (
                        "Non-percentage subject structures (per-admission, per-bed-day, "
                        "dollar-cap, or amount-targeted). Exposure not directly comparable "
                        "to 6%→3.5% cap. Shown in native units only."
                    ),
                })
            elif structure == "none" and expansion:
                t3_no_tax.append({
                    **row,
                    "note": "No subject provider taxes confirmed.",
                })

        if exposed and tier == 2:
            t2_exposed.append(row)

    # Sort main rows by Tier-1 dependence desc, then final gap desc.
    rows.sort(key=lambda x: (
        -(x["dependence_share_pct"] or 0.0),
        -x["final_gap_millions"],
    ))
    t2_exposed.sort(key=lambda x: x["final_gap_millions"], reverse=True)

    # National gap: Tier-2 exposed states only (excludes waiver, non-%).
    national_gap = round(sum(x["final_gap_millions"] for x in t2_exposed) / 1000, 2)

    # Provenance composition
    expansion_rows = [x for x in rows if x["expansion"]]
    n_scraped = sum(1 for x in expansion_rows if x.get("provider_tax_data_source") == "scraped")
    n_seed = sum(1 for x in expansion_rows if x.get("provider_tax_data_source") == "seed")
    n_unquant = len(t3_non_pct)
    n_waiver = len(waiver_rows)
    provenance_composition = (
        f"{n_scraped} states scraped, {n_seed} seed, "
        f"{n_unquant} unquantified structure, {n_waiver} waiver"
    )

    # Tier-1 dependence ranking: all states with dependence_share_pct available
    t1_ranked = sorted(
        [r for r in rows if r["dependence_share_pct"] is not None],
        key=lambda x: -(x["dependence_share_pct"] or 0.0),
    )

    return {
        "id": "provider_tax",
        "title": "Provider tax financing analysis (three-tier model)",
        "schedule": schedule,
        "rows": rows,
        "tier1_ranked": t1_ranked,
        "tier2_exposed": t2_exposed,
        "tier3_waiver": waiver_rows,
        "tier3_non_percentage": t3_non_pct,
        "tier3_no_tax": t3_no_tax,
        # Legacy fields preserved for backwards compatibility with dashboard
        "waiver_risk_states": waiver_rows,
        "unquantified_structures": t3_non_pct,
        "n_exposed": len(t2_exposed),
        "n_waiver_risk": len(waiver_rows),
        "n_unquantified": len(t3_non_pct),
        "national_final_gap_billion": national_gap,
        "provenance_composition": provenance_composition,
        "top_state": t2_exposed[0]["state"] if t2_exposed else (
            t1_ranked[0]["state"] if t1_ranked else None
        ),
        "exempt_classes": list(EXEMPT_CLASSES),
        "subject_classes": SUBJECT_CLASSES,
        "data_provenance": df["data_provenance"].iloc[0],
    }
