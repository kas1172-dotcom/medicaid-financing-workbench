"""
Analysis 1 — Provider tax cap exposure (per-class model).

THE QUESTION (analyst's judgment): the 2025 law's single biggest financing
threat to expansion states is the provider-tax ceiling phasing from 6.0% to
3.5%. Which states are most exposed, by how much, and on what timeline?

THE METHOD:
  The law exempts nursing facility and ICF/IID taxes from the phase-down.
  Only hospital, MCO, ambulance, and "other" provider taxes are subject.
  This matters: a state whose primary provider tax is on nursing facilities
  is NOT exposed to the cap, even if that rate exceeds 3.5%.

  For each non-exempt class c in a state:
      exposed_points_c = max(0, rate_c - cap)
      weight_c = rate_c / sum_of_all_non_exempt_rates   (revenue-share proxy)
      class_gap_c = nonfederal_share × weight_c × exposed_points_c / rate_c

  The state's total gap = sum of class_gap_c across all non-exempt classes
  with rate_c > 0.

  The phase-down walks the ceiling down 0.5pp/year from FFY2028 to FFY2032,
  so the gap opens gradually; we report the gap at each year.

  Non-expansion states are not subject to the reduced cap — their exposure is
  always zero (flagged explicitly).
"""

from __future__ import annotations

import pandas as pd

EXEMPT_CLASSES = frozenset({"nursing_facility", "icf_iid"})
SUBJECT_CLASSES = ["hospital", "mco", "ambulance", "other"]


def _compute_state_gap(
    nonfederal_share: float,
    taxes: dict,
    cap: float,
) -> tuple[float, dict[str, float]]:
    """
    Return (gap_$M, class_breakdown_dict) for one state at a given cap level.

    gap_$M          — total at-risk revenue in $M across all subject classes
    class_breakdown — {class_name: gap_$M} for auditing per-class contribution
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

    rows = []
    for _, r in df.iterrows():
        taxes = r.get("provider_taxes_by_class") or {}
        expansion = bool(r["expansion"])

        if not expansion:
            rows.append({
                "state": r["state"], "abbr": r["abbr"],
                "expansion": False,
                "provider_tax_rate": r["provider_tax_rate"],
                "provider_taxes_by_class": taxes,
                "exposed": False,
                "final_gap_millions": 0.0,
                "gap_share_of_nonfederal_pct": 0.0,
                "gap_by_year": {yr: 0.0 for yr in schedule},
                "gap_by_class": {},
                "note": "Non-expansion state; not subject to reduced cap.",
            })
            continue

        # Check exposure: any subject class above the target cap?
        subject_rates = {c: taxes.get(c, 0.0) for c in SUBJECT_CLASSES}
        max_subject = max(subject_rates.values()) if subject_rates else 0.0
        exposed = max_subject > target

        if exposed:
            final_gap, class_breakdown = _compute_state_gap(r["nonfederal_share"], taxes, target)
            gap_share_of_nonfed = round(100 * final_gap / r["nonfederal_share"], 1) if r["nonfederal_share"] else 0.0
            by_year = {}
            for yr, yr_cap in schedule.items():
                yr_gap, _ = _compute_state_gap(r["nonfederal_share"], taxes, yr_cap)
                by_year[yr] = round(yr_gap, 1)
        else:
            final_gap = 0.0
            class_breakdown = {}
            gap_share_of_nonfed = 0.0
            by_year = {yr: 0.0 for yr in schedule}

        rows.append({
            "state": r["state"],
            "abbr": r["abbr"],
            "expansion": True,
            "provider_tax_rate": r["provider_tax_rate"],
            "provider_taxes_by_class": taxes,
            "exposed": bool(exposed),
            "final_gap_millions": round(final_gap, 1),
            "gap_share_of_nonfederal_pct": gap_share_of_nonfed,
            "gap_by_year": by_year,
            "gap_by_class": class_breakdown,
            "note": None,
        })

    rows.sort(key=lambda x: x["final_gap_millions"], reverse=True)
    exposed_rows = [x for x in rows if x["exposed"]]

    national_gap = round(sum(x["final_gap_millions"] for x in rows) / 1000, 2)  # $B

    return {
        "id": "provider_tax",
        "title": "Provider tax cap exposure",
        "schedule": schedule,
        "rows": rows,
        "n_exposed": len(exposed_rows),
        "national_final_gap_billion": national_gap,
        "top_state": exposed_rows[0]["state"] if exposed_rows else None,
        "exempt_classes": list(EXEMPT_CLASSES),
        "subject_classes": SUBJECT_CLASSES,
        "data_provenance": df["data_provenance"].iloc[0],
    }
