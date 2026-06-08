"""
Analysis 1 — Provider tax cap gap.

THE QUESTION (analyst's judgment, not the tool's): the 2025 law's single biggest
financing threat to expansion states is the provider-tax ceiling phasing from
6.0% to 3.5%. Which states are most exposed, by how much, and on what timeline?

THE METHOD (this is the arithmetic the tool runs):
  A state's provider tax raises, roughly:
      revenue ~= provider_tax_rate% * net_patient_revenue_base
  We don't observe the base directly in seed mode, so we proxy the at-risk
  revenue as the share of the nonfederal share attributable to taxing above the
  target cap:
      exposed_rate_points = max(0, provider_tax_rate - target_cap)
      gap = nonfederal_share * (exposed_rate_points / provider_tax_rate)
  i.e. the fraction of current provider-tax-supported financing that sits above
  the 3.5% line and must be replaced or cut.

  The phase-down walks the ceiling down 0.5pp/year from 2028 to 2032, so the gap
  opens gradually; we report the gap at each year.

Only EXPANSION states are subject to the reduced cap; non-expansion states keep
the 6% ceiling, so their exposure to THIS provision is zero (flagged explicitly).
"""

from __future__ import annotations

import pandas as pd


def run(df: pd.DataFrame, params: dict) -> dict:
    pt = params["provider_tax"]
    target = pt["target_cap_pct"]
    start, end, step = pt["phasedown_start_year"], pt["phasedown_end_year"], pt["phasedown_step_pct_per_year"]
    current = pt["current_cap_pct"]

    # Ceiling schedule by year (6.0 -> 3.5 in 0.5 steps).
    schedule = {}
    cap = current
    for yr in range(start, end + 1):
        cap = max(target, round(cap - step, 2))
        schedule[yr] = cap

    rows = []
    for _, r in df.iterrows():
        rate = r["provider_tax_rate"]
        exposed = (
            r["expansion"]
            and rate > target
            and rate > 0
        )
        if exposed:
            # Final-year gap (cap fully phased to target).
            final_points = max(0.0, rate - target)
            final_gap = r["nonfederal_share"] * (final_points / rate)
            # Year-by-year gap as the ceiling steps down.
            by_year = {}
            for yr, yr_cap in schedule.items():
                pts = max(0.0, rate - yr_cap)
                by_year[yr] = round(r["nonfederal_share"] * (pts / rate), 1)
            gap_share_of_nonfed = round(100 * final_gap / r["nonfederal_share"], 1)
        else:
            final_gap = 0.0
            by_year = {yr: 0.0 for yr in schedule}
            gap_share_of_nonfed = 0.0

        rows.append({
            "state": r["state"],
            "abbr": r["abbr"],
            "expansion": bool(r["expansion"]),
            "provider_tax_rate": rate,
            "exposed": bool(exposed),
            "final_gap_millions": round(final_gap, 1),
            "gap_share_of_nonfederal_pct": gap_share_of_nonfed,
            "gap_by_year": by_year,
        })

    rows.sort(key=lambda x: x["final_gap_millions"], reverse=True)
    exposed_rows = [x for x in rows if x["exposed"]]

    national_gap = round(sum(x["final_gap_millions"] for x in rows) / 1000, 2)  # $B

    return {
        "id": "provider_tax",
        "title": "Provider tax cap exposure",
        "schedule": schedule,
        "rows": rows,
        "n_exposed": len(exposed_rows),
        "national_final_gap_billion": national_gap,
        "top_state": exposed_rows[0]["state"] if exposed_rows else None,
        "data_provenance": df["data_provenance"].iloc[0],
    }
