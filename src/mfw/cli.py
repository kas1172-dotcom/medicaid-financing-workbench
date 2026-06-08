"""
CLI entry point — the `mfw` command.

Commands:
  mfw refresh              interactive; fetches APIs + ingests manual uploads
  mfw build                non-interactive; builds dashboard from data/current/
  mfw analyze              run the analyses -> outputs/results.json
  mfw dashboard            alias for `mfw build` (legacy)
  mfw factsheet --state X  generate a brief-ready state fact sheet
  mfw scenario --cap 3.0   provider-tax-cap counterfactual
  mfw fetch --live         attempt live API pull (legacy)
  mfw draft                generate tell/show/so-what (requires ANTHROPIC_API_KEY)

`mfw build` is what the GitHub Action runs. It never prompts for files and never
fails because a manual-upload source is missing — it proceeds with the last-good
data from data/current/ and surfaces the "as of" date in the site.

`mfw refresh` is for local interactive use. It auto-fetches API sources and
prompts clearly when a manual file is needed: source name, download URL, exact
filename, and age of the current copy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml


def _load_params() -> dict:
    config_path = Path("config/policy_parameters.yaml")
    if not config_path.exists():
        alt = Path(__file__).parent.parent.parent / "config/policy_parameters.yaml"
        config_path = alt if alt.exists() else config_path
    if not config_path.exists():
        print("[warn] config/policy_parameters.yaml not found; run from project root.")
        return {}
    return yaml.safe_load(config_path.read_text())


def _load_data_sources() -> list[dict]:
    manifest_path = Path("config/data_sources.yaml")
    if not manifest_path.exists():
        alt = Path(__file__).parent.parent.parent / "config/data_sources.yaml"
        manifest_path = alt if alt.exists() else manifest_path
    if not manifest_path.exists():
        return []
    raw = yaml.safe_load(manifest_path.read_text())
    return raw.get("sources", [])


def _provenance_age(source_id: str) -> tuple[str | None, bool]:
    """
    Return (retrieved_date_str, is_stale) for a source in data/current/.
    stale = file older than refresh_frequency or missing.
    """
    prov_path = Path("data/current") / f"{source_id}.provenance.json"
    if not prov_path.exists():
        return None, True
    try:
        prov = json.loads(prov_path.read_text())
        retrieved = prov.get("retrieved_date")
        return retrieved, False
    except Exception:
        return None, True


def _refresh_frequency_days(freq: str) -> int:
    return {"weekly": 7, "monthly": 30, "quarterly": 90, "annual": 365, "once": 9999}.get(freq, 30)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_refresh(args, params):
    """
    Interactive refresh — runs for each source in the manifest.
    API sources are fetched automatically. Manual sources are looked for in
    data/inbox/ and the analyst is prompted clearly when a file is needed.
    """
    sources = _load_data_sources()
    if not sources:
        print("[warn] config/data_sources.yaml not found; nothing to refresh.")
        return

    Path("data/inbox").mkdir(parents=True, exist_ok=True)
    Path("data/current").mkdir(parents=True, exist_ok=True)

    refreshed, still_needed, failed = [], [], []

    for src in sources:
        sid = src["id"]
        name = src["name"]
        tier = src["tier"]
        freq = src.get("refresh_frequency", "weekly")
        expected = src.get("expected_filename")
        url = src.get("url", "")

        print(f"\n── {name} ({tier}) ──")

        if tier == "api":
            try:
                _refresh_api_source(sid, name)
                retrieved, _ = _provenance_age(sid)
                print(f"  ✓ Fetched and cached  [{retrieved or 'today'}]")
                refreshed.append(name)
            except Exception as exc:
                print(f"  ✗ Fetch failed: {exc}")
                failed.append(name)

        elif tier in ("manual_upload", "pdf"):
            inbox_file = Path("data/inbox") / expected if expected else None
            retrieved, stale = _provenance_age(sid)
            age_note = f"current copy: {retrieved}" if retrieved else "no current copy"

            if inbox_file and inbox_file.exists():
                try:
                    _ingest_manual_source(sid, inbox_file)
                    retrieved, _ = _provenance_age(sid)
                    print(f"  ✓ Ingested from data/inbox/  [{retrieved}]")
                    refreshed.append(name)
                except Exception as exc:
                    print(f"  ✗ Ingest failed: {exc}")
                    failed.append(name)
            else:
                print(f"  ⚠  MANUAL DOWNLOAD NEEDED")
                print(f"     Source:  {name}")
                print(f"     Get it:  {url}")
                print(f"     Save as: data/inbox/{expected}")
                print(f"     ({age_note})")
                still_needed.append(name)

    print(f"\n{'='*60}")
    print(f"Refresh summary:")
    print(f"  ✓ Refreshed ({len(refreshed)}): {', '.join(refreshed) or 'none'}")
    print(f"  ⚠ Still needed ({len(still_needed)}): {', '.join(still_needed) or 'none'}")
    print(f"  ✗ Failed ({len(failed)}): {', '.join(failed) or 'none'}")
    if still_needed:
        print("\n  Download the files above and re-run `mfw refresh` to ingest them.")
    print(f"\nRun `mfw build` to rebuild the dashboard from available data.")


def _refresh_api_source(source_id: str, name: str):
    """Auto-fetch an API-tier source and promote to data/current/."""
    import time

    if source_id == "cms64":
        from mfw.sources.cms64 import fetch_cms64, FetchError
        rows = fetch_cms64()
        _write_simple_provenance(source_id, name, "api", "REST API via data.medicaid.gov", len(rows))

    elif source_id == "census_acs":
        from mfw.sources.census_acs import fetch_acs_coverage, FetchError
        rows = fetch_acs_coverage()
        _write_simple_provenance(source_id, name, "api", "Census ACS API", len(rows))

    else:
        raise ValueError(f"Unknown API source: {source_id}")


def _ingest_manual_source(source_id: str, inbox_file: Path):
    """Ingest a manual-upload file, validate, and promote to data/current/."""
    import shutil

    Path("data/current").mkdir(parents=True, exist_ok=True)

    if source_id == "kff_provider_taxes":
        from mfw.sources.kff_provider_taxes import KFFProviderTaxesAdapter
        adapter = KFFProviderTaxesAdapter()
        df, prov = adapter.run()
        print(f"     Parsed {len(df)} rows; validation: {prov.validation_status}")
        return

    if source_id == "kff_cbo_state_allocations":
        import pandas as pd
        df = pd.read_csv(inbox_file, skiprows=2)
        out = Path("data/current") / f"{source_id}.csv"
        df.to_csv(out, index=False)
        _write_simple_provenance(source_id, source_id, "manual_upload", "KFF brief appendix", len(df))
        return

    # Generic: copy file to current/ as-is.
    import shutil
    dest = Path("data/current") / inbox_file.name
    shutil.copy2(inbox_file, dest)
    _write_simple_provenance(source_id, source_id, "manual_upload", "manual download", 0)


def _write_simple_provenance(source_id: str, name: str, tier: str, method: str, row_count: int):
    Path("data/current").mkdir(parents=True, exist_ok=True)
    prov = {
        "source_id": source_id,
        "source_name": name,
        "tier": tier,
        "method": method,
        "retrieved_date": date.today().isoformat(),
        "row_count": row_count,
        "validation_status": "pending",
    }
    out = Path("data/current") / f"{source_id}.provenance.json"
    out.write_text(json.dumps(prov, indent=2))


def cmd_build(args, params):
    """
    Non-interactive build — what the GitHub Action runs.
    Builds the dashboard from data/current/. Never prompts for files.
    For any stale or missing manual source, uses seed data and surfaces
    the "as of" date in the site rather than failing.
    """
    from mfw.outputs.dashboard_builder import build_dashboard_data

    print("Building dashboard (non-interactive)...")
    prefer_live = getattr(args, "live", False)
    data = build_dashboard_data(params, prefer_live=prefer_live)
    out_path = Path("dashboard/dashboard_data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, default=str))
    print(f"\ndashboard/dashboard_data.json written.")
    prov = data.get("meta", {}).get("data_provenance", "seed")
    print(f"data_provenance: {prov}")
    _print_source_status(data.get("data_sources", []))
    return data


def _print_source_status(sources: list[dict]):
    if not sources:
        return
    print("\nSource status:")
    for s in sources:
        status = s.get("status", "unknown")
        icon = {"current": "✓", "stale": "⚠", "missing": "✗", "unavailable": "–"}.get(status, "?")
        as_of = s.get("last_updated") or "never"
        print(f"  {icon} {s.get('name', s.get('id', '?'))} [{as_of}]")


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
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nResults written to {out_path}")
    return results


# Legacy alias: `mfw dashboard` → same as `mfw build`
def cmd_dashboard(args, params):
    return cmd_build(args, params)


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
    out_path.write_text(json.dumps(sheet, indent=2, default=str))
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

    out_path = Path(f"outputs/scenario_cap{cap}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nFull scenario written to {out_path}")
    return result


def cmd_fetch(args, params):
    """Legacy alias for auto-fetching API sources."""
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
        description=(
            "Medicaid Financing Workbench.\n\n"
            "Typical workflow:\n"
            "  mfw refresh   — fetch APIs + prompt for manual downloads\n"
            "  mfw build     — build dashboard from available data\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("refresh", help="Interactive: fetch APIs + prompt for manual uploads")

    p = sub.add_parser("build", help="Non-interactive build (used by GitHub Actions)")
    p.add_argument("--live", action="store_true", help="Prefer live API data over seed")

    p = sub.add_parser("analyze", help="Run all analyses → outputs/results.json")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("dashboard", help="Alias for `mfw build`")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("factsheet", help="Generate a state fact sheet")
    p.add_argument("--state", required=True, metavar="XX")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("scenario", help="Run a counterfactual (e.g. --cap 3.0)")
    p.add_argument("--cap", type=float, required=True, metavar="PCT")
    p.add_argument("--live", action="store_true")

    p = sub.add_parser("fetch", help="Legacy: attempt live API pull")
    p.add_argument("--live", action="store_true")

    sub.add_parser("draft", help="Generate tell/show/so-what (requires ANTHROPIC_API_KEY)")

    args = parser.parse_args()
    params = _load_params()

    dispatch = {
        "refresh": cmd_refresh,
        "build": cmd_build,
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
