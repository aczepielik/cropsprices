"""Tests for product name normalization and deduplication."""

import pytest

from cropsprices.product_normalize import PRODUCT_ALIASES, normalize_product


class TestChampionDeduplication:
    """Shampion, Szampion, and Champion should all normalize to the same name.

    Regression test for a bug where Szampion mapped to itself instead of
    Champion, causing the three variants to be counted separately and
    each too sparse to make the whitelist.
    """

    VARIANTS = [
        ("Jabłka Champion", "kg"),
        ("Jabłka: Champion", "kg"),
        ("Jabłka Shampion", "kg"),
        ("Jabłka: Shampion", "kg"),
        ("Jabłka Szampion", "kg"),
        ("Jabłka: Szampion", "kg"),
    ]

    def test_all_variants_normalize_to_champion(self):
        canonical = normalize_product("Jabłka: Champion", "kg")
        for name, unit in self.VARIANTS:
            result = normalize_product(name, unit)
            assert result == canonical, (
                f"normalize_product({name!r}, {unit!r}) = {result}, "
                f"expected {canonical}"
            )

    def test_no_self_referencing_aliases_that_should_merge(self):
        """An alias that maps to itself is pointless unless it's a canonical
        entry.  No variant of 'Champion' should map to itself."""
        champion_canonical = ("Jabłka: Champion", "kg")
        for name, unit in self.VARIANTS:
            key = (name, unit)
            if key in PRODUCT_ALIASES:
                target = PRODUCT_ALIASES[key]
                if key != champion_canonical:
                    assert target == champion_canonical, (
                        f"Alias {key} maps to {target}, "
                        f"expected {champion_canonical}"
                    )


class TestAliasTableSanity:
    """Verify the alias table is internally consistent."""

    def test_no_circular_aliases(self):
        """Following alias chains should always terminate (max depth 10).

        Self-referential entries (key maps to itself) are allowed — they
        mark canonical names.
        """
        for key in PRODUCT_ALIASES:
            seen = set()
            current = key
            for _ in range(10):
                if current not in PRODUCT_ALIASES or PRODUCT_ALIASES[current] == current:
                    break
                assert current not in seen, (
                    f"Circular alias detected: {key} → {current}"
                )
                seen.add(current)
                current = PRODUCT_ALIASES[current]

    def test_space_to_colon_apples_always_add_colon(self):
        """Space-form 'Jabłka X' entries should map to colon-form 'Jabłka: Y'."""
        for (name, unit), (target_name, _) in PRODUCT_ALIASES.items():
            if name.startswith("Jabłka ") and not name.startswith("Jabłka:"):
                assert target_name.startswith("Jabłka:"), (
                    f"Space-form apple alias {name!r} maps to {target_name!r} "
                    f"which doesn't use colon format"
                )


class TestNormalizeProduct:
    """Unit tests for normalize_product."""

    def test_strips_whitespace(self):
        assert normalize_product("  Jabłka Gala  ", "  kg  ") == (
            "Jabłka: Gala", "kg"
        )

    def test_unit_dot_normalization(self):
        assert normalize_product("Kapusta młoda", "szt") == (
            "Kapusta młoda", "szt."
        )

    def test_unknown_product_passes_through(self):
        assert normalize_product("Jabłka: Gala", "kg") == (
            "Jabłka: Gala", "kg"
        )
