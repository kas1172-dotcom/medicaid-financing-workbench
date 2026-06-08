"""Assembles dashboard/dashboard_data.json for the static front-end."""

from __future__ import annotations

from mfw.etl.panel import build_panel, panel_summary
from mfw.analysis import provider_tax, hcbs_risk, work_requirements, duals
from mfw.outputs.charts import (
    chart_provider_tax_gap,
    chart_hcbs_index,
    chart_work_req_loss,
    chart_duals_concentration,
)
from mfw.llm.draft import draft


def build_dashboard_data(params: dict, prefer_live: bool = False) -> dict:
    df = build_panel(prefer_live=prefer_live)
    summary = panel_summary(df)

    print("  Running analyses...")
    results = {
        "provider_tax": provider_tax.run(df, params),
        "hcbs_risk": hcbs_risk.run(df, params),
        "work_requirements": work_requirements.run(df, params),
        "duals": duals.run(df, params),
    }
    for name, r in results.items():
        print(f"    ✓ {r['title']} — provenance={r['data_provenance']}")

    print("  Generating charts...")
    charts = {}
    chart_fns = {
        "provider_tax": chart_provider_tax_gap,
        "hcbs_risk": chart_hcbs_index,
        "work_requirements": chart_work_req_loss,
        "duals": chart_duals_concentration,
    }
    for name, fn in chart_fns.items():
        try:
            charts[name] = str(fn(results[name]))
            print(f"    ✓ {charts[name]}")
        except Exception as exc:
            charts[name] = None
            print(f"    [warn] chart for {name} failed: {exc}")

    print("  Loading narrative (reviewed drafts or LLM)...")
    narrative = {}
    for analysis_id, result in results.items():
        narrative[analysis_id] = draft(analysis_id, result)
        src = narrative[analysis_id].get("_source", "llm")
        print(f"    ✓ {analysis_id} — source={src}")

    is_seed = summary["data_provenance"] == "seed"
    return {
        "meta": {
            "generated_by": "Medicaid Financing Workbench v0.1.0",
            "data_provenance": summary["data_provenance"],
            "provenance_note": (
                "SEED DATA — illustrative values anchored to KFF-published magnitudes. "
                "Run `mfw fetch --live` for authoritative CMS data. "
                "Do not cite these figures as official."
            ) if is_seed else (
                "Live data from data.medicaid.gov and api.census.gov."
            ),
        },
        "summary": summary,
        "analyses": results,
        "narrative": narrative,
        "charts": charts,
    }
