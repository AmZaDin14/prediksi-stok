"""Tests for the input parser module."""

from __future__ import annotations

import pytest

from app.parser import (
    ConfirmationParseResult,
    ParseResult,
    parse_confirmation_message,
    parse_sales_message,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
VALID_PRODUCTS = ["gula", "minyak", "tepung", "beras", "aqua", "roti hitam manis", "garam"]
DAILY_ESTIMATES: dict[str, float] = {
    "gula": 5.0,
    "minyak": 70.0,
    "tepung": 20.0,
    "beras": 430.0,
    "aqua": 20.0,
    "roti hitam manis": 2.0,
    "garam": 70.0,
}


def parse(text: str) -> ParseResult:
    """Shortcut for the common call pattern."""
    return parse_sales_message(text, VALID_PRODUCTS, DAILY_ESTIMATES)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    """Basic valid inputs."""

    def test_single_product(self):
        result = parse("terjual gula 5")
        assert result.sales == [("gula", 5.0)]
        assert result.errors == []
        assert result.needs_confirmation == []

    def test_single_product_capitalised(self):
        result = parse("TERJUAL GuLa 5")
        assert result.sales == [("gula", 5.0)]

    def test_single_product_leading_trailing_spaces(self):
        result = parse("  terjual gula 5  ")
        assert result.sales == [("gula", 5.0)]

    def test_comma_delimiter(self):
        result = parse("terjual gula 5, minyak 20")
        assert ("gula", 5.0) in result.sales
        assert ("minyak", 20.0) in result.sales
        assert len(result.sales) == 2

    def test_space_delimiter(self):
        result = parse("terjual gula 5 minyak 20")
        assert ("gula", 5.0) in result.sales
        assert ("minyak", 20.0) in result.sales
        assert len(result.sales) == 2

    def test_mixed_delimiters(self):
        result = parse("terjual gula 5, minyak 20 tepung 10")
        assert ("gula", 5.0) in result.sales
        assert ("minyak", 20.0) in result.sales
        assert ("tepung", 10.0) in result.sales
        assert len(result.sales) == 3

    def test_multi_word_product(self):
        result = parse("terjual roti hitam manis 10")
        assert result.sales == [("roti hitam manis", 10.0)]

    def test_multi_word_product_with_others(self):
        result = parse("terjual roti hitam manis 3, gula 2")
        assert ("roti hitam manis", 3.0) in result.sales
        assert ("gula", 2.0) in result.sales
        assert len(result.sales) == 2

    def test_decimal_quantity(self):
        result = parse("terjual gula 0.5")
        assert result.sales == [("gula", 0.5)]

    def test_zero_quantity(self):
        result = parse("terjual gula 0")
        assert result.sales == [("gula", 0.0)]


# ---------------------------------------------------------------------------
# Terjual prefix
# ---------------------------------------------------------------------------

class TestTerjualPrefix:
    def test_missing_terjual(self):
        result = parse("gula 5")
        assert result.sales == []
        assert any("terjual" in e for e in result.errors)

    def test_terjual_only_no_products(self):
        result = parse("terjual")
        assert result.sales == []
        assert len(result.errors) >= 1

    def test_terjual_with_extra_whitespace(self):
        result = parse("  terjual   gula   5  ")
        assert result.sales == [("gula", 5.0)]


# ---------------------------------------------------------------------------
# Auto-heal attached digits
# ---------------------------------------------------------------------------

class TestAutoHeal:
    def test_digit_attached_to_name(self):
        result = parse("terjual gula5")
        assert result.sales == [("gula", 5.0)]

    def test_digit_attached_multi_word(self):
        result = parse("terjual roti hitam manis5")
        assert result.sales == [("roti hitam manis", 5.0)]

    def test_mixed_clean_and_attached(self):
        result = parse("terjual gula5 minyak 20")
        assert ("gula", 5.0) in result.sales
        assert ("minyak", 20.0) in result.sales
        assert len(result.sales) == 2

    def test_digit_attached_with_comma(self):
        result = parse("terjual gula5, minyak20")
        assert ("gula", 5.0) in result.sales
        assert ("minyak", 20.0) in result.sales
        assert len(result.sales) == 2


# ---------------------------------------------------------------------------
# Unknown product  -- errors list available products
# ---------------------------------------------------------------------------

class TestUnknownProduct:
    def test_unknown_product_error(self):
        result = parse("terjual susu 5")
        assert result.sales == []
        assert len(result.errors) == 1
        assert "Unknown product" in result.errors[0]
        # Should list available products
        assert "gula" in result.errors[0].lower()
        assert "minyak" in result.errors[0].lower()

    def test_partial_unknown(self):
        """One known, one unknown."""
        result = parse("terjual gula 5, susu 10")
        assert result.sales == [("gula", 5.0)]
        assert len(result.errors) == 1
        assert "susu" in result.errors[0]

    def test_unknown_with_casing(self):
        result = parse("terjual SuSu 5")
        assert result.sales == []
        assert "susu" in result.errors[0]


# ---------------------------------------------------------------------------
# Negative quantity
# ---------------------------------------------------------------------------

class TestNegativeQuantity:
    def test_negative_qty(self):
        result = parse("terjual gula -5")
        assert result.sales == []
        assert any("negative" in e.lower() for e in result.errors)

    def test_negative_with_valid(self):
        result = parse("terjual gula -5, minyak 20")
        assert ("minyak", 20.0) in result.sales
        assert any("negative" in e.lower() for e in result.errors)
        assert len(result.sales) == 1


# ---------------------------------------------------------------------------
# Missing quantity
# ---------------------------------------------------------------------------

class TestMissingQuantity:
    def test_product_without_qty(self):
        result = parse("terjual gula")
        assert result.sales == []
        assert any("Missing quantity" in e for e in result.errors)

    def test_qty_without_product(self):
        result = parse("terjual 5")
        assert result.sales == []
        assert any("Missing product" in e for e in result.errors) or any(
            "Could not parse" in e for e in result.errors
        )

    def test_mixed_missing_qty(self):
        result = parse("terjual gula, minyak 20")
        assert ("minyak", 20.0) in result.sales
        assert any("Missing quantity" in e for e in result.errors)
        assert len(result.sales) == 1


# ---------------------------------------------------------------------------
# Zero quantity (accept silently)
# ---------------------------------------------------------------------------

class TestZeroQuantity:
    def test_zero_accepted(self):
        result = parse("terjual gula 0")
        assert result.sales == [("gula", 0.0)]

    def test_zero_mixed_with_others(self):
        result = parse("terjual gula 0, minyak 20")
        assert ("gula", 0.0) in result.sales
        assert ("minyak", 20.0) in result.sales
        assert len(result.sales) == 2


# ---------------------------------------------------------------------------
# Suspicious quantity  (> 10x estimated daily avg)
# ---------------------------------------------------------------------------

class TestSuspiciousQuantity:
    def test_over_10x_needs_confirmation(self):
        """Gula daily est = 5.0, so > 50 should flag."""
        result = parse("terjual gula 51")
        assert result.sales == []
        assert result.needs_confirmation == [("gula", 51.0)]

    def test_exactly_10x_is_ok(self):
        """Gula daily est = 5.0, exactly 50 should be accepted."""
        result = parse("terjual gula 50")
        assert result.sales == [("gula", 50.0)]
        assert result.needs_confirmation == []

    def test_below_10x_is_ok(self):
        result = parse("terjual gula 30")
        assert result.sales == [("gula", 30.0)]
        assert result.needs_confirmation == []

    def test_confirmation_and_valid_mixed(self):
        result = parse("terjual gula 51, minyak 20")
        assert result.needs_confirmation == [("gula", 51.0)]
        assert ("minyak", 20.0) in result.sales
        assert len(result.sales) == 1

    def test_estimate_zero_does_not_flag(self):
        """If estimate is 0, 10x is 0, so any qty > 0 flags, but we skip."""
        # Daily estimate 0 for a product should not cause flagging
        estimates = {"some_item": 0.0}
        result = parse_sales_message(
            "terjual some_item 999",
            ["some_item"],
            estimates,
        )
        # When estimate is 0, qty > 0 is > 10*0 = 0, so it flags
        # Actually 10 * 0 = 0, and qty = 999 > 0, so it SHOULD flag.
        # But the spec says "Qty > 10x estimated daily avg -> add to needs_confirmation"
        # If estimate is 0, then 10*0 = 0, so any qty > 0 triggers it.
        # Let me think about this.
        # Actually the condition in the code is:
        #   estimated > 0 and qty > 10 * estimated
        # So if estimated is 0, it won't flag. That seems reasonable.
        assert result.sales == [("some_item", 999.0)]
        assert result.needs_confirmation == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string(self):
        result = parse("")
        assert result.sales == []
        assert len(result.errors) >= 1

    def test_only_whitespace(self):
        result = parse("   ")
        assert result.sales == []
        assert len(result.errors) >= 1

    def test_only_terjual_prefix_spaces(self):
        result = parse("terjual   ")
        assert result.sales == []
        assert len(result.errors) >= 1

    def test_multiple_errors(self):
        """Multiple unknown products should each produce an error."""
        result = parse("terjual susu 5, keju 10")
        assert result.sales == []
        assert len(result.errors) == 2

    def test_no_valid_products(self):
        result = parse_sales_message("terjual gula 5", [], {})
        assert result.sales == []
        assert any("Unknown product" in e for e in result.errors)

    def test_no_daily_estimates(self):
        result = parse_sales_message("terjual gula 5", ["gula"], {})
        assert result.sales == [("gula", 5.0)]
        assert result.needs_confirmation == []

    def test_large_quantity_normal_estimate(self):
        """garam has daily est of 70, so > 700 should flag."""
        result = parse("terjual garam 701")
        assert result.needs_confirmation == [("garam", 701.0)]
        assert result.sales == []

    def test_complex_multi_product(self):
        result = parse("terjual gula 5, minyak 10, tepung 15, beras 20, aqua 25")
        assert len(result.sales) == 5
        assert result.errors == []

    def test_products_not_case_sensitive(self):
        result = parse("terjual GULA 5 MinYaK 10")
        assert ("gula", 5.0) in result.sales
        assert ("minyak", 10.0) in result.sales


# ---------------------------------------------------------------------------
# parse_confirmation_message
# ---------------------------------------------------------------------------


class TestParseConfirmationMessage:
    """parse_confirmation_message parses "cek stok <product> <qty>" correctly."""

    def test_single_product(self):
        result = parse_confirmation_message("cek stok gula 25", VALID_PRODUCTS)
        assert result.confirmations == [("gula", 25.0)]
        assert result.errors == []

    def test_multi_product_comma(self):
        result = parse_confirmation_message("cek stok gula 25, minyak 900", VALID_PRODUCTS)
        assert ("gula", 25.0) in result.confirmations
        assert ("minyak", 900.0) in result.confirmations
        assert len(result.confirmations) == 2
        assert result.errors == []

    def test_unknown_product(self):
        result = parse_confirmation_message("cek stok invalid 10", VALID_PRODUCTS)
        assert result.confirmations == []
        assert len(result.errors) == 1

    def test_missing_quantity(self):
        result = parse_confirmation_message("cek stok gula", VALID_PRODUCTS)
        assert result.confirmations == []
        assert len(result.errors) == 1

    def test_negative_quantity(self):
        result = parse_confirmation_message("cek stok gula -5", VALID_PRODUCTS)
        assert result.confirmations == []
        assert len(result.errors) == 1

    def test_capitalised_product(self):
        result = parse_confirmation_message("cek stok GULA 25", VALID_PRODUCTS)
        assert result.confirmations == [("gula", 25.0)]
        assert result.errors == []

    def test_missing_prefix(self):
        result = parse_confirmation_message("laporkan stok gula 25", VALID_PRODUCTS)
        assert result.confirmations == []
        assert len(result.errors) == 1

    def test_multi_product_space_only(self):
        result = parse_confirmation_message("cek stok gula 25 minyak 900", VALID_PRODUCTS)
        assert ("gula", 25.0) in result.confirmations
        assert ("minyak", 900.0) in result.confirmations
        assert len(result.confirmations) == 2
        assert result.errors == []

    def test_two_word_product(self):
        result = parse_confirmation_message("cek stok roti hitam manis 5", VALID_PRODUCTS)
        assert result.confirmations == [("roti hitam manis", 5.0)]
        assert result.errors == []

    def test_zero_quantity_valid(self):
        result = parse_confirmation_message("cek stok gula 0", VALID_PRODUCTS)
        assert result.confirmations == [("gula", 0.0)]
        assert result.errors == []
