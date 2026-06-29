"""
Seed dataset: offline fallback so the workbench runs for anyone, immediately.
=============================================================================

IMPORTANT: read before citing any number from this file.

These are ILLUSTRATIVE seed values used so the tool is runnable without network
access. Spending and enrollment magnitudes are anchored to publicly reported
KFF / CMS figures; values for smaller states are reasonable estimates scaled to
enrollment. They are NOT a substitute for the live data.

Provider-tax rates are structured PER CLASS, reflecting how the 2025 law works:
  EXEMPT from the cap:  nursing_facility, icf_iid
  SUBJECT to the cap:   hospital, mco, ambulance, other

The split matters because a state whose primary provider tax is on nursing
facilities is NOT exposed to the reduced cap, even if that rate exceeds 3.5%.
The current seed data encodes this distinction for all 51 jurisdictions.

Anchored facts (high confidence, KFF Dec 2025 / Feb 2026):
  - 31 expansion states have a non-exempt provider tax above 3.5%.
  - 28 of those 31 have a hospital tax above 3.5%.
  - The hold-harmless limit for existing taxes phases from 6.0% to 3.5%,
    0.5pp/year, FFY2028–FFY2032.
  - New/increased taxes face a 0% hold-harmless limit, effective July 2025.
  - Total reconciliation Medicaid reduction: $911B over 10 years.
  - Provider-tax provisions: $226B ($89B new/increased, $102B reduced
    hold-harmless, $35B uniformity waivers).
  - FFY2024 federal/state aggregate split: 65%/35%.
  - Provider taxes fund a median 18% of the non-federal share nationally.

To replace seed values with authoritative data, run:
    mfw refresh        # prompts for manual uploads + auto-pulls APIs
    mfw build          # rebuilds analysis from data/current/

Every analysis output carries a `data_provenance` flag ("seed" or "live") so a
reader always knows which they are looking at.
"""

from __future__ import annotations

# ── State panel columns ───────────────────────────────────────────────────────
# state, abbr, fips, expansion
# total_medicaid_fed_spend ($M), nonfederal_share ($M)
# hcbs_spend ($M), enrollment, expansion_adults, duals, fmap (%)
#
# has_mco_tax is kept for backwards-compat but the authoritative class-level
# data is in _PROVIDER_TAXES_BY_CLASS below.

