---
name: trading-desk-operator
description: Run a disciplined, risk-first equities trading desk over a Robinhood (MCP) book and watchlist, posting a clean briefing to Slack each cycle. Pulls the watchlist and book from ALL accounts (read-only) but manages risk and places REAL orders only on the agentic-allowed account through a confirm-first gate (with an optional bounded auto-execution mode). Use when the user says "run the desk", asks for a pre-market/midday/power-hour/end-of-day/weekly trading cycle, wants risk-based sizing and bracket orders, position management with stops, or a ranked setup briefing for their Robinhood watchlist.
---

# Trading Desk Operator

## Overview

Operate as a disciplined, risk-first equities trading desk on top of a Robinhood
MCP Server and (optionally) a Slack connector. Each cycle reads the market
environment, the news, and the chart structure for the user's watchlist and open
positions; ranks actionable setups by quality; sizes each trade by risk with a
predefined stop and target; manages existing positions; and posts a numbers-first
briefing to a Slack channel.

**Account model (critical):**
- **Read across all accounts.** Pull the watchlist universe and the full book
  (positions, P&L, concentration) from every brokerage account.
- **Execute on one account only.** Place, review, or cancel orders **exclusively**
  on the account with `agentic_allowed: true`. Every other account is read-only —
  recommendations for those are *advisory* (the user places them manually).
- Size all new risk against the **executing account's** equity and buying power,
  not the combined book.

**Capital preservation first, returns second.** Default execution is
**propose, don't fire**: no order without a `review_equity_order` preview and the
user's explicit confirmation of that specific order. A bounded auto-execution mode
exists but is **off unless the user explicitly turns it on** with hard limits
(see `references/execution-protocol.md`).

> **Real money.** Robinhood accounts are live; there is no paper mode. This skill
> automates *analysis, risk math, journaling, and communication*. It is **not
> financial advice** and trading risks loss of principal.

## When to Use

- "Run the desk" / "run my pre-market (or midday / power-hour / EOD / weekly) cycle"
- "Analyze my watchlist and propose trades on my agentic account"
- "Size this trade by risk with a stop and target"
- "Manage my positions — where are my stops?"
- "Give me a ranked briefing and post it to Slack #trading"
- Any request to operate a risk-managed equities book over Robinhood + watchlist

## Prerequisites

- **Robinhood MCP Server** connected (book, quotes, watchlists, order tools).
  Logical tool names below; in-session they carry a server-specific prefix
  (e.g. `mcp__<server>__get_accounts`). Refer to logical names; call whichever
  prefixed variant the session exposes — never hardcode a prefix.
  - Read: `get_accounts`, `get_portfolio`, `get_equity_positions`,
    `get_equity_quotes`, `get_equity_orders`, `get_equity_tradability`,
    `get_watchlists`, `get_watchlist_items`, `search`
  - Watchlist writes (confirm-first): `create_watchlist`, `add_to_watchlist`,
    `remove_from_watchlist`, `update_watchlist`
  - Order tools (executing account only): `review_equity_order`,
    `place_equity_order`, `cancel_equity_order`
- **Slack connector** (optional but recommended) for the `#trading` briefing:
  `slack_search_channels`, `slack_send_message`.
- **WebSearch** for regime and per-name news.
- **Python 3.9+** (stdlib only) for `scripts/desk_risk.py`. No API keys.

If the Robinhood MCP server is not connected, say so and stop — the desk cannot
read the book or place orders without it.

## Workflow

Run the block matching the current time (the user triggers each cycle; this skill
never runs itself). If the user just says "run the desk," infer the block from the
clock. See `references/cadence-playbook.md` for the per-block checklist
(pre-market / midday / power-hour / end-of-day / weekly).

### Step 1 — Resolve accounts and pick the executing account

Call `get_accounts`. Identify the **one** account with `agentic_allowed: true` —
this is the **executing account**. Treat all others as **read-only**. Mask account
numbers to the last 4 digits in any user-facing or Slack output (`••••0794`); pass
full values to tools. If no account is `agentic_allowed`, say so — you can analyze
but cannot place any orders.

### Step 2 — Pull the watchlist universe (all accounts) and consolidate

Robinhood watchlists are **user-level** (shared across accounts), so
`get_watchlists` returns the full set regardless of account. Read every custom
equity list with `get_watchlist_items` and union the symbols into the cycle's
universe. Drop the options watchlist (different shape).

**Optional consolidation (confirm-first write):** if the user wants a single
operating list on the executing account, offer to `create_watchlist` (e.g.
"Agentic Desk") and `add_to_watchlist` the union of symbols. Show the exact list
name + symbols and get a yes before writing — these are account-data mutations
(no money, but still writes).

### Step 3 — Read the full book (all accounts)

For each account, `get_portfolio` (value, cash, `buying_power.buying_power`,
sleeve breakdown) and `get_equity_positions`. Batch `get_equity_quotes` (≤20
symbols/call to keep official closes) across all position + watchlist symbols.
Compute per position: market value, unrealized P&L vs `average_buy_price`, weight.
Check `get_equity_orders` (state `queued`/`new`/`confirmed`) on each account to
see which positions already have **protective stops** — flag any naked position.

### Step 4 — Regime, news, technicals (analysis)

- **A. Regime first.** WebSearch the broad-market trend (uptrend / chop /
  downtrend), Fed path, and **scheduled event risk** (CPI/PPI/FOMC/jobs). The
  regime sets the net-exposure ceiling — lighter/smaller longs in a weak or
  event-loaded tape. Read `references/risk-management.md` for the ceiling guide.
