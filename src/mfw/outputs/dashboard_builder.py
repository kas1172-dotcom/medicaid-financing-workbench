"""Assembles dashboard/dashboard_data.json for the static front-end."""

from __future__ import annotations

from pathlib import Path

import yaml

from mfw.etl.panel import build_panel, panel_summary
from mfw.analysis import provider_tax, hcbs_risk, work_requirements, duals
from mfw.outputs.charts import (
    chart_provider_tax_gap,
    chart_work_req_loss,
)
from mfw.llm.draft import draft


def _load_data_sources() -> list[dict]:
    for candidate in [Path("config/data_sources.yaml"), Path(__file__).parents[3] / "config/data_sources.yaml"]:
        if candidate.exists():
            raw = yaml.safe_load(candidate.read_text())
            return raw.get("sources", [])
    return []


def _source_status(source_id: str) -> dict:
    """Return status dict for one source from data/current/ provenance sidecar."""
    import json
    prov_path = Path("data/current") / f"{source_id}.provenance.json"
    if not prov_path.exists():
        return {"status": "missing", "last_updated": None}
    try:
        prov = json.loads(prov_path.read_text())
        return {
            "status": "current",
            "last_updated": prov.get("retrieved_date"),
            "row_count": prov.get("row_count"),
            "validation_status": prov.get("validation_status", "pending"),
        }
    except Exception:
        return {"status": "unavailable", "last_updated": None}


def _build_sources_manifest(sources: list[dict]) -> list[dict]:
    """Combine manifest entries with live status from data/current/."""
    result = []
    for src in sources:
        sid = src["id"]
        status = _source_status(sid)
        result.append({
            "id": sid,
            "name": src["name"],
            "tier": src["tier"],
            "method": src.get("method", ""),
            "url": src.get("url", ""),
            "expected_filename": src.get("expected_filename"),
            "refresh_frequency": src.get("refresh_frequency", ""),
            "validate_against": src.get("validate_against"),
            "description": src.get("description", "").strip(),
            **status,
        })
    return result


_SCAFFOLD_TABS = {
    "hcbs": {
        "id": "hcbs",
        "label": "Home & Community-Based Services",
        "status": "in_progress",
        "analytical_question": (
            "HCBS is an optional Medicaid benefit with no federal floor. "
            "As the reconciliation law squeezes state financing, which states' "
            "HCBS programs are most at risk, and what would cuts mean for people "
            "who rely on home care to remain in the community?"
        ),
        "method": (
            "A composite 0-10 vulnerability index combining: (1) HCBS share of total "
            "Medicaid spending (stakes); (2) reliance on the now-capped provider-tax "
            "financing (exposure); (3) projected per-enrollee federal cut; (4) nonfederal "
            "share strain. Each component normalized 0-1 before weighting. Tier thresholds: "
            "High ≥6.5, Medium ≥4.0, Low <4.0. This is a risk screen, not a forecast of cuts."
        ),
        "data_source": (
            "CMS-64 T-19 HCBS expenditure data (CMS Medicaid Financial Management Data); "
            "CMS HCBS waiver enrollment (1915(c) and 1115); "
            "KFF HCBS spending and enrollment tables."
        ),
        "source_url": "https://www.medicaid.gov/medicaid/home-community-based-services/index.html",
        "why_in_progress": (
            "The index method is designed and ready. The state-level HCBS spending "
            "data from CMS-64 T-19 has not yet been ingested (it requires a manual "
            "download of the T-19 expenditure report). Once ingested, this tab will "
            "display a ranked table and chart identical in format to the Financing tab."
        ),
    },
    "managed_care": {
        "id": "managed_care",
        "label": "Managed Care",
        "status": "in_progress",
        "analytical_question": (
            "More than two-thirds of Medicaid enrollees are in managed care plans. "
            "How do the reconciliation law's financing changes interact with managed care "
            "contracts, MCO taxes, and capitation rates — and what does that mean for "
            "plan participation and enrollee access?"
        ),
        "method": (
            "Analysis will combine: (1) MCO tax exposure — states with MCO provider taxes "
            "above 3.5% face the same hold-harmless cap as hospital taxes; (2) managed care "
            "penetration rate by state; (3) capitation rate adequacy — whether per-member "
            "per-month payments remain viable after the financing change. "
            "Source: CMS managed care enrollment report + state contract actuarial filings."
        ),
        "data_source": (
            "CMS Medicaid Managed Care Enrollment Report (annual, CMS.gov); "
            "State Medicaid managed care contract rates (state-level, requires manual collection)."
        ),
        "source_url": "https://www.medicaid.gov/medicaid/managed-care/enrollment/report/index.html",
        "why_in_progress": (
            "The managed care enrollment data requires a manual download of the CMS annual "
            "report. The capitation rate analysis requires state-level contract data that "
            "is collected by KFF but not yet available in a consolidated API."
        ),
    },
    "dual_eligibles": {
        "id": "dual_eligibles",
        "label": "Dual Eligibles",
        "status": "in_progress",
        "analytical_question": (
            "Dual eligibles — people enrolled in both Medicare and Medicaid — are a small "
            "share of Medicaid enrollment but account for 40-50% of spending in many states. "
            "Where is that concentration sharpest, and what do Medicaid financing cuts mean "
            "for people at the Medicare-Medicaid seam?"
        ),
        "method": (
            "Dual enrollment share = duals ÷ total enrollment. "
            "Spending share estimated by applying a 3× per-capita cost multiple "
            "(a documented published approximation reflecting duals' LTSS, HCBS, and "
            "complex-care utilization). Concentration ratio = spending share ÷ enrollment share. "
            "States above the 1:1 line in a scatter of enrollment vs. spending share "
            "carry disproportionate fiscal exposure when Medicaid is cut."
        ),
        "data_source": (
            "CMS Medicaid managed care enrollment data (duals component); "
            "KFF, 'Medicaid's Role for Dual Eligible Beneficiaries' (2024); "
            "MedPAC and KFF for the 3× cost multiple."
        ),
        "source_url": "https://www.kff.org/medicaid/issue-brief/medicaids-role-for-dual-eligible-beneficiaries/",
        "why_in_progress": (
            "The method and data sources are identified. The dual-eligible enrollment data "
            "by state requires ingestion from the CMS managed care enrollment report "
            "(same file as the Managed Care tab). Both tabs will be completed together "
            "once that file is ingested."
        ),
    },
}


