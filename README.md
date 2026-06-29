# Medicaid Financing Workbench

An analyst workbench for Medicaid financing research, built around the workflow
of a research associate on a state-Medicaid policy team. It ingests the public
federal datasets the work depends on, joins them into one analysis-ready panel,
runs four financing analyses tied to the 2025 reconciliation law, and drafts
reviewable findings in a **tell / show / so what** structure.

The design goal is to automate the mechanical 80% of the job (fetch, clean,
compute, chart, draft) so the analyst's time goes to the analysis and the
"so what," not to wrangling spreadsheets.

> **What this is and isn't.** The tool runs the arithmetic and drafts prose from
> verified numbers. The analytical judgment (which questions to ask, how to
> weight an index, whether a result is real or an artifact) stays with the
> analyst. Every generated draft ships with a claims-to-verify checklist; the
> analyst owns every published conclusion.

## The four analyses

| Analysis | Question | Method |
|---|---|---|
| **Provider tax cap exposure** | Which expansion states are most exposed as the provider-tax ceiling phases from 6.0% to 3.5%, and by how much? | At-risk revenue above the target cap, walked down the statutory schedule (2028–2032). |
| **HCBS vulnerability index** | Where are optional home-care benefits under the most financing pressure? | A 0–10 composite of HCBS stakes + financing exposure, weights in config. A risk screen, not a forecast. |
| **Work-requirements coverage loss** | How many adults lose coverage, and why? | Loss modeled as administrative churn among already-eligible adults, calibrated to Arkansas (~18,000). |
| **Dual-eligible concentration** | Where does a small enrollee share map to a large spending share? | Enrollment share weighted by duals' ~3x per-capita spending. |

## Data sources

- **CMS-64 Medicaid Financial Management Data**: `data.medicaid.gov` (state expenditures and federal match)
- **CMS Managed Care Enrollment Report**: `data.medicaid.gov` (MCO penetration, dual-by-plan counts)
- **Census ACS Subject Table S2704**: `api.census.gov` (state public-coverage estimates)
- **KFF**: 2025–26 Medicaid Budget Survey; "5 Key Facts About Medicaid and Provider Taxes"; reconciliation-law tracker (policy parameters and CBO scores)

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Optional environment variables:

```bash
export ANTHROPIC_API_KEY=...   # enables `mfw draft` (the tell/show/so-what generator)
export CENSUS_API_KEY=...       # raises Census API rate limits (optional)
```

## Run

```bash
mfw analyze                 # run the four analyses -> outputs/results.json
mfw dashboard               # build dashboard/dashboard_data.json (+ charts), then open dashboard/index.html
mfw factsheet --state NC    # generate a brief-ready state fact sheet
mfw scenario --cap 3.0      # provider-tax-cap counterfactual
mfw fetch --live            # attempt live data pull (falls back to seed on failure)
```

Add `--live` to any command to prefer live federal data; without it the tool
uses the bundled seed dataset so it runs instantly and deterministically.

The dashboard is a static page reading `dashboard_data.json`, so it deploys to
GitHub Pages as-is.

## How the narrative layer works

`mfw draft` (and the dashboard) produce a **tell / show / so what** brief per finding:

- **Tell me**: the plain-language finding
- **Show me**: the computation, an accurate figure description, and sources
- **So what**: a neutral implication plus both stakeholder cases

The LLM layer passes computed numbers as **immutable ground truth**, returns a
**claims-to-verify** checklist and **loaded-language flags** with every draft,
and presents contested items with both sides fairly stated. See `NEUTRALITY.md`.
Without an API key the pipeline still completes using the analyst-reviewed drafts
in `dashboard/reviewed_drafts.json`.

## Limitations

This is a prototype built on **public aggregate data**, and it says so on every
screen via the `data_provenance` flag.

- The bundled **seed dataset uses illustrative per-state values** anchored to
  KFF-published magnitudes where possible. Run `mfw fetch --live` to replace them
  with authoritative CMS-64 / Census figures. Do not cite seed values as official.
- **T-MSIS / TAF research files** (enrollee-level claims) require a CMS Data Use
  Agreement and would materially refine the work-requirements and dual-eligible
  models. The architecture leaves a clear slot for them.
- The indices and models encode **analyst choices** (index weights, churn rate,
  dual cost multiple). They are documented, configurable, and meant to be argued
  with, not treated as settled.

## Project layout

```
config/policy_parameters.yaml   # the control panel: edit a number, everything recomputes
src/mfw/sources/                # data fetchers (CMS-64, managed care, ACS) + seed
src/mfw/etl/panel.py            # the single join point
src/mfw/analysis/               # the four analyses (the real arithmetic)
src/mfw/modeling/scenarios.py   # parameterized counterfactuals
src/mfw/llm/draft.py            # tell/show/so-what with honesty + neutrality contract
src/mfw/outputs/                # charts, fact sheets, dashboard data
dashboard/                      # static UI (deploys to GitHub Pages)
notebooks/                      # worked analysis with narrative
```
