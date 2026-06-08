# Neutrality standard

This workbench is built for a nonpartisan health policy setting, where the
credibility of a finding depends on it being trusted across the aisle. Neutrality
here is a concrete, testable property of the output — not a vibe.

## What neutrality means in this tool

1. **Neutral description, not split-the-difference.** Findings state what the data
   shows in language neither side would call slanted. "The provision reduces
   federal Medicaid spending by $X and CBO projects Y fewer enrollees" — not
   "devastating cuts" or "commonsense reforms."

2. **Both cases, fairly stated.** Where a genuine policy dispute exists, the
   output gives the strongest version of each side's argument — the version a
   knowledgeable advocate for that position would actually make, not a strawman.
   Purely factual or administrative items get no forced split (`stakeholder_balance: null`).

3. **Attribute, don't adjudicate.** "Supporters argue X; critics argue Y," with
   the open empirical question flagged — never the tool declaring who is right.

4. **A loaded-language check.** Generated prose is scanned for charged terms; any
   are surfaced in `loaded_language_flags` for the analyst to neutralize.

## The line that protects the analysis

Neutrality of **framing** is the goal. It does **not** pull the **numbers** toward
a false midpoint. If CBO scores a provision at $326B, the tool reports $326B —
it does not soften the figure because one side finds it inconvenient.

> Balanced presentation, factual spine. Framing balance applies only to how
> contested *interpretations* are presented, never to the data itself.

## Where it's enforced

- `src/mfw/llm/draft.py` — the system contract instructs neutral framing, dual
  stakeholder cases, immutable numbers, and the loaded-language flag.
- `dashboard/index.html` — the "So what" tab renders both cases side by side and
  states explicitly that the tool does not signal which is correct.
