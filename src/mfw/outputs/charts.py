"""Chart generation — one function per analysis, deterministic output paths."""

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
    """Horizontal bar chart — provider-tax at-risk revenue, top exposed states."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in result["rows"] if r["exposed"]][:15]
    if not rows:
        return _empty_chart(out_dir / "provider_tax_gap.png", "No exposed states")

    states = [r["abbr"] for r in rows]
    gaps = [r["final_gap_millions"] for r in rows]
    max_gap = max(gaps) if gaps else 1

    fig, ax = plt.subplots(figsize=(8, max(4, len(states) * 0.5)))
    ax.barh(states[::-1], gaps[::-1], color=ACCENT, edgecolor="none")
    ax.set_xlabel("At-risk revenue ($M, final year of phase-down)")
    ax.set_title("Provider Tax Cap — At-Risk Revenue by State\n(expansion states above 3.5% ceiling)",
                 fontsize=11, fontweight="bold")
    ax.set_xlim(0, max_gap * 1.18)
    for bar, val in zip(ax.patches, gaps[::-1]):
        ax.text(bar.get_width() + max_gap * 0.012, bar.get_y() + bar.get_height() / 2,
                f"${val:,.0f}M", va="center", fontsize=8)
    _provenance_note(ax, result["data_provenance"])
    plt.tight_layout()
    out = out_dir / "provider_tax_gap.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out


def chart_hcbs_index(result: dict, out_dir: Path = CHARTS_DIR) -> Path:
    """Horizontal bar chart — HCBS vulnerability index, top 20 states, color by tier."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = result["rows"][:20]

    states = [r["abbr"] for r in rows]
    scores = [r["hcbs_index"] for r in rows]
    colors = [TIER_COLORS[r["risk_tier"]] for r in rows]

    fig, ax = plt.subplots(figsize=(8, max(5, len(states) * 0.5)))
    ax.barh(states[::-1], scores[::-1], color=colors[::-1], edgecolor="none")
    ax.set_xlabel("HCBS Vulnerability Index (0–10)")
    ax.set_title("HCBS Vulnerability Index — Top 20 States\n(risk screen, not a forecast)",
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
    """Horizontal bar chart — modeled procedural coverage loss by state."""
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
        "Work Requirements — Modeled Coverage Loss by State\n"
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
    """Scatter — dual enrollment share vs. estimated dual spending share by state."""
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
