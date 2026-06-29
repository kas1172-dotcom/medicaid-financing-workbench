"""State fact sheet: all four analyses filtered to one state."""

from __future__ import annotations

from mfw.etl.panel import build_panel
from mfw.analysis import provider_tax, hcbs_risk, work_requirements, duals


def build_factsheet(state_abbr: str, params: dict, prefer_live: bool = False) -> dict:
    df = build_panel(prefer_live=prefer_live)
    row = df[df["abbr"] == state_abbr]
    if row.empty:
        return {"error": f"State '{state_abbr}' not found. Check abbreviation."}
    r = row.iloc[0]

    pt_result = provider_tax.run(df, params)
    hcbs_result = hcbs_risk.run(df, params)
    wr_result = work_requirements.run(df, params)
    dual_result = duals.run(df, params)

    pt_row = next((x for x in pt_result["rows"] if x["abbr"] == state_abbr), {})
    hcbs_row = next((x for x in hcbs_result["rows"] if x["abbr"] == state_abbr), {})
    wr_row = next((x for x in wr_result["rows"] if x.get("abbr") == state_abbr), None)
    dual_row = next((x for x in dual_result["rows"] if x["abbr"] == state_abbr), {})

    return {
        "state_name": r["state"],
        "abbr": state_abbr,
        "data_provenance": r["data_provenance"],
        "expansion": bool(r["expansion"]),
        "fmap": float(r["fmap"]),
        "headline_figures": {
            "total_medicaid_enrollment": int(r["enrollment"]),
            "expansion_adults": int(r["expansion_adults"]) if r["expansion"] else None,
            "dual_eligibles": int(r["duals"]),
            "total_medicaid_spend_millions": int(r["total_medicaid_spend"]),
            "hcbs_spend_millions": int(r["hcbs_spend"]),
            "hcbs_share_of_spending_pct": float(r["hcbs_share"]),
        },
        "provider_tax": {
            "rate_pct": float(pt_row.get("provider_tax_rate", 0)),
            "exposed_to_cap": bool(pt_row.get("exposed", False)),
            "final_gap_millions": float(pt_row.get("final_gap_millions", 0)),
            "gap_share_of_nonfederal_pct": float(pt_row.get("gap_share_of_nonfederal_pct", 0)),
        },
        "hcbs_risk": {
            "index": float(hcbs_row.get("hcbs_index", 0)),
            "risk_tier": hcbs_row.get("risk_tier", "N/A"),
            "projected_cut_millions": float(hcbs_row.get("projected_cut_millions", 0)),
        },
        "work_requirements": wr_row if wr_row else {
            "note": "Non-expansion state, not subject to expansion work requirement provision.",
            "status": "not_applicable",
        },
        "dual_eligible": dual_row,
    }
