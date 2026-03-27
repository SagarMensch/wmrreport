"""
Domain Abbreviation Map — Query Expansion
==========================================
Maps domain-specific abbreviations (SCR, PDO, WBS, etc.)
to their full forms for query expansion before retrieval.
"""

import re

# ── Abbreviation → Full Expansion ────────────────────────────────────────
# Each abbreviation maps to space-separated expansion terms.
# These terms are injected into the BM25 and fulltext queries
# so that "SCR" finds "Site Change Request" in descriptions.

ABBREVIATION_MAP: dict[str, str] = {
    # Well operations
    "scr":   "scr site change request survey completion report scr_no scr_date",
    "wmr":   "wmr well monitoring report wellmonitoringreport",
    "pdo":   "pdo petroleum development oman pdo_well_id",
    "npt":   "npt non productive time nonproductive",
    "rig":   "rig rig_no rig_name drilling",
    "spud":  "spud spud_date well_name_after_spud",
    "td":    "td total depth target_depth",
    "bop":   "bop blowout preventer",
    "wbs":   "wbs work breakdown structure wbs_code wbs_no",
    "sap":   "sap sap_drilling_sequence system applications products",
    "flaf":  "flaf flat time allowance factor",
    "dls":   "dls dog leg severity",

    # Organizational
    "ph":    "ph project holder ph_name ph_emp_id productivity",
    "odc":   "odc oil development contract",
    "kpi":   "kpi key performance indicator",
    "gb":    "gb general business job_progress_report_gb",
    "po":    "po purchase order project_po",

    # Progress & metrics
    "cum":   "cum cumulative cum_progress progress",
    "pct":   "pct percent percentage",
    "rev":   "rev revenue actual_revenue",
    "avg":   "avg average mean",
    "ytd":   "ytd year to date",
    "mtd":   "mtd month to date",
    "wtd":   "wtd week to date",

    # Technical
    "sql":   "sql query database",
    "id":    "id identifier unique",
    "uid":   "uid unique identifier",
}


def expand_query(query: str) -> str:
    """
    Expand domain abbreviations in a query string.

    Example:
        expand_query("Show SCR number for all wells")
        → "Show SCR site change request survey completion report scr_no scr_date number for all wells"
    """
    words = query.split()
    expanded_words = []

    for word in words:
        clean = re.sub(r'[^\w]', '', word).lower()
        if clean in ABBREVIATION_MAP:
            # Keep original word + add expansion
            expanded_words.append(word)
            expanded_words.append(ABBREVIATION_MAP[clean])
        else:
            expanded_words.append(word)

    return " ".join(expanded_words)


def get_column_name_hints(query: str) -> list[str]:
    """
    Extract likely column name patterns from the query.
    Returns potential column names based on abbreviation hints.

    Example:
        get_column_name_hints("SCR number and progress")
        → ["scr_no", "scr_date", "progress"]
    """
    hints = []
    words = query.split()
    for word in words:
        clean = re.sub(r'[^\w]', '', word).lower()
        if clean in ABBREVIATION_MAP:
            # Extract words that look like column names (contain underscore)
            expansion = ABBREVIATION_MAP[clean]
            for token in expansion.split():
                if "_" in token:
                    hints.append(token)
    return hints
