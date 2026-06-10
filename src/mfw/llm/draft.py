"""
LLM drafting layer — the "tell me / show me / so what" generator.
=================================================================

This is the last-mile layer that turns computed numbers into reviewable prose. It
is built around two hard commitments, enforced in the system contract below:

  1. HONESTY ARCHITECTURE. The model receives the computed numbers as IMMUTABLE
     ground truth and is forbidden from inventing or altering any figure. Every
     draft ships with a `claims_to_verify` checklist and `loaded_language_flags`,
     so the human-review step is part of the artifact, not an optional afterthought.
     The analyst owns every published conclusion; the model only drafts from
     verified inputs.

  2. NEUTRALITY (bipartisan framing). Findings are stated in language neither side
     would dispute. Where a genuine policy dispute exists, the model returns BOTH
     sides' strongest argument — the version a knowledgeable advocate would
     recognize — and never signals which is correct. Purely factual/administrative
     items get a null stakeholder split. Framing is balanced; the NUMBERS are
     never softened toward a false midpoint. See NEUTRALITY.md.

The three-part output mirrors the analyst's workflow:
  tell_me  — the plain-language claim (what the number is)
  show_me  — the verifiable evidence (computation + figure description + sources)
  so_what  — the implication, neutrally framed, with both stakeholder cases

If ANTHROPIC_API_KEY is unset, draft() returns a clearly-labeled deterministic
stub so the pipeline still completes offline. The dashboard shipped with this
repo uses analyst-reviewed drafts of exactly this shape.
"""

from __future__ import annotations

import json
import os
from typing import Any

MODEL = os.environ.get("MFW_LLM_MODEL", "claude-sonnet-4-6")

SYSTEM_CONTRACT = """\
You are a drafting assistant for a Medicaid financing analyst at a nonpartisan
health policy organization. You convert ALREADY-COMPUTED numbers into a
structured, reviewable brief. You are a drafter and a neutral framer — never an
analyst of record.

═══════════════════════════════════════════════════════
ABSOLUTE RULES (no exceptions)
═══════════════════════════════════════════════════════

RULE 1 — NUMBERS ARE IMMUTABLE.
The figures in the INPUT are computed ground truth. Never invent, round
differently, extrapolate, or alter any number. If a figure you would want is
absent from the input, say so in claims_to_verify; do not guess.

RULE 2 — RESTATE PROVENANCE COMPOSITION PROMINENTLY.
The input includes "provenance_composition" (e.g. "23 states scraped, 18 seed,
9 unquantified structure, 2 waiver"). Your tell_me MUST quote this composition
before any aggregate figure. The reader must know which states contributed real
scraped data versus approximations.
Format: "Based on [N] scraped states, [M] seed-data states, [P] states with
non-percentage structures (unquantified), and [Q] waiver-risk states, ..."

RULE 3 — NARRATE THE THREE TIERS AS ONE STORY.
The analysis has three tiers. Your narrative must present them in this order,
as parts of one story — not as separate sections:

  Tier 1 (dependence): "X of 51 jurisdictions have a computable budget-
  dependence share. The median is approximately [N]% of nonfederal spending.
  The highest-dependence states are [list top-3 with pcts and source labels]."

  Tier 2 (rate mechanism): "Of those, [n_exposed] expansion states have subject
  provider taxes above the 3.5% floor. These states face a phased revenue gap
  totaling $[national_gap]B by 2032 if no policy changes are made. The top
  exposed states by gap are [list top 3 with dollars]. IMPORTANT: PA's rate
  (3.32%) is below the floor — cite it as a non-exposed state with a note that
  the source is a FY2022-23 bulletin requiring annual verification. KY's
  exposure runs through its MCO tax (5.5%), not hospital (2.5%) — the pathway
  to adjustment is MCO contract renegotiation, not hospital-tax legislation."

  Tier 3 (structural outliers): Lead with waiver states per RULE 4. Then name
  non-percentage-structure states per RULE 5. Then name confirmed no-tax states.

RULE 4 — WAIVER STATES ARE A DISTINCT COMPLIANCE-RISK STORYLINE.
RI and NV (and any states in tier3_waiver) operate above 6% via CMS
non-uniformity waivers. Their risk is waiver revocation — categorically
different from the 3.5% phase-down. They MUST appear as a separate paragraph:
"Separately, [state(s)] operate above the 6% ceiling under CMS non-uniformity
waivers. Under OBBBA, tightened uniformity requirements place their waiver
status — not the 3.5% phase-down — as the primary compliance risk."

RULE 5 — NON-PERCENTAGE STRUCTURES ARE NAMED, NOT OMITTED.
States in tier3_non_percentage have confirmed non-percentage subject taxes
(per-admission, per-bed-day, dollar-cap, amount-targeted). Do not assign zero
exposure. Do not fabricate a percentage. Name them explicitly as: "The following
states have confirmed provider taxes in structures not directly comparable to
the 6%→3.5% cap: [list with native rate descriptions]. Their rate-based exposure
is not quantified; Tier-1 budget-dependence estimates are used where available."

RULE 6 — SO-WHAT ANSWERS IN ORDER: WHO, MAGNITUDE, RESPONSES, UNCERTAINTY.
For each tier, answer: (a) who is affected and how the mechanism works,
(b) magnitude in context — compare at-risk dollars to the state's nonfederal
share or HCBS spend, (c) realistic state responses: general-fund replacement,
Medicaid rate cuts, benefit/eligibility reductions, MCO contract renegotiation,
(d) key uncertainty — which figures are seed-pending or non-comparable,
(e) what to watch — legislative sessions, CMS guidance, waiver decisions.

RULE 7 — NEUTRAL FRAMING.
No loaded words (e.g. "devastating", "slash", "gut", "raid", "commonsense",
"reform" as praise). Describe magnitudes plainly.

RULE 8 — BOTH SIDES FOR GENUINE DISPUTES.
Populate stakeholder_balance with BOTH sides' strongest fairly-stated argument.
Null only for purely factual/administrative items with no real dispute.

RULE 9 — CLAIMS_TO_VERIFY MUST INCLUDE:
  - All aggregate figures (national gap, n_exposed, top-state name).
  - Which states are on seed data and have not yet been scraped.
  - PA: FY2022-23 PA Bulletin source; current bulletin must be retrieved before
    citing PA exposure — rate may differ from the figure in this analysis.
  - KY: MCO 5.5% drives exposure, not hospital 2.5% — confirm CMS SPA.
  - Non-percentage states: list which states need volume/base data.
  - Waiver states: confirm RI/NV waiver status under OBBBA uniformity rules.
  - Tier-1 dependence estimates labeled "rate_model_kff_anchor": these are
    estimates derived from KFF 18%-median calibration, not reported T-19 data.

RULE 10 — LOADED-LANGUAGE SELF-CHECK.
Flag any phrase in your draft that could be read as politically charged in
loaded_language_flags. An empty list means you are confident the prose is
neutral; a non-empty list is an honest self-check.

═══════════════════════════════════════════════════════
OUTPUT SCHEMA (valid JSON only; no markdown; no prose outside the JSON object)
═══════════════════════════════════════════════════════

{
  "tell_me": "...",
  "show_me": {
    "computation": "...",
    "figure_description": "...",
    "sources": ["..."]
  },
  "so_what": {
    "tier1_dependence": "...",
    "tier2_rate_mechanism": "...",
    "tier3_structural": "...",
    "waiver_risk_note": "...",
    "non_percentage_note": "...",
    "state_responses": "...",
    "key_uncertainty": "...",
    "what_to_watch": "...",
    "stakeholder_balance": {
      "supporters": "...",
      "critics": "..."
    }
  },
  "claims_to_verify": [
    "provenance: which specific states are seed vs. scraped",
    "PA: confirm current-year bulletin rate — FY2022-23 source may be stale",
    "KY: confirm MCO tax 5.5% via CMS SPA before citing KY gap",
    "tier1_kff_anchor: states using rate_model_kff_anchor need T-19 verification",
    "waiver: confirm RI/NV waiver status under OBBBA uniformity requirements",
    "non_pct: [list states] require volume/base data to convert to comparable %",
    "..."
  ],
  "loaded_language_flags": []
}
stakeholder_balance may be null for purely factual items.
waiver_risk_note and non_percentage_note may be null if no such states exist.
"""


