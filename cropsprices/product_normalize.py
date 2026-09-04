"""Product name + unit normalization for deduplication.

Cleans trailing whitespace, normalizes unit dots, and resolves
name variants via a lookup table.  Used by both build_arrow_db.py
and generate_availability.py.
"""

# ---------------------------------------------------------------------------
# Alias table: (old_name, old_unit) → (canonical_name, canonical_unit)
# Keys and values are the RAW strings that appear in parsed CSVs / manifest.
# ---------------------------------------------------------------------------

PRODUCT_ALIASES: dict[tuple[str, str], tuple[str, str]] = {
    # -- Trailing whitespace is handled by strip(), no alias needed --

    # Borówka singular → plural (KRAJOWE had both)
    ("Borówka amerykańska", "kg"): ("Borówki amerykańskie", "kg"),

    # Unit: "szt" → "szt."
    ("Kapusta młoda", "szt"): ("Kapusta młoda", "szt."),
    ("Pory", "szt"): ("Pory", "szt."),
    ("Selery młode", "szt"): ("Selery młode", "szt."),

    # Jabłka space → colon format (26 overlapping varieties)
    ("Jabłka Alwa", "kg"): ("Jabłka: Alwa", "kg"),
    ("Jabłka Antonówka", "kg"): ("Jabłka: Antonówki", "kg"),
    ("Jabłka Antonówki", "kg"): ("Jabłka: Antonówki", "kg"),
    ("Jabłka Boiken", "kg"): ("Jabłka: Boiken", "kg"),
    ("Jabłka Boskoop", "kg"): ("Jabłka: Boskoop", "kg"),
    ("Jabłka Celesta", "kg"): ("Jabłka: Celesta", "kg"),
    ("Jabłka Cortland", "kg"): ("Jabłka: Cortland", "kg"),
    ("Jabłka Delikates", "kg"): ("Jabłka: Delikates", "kg"),
    ("Jabłka Early Geneva", "kg"): ("Jabłka: Early Geneva", "kg"),
    ("Jabłka Elstar", "kg"): ("Jabłka: Elstar", "kg"),
    ("Jabłka Empire", "kg"): ("Jabłka: Empire", "kg"),
    ("Jabłka Gala", "kg"): ("Jabłka: Gala", "kg"),
    ("Jabłka Gloster", "kg"): ("Jabłka: Gloster", "kg"),
    ("Jabłka Golden", "kg"): ("Jabłka: Golden", "kg"),
    ("Jabłka Idared", "kg"): ("Jabłka: Idared", "kg"),
    ("Jabłka Jerseymac", "kg"): ("Jabłka: Jerseymac", "kg"),
    ("Jabłka Jonagold", "kg"): ("Jabłka: Jonagold", "kg"),
    ("Jabłka Jonagored", "kg"): ("Jabłka: Jonagored", "kg"),
    ("Jabłka Ligol", "kg"): ("Jabłka: Ligol", "kg"),
    ("Jabłka Lobo", "kg"): ("Jabłka: Lobo", "kg"),
    ("Jabłka Papierówki", "kg"): ("Jabłka: Papierówki", "kg"),
    ("Jabłka Paula Red", "kg"): ("Jabłka: Paula Red", "kg"),
    ("Jabłka Paula-Red", "kg"): ("Jabłka: Paula-Red", "kg"),
    ("Jabłka Paulared", "kg"): ("Jabłka: Paulared", "kg"),
    ("Jabłka Piros", "kg"): ("Jabłka: Piros", "kg"),
    ("Jabłka Rubin", "kg"): ("Jabłka: Rubin", "kg"),
    ("Jabłka Szara Reneta", "kg"): ("Jabłka: Szara Reneta", "kg"),
    ("Jabłka Szampion", "kg"): ("Jabłka: Champion", "kg"),
    ("Jabłka Champion", "kg"): ("Jabłka: Champion", "kg"),
    ("Jabłka Shampion", "kg"): ("Jabłka: Champion", "kg"),

    # Jabłka only in colon form (no space-form duplicate) — keep as-is but
    # listed here so the alias table is the single source of truth.
    ("Jabłka: Antonówki", "kg"): ("Jabłka: Antonówki", "kg"),
    ("Jabłka: Champion", "kg"): ("Jabłka: Champion", "kg"),
    ("Jabłka: Eliza", "kg"): ("Jabłka: Eliza", "kg"),
    ("Jabłka: Genewa", "kg"): ("Jabłka: Early Geneva", "kg"),
    ("Jabłka: Katja", "kg"): ("Jabłka: Katja", "kg"),
    ("Jabłka: Malinówki", "kg"): ("Jabłka: Malinówki", "kg"),
    ("Jabłka: Shampion", "kg"): ("Jabłka: Champion", "kg"),
    ("Jabłka: Szampion", "kg"): ("Jabłka: Champion", "kg"),

    # Data error: Jabłka Ogórki długie → should be removed, not aliased.
    # Kept commented so it's visible:
    # ("Jabłka Ogórki długie", "kg"): ???
}

# Units that should always carry a trailing dot
_UNITS_NEEDING_DOT = {"szt"}


def normalize_product(name: str, unit: str) -> tuple[str, str]:
    """Strip whitespace, normalize unit dots, resolve name aliases.

    Returns (canonical_name, canonical_unit).
    """
    name = name.strip()
    unit = unit.strip()

    # Normalize unit dot
    if unit in _UNITS_NEEDING_DOT:
        unit = "szt."

    # Resolve alias
    key = (name, unit)
    if key in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[key]

    return name, unit
