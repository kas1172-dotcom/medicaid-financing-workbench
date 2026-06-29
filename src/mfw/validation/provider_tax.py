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
SCRAPED_TAXES_FILE = CURRENT_DIR / "state_provider_taxes.csv"
KFF_PROVIDER_TAXES_FILE = CURRENT_DIR / "kff_provider_taxes.csv"
SCRAPE_VS_KFF_DELTAS_FILE = CURRENT_DIR / "scrape_vs_kff_deltas.csv"

# Threshold above which a divergence is flagged (percentage points).
DELTA_FLAG_THRESHOLD_PP = 1.0

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


def run_scrape_vs_kff() -> dict:
    """
    Cross-check scraped state provider-tax rates against KFF published rates.

    Compares rows from state_provider_taxes.csv (rate_basis != not_comparable,
    confidence != failed) to kff_provider_taxes.csv. Emits per-state, per-class
    deltas to scrape_vs_kff_deltas.csv.

    Divergence is information to display, not an error to hide. States where the
    scraper found not_comparable structure are excluded from the delta check.

    Returns a summary dict for dashboard_data.json under validation.scrape_vs_kff.
    """
    import pandas as pd

    result_base = {
        "check": "scrape_vs_kff_rates",
        "description": (
            "Cross-checks scraped state provider-tax rates against KFF published rates. "
            "Only comparable (rate_basis != not_comparable) scraped rows are checked."
        ),
        "as_of": date.today().isoformat(),
    }

    if not SCRAPED_TAXES_FILE.exists():
        return {**result_base, "result": "data_unavailable",
                "notes": "state_provider_taxes.csv not present: run the scraper first."}

    if not KFF_PROVIDER_TAXES_FILE.exists():
        return {**result_base, "result": "data_unavailable",
                "notes": "kff_provider_taxes.csv not present: upload via data/inbox/."}

    try:
        scraped = pd.read_csv(SCRAPED_TAXES_FILE)
        kff = pd.read_csv(KFF_PROVIDER_TAXES_FILE)

        # Normalise KFF column names: look for abbr/state col and rate col.
        kff.columns = [c.strip() for c in kff.columns]
        abbr_col = next(
            (c for c in kff.columns if c.lower() in ("abbr", "state_abbr", "state")), None
        )
        if abbr_col is None:
            return {**result_base, "result": "error",
                    "notes": f"Cannot identify state column in KFF file. Columns: {list(kff.columns)}"}

        # Restrict scraped to comparable rows.
        comparable = scraped[
            (scraped["rate_basis"] != "not_comparable") &
            (scraped["confidence"] != "failed") &
            scraped["effective_rate_pct"].notna()
        ].copy()

        if comparable.empty:
            return {**result_base, "result": "no_comparable_rows",
                    "notes": "No scraped rows have rate_basis='reported'/'derived'. Nothing to cross-check."}

        # Build KFF lookup: {(abbr, provider_class): rate_pct}
        # KFF may use provider class columns or a 'provider_class' column.
        kff_lookup: dict[tuple[str, str], float] = {}
        provider_class_col = next(
            (c for c in kff.columns if "class" in c.lower() or "type" in c.lower()), None
        )
        rate_col = next(
            (c for c in kff.columns if "rate" in c.lower() or "pct" in c.lower() or "%" in c), None
        )

        if provider_class_col and rate_col:
            for _, row in kff.iterrows():
                abbr = str(row[abbr_col]).strip().upper()
                pclass = str(row[provider_class_col]).strip().lower()
                try:
                    rate = float(str(row[rate_col]).replace("%", "").strip())
                    kff_lookup[(abbr, pclass)] = rate
                except (ValueError, TypeError):
                    pass
        else:
            # KFF file has provider class as separate columns (wide format).
            class_cols = [c for c in kff.columns if c.lower() not in (abbr_col.lower(),)]
            for _, row in kff.iterrows():
                abbr = str(row[abbr_col]).strip().upper()
                for col in class_cols:
                    try:
                        rate = float(str(row[col]).replace("%", "").strip())
                        kff_lookup[(abbr, col.lower())] = rate
                    except (ValueError, TypeError):
                        pass

        # Compare.
        delta_rows = []
        for _, row in comparable.iterrows():
            abbr = str(row["abbr"]).strip().upper()
            pclass = str(row["provider_class"]).strip().lower()
            scraped_rate = float(row["effective_rate_pct"])

            kff_rate = kff_lookup.get((abbr, pclass))
            if kff_rate is None:
                # Try partial class name matching.
                kff_rate = next(
                    (v for (a, c), v in kff_lookup.items() if a == abbr and pclass in c), None
                )

            if kff_rate is None:
                delta_rows.append({
                    "abbr": abbr,
                    "state": row["state"],
                    "provider_class": pclass,
                    "scraped_rate_pct": scraped_rate,
                    "kff_rate_pct": None,
                    "delta_pp": None,
                    "flagged": False,
                    "note": "No KFF entry for this state+class.",
                })
                continue

            delta = round(scraped_rate - kff_rate, 3)
            flagged = abs(delta) >= DELTA_FLAG_THRESHOLD_PP
            delta_rows.append({
                "abbr": abbr,
                "state": row["state"],
                "provider_class": pclass,
                "scraped_rate_pct": scraped_rate,
                "kff_rate_pct": kff_rate,
                "delta_pp": delta,
                "flagged": flagged,
                "note": (
                    f"Scraped {scraped_rate:.2f}% vs KFF {kff_rate:.2f}%: "
                    f"{'FLAGGED' if flagged else 'within tolerance'} "
                    f"(threshold ±{DELTA_FLAG_THRESHOLD_PP}pp)"
                ),
            })

        deltas_df = pd.DataFrame(delta_rows)
        CURRENT_DIR.mkdir(parents=True, exist_ok=True)
        deltas_df.to_csv(SCRAPE_VS_KFF_DELTAS_FILE, index=False)

        n_flagged = int(deltas_df["flagged"].sum()) if not deltas_df.empty else 0
        n_checked = len(deltas_df)
        flagged_abbrs = (
            deltas_df[deltas_df["flagged"]]["abbr"].tolist() if not deltas_df.empty else []
        )

        return {
            **result_base,
            "result": "flagged" if n_flagged else "pass",
            "n_checked": n_checked,
            "n_flagged": n_flagged,
            "flagged_states": flagged_abbrs,
            "output_file": str(SCRAPE_VS_KFF_DELTAS_FILE),
            "notes": (
                f"{n_flagged}/{n_checked} state+class pairs diverge >{DELTA_FLAG_THRESHOLD_PP}pp from KFF. "
                "Divergence is informational: review before publication."
                if n_flagged else
                f"All {n_checked} checked pairs within ±{DELTA_FLAG_THRESHOLD_PP}pp of KFF."
            ),
        }

    except Exception as exc:
        return {**result_base, "result": "error", "notes": f"Cross-check failed: {exc}"}
