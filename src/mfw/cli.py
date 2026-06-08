"""
CLI entry point — the `mfw` command.

Commands:
  mfw analyze              run the four analyses -> outputs/results.json
  mfw dashboard            build dashboard/dashboard_data.json (+ charts)
  mfw factsheet --state X  generate a brief-ready state fact sheet
  mfw scenario --cap 3.0   provider-tax-cap counterfactual
  mfw fetch --live         attempt live data pull
  mfw draft                generate tell/show/so-what (requires ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml


def _load_params() -> dict:
    config_path = Path("config/policy_parameters.yaml")
    if not config_path.exists():
        # Try relative to the package install location.
        alt = Path(__file__).parent.parent.parent / "config/policy_parameters.yaml"
        config_path = alt if alt.exists() else config_path
    if not config_path.exists():
        print("[warn] config/policy_parameters.yaml not found; run from project root.")
        return {}
    return yaml.safe_load(config_path.read_text())


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_analyze(args, params):
    from mfw.etl.panel import build_panel, panel_summary
    from mfw.analysis import provider_tax, hcbs_risk, work_requirements, duals

    print("Building panel...")
    df = build_panel(prefer_live=getattr(args, "live", False))
    summary = panel_summary(df)
    provenance = summary["data_provenance"]
    print(f"  Panel ready: {summary['n_states']} states, provenance={provenance}")

    results = {}
    analyses = [
        ("provider_tax", provider_tax),
        ("hcbs_risk", hcbs_risk),
        ("work_requirements", work_requirements),
        ("duals", duals),
    ]
    for name, mod in analyses:
        print(f"  Running {name}...")
        r = mod.run(df, params)
        results[name] = r
        print(f"    ✓ {r['title']} — provenance={r['data_provenance']}")

    out_path = Path("outputs/results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {out_path}")
    print(f"data_provenance: {provenance}")
    return results


def cmd_dashboard(args, params):
    from mfw.outputs.dashboard_builder import build_dashboard_data

    print("Building dashboard data...")
    data = build_dashboard_data(params, prefer_live=getattr(args, "live", False))
    out_path = Path("dashboard/dashboard_data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, default=str))
    print(f"\ndashboard/dashboard_data.json written.")
    print("Open dashboard/index.html in a browser to view (serve via `python -m http.server` from project root).")
    return data


def cmd_factsheet(args, params):
    from mfw.outputs.factsheet import build_factsheet

    state = args.state.upper()
    print(f"Building fact sheet for {state}...")
    sheet = build_factsheet(state, params, prefer_live=getattr(args, "live", False))

    if "error" in sheet:
        print(f"Error: {sheet['error']}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"FACT SHEET: {sheet.get('state_name', state)}")
    print(f"Expansion: {sheet['expansion']}  |  FMAP: {sheet['fmap']}%  |  Provenance: {sheet['data_provenance']}")
    print(f"{'='*60}")
    hf = sheet.get("headline_figures", {})
    print(f"  Enrollment:           {hf.get('total_medicaid_enrollment', 'N/A'):,}")
    print(f"  Expansion adults:     {hf.get('expansion_adults') or 'N/A'}")
    print(f"  Dual eligibles:       {hf.get('dual_eligibles', 'N/A'):,}")
    print(f"  Total spend:          ${hf.get('total_medicaid_spend_millions', 0):,.0f}M")
    print(f"  HCBS spend:           ${hf.get('hcbs_spend_millions', 0):,.0f}M  ({hf.get('hcbs_share_of_spending_pct', 0):.1f}% of total)")
    pt = sheet.get("provider_tax", {})
    print(f"\n  Provider tax rate:    {pt.get('rate_pct', 0):.1f}%  (exposed: {pt.get('exposed_to_cap', False)})")
    if pt.get("exposed_to_cap"):
        print(f"  Final-year gap:       ${pt.get('final_gap_millions', 0):,.0f}M  ({pt.get('gap_share_of_nonfederal_pct', 0):.1f}% of nonfederal share)")
    hcbs = sheet.get("hcbs_risk", {})
    print(f"\n  HCBS vulnerability:   {hcbs.get('index', 0):.1f}/10  [{hcbs.get('risk_tier', 'N/A')}]")
    wr = sheet.get("work_requirements", {})
    if wr.get("status") != "not_applicable":
        print(f"\n  Work req. status:     {wr.get('status', 'N/A')}")
        print(f"  Modeled loss:         {wr.get('modeled_coverage_loss', 0):,} persons  ({wr.get('loss_pct_of_subject', 0):.1f}% of subject adults)")

    out_path = Path(f"outputs/factsheet_{state}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sheet, indent=2))
    print(f"\nFull fact sheet written to {out_path}")
    return sheet


def cmd_scenario(args, params):
    from mfw.etl.panel import build_panel
    from mfw.modeling.scenarios import run_scenario

    cap = float(args.cap)
    base_cap = params.get("provider_tax", {}).get("target_cap_pct", 3.5)
    print(f"Running provider-tax-cap scenario: {base_cap}% → {cap}%")
    df = build_panel(prefer_live=getattr(args, "live", False))
    overrides = {"provider_tax": {"target_cap_pct": cap}}
    result = run_scenario(df, params, overrides)

    deltas = result["deltas"]
    base_gap = result["base"]["provider_tax"]["national_final_gap_billion"]
    scen_gap = result["scenario"]["provider_tax"]["national_final_gap_billion"]
    print(f"\n  Baseline national gap (cap={base_cap}%): ${base_gap:.2f}B")
    print(f"  Scenario national gap (cap={cap}%):    ${scen_gap:.2f}B")
    print(f"  Delta:                                 ${deltas['provider_tax_national_gap_billion']:+.2f}B")
    base_loss = result["base"]["work_requirements"]["national_modeled_loss"]
    scen_loss = result["scenario"]["work_requirements"]["national_modeled_loss"]
    print(f"\n  Work-req loss (unchanged by cap):      {base_loss:,} → {scen_loss:,}")

    out_path = Path(f"outputs/scenario_cap{cap}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nFull scenario written to {out_path}")
    return result


def cmd_fetch(args, params):
    from mfw.sources.cms64 import fetch_cms64, FetchError
    print("Attempting live CMS-64 fetch from data.medicaid.gov...")
    try:
        rows = fetch_cms64()
        print(f"  ✓ {len(rows)} rows fetched and cached to data/raw/")
    except FetchError as exc:
        print(f"  ✗ CMS-64 fetch failed: {exc}")
        print("  Seed data will be used for analyses.")


def cmd_draft(args, params):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[info] ANTHROPIC_API_KEY not set — using reviewed stubs from dashboard/reviewed_drafts.json")

    results_path = Path("outputs/results.json")
    if not results_path.exists():
        print("Run `mfw analyze` first.")
        sys.exit(1)

    from mfw.llm.draft import draft
    results = json.loads(results_path.read_text())
    drafts = {}
    for analysis_id, result in results.items():
        print(f"  Drafting {analysis_id}...")
        drafts[analysis_id] = draft(analysis_id, result)

    out_path = Path("outputs/drafts.json")
    out_path.write_text(json.dumps(drafts, indent=2))
    print(f"Drafts written to {out_path}")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="mfw",
        description="Medicaid Financing Workbench — four analyses, one command.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("analyze", help="Run the four analyses → outputs/results.json")
    p.add_argument("--live", action="store_true", help="Prefer live federal data")

    p = sub.add_parser("dashboard", help="Build dashboard/dashboard_data.json + charts")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("factsheet", help="Generate a state fact sheet")
    p.add_argument("--state", required=True, metavar="XX", help="Two-letter state abbreviation")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("scenario", help="Run a counterfactual (e.g. --cap 3.0)")
    p.add_argument("--cap", type=float, required=True, metavar="PCT",
                   help="Provider tax target cap in percent (e.g. 3.0)")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("fetch", help="Attempt live data pull from federal APIs")
    p.add_argument("--live", action="store_true")

    sub.add_parser("draft", help="Generate tell/show/so-what (requires ANTHROPIC_API_KEY)")

    args = parser.parse_args()
    params = _load_params()

    dispatch = {
        "analyze": cmd_analyze,
        "dashboard": cmd_dashboard,
        "factsheet": cmd_factsheet,
        "scenario": cmd_scenario,
        "fetch": cmd_fetch,
        "draft": cmd_draft,
    }

    if args.command not in dispatch:
        parser.print_help()
        sys.exit(1)

    dispatch[args.command](args, params)


if __name__ == "__main__":
    main()
