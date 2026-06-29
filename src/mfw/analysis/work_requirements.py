"""
Analysis 3: Work-requirements coverage loss.

THE QUESTION: the law's largest single Medicaid saving (~$326B/10yr per CBO) comes
from work requirements. How many expansion adults are likely to LOSE coverage by
state, and, crucially, WHY?

THE METHOD, and the key analytical point: KFF's research shows most adults subject
to requirements already work or qualify for an exemption. So modeled coverage loss
is driven overwhelmingly by ADMINISTRATIVE CHURN: eligible people losing coverage
because they fail to navigate monthly reporting, not by people refusing to work.
We make that explicit by decomposing the estimate:

  subject_adults            = expansion_adults (those in the expansion group)
  already_working_or_exempt = subject_adults * already_working_or_exempt_share
  at_risk_pool              = already_working_or_exempt   (these are ELIGIBLE people)
  modeled_loss              = at_risk_pool * administrative_churn_rate

The churn rate is calibrated against the documented Arkansas experience (~18,000
losses) and Georgia's low-enrollment Pathways model. The output reports loss as
"procedural / administrative," never as "failure to work": that framing is the
finding.
"""

from __future__ import annotations

import pandas as pd

from ..sources import seed


def run(df: pd.DataFrame, params: dict) -> dict:
    wr = params["work_requirements"]
    exempt_share = wr["already_working_or_exempt_share"]
    churn = wr["administrative_churn_rate"]

    rows = []
    for _, r in df.iterrows():
        if not r["expansion"] or r["expansion_adults"] == 0:
            continue
        subject = int(r["expansion_adults"])
        eligible_but_at_risk = int(subject * exempt_share)
        modeled_loss = int(eligible_but_at_risk * churn)
        status = seed.WORK_REQUIREMENT_STATUS.get(r["abbr"], {})
        rows.append({
            "state": r["state"], "abbr": r["abbr"],
            "subject_adults": subject,
            "already_working_or_exempt": eligible_but_at_risk,
            "modeled_coverage_loss": modeled_loss,
            "loss_pct_of_subject": round(100 * modeled_loss / subject, 1),
            "status": r["work_req_status"],
            "effective": status.get("effective"),
            "note": status.get("note"),
        })

    rows.sort(key=lambda x: x["modeled_coverage_loss"], reverse=True)
    national_loss = sum(x["modeled_coverage_loss"] for x in rows)
    return {
        "id": "work_requirements",
        "title": "Work requirements: modeled coverage loss",
        "rows": rows,
        "national_modeled_loss": national_loss,
        "national_modeled_loss_million": round(national_loss / 1e6, 2),
        "exempt_share": exempt_share,
        "churn_rate": churn,
        "arkansas_anchor": wr["arkansas_coverage_loss"],
        "top_state": rows[0]["state"] if rows else None,
        "data_provenance": df["data_provenance"].iloc[0],
    }