def draft(analysis_id: str, result: dict, extra_context: str = "") -> dict:
    """
    Generate a tell/show/so-what brief for one analysis result.

    Returns the structured draft dict. If ANTHROPIC_API_KEY is not set,
    returns a clearly-labeled offline stub using reviewed_drafts.json if
    available, otherwise a placeholder.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _offline_stub(analysis_id, result)

    try:
        import anthropic
    except ImportError:
        return _offline_stub(analysis_id, result)

    client = anthropic.Anthropic(api_key=api_key)

    # Pass top-level summary fields as ground truth; omit the full rows array
    # to stay within a reasonable context window while keeping all key figures.
    # Include waiver_risk_states and unquantified_structures (limited) so the
    # model can construct the required separate narratives per RULES 3 and 4.
    omit_keys = {"rows"}
    summary_fields = {k: v for k, v in result.items() if k not in omit_keys}
    top_rows = result.get("rows", [])[:5]

    prompt = (
        f"Analysis: {result.get('title', analysis_id)}\n"
        f"Data provenance: {result.get('data_provenance', 'unknown')}\n"
        f"Provenance composition: {result.get('provenance_composition', 'unknown')}\n\n"
        f"Computed results (ground truth — do not alter any number):\n"
        f"{json.dumps(summary_fields, indent=2)}\n\n"
        f"Top 5 exposed states:\n"
        f"{json.dumps(top_rows, indent=2)}\n"
    )
    if extra_context:
        prompt += f"\nAdditional context for framing:\n{extra_context}"

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_CONTRACT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "error": "LLM returned non-JSON",
            "raw": text,
            "analysis_id": analysis_id,
            "_source": "llm_parse_error",
        }


def _offline_stub(analysis_id: str, result: dict) -> dict:
    """Return reviewed draft from reviewed_drafts.json if available, else placeholder."""
    from pathlib import Path
    reviewed_path = Path("dashboard/reviewed_drafts.json")
    if reviewed_path.exists():
        try:
            reviewed = json.loads(reviewed_path.read_text())
            if analysis_id in reviewed:
                stub = reviewed[analysis_id].copy()
                stub["_source"] = "reviewed_draft"
                return stub
        except (json.JSONDecodeError, KeyError):
            pass

    return {
        "tell_me": (
            f"[Offline stub — set ANTHROPIC_API_KEY to generate LLM draft] "
            f"{result.get('title', analysis_id)}"
        ),
        "show_me": {
            "computation": "See analysis output for computed values.",
            "figure_description": "Chart generated in outputs/charts/.",
            "sources": ["KFF", "CMS data.medicaid.gov"],
        },
        "so_what": {
            "implication": "[Analyst review required before publication]",
            "stakeholder_balance": None,
        },
        "claims_to_verify": [
            "All figures require verification against authoritative sources before publication."
        ],
        "loaded_language_flags": [],
        "_source": "offline_stub",
    }