_SEED_ROWS = [
    # state, abbr, fips, expansion, _legacy_rate, has_mco_tax,
    # total_medicaid_fed_spend, nonfederal_share, hcbs_spend, enrollment,
    # expansion_adults, duals, fmap
    ("Alabama",        "AL", "01", False, 0.0, False,  5200,  2100,  1300,  1050000,       0,  190000, 72.6),
    ("Alaska",         "AK", "02", True,  0.0, False,  1600,   700,   620,   250000,   62000,   18000, 50.0),
    ("Arizona",        "AZ", "04", True,  4.5, True,  13800,  4200,  2600,  2300000,  640000,  170000, 69.7),
    ("Arkansas",       "AR", "05", True,  5.9, False,  6600,  1900,  1100,  1020000,  340000,  120000, 71.3),
    ("California",     "CA", "06", True,  5.5, True,  87000, 39000, 16500, 14800000, 5000000, 1500000, 56.2),
    ("Colorado",       "CO", "08", True,  5.5, False,  7600,  3500,  2100,  1700000,  560000,  120000, 50.0),
    ("Connecticut",    "CT", "09", True,  5.8, False,  6300,  3400,  2400,  1050000,  300000,  120000, 50.0),
    ("Delaware",       "DE", "10", True,  4.0, False,  1700,   800,   500,   300000,   95000,   28000, 56.0),
    ("Florida",        "FL", "12", False, 0.0, False, 19500,  7600,  3900,  4900000,       0,  560000, 61.1),
    ("Georgia",        "GA", "13", False, 0.0, False,  9800,  3800,  2000,  2200000,   60000,  290000, 65.9),
    ("Hawaii",         "HI", "15", True,  5.5, True,   2300,  1000,   620,   430000,  120000,   42000, 56.3),
    ("Idaho",          "ID", "16", True,  0.0, False,  2600,   850,   650,   430000,  130000,   40000, 70.1),
    ("Illinois",       "IL", "17", True,  5.9, True,  16500,  7000,  3400,  3400000, 1000000,  330000, 50.6),
    ("Indiana",        "IN", "18", True,  5.9, False,  9500,  3000,  1600,  1900000,  600000,  170000, 65.7),
    ("Iowa",           "IA", "19", True,  5.5, True,   4200,  1500,  1100,   780000,  220000,   75000, 62.5),
    ("Kansas",         "KS", "20", False, 0.0, True,   2700,  1100,   780,   430000,       0,   70000, 60.1),
    ("Kentucky",       "KY", "21", True,  5.5, False,  9700,  2400,  1700,  1600000,  500000,  180000, 76.0),
    ("Louisiana",      "LA", "22", True,  5.5, False,  8900,  2600,  1500,  1700000,  580000,  170000, 73.0),
    ("Maine",          "ME", "23", True,  0.0, False,  2700,  1100,   850,   400000,  100000,   55000, 62.6),
    ("Maryland",       "MD", "24", True,  5.5, False,  9200,  4300,  2700,  1600000,  430000,  140000, 50.0),
    ("Massachusetts",  "MA", "25", True,  5.9, True,  14500,  7200,  4100,  2000000,  450000,  240000, 50.0),
    ("Michigan",       "MI", "26", True,  6.0, True,  15200,  4800,  3000,  2800000,  900000,  290000, 65.0),
    ("Minnesota",      "MN", "27", True,  5.5, True,   9800,  4600,  3200,  1300000,  350000,  140000, 50.0),
    ("Mississippi",    "MS", "28", False, 0.0, False,  4900,  1300,   980,   780000,       0,  130000, 77.9),
    ("Missouri",       "MO", "29", True,  5.9, True,   9200,  3100,  1900,  1500000,  330000,  170000, 65.1),
    ("Montana",        "MT", "30", True,  0.0, False,  1900,   650,   520,   300000,   95000,   25000, 67.4),
    ("Nebraska",       "NE", "31", True,  0.0, False,  2300,   950,   700,   380000,  100000,   38000, 58.4),
    ("Nevada",         "NV", "32", True,  4.5, True,   3700,  1300,   720,   820000,  280000,   55000, 63.9),
    ("New Hampshire",  "NH", "33", True,  5.5, False,  1700,   800,   560,   230000,   62000,   28000, 50.0),
    ("New Jersey",     "NJ", "34", True,  5.8, True,  10800,  5300,  3000,  1800000,  550000,  220000, 50.0),
    ("New Mexico",     "NM", "35", True,  5.0, True,   6100,  1600,  1100,   840000,  290000,   65000, 72.4),
    ("New York",       "NY", "36", True,  5.9, True,  44000, 21000, 12000,  7000000, 1700000,  900000, 50.0),
    ("North Carolina", "NC", "37", True,  5.2, False, 14500,  4800,  2700,  3000000,  640000,  290000, 65.0),
    ("North Dakota",   "ND", "38", True,  0.0, False,   900,   400,   320,   120000,   35000,   12000, 50.0),
    ("Ohio",           "OH", "39", True,  5.9, True,  19000,  6300,  3600,  3000000,  780000,  330000, 64.5),
    ("Oklahoma",       "OK", "40", True,  0.0, False,  6300,  2000,  1100,  1100000,  300000,  120000, 68.6),
    ("Oregon",         "OR", "41", True,  5.5, False,  9200,  2900,  1900,  1400000,  450000,  120000, 64.0),
    ("Pennsylvania",   "PA", "42", True,  5.9, True,  20500,  8500,  5200,  3100000,  830000,  430000, 56.0),
    ("Rhode Island",   "RI", "44", True,  5.5, False,  2200,  1000,   720,   320000,   90000,   38000, 54.0),
    ("South Carolina", "SC", "45", False, 0.0, False,  5600,  1900,  1200,  1100000,       0,  150000, 70.0),
    ("South Dakota",   "SD", "46", True,  0.0, False,   980,   380,   300,   150000,   30000,   14000, 56.0),
    ("Tennessee",      "TN", "47", False, 0.0, True,   9500,  3300,  1900,  1500000,       0,  220000, 65.6),
    ("Texas",          "TX", "48", False, 0.0, False, 27000, 11000,  5400,  4300000,       0,  560000, 60.3),
    ("Utah",           "UT", "49", True,  0.0, False,  3100,   950,   680,   560000,  170000,   45000, 67.6),
    ("Vermont",        "VT", "50", True,  0.0, False,  1500,   700,   540,   170000,   45000,   22000, 53.6),
    ("Virginia",       "VA", "51", True,  5.8, True,  11500,  5200,  2800,  1900000,  680000,  180000, 50.0),
    ("Washington",     "WA", "53", True,  5.5, True,  12000,  5400,  3300,  2000000,  650000,  180000, 50.0),
    ("West Virginia",  "WV", "54", True,  5.5, False,  4200,  1000,   800,   600000,  180000,   70000, 75.2),
    ("Wisconsin",      "WI", "55", False, 0.0, False,  7000,  2700,  2000,  1200000,       0,  170000, 60.5),
    ("Wyoming",        "WY", "56", False, 0.0, False,   600,   270,   220,    80000,       0,    9000, 50.0),
    ("District of Columbia", "DC", "11", True, 5.5, True, 3200, 800, 700, 270000, 90000, 30000, 70.0),
]

