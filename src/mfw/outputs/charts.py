"""Chart generation: one function per analysis, deterministic output paths."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

CHARTS_DIR = Path("outputs/charts")
TIER_COLORS = {"High": "#c0392b", "Medium": "#e67e22", "Low": "#27ae60"}
ACCENT = "#0D8F82"


def _provenance_note(ax, provenance: str) -> None:
    ax.annotate(
        f"Data provenance: {provenance}  |  Medicaid Financing Workbench",
        xy=(0.01, 0.005), xycoords="figure fraction", fontsize=6, color="#888888",
    )


def chart_provider_tax_gap(result: dict, out_dir: Path = CHARTS_DIR) -> Path:
    """
    Two-panel chart: Tier-1 dependence ranking (top 20) with Tier-2 gap overlay.

    Left panel: budget-dependence share (%) for states with available data,
    sorted descending. States with Tier-2 rate exposure shown in a darker shade.
    Right panel: Tier-2 at-risk revenue ($M) for exposed states.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Tier 1: dependence ranking
    t1_rows = [
        r for r in result.get("tier1_ranked", result.get("rows", []))
        if r.get("dependence_share_pct") is not None
    ][:20]

    # Tier 2: gap rows
    t2_rows = [r for r in result.get("tier2_exposed", []) if r.get("final_gap_millions", 0) > 0][:15]

    if not t1_rows and not t2_rows:
        return _empty_chart(out_dir / "provider_tax_gap.png", "Insufficient data")

    fig, axes = plt.subplots(1, 2, figsize=(14, max(5, max(len(t1_rows), len(t2_rows)) * 0.45 + 1)))

    # ── Left panel: Tier-1 dependence ────────────────────────────────
    ax1 = axes[0]
    if t1_rows:
        abbrs = [r["abbr"] for r in t1_rows]
        dep_pcts = [r["dependence_share_pct"] for r in t1_rows]
        colors = [
            "#0a5e56" if r.get("exposed") else (
                "#e8a820" if r.get("tier") == 3 else ACCENT
            )
            for r in t1_rows
        ]
        ax1.barh(abbrs[::-1], dep_pcts[::-1], color=colors[::-1], edgecolor="none")
        ax1.axvline(18, color="#666", linestyle="--", linewidth=0.8, alpha=0.6)
        ax1.text(18.5, 0, "18% KFF\nmedian", fontsize=7, color="#666", va="bottom")
        ax1.set_xlabel("Provider tax dependence (% of nonfederal share)")
        ax1.set_title(
            "High provider-tax dependence creates\nfinancing risk for 31+ states",
            fontsize=10, fontweight="bold",
        )
        # Legend patches
        patches = [
            mpatches.Patch(color="#0a5e56", label="Tier 2: rate above 3.5%"),
            mpatches.Patch(color=ACCENT,    label="Tier 1: dependence only"),
            mpatches.Patch(color="#e8a820", label="Tier 3: structural outlier"),
        ]
        ax1.legend(handles=patches, fontsize=7, loc="lower right")
        _provenance_note(ax1, result["data_provenance"])
    else:
        ax1.text(0.5, 0.5, "Dependence data unavailable", ha="center", va="center",
                 transform=ax1.transAxes)
        ax1.axis("off")

    # ── Right panel: Tier-2 rate exposure ────────────────────────────
    ax2 = axes[1]
    if t2_rows:
        states2 = [r["abbr"] for r in t2_rows]
        gaps = [r["final_gap_millions"] for r in t2_rows]
        max_gap = max(gaps) if gaps else 1
        ax2.barh(states2[::-1], gaps[::-1], color="#0a5e56", edgecolor="none")
        ax2.set_xlabel("Revenue requiring replacement ($M, 2032 phase-down)")
        ax2.set_title(
            "States above the 3.5% floor face direct\nprovider-tax revenue replacement pressure",
            fontsize=10, fontweight="bold",
        )
        ax2.set_xlim(0, max_gap * 1.18)
        for bar, val in zip(ax2.patches, gaps[::-1]):
            ax2.text(
                bar.get_width() + max_gap * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"${val:,.0f}M", va="center", fontsize=8,
            )
        _provenance_note(ax2, result["data_provenance"])
    else:
        ax2.text(0.5, 0.5, "No Tier-2 exposed states", ha="center", va="center",
                 transform=ax2.transAxes)
        ax2.axis("off")

    plt.tight_layout()
    out = out_dir / "provider_tax_gap.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_hcbs_index(result: dict, out_dir: Path = CHARTS_DIR) -> Path:
    """Horizontal bar chart: HCBS vulnerability index, top 20 states, color by tier."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = result["rows"][:20]

    states = [r["abbr"] for r in rows]
    scores = [r["hcbs_index"] for r in rows]
    colors = [TIER_COLORS[r["risk_tier"]] for r in rows]

    fig, ax = plt.subplots(figsize=(8, max(5, len(states) * 0.5)))
    ax.barh(states[::-1], scores[::-1], color=colors[::-1], edgecolor="none")
    ax.set_xlabel("HCBS Vulnerability Index (0–10)")
    ax.set_title("HCBS Vulnerability Index: Top 20 States\n(risk screen, not a forecast)",
                 fontsize=11, fontweight="bold")
    ax.set_xlim(0, 10.5)
    ax.axvline(6.5, color=TIER_COLORS["High"], linestyle="--", linewidth=0.8, alpha=0.5)
    ax.axvline(4.0, color=TIER_COLORS["Medium"], linestyle="--", linewidth=0.8, alpha=0.5)
    patches = [mpatches.Patch(color=v, label=f"{k} (≥{'6.5' if k == 'High' else '4.0' if k == 'Medium' else '0'})")
               for k, v in TIER_COLORS.items()]
    ax.legend(handles=patches, loc="lower right", fontsize=8)
    _provenance_note(ax, result["data_provenance"])
    plt.tight_layout()
    out = out_dir / "hcbs_index.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_work_req_loss(result: dict, out_dir: Path = CHARTS_DIR) -> Path:
    """Horizontal bar chart: modeled procedural coverage loss by state."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = result["rows"][:15]
    if not rows:
        return _empty_chart(out_dir / "work_req_loss.png", "No expansion states")

    states = [r["abbr"] for r in rows]
    losses = [r["modeled_coverage_loss"] for r in rows]

    fig, ax = plt.subplots(figsize=(8, max(4, len(states) * 0.5)))
    ax.barh(states[::-1], losses[::-1], color="#8e44ad", edgecolor="none")
    ax.set_xlabel("Modeled coverage loss (persons, procedural/administrative)")
    ax.set_title(
        "Work Requirements: Modeled Coverage Loss by State\n"
        f"(~{result['exempt_share']*100:.0f}% already work or qualify for exemption; "
        f"loss is procedural churn, not non-work)",
        fontsize=10, fontweight="bold",
    )
    _provenance_note(ax, result["data_provenance"])
    plt.tight_layout()
    out = out_dir / "work_req_loss.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_duals_concentration(result: dict, out_dir: Path = CHARTS_DIR) -> Path:
    """Scatter: dual enrollment share vs. estimated dual spending share by state."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = result["rows"]

    x = [r["dual_enroll_share_pct"] for r in rows]
    y = [r["dual_spend_share_pct"] for r in rows]
    labels = [r["abbr"] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(x, y, color="#2c3e50", s=35, alpha=0.75, zorder=3)
    for xi, yi, lbl in zip(x, y, labels):
        if yi > 42 or xi > 24:
            ax.annotate(lbl, (xi, yi), fontsize=7, ha="left", va="bottom",
                        xytext=(3, 2), textcoords="offset points")
    lim = max(max(x), max(y)) * 1.05
    ax.plot([0, lim], [0, lim], "k--", linewidth=0.7, alpha=0.35, label="1:1 reference")
    ax.set_xlabel("Dual eligibles as % of total Medicaid enrollment")
    ax.set_ylabel("Estimated dual spending as % of total Medicaid spending")
    ax.set_title(
        "Dual-Eligible Concentration: Enrollment Share vs. Spending Share\n"
        f"(3× per-capita cost multiple applied; national dual spend share: "
        f"{result['national_dual_spend_share_pct']}%)",
        fontsize=10, fontweight="bold",
    )
    ax.legend(fontsize=8)
    _provenance_note(ax, result["data_provenance"])
    plt.tight_layout()
    out = out_dir / "duals_concentration.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def _empty_chart(path: Path, label: str) -> Path:
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, label, ha="center", va="center", transform=ax.transAxes)
    ax.axis("off")
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path