def build_dashboard_data(params: dict, prefer_live: bool = False) -> dict:
    df = build_panel(prefer_live=prefer_live)
    summary = panel_summary(df)

    print("  Running financing analyses...")
    pt_result = provider_tax.run(df, params)
    wr_result = work_requirements.run(df, params)
    print(f"    ✓ {pt_result['title']} — provenance={pt_result['data_provenance']}")
    print(f"    ✓ {wr_result['title']} — provenance={wr_result['data_provenance']}")

    print("  Generating charts...")
    charts = {}
    for name, fn, result in [
        ("provider_tax", chart_provider_tax_gap, pt_result),
        ("work_requirements", chart_work_req_loss, wr_result),
    ]:
        try:
            charts[name] = str(fn(result))
            print(f"    ✓ {charts[name]}")
        except Exception as exc:
            charts[name] = None
            print(f"    [warn] chart for {name} failed: {exc}")

    print("  Loading narrative...")
    narrative = {}
    for analysis_id, result in [("provider_tax", pt_result), ("work_requirements", wr_result)]:
        narrative[analysis_id] = draft(analysis_id, result)
        src = narrative[analysis_id].get("_source", "llm")
        print(f"    ✓ {analysis_id} — source={src}")

    print("  Building data sources manifest...")
    raw_sources = _load_data_sources()
    data_sources = _build_sources_manifest(raw_sources)

    print("  Running validation...")
    from mfw.validation import provider_tax as pt_validation
    validation = {
        "provider_tax_ranking": pt_validation.run(pt_result),
    }
    print(f"    ✓ provider_tax_ranking — {validation['provider_tax_ranking'].get('result', 'unknown')}")

    is_seed = summary["data_provenance"] == "seed"
    prov_comp = pt_result.get("provenance_composition", "")
    n_t1 = sum(1 for r in pt_result.get("rows", []) if r.get("dependence_share_pct") is not None)
    n_t2 = pt_result.get("n_exposed", 0)
    n_t3 = (
        pt_result.get("n_waiver_risk", 0)
        + pt_result.get("n_unquantified", 0)
        + len(pt_result.get("tier3_no_tax", []))
    )
    return {
        "meta": {
            "generated_by": "Medicaid Financing Workbench v0.3.0",
            "data_provenance": summary["data_provenance"],
            "provenance_composition": prov_comp,
            "n_tier1_with_dependence": n_t1,
            "n_tier2_exposed": n_t2,
            "n_tier3_outliers": n_t3,
            "n_exposed": n_t2,
            "n_waiver_risk": pt_result.get("n_waiver_risk"),
            "n_unquantified": pt_result.get("n_unquantified"),
            "national_gap_billion": pt_result.get("national_final_gap_billion"),
            "provenance_note": (
                "SEED DATA — illustrative values anchored to KFF-published magnitudes. "
                "Run `mfw refresh` then `mfw build` for authoritative CMS data. "
                "Do not cite these figures as official."
            ) if is_seed else (
                f"Live data from state scrapers + CMS. Provenance: {prov_comp}."
            ),
        },
        "summary": summary,
        "analyses": {
            "provider_tax": pt_result,
            "work_requirements": wr_result,
        },
        "narrative": narrative,
        "charts": charts,
        "scaffold": _SCAFFOLD_TABS,
        "data_sources": data_sources,
        "validation": validation,
    }
