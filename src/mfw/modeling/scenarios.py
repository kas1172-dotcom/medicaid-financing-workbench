"""
Scenario engine — counterfactuals without rewriting analyses.

The analyst asks "what if 25 states had to cut to exactly 3.5% by 2030?" or
"what if the churn rate is really 25%, not 18%?" by passing parameter overrides.
Every analysis re-runs against the modified parameters and the deltas are
reported. This is the time-saver: explore a policy space in seconds, then spend
the saved time on the "so what."
"""

from __future__ import annotations

import copy

import pandas as pd

from ..analysis import provider_tax, hcbs_risk, work_requirements, duals

_ANALYSES = {
    "provider_tax": provider_tax,
    "hcbs_risk": hcbs_risk,
    "work_requirements": work_requirements,
    "duals": duals,
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def run_scenario(df: pd.DataFrame, base_params: dict, overrides: dict) -> dict:
    """Run all analyses under base and overridden params; return both + deltas."""
    scen_params = _deep_merge(base_params, overrides)
    base_out, scen_out = {}, {}
    for name, mod in _ANALYSES.items():
        base_out[name] = mod.run(df, base_params)
        scen_out[name] = mod.run(df, scen_params)

    base_pt = base_out["provider_tax"]
    scen_pt = scen_out["provider_tax"]

    # Dollar gap delta (Tier-2 exposed states, revenue requiring replacement).
    gap_delta_b = round(
        scen_pt["national_final_gap_billion"] - base_pt["national_final_gap_billion"], 2
    )

    # Per-state replacement dollars at scenario cap vs base cap.
    base_gaps = {r["abbr"]: r["final_gap_millions"] for r in base_pt.get("rows", [])}
    scen_gaps = {r["abbr"]: r["final_gap_millions"] for r in scen_pt.get("rows", [])}
    state_deltas = [
        {
            "abbr": abbr,
            "base_gap_millions": base_gaps.get(abbr, 0.0),
            "scenario_gap_millions": scen_gaps.get(abbr, 0.0),
            "replacement_dollars_delta": round(
                scen_gaps.get(abbr, 0.0) - base_gaps.get(abbr, 0.0), 1
            ),
        }
        for abbr in set(list(base_gaps) + list(scen_gaps))
        if scen_gaps.get(abbr, 0.0) != base_gaps.get(abbr, 0.0)
    ]
    state_deltas.sort(key=lambda x: -abs(x["replacement_dollars_delta"]))

    deltas = {
        "provider_tax_national_gap_billion": gap_delta_b,
        "provider_tax_state_deltas": state_deltas,
        "work_req_national_loss": (
            scen_out["work_requirements"]["national_modeled_loss"]
            - base_out["work_requirements"]["national_modeled_loss"]
        ),
    }
    return {"overrides": overrides, "base": base_out, "scenario": scen_out, "deltas": deltas}
