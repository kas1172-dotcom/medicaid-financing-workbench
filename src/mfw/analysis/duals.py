"""
Analysis 4 — Dual-eligible spending concentration.

THE QUESTION: dual eligibles (Medicare + Medicaid) are a small share of enrollees
but a large share of spending. Where is that concentration sharpest — and why does
it matter for this role? Because the team's work sits at the Medicare-Medicaid seam,
and cuts that look small in enrollee terms can land heavily on duals.

THE METHOD:
  dual_share_enrollment = duals / enrollment
  Spending is disproportionately concentrated in duals (LTSS, HCBS, complex care).
  We apply a documented concentration factor: duals consume spending at roughly
  3x the per-capita rate of non-duals (a standard published approximation). From
  that we estimate the dual share of spending and flag states where a small
  enrollee share maps to an outsized spending share.
"""

from __future__ import annotations

import pandas as pd

DUAL_COST_MULTIPLE = 3.0  # duals' per-capita spend ~3x non-duals (published approximation)


def run(df: pd.DataFrame, params: dict) -> dict:
    rows = []
    for _, r in df.iterrows():
        enroll = r["enrollment"]
        duals = r["duals"]
        if enroll == 0:
            continue
        dual_enroll_share = duals / enroll
        # Share of spending = weighted by cost multiple.
        num = dual_enroll_share * DUAL_COST_MULTIPLE
        denom = num + (1 - dual_enroll_share)
        dual_spend_share = num / denom
        rows.append({
            "state": r["state"], "abbr": r["abbr"],
            "duals": int(duals),
            "dual_enroll_share_pct": round(100 * dual_enroll_share, 1),
            "dual_spend_share_pct": round(100 * dual_spend_share, 1),
            "concentration_ratio": round(dual_spend_share / dual_enroll_share, 2),
            "est_dual_spend_millions": round(r["total_medicaid_spend"] * dual_spend_share, 1),
        })
    rows.sort(key=lambda x: x["dual_spend_share_pct"], reverse=True)
    return {
        "id": "duals",
        "title": "Dual-eligible spending concentration",
        "rows": rows,
        "cost_multiple": DUAL_COST_MULTIPLE,
        "national_dual_spend_share_pct": round(
            sum(x["est_dual_spend_millions"] for x in rows)
            / df["total_medicaid_spend"].sum() * 100, 1),
        "top_state": rows[0]["state"] if rows else None,
        "data_provenance": df["data_provenance"].iloc[0],
    }
