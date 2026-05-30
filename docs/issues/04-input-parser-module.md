# 04 - Input Parser module

**Type:** AFK

## Parent

PRD.md

## What to build

A pure-function module that parses WhatsApp message text into structured sales data.

Module interface:
- `parse_sales_message(raw_text: str, valid_products: list[str]) -> ParseResult`
- `ParseResult` = `{ sales: list[(product, quantity)], errors: list[str], needs_confirmation: list[(product, quantity)] }`

Rules:
- Strip and lowercase input
- Accept comma-separated or space-separated: `terjual gula 5, minyak 20` or `terjual gula 5 minyak 20`
- Auto-heal: `gula5` → `gula 5` (digit attached to name), extra whitespace collapsed
- Reject: unknown product name with error listing available products
- Reject: negative quantity with error
- Reject: missing quantity with format reminder
- Accept zero quantity (no warning)
- Flag for confirmation: quantity > 10x estimated daily average (from product catalog)
- `terjual` keyword required — `gula 5` alone is rejected with format reminder

## Acceptance criteria

- [ ] Parses standard input: `"terjual gula 5, minyak 20"` → 2 sales, no errors
- [ ] Auto-heals casing: `"Terjual Gula 5"` → 1 sale
- [ ] Auto-heals attached digit: `"terjual gula5"` → 1 sale
- [ ] Auto-heals extra whitespace: `"terjual  gula   5"` → 1 sale
- [ ] Accepts comma or space delimiter
- [ ] Rejects unknown product `"terjual mink 5"` with error listing available products
- [ ] Rejects negative: `"terjual gula -5"` with error
- [ ] Rejects missing quantity: `"terjual gula"` with format reminder
- [ ] Rejects missing keyword: `"gula 5"` with format reminder
- [ ] Accepts zero: `"terjual gula 0"` with no error
- [ ] Flags absurd quantity: `"terjual gula 9999"` needs confirmation

## Blocked by

None — depends only on product catalog shape which is stable
