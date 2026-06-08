# Candidate Discovery (news + technicals, S&P 500 only)

The desk is not limited to the watchlist. Each cycle it may **discover** fresh
long candidates from news and technical strength — but every discovered pick must
be a **current S&P 500 constituent**. This keeps the universe liquid, well-covered,
and inside the user's mandate.

Discovery *supplements* the watchlist universe; it never lowers the bar. Only
A-quality setups survive ranking, and the regime ceiling + event-risk rules in
`risk-management.md` still gate how much new risk gets added.

## 1. News-driven candidates

Use WebSearch to surface names with a real, fresh catalyst (prefer ≤ ~5 trading
days old):
- "biggest stock gainers today / this week", "stocks making new 52-week highs"
- earnings beats with strong guidance; analyst upgrades / price-target raises
- sector tailwinds, product launches, regulatory wins, large contract awards

For each surfaced name, classify the catalyst **tailwind / headwind / noise** and
keep only tailwinds with follow-through. Discard pure headline pops with no
structure. **No new swing entries into an upcoming earnings print** unless the user
asked for the event trade.

## 2. Technical-driven candidates

Favor leadership and trend continuation:
- Trading at/near new highs or breaking a clean base; above rising 20/50/200-day MAs
- Strong relative strength vs. SPY; constructive volume on up-days
- A clean, definable trigger and a structure-based stop (≥ 2R to target)

> **Data limit:** the Robinhood MCP tools give live quotes but **no historical
> bars**. Moving-average and swing-low precision is limited — lean on round-number
> support, prior closes, new-high context, and any chart the user supplies, and
> label level reads as approximate. Use `get_equity_quotes` for live prices on
> discovered names; `get_equity_tradability` before proposing an order.

## 3. The S&P 500 membership gate (mandatory)

Before a discovered name can be ranked or proposed, confirm S&P 500 membership:

```bash
python3 skills/trading-desk-operator/scripts/sp500_filter.py \
  --tickers "NVDA,UBER,SOFI,JPM" --as-of <today> --output-dir reports/
```

- **`in_sp500`** — snapshot-confirmed members; eligible to proceed.
- **`unverified`** — not in the bundled snapshot. Do **not** reject silently and do
  **not** propose yet: confirm membership **live** via WebSearch
  ("is `<TICKER>` a current S&P 500 constituent?"). Include only if confirmed.
- **`stale: true`** — the snapshot is older than `--max-age-days`. Verify **every**
  discovered pick live, not just the unverified ones.

The bundled snapshot (`assets/sp500_constituents.json`) is a **fast-path cache, not
the source of truth** — index membership changes ~20×/year. WebSearch is the
authoritative check. Watchlist names the user explicitly tracks are exempt from this
gate (the user chose them); the gate applies to **discovered** candidates only.

> Common rejects this catches: foreign ADRs (e.g. TSM, BABA), recent IPOs not yet
> added, and small-caps — all liquid enough to trade but outside the S&P 500
> mandate. Exclude them from discovery.

## 4. Merge and proceed

Union the confirmed discovered candidates with the watchlist universe, de-dupe, then
rank and size exactly as in the main workflow (Step 5). In the briefing, mark each
setup's origin — `watchlist` or `discovered` — and for discovered names note the
catalyst and that S&P 500 membership was confirmed.

## Refreshing the snapshot

When the snapshot goes stale, replace `assets/sp500_constituents.json` from an
official/maintained source (e.g. an S&P 500 constituents CSV), keeping the
`as_of` / `source` / `symbols` shape. Re-run the filter tests after updating:

```bash
python3 -m pytest skills/trading-desk-operator/scripts/tests/test_sp500_filter.py -q
```
