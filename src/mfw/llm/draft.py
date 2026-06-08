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

ABSOLUTE RULES:
1. The numbers in the INPUT are ground truth. Never invent, round differently,
   extrapolate, or alter any figure. If a figure you'd want is not provided, say
   so in claims_to_verify rather than guessing.
2. Neutral framing. State findings in language neither a supporter nor a critic
   would call slanted. No loaded words (e.g. "devastating", "commonsense",
   "slash", "gut", "reform" used as praise). Describe magnitudes plainly.
3. Where the item has a genuine policy dispute, populate stakeholder_balance with
   BOTH sides' strongest, fairly-stated argument. Do not signal which is right.
   Use null only for purely factual/administrative items with no real dispute.
4. Always populate claims_to_verify: the specific factual/methodological claims a
   human reviewer must confirm before publication.
5. Flag any phrase in your own draft that could be read as politically charged or
   loaded in loaded_language_flags. An empty list means you are confident the
   prose is neutral; a non-empty list is an honest self-check for the reviewer.

Respond ONLY with valid JSON matching this exact schema (no markdown, no prose outside the JSON object):
{
  "tell_me": "...",
  "show_me": {
    "computation": "...",
    "figure_description": "...",
    "sources": ["..."]
  },
  "so_what": {
    "implication": "...",
    "stakeholder_balance": {
      "supporters": "...",
      "critics": "..."
    }
  },
  "claims_to_verify": ["...", "..."],
  "loaded_language_flags": []
}
stakeholder_balance may be null for purely factual items.
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
    summary_fields = {k: v for k, v in result.items() if k != "rows"}
    top_rows = result.get("rows", [])[:5]

    prompt = (
        f"Analysis: {result.get('title', analysis_id)}\n"
        f"Data provenance: {result.get('data_provenance', 'unknown')}\n\n"
        f"Computed results (ground truth — do not alter any number):\n"
        f"{json.dumps(summary_fields, indent=2)}\n\n"
        f"Top 5 states:\n"
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
