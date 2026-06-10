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
differently, extrapolate, or alter any number. If a figure you would want
is absent from the input, say so in claims_to_verify; do not guess.

RULE 2 — RESTATE PROVENANCE COMPOSITION PROMINENTLY.
The input includes a "provenance_composition" field (e.g. "12 states scraped,
31 seed, 5 unquantified structure, 2 waiver"). Your tell_me MUST quote this
composition. The reader must know which states contributed real scraped data
versus which are approximations, before they encounter any aggregate figure.
Format: "Based on [N] scraped states, [M] seed-data states, [P] states with
non-percentage structures (unquantified), and [Q] waiver-risk states, ..."

RULE 3 — WAIVER STATES ARE A DISTINCT COMPLIANCE-RISK STORYLINE.
RI and NV (and any states in waiver_risk_states) operate above 6% via CMS
non-uniformity waivers. Their risk is categorically different from the
standard 3.5% phase-down exposure. They MUST appear as a separate paragraph
or section — never merged into the standard exposure narrative. Phrase as:
"Separately, [state(s)] operate above the 6% ceiling under CMS non-uniformity
waivers. Under [law], tightened uniformity requirements place their waiver
status — not the 3.5% phase-down — as the primary compliance risk."

RULE 4 — UNQUANTIFIED STRUCTURES ARE NAMED, NOT OMITTED.
States in unquantified_structures have confirmed non-percentage tax structures
(per-admission, per-bed-day, dollar-cap, amount-targeted). Do not assign them
zero exposure. Do not assign them a fabricated percentage. Name them explicitly
as: "The following states have confirmed provider taxes but in structures not
directly comparable to the 6%→3.5% percentage cap: [list with native rates].
Their exposure is not quantified in this analysis."

RULE 5 — NEUTRAL FRAMING.
State findings in language neither a supporter nor a critic would call slanted.
No loaded words (e.g. "devastating", "commonsense", "slash", "gut", "raid",
"reform" used as praise or condemnation). Describe magnitudes plainly.

RULE 6 — BOTH SIDES FOR GENUINE DISPUTES.
Where the item has a genuine policy dispute, populate stakeholder_balance with
BOTH sides' strongest, fairly-stated argument. Do not signal which is right.
Use null only for purely factual/administrative items with no real dispute.

RULE 7 — CLAIMS_TO_VERIFY MUST INCLUDE:
  - All aggregate figures (national gap, n_exposed, top state name).
  - Which states are currently on seed data and not yet scraped.
  - PA rate staleness: the PA bulletin-year source and that the current bulletin
    must be retrieved before using the PA exposure figure.
  - Any state whose seed rate differs materially from scraped rate.
  - The unquantified-structure states and what it would take to quantify them.
  - Waiver states' OBBBA compliance timeline.

RULE 8 — LOADED-LANGUAGE SELF-CHECK.
Flag any phrase in your own draft that could be read as politically charged in
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
    "implication": "...",
    "waiver_risk_note": "...",
    "unquantified_note": "...",
    "stakeholder_balance": {
      "supporters": "...",
      "critics": "..."
    }
  },
  "claims_to_verify": [
    "provenance: which specific states are seed vs. scraped",
    "PA: confirm current-year bulletin rates before citing PA exposure",
    "unquantified: [list states] require volume data to convert to % exposure",
    "waiver: confirm RI/NV waiver status under OBBBA uniformity requirements",
    "..."
  ],
  "loaded_language_flags": []
}
stakeholder_balance may be null for purely factual items.
waiver_risk_note and unquantified_note may be null if no such states exist in the input.
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