_COLUMNS = [
    "state", "abbr", "fips", "expansion", "_legacy_rate", "has_mco_tax",
    "total_medicaid_fed_spend", "nonfederal_share", "hcbs_spend", "enrollment",
    "expansion_adults", "duals", "fmap",
]

# ── Per-class provider tax rates ──────────────────────────────────────────────
# Rates are % of net patient revenue.
#
# EXEMPT from the hold-harmless phase-down: nursing_facility, icf_iid
# SUBJECT to the hold-harmless phase-down: hospital, mco, ambulance, other
#
# Design of the 31-state exposure pattern:
#   - 31 expansion states have at least one subject-class tax above 3.5%.
#   - 28 of those 31 have a hospital tax above 3.5% (KFF anchor).
#   - The other 3 (AZ, NV, NM) are exposed via their MCO tax only.
#   - 10 expansion states have provider taxes only on exempt classes
#     (nursing_facility/icf_iid), so they are NOT exposed to the cap.
#   - Non-expansion states keep the 6% ceiling; their class-level data is
#     encoded for completeness but their cap-exposure is always zero.
#
# Key: (hospital, mco, ambulance, other, nursing_facility, icf_iid)

_PROVIDER_TAXES_BY_CLASS = {
    # Non-expansion states: kept for completeness; not subject to reduced cap.
    "AL": {"hospital": 4.2, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.8, "icf_iid": 0.0},
    "FL": {"hospital": 1.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "GA": {"hospital": 1.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "KS": {"hospital": 1.5, "mco": 1.8, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "MS": {"hospital": 1.2, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "SC": {"hospital": 1.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "TN": {"hospital": 1.0, "mco": 1.5, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "TX": {"hospital": 1.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "WI": {"hospital": 1.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "WY": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 0.0, "icf_iid": 0.0},

    # Expansion states, NOT exposed (non-exempt taxes all at or below 3.5%, or zero).
    # These 10 states have their meaningful provider taxes on exempt classes only.
    "AK": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 0.0, "icf_iid": 0.0},
    "ID": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 3.5},
    "ME": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "MT": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "ND": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 4.0, "icf_iid": 0.0},
    "NE": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "OK": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 4.0, "icf_iid": 0.0},
    "SD": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 4.0, "icf_iid": 0.0},
    "UT": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.0, "icf_iid": 0.0},
    "VT": {"hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},

    # Expansion states: exposed via MCO tax only (hospital tax at or below 3.5%).
    # These 3 states account for the gap between 31 total and 28 hospital-exposed.
    "AZ": {"hospital": 3.5, "mco": 4.5, "ambulance": 0.0, "other": 0.0, "nursing_facility": 3.5, "icf_iid": 0.0},
    "NV": {"hospital": 3.5, "mco": 4.5, "ambulance": 0.0, "other": 0.0, "nursing_facility": 3.5, "icf_iid": 0.0},
    "NM": {"hospital": 3.0, "mco": 5.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 4.0, "icf_iid": 0.0},

    # Expansion states: exposed via hospital tax above 3.5% (28 states).
    "AR": {"hospital": 5.9, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "CA": {"hospital": 5.5, "mco": 1.8, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "CO": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "CT": {"hospital": 5.8, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.8, "icf_iid": 0.0},
    "DC": {"hospital": 5.5, "mco": 1.5, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "DE": {"hospital": 4.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 4.0, "icf_iid": 0.0},
    "HI": {"hospital": 5.5, "mco": 1.5, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "IL": {"hospital": 5.9, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "IN": {"hospital": 5.9, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "IA": {"hospital": 5.5, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "KY": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "LA": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "MA": {"hospital": 5.9, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "MD": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "MI": {"hospital": 6.0, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 6.0, "icf_iid": 0.0},
    "MN": {"hospital": 5.5, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "MO": {"hospital": 5.9, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "NC": {"hospital": 5.2, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.2, "icf_iid": 0.0},
    "NH": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "NJ": {"hospital": 5.8, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.8, "icf_iid": 0.0},
    "NY": {"hospital": 5.9, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "OH": {"hospital": 5.9, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "OR": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "PA": {"hospital": 5.9, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.9, "icf_iid": 0.0},
    "RI": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "VA": {"hospital": 5.8, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.8, "icf_iid": 0.0},
    "WA": {"hospital": 5.5, "mco": 2.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
    "WV": {"hospital": 5.5, "mco": 0.0, "ambulance": 0.0, "other": 0.0, "nursing_facility": 5.5, "icf_iid": 0.0},
}

EXEMPT_CLASSES = frozenset({"nursing_facility", "icf_iid"})
SUBJECT_CLASSES = frozenset({"hospital", "mco", "ambulance", "other"})


def _max_subject_rate(abbr: str) -> float:
    """Return the highest rate among subject (non-exempt) provider classes."""
    taxes = _PROVIDER_TAXES_BY_CLASS.get(abbr, {})
    rates = [taxes.get(c, 0.0) for c in SUBJECT_CLASSES]
    return max(rates) if rates else 0.0


def load_seed_records():
    """Return the seed dataset as a list of dicts, tagged provenance='seed'."""
    rows = []
    for r in _SEED_ROWS:
        rec = dict(zip(_COLUMNS, r))
        rec["total_medicaid_spend"] = rec["total_medicaid_fed_spend"] + rec["nonfederal_share"]
        rec["hcbs_share"] = round(100 * rec["hcbs_spend"] / rec["total_medicaid_spend"], 1)
        rec["data_provenance"] = "seed"

        # Authoritative per-class rates; fall back to empty dict if not in map.
        abbr = rec["abbr"]
        classes = _PROVIDER_TAXES_BY_CLASS.get(abbr, {
            "hospital": 0.0, "mco": 0.0, "ambulance": 0.0, "other": 0.0,
            "nursing_facility": 0.0, "icf_iid": 0.0,
        })
        rec["provider_taxes_by_class"] = classes

        # provider_tax_rate = max NON-EXEMPT rate (used by analysis; replaces old blended rate).
        rec["provider_tax_rate"] = _max_subject_rate(abbr)

        # has_mco_tax preserved for backwards-compat display.
        rec["has_mco_tax"] = classes.get("mco", 0.0) > 0.0

        rows.append(rec)
    return rows


# Documented state implementation of the 2025 reconciliation law's work-requirement
# provisions. Status reflects KFF reporting on early state action.
WORK_REQUIREMENT_STATUS = {
    "NC": {
        "status": "enacted",
        "effective": "2027-01",
        "note": "Enacted standards stricter than the federal minimum; April 2026 "
                "legislation appropriated $319M to close the FY2026 shortfall.",
    },
    "CA": {
        "status": "enacted",
        "effective": "2027-01",
        "note": "Governor's budget voluntarily extends work requirements and "
                "6-month redeterminations to certain state-funded immigrant enrollees. "
                "~5M expansion enrollees potentially affected; ~63% of adults without "
                "dependent children already work 80+ hrs/month or attend school.",
    },
    "AR": {
        "status": "enacted",
        "effective": "2026-07",
        "note": "Re-implementing after the 2018 attempt that caused ~18,000 coverage "
                "losses before being halted by a federal court.",
    },
    "GA": {
        "status": "enacted",
        "effective": "2026-07",
        "note": "Operating the 'Pathways to Coverage' partial-expansion model with a "
                "work requirement; documented low enrollment relative to projections.",
    },
}