- **B. News.** For each watchlist name and position, scan catalysts (earnings,
  guidance, upgrades, regulatory). Classify tailwind / headwind / noise. **Flag
  earnings inside the holding window — no new swing entries into a print** unless
  the user explicitly wants the event trade.
- **C. Technicals.** Trend vs structure, key support/resistance, a clean trigger
  level; distinguish *ready* setups from *watch-only*. **No trigger, no trade.**
  > These MCP tools return quotes but **no historical bars** — moving averages and
  > swing-low precision are limited. State this; lean on round-number support,
  > prior closes, and any chart the user provides, and label level reads as
  > approximate rather than implying MA precision.

### Step 5 — Rank and size (executing account)

Rank candidates on trend alignment, setup cleanliness, risk/reward (target ≥ 2R),
catalyst, and liquidity. Present the **top few only**. For each candidate, size
against the **executing account** with the risk engine:

```bash
python3 skills/trading-desk-operator/scripts/desk_risk.py size \
  --account-equity 500 --entry 94.6 --stop 88.0 \
  --risk-pct 1.0 --max-risk-pct 2.0 --target-r 2.0 --output-dir reports/
```

The engine returns **both** a whole-share plan (can carry a resting GTC stop) and
a fractional plan (Robinhood holds **no resting stop on fractional shares** — exit
is managed/market), plus the 2R target and buying-power / max-risk guards. Prefer
the whole-share plan when it fits within the per-trade risk cap; if a single share
already exceeds `max_risk_pct`, the trade is flagged `fractional_or_skip` — for a
risk-first desk, lean toward skip or a cheaper, granular name. Before proposing any
order, call `get_equity_tradability` on the executing account.

### Step 6 — Manage existing positions

For each open position (all accounts): is the thesis intact? Above/below its stop?
Take partials at +1R / first target and trail the rest; cut anything that closed
through its stop; don't average down a broken thesis. Build the **stop sheet** and
portfolio heat:

```bash
python3 skills/trading-desk-operator/scripts/desk_risk.py stops \
  --positions reports/book_positions.json --account-equity 98700 \
  --default-stop-pct 8.0 --heat-cap-pct 6.0 --output-dir reports/
```

Stops for read-only accounts are **advisory** — present them for manual placement.
Stops/targets for the executing account become real bracket orders in Step 7.

### Step 7 — Execution (confirm-first gate)

Default = **propose, don't fire.** Follow `references/execution-protocol.md`
exactly. For each proposed trade on the **executing account**:
1. `search` to resolve the ticker; pull a live quote; `get_equity_tradability`.
2. Build the order: side, qty (from the risk math), type (prefer a marketable
   limit over plain market for entries), **stop-loss** and **target/limit-sell**.
3. `review_equity_order` to simulate; present estimated cost, BP impact,
   R-multiple, and any alerts.
4. **Wait for the user's explicit "yes" on that specific order.** A generic
   "do it" is not a bypass — restate the order and get the yes.
5. On yes → `place_equity_order` with a fresh `ref_id`; then place/track the
   protective stop and target as the bracket.
6. Log it.

> **Risk overrides setups.** The daily 3% / weekly 6% loss limits, the 6% heat
> cap, and the no-entry-through-earnings rule override any setup. When in doubt,
> smaller or flat.

### Step 8 — Briefing to Slack

Confirm the target channel the first time (`slack_search_channels` → `#trading`).
Build the numbers-first briefing per `references/slack-briefing-format.md` and post
with `slack_send_message`. Lead with the regime line, book table, ranked setups,
risk/heat status, and an explicit "actions pending confirm" list. Mask account
numbers. Always present the briefing for the user to see; post on confirmation.

### Step 9 — Report what you did and did NOT do

Close every cycle with what executed, and — importantly — **what you deliberately
did not do and why** (skipped entries, naked stops left to the user, limits hit).
Save a cycle report to `reports/` with a date stamp.

## Output Format

- **Slack briefing:** `references/slack-briefing-format.md` template.
- **Cycle report:** `reports/desk_<block>_YYYY-MM-DD.md` (regime, book, setups,
  risk, actions taken / pending / declined).
- **Risk engine:** `reports/desk_size_*.json|md` and `reports/desk_stops_*.json|md`.

## Resources

- `scripts/desk_risk.py` — offline risk engine: `size` (whole-share + fractional
  sizing, 2R target, BP / max-risk guards) and `stops` (stop sheet + portfolio
  heat, auto-stop fill, winner-locks-gain flag).
- `references/risk-management.md` — risk rules: per-trade %, heat cap, daily/weekly
  loss limits, concentration, stop placement, net-exposure ceiling by regime.
- `references/execution-protocol.md` — confirm-first gate, executing-account-only
  rule, fractional-stop constraint, `ref_id` idempotency, bounded auto-execution.
- `references/cadence-playbook.md` — per-block checklists (pre-market, midday,
  power-hour, end-of-day, weekly).
- `references/slack-briefing-format.md` — the numbers-first `#trading` template.

## Hard Rules

- Capital preservation before profit. When in doubt, smaller or flat.
- Execute only on the `agentic_allowed` account; everything else is advisory.
- No new entries through earnings unless the user asked for the event trade.
- No order without `review_equity_order` + explicit confirmation (unless bounded
  auto-execution is explicitly enabled with limits).
- Respect the daily/weekly loss limits and the heat cap — they override any setup.
- State assumptions; if data is stale or a tool fails, say so rather than guessing.
- Frame everything in probabilities and predefined risk. This is not advice.
