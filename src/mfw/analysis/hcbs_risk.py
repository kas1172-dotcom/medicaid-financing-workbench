"""
Analysis 2: HCBS vulnerability index.

THE QUESTION: home- and community-based services (HCBS) are an OPTIONAL Medicaid
benefit. History shows optional benefits are first on the chopping block when
states face fiscal pressure. As the reconciliation law squeezes state financing,
which states' HCBS programs are most at risk?

THE METHOD: a composite 0-10 index. Each state is scored 0-1 on four normalized
components, weighted (weights live in config, so the analyst can re-weight and
re-rank without touching code), then scaled to 0-10:

  1. hcbs_spending_share  : how much of the program is HCBS        (the STAKES)
  2. provider_tax_reliance: reliance on the now-capped financing   (EXPOSURE)
  3. federal_cut_magnitude: projected dollar hit, size-normalized  (EXPOSURE)
  4. nonfederal_share_strain: share of the bill the state already carries (EXPOSURE)

This is deliberately a RISK SCREEN, not a forecast. It surfaces states warranting
a closer look; it does not predict that any state will cut HCBS. That distinction
is stated in every output so the index is never over-read.
"""

from __future__ import annotations

import pandas as pd


def _normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0.0
    return (series - lo) / (hi - lo)


def run(df: pd.DataFrame, params: dict) -> dict:
    w = params["hcbs_risk_weights"]
    total_cut_b = params["cbo_scores"]["total_medicaid_reduction_10yr_billion"]

    d = df.copy()

    # Component 1: HCBS share of spending (stakes).
    c_hcbs = _normalize(d["hcbs_share"])
    # Component 2: provider-tax reliance: rate scaled by whether it's exposed.
    reliance_raw = d["provider_tax_rate"] * d["expansion"].astype(int)
    c_reliance = _normalize(reliance_raw)
    # Component 3: projected federal cut, allocated proportional to federal spend,
    # then normalized so big states don't automatically dominate the SCREEN.
    fed_share = d["total_medicaid_fed_spend"] / d["total_medicaid_fed_spend"].sum()
    proj_cut = fed_share * total_cut_b * 1000  # $M over 10yr
    d["projected_cut_millions"] = proj_cut.round(0)
    c_cut = _normalize(proj_cut / d["enrollment"])  # per-enrollee hit
    # Component 4: nonfederal share strain.
    c_strain = _normalize(d["nonfederal_share"] / d["total_medicaid_spend"])

    # Normalized 0-1 components are independent of the weights, so we ship them
    # with each row: the dashboard can re-weight and re-rank live without a rebuild.
    d["c_hcbs"] = c_hcbs.round(4)
    d["c_reliance"] = c_reliance.round(4)
    d["c_cut"] = c_cut.round(4)
    d["c_strain"] = c_strain.round(4)

    score01 = (
        w["hcbs_spending_share"] * c_hcbs
        + w["provider_tax_reliance"] * c_reliance
        + w["federal_cut_magnitude"] * c_cut
        + w["nonfederal_share_strain"] * c_strain
    )
    d["hcbs_index"] = (score01 * 10).round(1)

    def tier(x):
        return "High" if x >= 6.5 else ("Medium" if x >= 4.0 else "Low")
    d["risk_tier"] = d["hcbs_index"].apply(tier)

    rows = [
        {
            "state": r["state"], "abbr": r["abbr"],
            "hcbs_index": float(r["hcbs_index"]),
            "risk_tier": r["risk_tier"],
            "hcbs_share": float(r["hcbs_share"]),
            "hcbs_spend_millions": float(r["hcbs_spend"]),
            "projected_cut_millions": float(r["projected_cut_millions"]),
            "expansion": bool(r["expansion"]),
            "components": {
                "hcbs_spending_share": float(r["c_hcbs"]),
                "provider_tax_reliance": float(r["c_reliance"]),
                "federal_cut_magnitude": float(r["c_cut"]),
                "nonfederal_share_strain": float(r["c_strain"]),
            },
        }
        for _, r in d.sort_values("hcbs_index", ascending=False).iterrows()
    ]

    counts = d["risk_tier"].value_counts().to_dict()
    return {
        "id": "hcbs_risk",
        "title": "HCBS vulnerability index",
        "rows": rows,
        "tier_counts": {k: int(v) for k, v in counts.items()},
        "top_state": rows[0]["state"],
        "weights": w,
        "data_provenance": df["data_provenance"].iloc[0],
    }
