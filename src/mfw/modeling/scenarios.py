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

    deltas = {
        "provider_tax_national_gap_billion": round(
            scen_out["provider_tax"]["national_final_gap_billion"]
            - base_out["provider_tax"]["national_final_gap_billion"], 2),
        "work_req_national_loss": (
            scen_out["work_requirements"]["national_modeled_loss"]
            - base_out["work_requirements"]["national_modeled_loss"]),
    }
    return {"overrides": overrides, "base": base_out, "scenario": scen_out, "deltas": deltas}
