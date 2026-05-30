"""Input parser for Prediksi Stok WhatsApp messages.

Handles parsing of "terjual <product> <qty>[, ...]" messages
with auto-correction, validation, and suspicious-qty detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParseResult:
    """Result of parsing a sales message.

    Attributes:
        sales: List of (product_name, quantity) tuples that passed validation.
        errors: Human-readable error messages for invalid entries.
        needs_confirmation: List of (product_name, quantity) tuples whose
            quantity exceeds 10x the estimated daily average.
    """

    sales: list[tuple[str, float]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    needs_confirmation: list[tuple[str, float]] = field(default_factory=list)


# Regex to match a product+quantity pair.
# Captures product name (word characters and spaces) then quantity.
# Quantity may be negative, integer, or decimal.
_PAIR_RE = re.compile(
    r"""
    (?P<product>[\w\s]+?)        # product name (non-greedy)
    \s*                          # optional whitespace
    (?P<qty>-?\d+(?:\.\d+)?)    # quantity (optional minus, integer or decimal)
    (?:\s|,|$)                   # separator (space, comma, or end-of-string)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Pattern to detect a lone number (used inside _split_pairs).
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _normalise_text(raw: str) -> str:
    """Strip, lowercase, and collapse whitespace."""
    return " ".join(raw.strip().lower().split())


def _heal_attached_digit(token: str) -> str:
    """Insert a space between a product name and a trailing digit.

    "gula5" -> "gula 5", "roti2" -> "roti 2".
    Does NOT split decimal numbers ("0.5" stays unchanged).
    Only splits when digits are immediately preceded by a letter
    so that decimals like "0.5" are not broken.
    """
    m = re.search(r"(?<=[a-zA-Z])(\d+)$", token)
    if m:
        name_part = token[: m.start()]
        qty_part = token[m.start() :]
        return f"{name_part} {qty_part}"
    return token


def _parse_clause(clause: str) -> list[str]:
    """Parse a single comma-free clause into product-qty pairs.

    A clause is expected to contain alternating product-name tokens and
    quantity tokens separated by whitespace, e.g. "gula 5 minyak 20".
    Handles auto-heal of attached digits within tokens.
    """
    tokens = clause.split()
    # First pass: heal attached digits (gula5 -> gula 5)
    healed: list[str] = []
    for tok in tokens:
        healed_tok = _heal_attached_digit(tok)
        healed.extend(healed_tok.split())

    pairs: list[str] = []
    name_parts: list[str] = []
    for tok in healed:
        if _NUMBER_RE.match(tok):
            if name_parts:
                pairs.append(f"{' '.join(name_parts)} {tok}")
                name_parts = []
            else:
                # Quantity without preceding name — emit bare for error handling
                pairs.append(tok)
        else:
            name_parts.append(tok)
    # Leftover name parts with no trailing quantity
    if name_parts:
        pairs.append(" ".join(name_parts))

    return pairs


def _split_pairs(text: str) -> list[str]:
    """Split the raw text after 'terjual' into individual product-qty pairs.

    Commas act as hard pair separators (boundaries).  Within each
    comma-delimited clause, whitespace-separated tokens are grouped into
    alternating name/qty pairs.
    """
    # Normalise whitespace first (but keep commas)
    text = " ".join(text.split())
    # Split on commas to get clauses
    clauses = [c.strip() for c in text.split(",") if c.strip()]
    pairs: list[str] = []
    for clause in clauses:
        pairs.extend(_parse_clause(clause))
    return pairs


def parse_sales_message(
    raw_text: str,
    valid_products: list[str],
    daily_estimates: dict[str, float],
) -> ParseResult:
    """Parse a ``terjual`` sales report message.

    Args:
        raw_text: The raw message text from WhatsApp.
        valid_products: List of recognised product names (lowercase).
        daily_estimates: Mapping of lowercase product name to its estimated
            average daily sales quantity.

    Returns:
        A :class:`ParseResult` with validated sales, errors, and
        confirmation-flagged entries.
    """
    result = ParseResult()
    text = _normalise_text(raw_text)

    # --- Require "terjual" prefix -------------------------------------------
    prefix = "terjual"
    if not text.startswith(prefix):
        result.errors.append(
            'Message must start with "terjual" (e.g. "terjual gula 5, minyak 20").'
        )
        return result

    body = text[len(prefix) :].strip()
    if not body:
        result.errors.append(
            'No products found after "terjual". '
            'Expected format: "terjual <product> <qty>[, <product> <qty>...]'
        )
        return result

    # --- Split into individual pairs -----------------------------------------
    pairs = _split_pairs(body)

    valid_lower = {p.lower(): p for p in valid_products}
    lower_estimates = {k.lower(): v for k, v in daily_estimates.items()}

    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue

        # Parse "name qty" using regex for robustness
        m = _PAIR_RE.fullmatch(pair)
        if not m:
            # Could be a lone product name (missing qty) or a lone number
            # Check if it looks like just a name
            if re.match(r"^[\w\s]+$", pair) and not re.search(r"\d", pair):
                result.errors.append(
                    f'Missing quantity for "{pair}". '
                    'Format: "terjual <product> <qty>"'
                )
            elif _NUMBER_RE.match(pair):
                result.errors.append(
                    f'Missing product name for quantity "{pair}". '
                    'Format: "terjual <product> <qty>"'
                )
            else:
                result.errors.append(
                    f'Could not parse "{pair}". '
                    'Format: "terjual <product> <qty>"'
                )
            continue

        name_raw = m.group("product").strip()
        qty_raw = m.group("qty")

        # --- Validate product name -------------------------------------------
        if not name_raw:
            result.errors.append(
                f'Missing product name for quantity "{qty_raw}". '
                'Format: "terjual <product> <qty>"'
            )
            continue

        name_lower = name_raw.lower()
        if name_lower not in valid_lower:
            available = ", ".join(sorted(valid_products))
            result.errors.append(
                f'Unknown product "{name_raw}". Available products: {available}'
            )
            continue

        canonical_name = valid_lower[name_lower]
        qty = float(qty_raw)

        # --- Validate quantity -----------------------------------------------
        if qty < 0:
            result.errors.append(
                f"Negative quantity ({qty}) for \"{canonical_name}\" is not allowed."
            )
            continue

        # --- Zero is accepted silently (no special treatment needed) ---------

        # --- Qty > 10x estimated daily avg -> flag for confirmation ----------
        estimated = lower_estimates.get(name_lower)
        if estimated is not None and estimated > 0 and qty > 10 * estimated:
            result.needs_confirmation.append((canonical_name, qty))
        else:
            result.sales.append((canonical_name, qty))

    return result
