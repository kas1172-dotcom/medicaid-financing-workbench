"""
Analysis 3b: Managed-care MCO-tax exposure.

THE QUESTION: more than two-thirds of Medicaid enrollees are in managed care, and
many states tax their managed care organizations (MCOs) to help fund the program.
MCO provider taxes face the SAME 3.5% hold-harmless phase-down as hospital taxes.
Which states tax their MCOs, and which are exposed when the ceiling drops?

THE METHOD: pull the MCO-class effective rate from each state's provider-tax
profile (the same panel the financing analysis uses). A state is "exposed" if it
is an expansion state with an MCO rate above the 3.5% floor. The rate gap
(rate - 3.5) is the per-point exposure that must be unwound by 2032. MCO taxes are
distinct from hospital taxes in their political economy: they are renegotiated
through managed care contracts rather than direct legislation, so the adjustment
path differs even when the dollar exposure is similar.

This is a structural exposure screen, not a revenue forecast: without per-state MCO
tax revenue we report the rate and the gap above the floor, not a dollar figure.
"""

from __future__ import annotations

import pandas as pd

MCO_FLOOR = 3.5  # 2032 hold-harmless floor for subject classes (incl. MCO)


def run(df: pd.DataFrame, params: dict) -> dict:
    rows = []
    for _, r in df.iterrows():
        classes = r.get("provider_taxes_by_class") or {}
        mco_rate = classes.get("mco")
        if not mco_rate or mco_rate <= 0:
            continue
        expansion = bool(r["expansion"])
        exposed = bool(expansion and mco_rate > MCO_FLOOR)
        rows.append({
            "state": r["state"], "abbr": r["abbr"],
            "mco_rate": round(float(mco_rate), 2),
            "exposed": exposed,
            "expansion": expansion,
            "rate_gap_above_floor": round(max(0.0, mco_rate - MCO_FLOOR), 2),
            "enrollment_millions": round(float(r["enrollment"]) / 1e6, 2),
            "has_hospital_tax": bool((classes.get("hospital") or 0) > 0),
            "data_source": str(r.get("provider_tax_data_source", "seed")),
        })

    rows.sort(key=lambda x: (x["exposed"], x["mco_rate"]), reverse=True)
    n_exposed = sum(1 for x in rows if x["exposed"])
    return {
        "id": "managed_care",
        "title": "Managed-care MCO-tax exposure",
        "rows": rows,
        "floor_pct": MCO_FLOOR,
        "n_states_with_mco_tax": len(rows),
        "n_exposed": n_exposed,
        "top_state": rows[0]["state"] if rows else None,
        "max_rate": rows[0]["mco_rate"] if rows else None,
        "data_provenance": df["data_provenance"].iloc[0],
    }
