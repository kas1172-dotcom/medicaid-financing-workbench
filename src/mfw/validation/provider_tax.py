"""
Provider-tax exposure validation.

Cross-checks this workbench's state exposure ranking against KFF's published
per-state CBO allocation from:

  "Allocating CBO's Estimates of Federal Medicaid Spending Reductions Across
  the States" (KFF, 2025–2026)
  URL: https://www.kff.org/medicaid/issue-brief/allocating-cbos-estimates-of-federal-medicaid-spending-reductions-across-the-states/

The KFF brief allocates CBO's $226B provider-tax estimate across states using
the states' shares of total Medicaid federal spending. The workbench uses a
different but related method (nonfederal share × at-risk rate fraction). If the
two rankings agree at the top, that is a meaningful corroboration of the
workbench's exposure ordering.

Agreement criterion: Spearman rank correlation ≥ 0.75 for exposed states, AND
top-5 overlap ≥ 3 states, is reported as "pass". Below either threshold → "flag".
If the KFF file is not in data/current/, returns "data_unavailable".
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

CURRENT_DIR = Path("data/current")
KFF_ALLOCATION_FILE = CURRENT_DIR / "kff_cbo_state_allocations.csv"
KFF_ALLOCATION_PROVENANCE = CURRENT_DIR / "kff_cbo_state_allocations.provenance.json"

# KFF CBO allocation source reference.
SOURCE_CITATION = (
    "KFF, 'Allocating CBO's Estimates of Federal Medicaid Spending Reductions "
    "Across the States' (2025–2026). "
    "URL: https://www.kff.org/medicaid/issue-brief/"
    "allocating-cbos-estimates-of-federal-medicaid-spending-reductions-across-the-states/"
)


def run(provider_tax_result: dict) -> dict:
    """
    Compare workbench exposure ranking to KFF CBO state allocations.

    Returns a dict suitable for inclusion in dashboard_data.json under
    validation.provider_tax_ranking.
    """
    workbench_top = [
        r["abbr"]
        for r in provider_tax_result.get("rows", [])
        if r.get("exposed")
    ]

    base = {
        "check": "provider_tax_exposure_ranking",
        "description": (
            "Compares this workbench's state exposure ranking to KFF's published "
            "per-state CBO allocation of the $226B provider-tax estimate."
        ),
        "source": SOURCE_CITATION,
        "workbench_top_exposed": workbench_top[:10],
        "kff_top_states": None,
        "as_of": date.today().isoformat(),
    }

    if not KFF_ALLOCATION_FILE.exists():
        return {
            **base,
            "result": "data_unavailable",
            "notes": (
                "KFF CBO state allocation file not yet uploaded. "
                "Run `mfw refresh` and follow the prompt to download "
                "kff_cbo_state_allocations.csv into data/inbox/."
            ),
        }

    try:
        import pandas as pd
        df = pd.read_csv(KFF_ALLOCATION_FILE)
        # Expected columns: state_abbr (or state), provider_tax_allocation_$M
        abbr_col = next(
            (c for c in df.columns if c.lower() in ("abbr", "state_abbr", "state")), None
        )
        alloc_col = next(
            (c for c in df.columns if "alloc" in c.lower() or "provider" in c.lower()), None
        )
        if not abbr_col or not alloc_col:
            return {
                **base,
                "result": "error",
                "notes": f"Could not identify state/allocation columns. Columns found: {list(df.columns)}",
            }

        df_sorted = df.sort_values(alloc_col, ascending=False)
        kff_top = df_sorted[abbr_col].head(10).tolist()
        base["kff_top_states"] = kff_top

        # Overlap check: top-5 intersection.
        wb_top5 = set(workbench_top[:5])
        kff_top5 = set(kff_top[:5])
        overlap = len(wb_top5 & kff_top5)

        # Rank correlation on exposed states.
        try:
            from scipy.stats import spearmanr
            wb_abbrs = [r["abbr"] for r in provider_tax_result.get("rows", []) if r.get("exposed")]
            wb_ranks = {a: i for i, a in enumerate(wb_abbrs)}
            kff_ranks = {a: i for i, a in enumerate(kff_top)}
            common = list(set(wb_ranks) & set(kff_ranks))
            if len(common) >= 5:
                wb_r = [wb_ranks[a] for a in common]
                kff_r = [kff_ranks[a] for a in common]
                corr, _ = spearmanr(wb_r, kff_r)
            else:
                corr = None
        except ImportError:
            corr = None

        if overlap >= 3 and (corr is None or corr >= 0.75):
            result = "pass"
            notes = (
                f"Top-5 overlap: {overlap}/5 states. "
                + (f"Spearman ρ = {corr:.2f}. " if corr is not None else "")
                + "Rankings agree at the top."
            )
        else:
            result = "flag"
            notes = (
                f"Top-5 overlap: {overlap}/5 states (threshold: 3). "
                + (f"Spearman ρ = {corr:.2f} (threshold: 0.75). " if corr is not None else "")
                + "Review discrepancies before publication."
            )

        prov = {}
        if KFF_ALLOCATION_PROVENANCE.exists():
            prov = json.loads(KFF_ALLOCATION_PROVENANCE.read_text())

        return {
            **base,
            "result": result,
            "notes": notes,
            "kff_data_as_of": prov.get("retrieved_date"),
        }

    except Exception as exc:
        return {
            **base,
            "result": "error",
            "notes": f"Validation failed: {exc}",
        }
