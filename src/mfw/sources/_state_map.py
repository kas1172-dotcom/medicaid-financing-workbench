"""
Maps the various state name formats used by data.medicaid.gov to canonical
two-letter abbreviations and FIPS codes.
"""

# Canonical: abbr -> (full_name, fips)
STATES = {
    "AL": ("Alabama",             "01"),
    "AK": ("Alaska",              "02"),
    "AZ": ("Arizona",             "04"),
    "AR": ("Arkansas",            "05"),
    "CA": ("California",          "06"),
    "CO": ("Colorado",            "08"),
    "CT": ("Connecticut",         "09"),
    "DE": ("Delaware",            "10"),
    "DC": ("District of Columbia","11"),
    "FL": ("Florida",             "12"),
    "GA": ("Georgia",             "13"),
    "HI": ("Hawaii",              "15"),
    "ID": ("Idaho",               "16"),
    "IL": ("Illinois",            "17"),
    "IN": ("Indiana",             "18"),
    "IA": ("Iowa",                "19"),
    "KS": ("Kansas",              "20"),
    "KY": ("Kentucky",            "21"),
    "LA": ("Louisiana",           "22"),
    "ME": ("Maine",               "23"),
    "MD": ("Maryland",            "24"),
    "MA": ("Massachusetts",       "25"),
    "MI": ("Michigan",            "26"),
    "MN": ("Minnesota",           "27"),
    "MS": ("Mississippi",         "28"),
    "MO": ("Missouri",            "29"),
    "MT": ("Montana",             "30"),
    "NE": ("Nebraska",            "31"),
    "NV": ("Nevada",              "32"),
    "NH": ("New Hampshire",       "33"),
    "NJ": ("New Jersey",          "34"),
    "NM": ("New Mexico",          "35"),
    "NY": ("New York",            "36"),
    "NC": ("North Carolina",      "37"),
    "ND": ("North Dakota",        "38"),
    "OH": ("Ohio",                "39"),
    "OK": ("Oklahoma",            "40"),
    "OR": ("Oregon",              "41"),
    "PA": ("Pennsylvania",        "42"),
    "RI": ("Rhode Island",        "44"),
    "SC": ("South Carolina",      "45"),
    "SD": ("South Dakota",        "46"),
    "TN": ("Tennessee",           "47"),
    "TX": ("Texas",               "48"),
    "UT": ("Utah",                "49"),
    "VT": ("Vermont",             "50"),
    "VA": ("Virginia",            "51"),
    "WA": ("Washington",          "53"),
    "WV": ("West Virginia",       "54"),
    "WI": ("Wisconsin",           "55"),
    "WY": ("Wyoming",             "56"),
}

# Build reverse lookup: every name variant CMS uses -> abbr
_CMS_NAME_TO_ABBR: dict[str, str] = {}
for _abbr, (_name, _fips) in STATES.items():
    _CMS_NAME_TO_ABBR[_name.lower()] = _abbr

# Extra CMS-specific abbreviations/spellings
_CMS_EXTRAS = {
    "dist. of col.": "DC",
    "district of columbia": "DC",
    "n. mariana islands": "MP",   # territory: excluded from 50+DC analysis
    "northern mariana islands": "MP",
    "amer. samoa": "AS",
    "american samoa": "AS",
    "guam": "GU",
    "puerto rico": "PR",
    "virgin islands": "VI",
    "national totals": None,
}
for _k, _v in _CMS_EXTRAS.items():
    _CMS_NAME_TO_ABBR[_k] = _v


def cms_name_to_abbr(name: str) -> str | None:
    """
    Convert a CMS dataset state name to a 2-letter abbreviation.
    Returns None for territories, aggregates, or unrecognised names.
    """
    return _CMS_NAME_TO_ABBR.get(name.strip().lower())


def abbr_to_fips(abbr: str) -> str | None:
    entry = STATES.get(abbr.upper())
    return entry[1] if entry else None


# The 51 jurisdictions (50 states + DC) we analyse
ANALYSIS_ABBRS: frozenset[str] = frozenset(STATES.keys())
