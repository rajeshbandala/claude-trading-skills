---
layout: default
title: "Robinhood Portfolio Manager"
grand_parent: English
parent: Skill Guides
nav_order: 42
lang_peer: /ja/skills/robinhood-portfolio-manager/
permalink: /en/skills/robinhood-portfolio-manager/
generated: true
---

# Robinhood Portfolio Manager
{: .no_toc }

Comprehensive portfolio analysis using Robinhood MCP Server integration to fetch holdings and positions, then analyze asset allocation, risk metrics, individual stock positions, diversification, and generate rebalancing recommendations. Optionally place orders with a strict confirm-first, one-order-at-a-time guardrail. Use when user requests portfolio review, position analysis, risk assessment, performance evaluation, rebalancing suggestions, or guided order placement for their Robinhood account.
{: .fs-6 .fw-300 }

<span class="badge badge-api">Robinhood Required</span>

[Download Skill Package (.skill)](https://github.com/tradermonty/claude-trading-skills/raw/main/skill-packages/robinhood-portfolio-manager.skill){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View Source on GitHub](https://github.com/tradermonty/claude-trading-skills/tree/main/skills/robinhood-portfolio-manager){: .btn .fs-5 .mb-4 .mb-md-0 }

<details open markdown="block">
  <summary>Table of Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## 1. Overview

Analyze and manage investment portfolios by integrating with a Robinhood MCP Server to fetch current holdings data, then performing comprehensive analysis covering asset allocation, diversification, risk metrics, individual position evaluation, and rebalancing recommendations. Generate detailed portfolio reports with actionable insights, and — only when the user explicitly opts in — execute approved orders one at a time through a confirm-first workflow.

This skill leverages the Robinhood brokerage API through MCP (Model Context Protocol) to access live portfolio data, ensuring analysis is based on actual current positions rather than manually entered data.

Robinhood accounts are **real-money** accounts (there is no paper/simulated mode). All execution is human-in-the-loop by design: this skill never auto-executes and never batches orders.

---

## 2. When to Use

Invoke this skill when the user requests:
- "Analyze my Robinhood portfolio"
- "Review my current positions"
- "What's my asset allocation?"
- "Check my portfolio risk"
- "Should I rebalance my portfolio?"
- "Evaluate my holdings"
- "Portfolio performance review"
- "What stocks should I buy or sell?"
- "Help me place this trade on Robinhood" (triggers the confirm-first execution workflow)
- "Show / update my watchlist" or "track these candidates" (triggers watchlist integration)
- Any request involving portfolio-level analysis, management, watchlists, or guided order placement on Robinhood

---

## 3. Prerequisites

### Robinhood MCP Server Setup

This skill requires a Robinhood MCP Server to be configured and connected. The MCP server provides access to:
- Current portfolio positions
- Account balances and buying power
- Live equity quotes for held and candidate securities
- Order history and order placement

**MCP Server Tools Used (logical names):**

Read tools (analysis):
- `get_accounts` - List brokerage accounts (returns `account_number`, `brokerage_account_type`, `type`, `nickname`, `is_default`, `agentic_allowed`)
- `get_portfolio` - Total value, cash, buying power, **and per-asset-class aggregates** (`equity_value`, `options_value`, `crypto_value`, `futures_value`, `event_contracts_value`, `mutual_funds_value`, `fixed_income_value`) for one account (needs `account_number`)
- `get_equity_positions` - Open equity positions for one account: `symbol`, `quantity`, `average_buy_price`, `shares_available_for_sells`, `intraday_quantity`, `type` (no market price — pair with `get_equity_quotes`)
- `get_equity_quotes` - Live quotes + official last-session close for up to ~20 symbols per call
- `get_equity_orders` - Existing/open and historical orders (used to reconcile stops and pending trades)
- `get_equity_tradability` - Whether a symbol is currently tradable

> **Equity-only enumeration:** `get_equity_positions` lists **equities only**.
> This MCP surface has **no** `get_option_positions` / `get_crypto_positions`
> tool, so options, crypto, futures, etc. are visible only as the **aggregate
> dollar values** in `get_portfolio` — never as individual contracts/lots. Report
> those sleeves by value and % of account, flag them as **un-enumerated risk**,
> and point the user to the Robinhood app for position-level detail.

Watchlist tools (candidate tracking):
- `get_watchlists` - List the user's watchlists (returns each list's `id` + name)
- `get_watchlist_items` - Items in a stock/ETF/crypto/index watchlist (needs `list_id`; no live prices — pair with `get_equity_quotes`)
- `get_options_watchlist` - The options watchlist (use this, NOT `get_watchlist_items`, for options)
- `get_popular_lists` - Curated/popular lists the user can follow
- `add_to_watchlist` / `remove_from_watchlist` / `create_watchlist` / `update_watchlist` - Modify watchlists (writes — confirm before calling)
- `add_option_to_watchlist` / `remove_option_from_watchlist` - Modify the options watchlist (writes — confirm)

Order tools (confirm-first execution only):
- `review_equity_order` - Dry-run preview of an order without placing it
- `place_equity_order` - Place a single order (ONLY after explicit user approval)
- `cancel_equity_order` - Cancel an existing order

> **Tool namespace note:** These tools are exposed under the user's configured
> Robinhood MCP server and appear in-session with a server-specific prefix
> (for example `mcp__<server>__get_equity_positions`). The server name/prefix
> varies by environment, so refer to the tools by their logical base names above
> and call whichever prefixed variant your session exposes. Do not hardcode a
> specific server prefix.

If the Robinhood MCP Server is not connected, inform the user and provide setup guidance from `references/robinhood-mcp-setup.md`.

---

## 4. Quick Start

```bash
Call get_accounts. It returns data.accounts[] with account_number,
brokerage_account_type, type (margin/cash), nickname, is_default, agentic_allowed.
```

---

## 5. Workflow

### Step 1: Fetch Portfolio Data via Robinhood MCP

Use the Robinhood MCP Server tools to gather current portfolio information. Every
read tool returns a `{"data": {...}, "guide": "..."}` envelope — read from `data`
and follow any `guide` instructions the server includes.

**1.0 Select the account (required before any per-account call):**
```
Call get_accounts. It returns data.accounts[] with account_number,
brokerage_account_type, type (margin/cash), nickname, is_default, agentic_allowed.
```
- If exactly one account exists, use it.
- If multiple accounts exist, **present them and ask the user to choose** — never
  silently default. `get_equity_positions` / `get_portfolio` require the chosen
  `account_number`.
- When displaying an account number to the user, **mask all but the last 4 digits**
  (e.g. `••••0794`); pass the full unmasked value to the tools.
- Sort for display: default first, then `agentic_allowed=true`, then other
  individual, then retirement.

**1.1 Get Account Value and Cash (`get_portfolio`, with `account_number`):**
Read from `data`:
- `total_value` — account/portfolio value
- `cash` — cash balance
- `buying_power.buying_power` — authoritative spendable figure (use for affordability)
- `equity_value`, `options_value`, `crypto_value`, … — asset-class breakdown
  (zero-value classes can be omitted from display)
- `currency` / `buying_power.display_currency`

**1.2 Get Current Positions (`get_equity_positions`, with `account_number`):**
Read `data.positions[]`; each position has:
- `symbol`, `quantity` (fractional supported), `type` (usually `long`)
- `average_buy_price` — average cost per share as shown in the Robinhood app
  (already reflects partial sells; **may be omitted** while a position reconciles)
- `shares_available_for_sells` — **use this for sellable shares, not `quantity`**
- `intraday_quantity` — yesterday's quantity = `quantity - intraday_quantity`
- **No market price or P&L is included** — compute those in Step 1.3.
- Paginate: if the response includes a `next` cursor, pass it back via `cursor`
  until all positions are retrieved.

**1.3 Enrich with Live Quotes (`get_equity_quotes`):**
```
Call get_equity_quotes with the held symbols (batch in groups of ≤20; above 20
the closes are omitted and closes_error is set, so chunk the request).
```
For each position compute: market value = `quantity × price`; unrealized P&L =
`(price − average_buy_price) × quantity` (skip P&L when `average_buy_price` is
missing); position weight = market value ÷ `total_value`.

> **No portfolio-history endpoint:** Unlike some brokers, the Robinhood MCP
> surface does not provide a portfolio-history time series. Derive performance
> context from current positions (unrealized P&L vs. cost basis) and note in the
> report that time-weighted historical return / drawdown is unavailable from the
> live feed. If the user wants historical return, ask them to supply it manually.

**1.4 Look at the options sleeve (and other non-equity sleeves):**
Whenever `get_portfolio` reports a non-zero `options_value` (or `crypto_value`,
`futures_value`, …), explicitly surface it instead of silently dropping it:
- Report the **aggregate dollar value and % of account** from `get_portfolio`.
- Call `get_options_watchlist` to list any **tracked single-leg option contracts**
  (each item's `name`, e.g. "Long Call AAPL Jan 2026 $200", and `option_ids`).
  This is a **watchlist, not holdings** — and multi-leg strategies are not shown.
- **Held option positions/orders cannot be enumerated** on this MCP surface (there
  is no `get_option_positions` / `get_option_orders`). State this plainly and point
  the user to the Robinhood app for contract-level detail (strikes, expiries, P&L).
  *If the environment exposes `get_option_quotes` / `review_option_order` /
  `place_option_order`, those work on individual `option_ids` (e.g. from the
  watchlist) but still do not list current holdings.*
- **Flag any aggregate-only sleeve >10% of the account as un-enumerated risk** — its
  leverage, direction, and expiries are invisible and may dominate account risk.
- Empty options watchlist + `options_value > 0` is normal: it means the user holds
  options they haven't watchlisted; the value is real but the legs are app-only.

**Data Validation:**
- Verify all positions have valid ticker symbols and that every held symbol got a quote
- Confirm computed market values + `cash` sum to approximately `total_value`
- Treat a missing `average_buy_price` as "cost basis pending" (report value, not P&L)
- Handle edge cases (fractional shares, cash-only accounts, non-equity holdings)

### Step 2: Enrich Position Data

For each position in the portfolio, gather additional market data and fundamentals:

**2.1 Current Market Data:**
- Live price quotes via `get_equity_quotes`
- Daily volume and liquidity metrics (via WebSearch if not in MCP)
- 52-week range
- Market capitalization

**2.2 Fundamental Data:**
Use WebSearch or available market data to fetch:
- Sector and industry classification
- Key valuation metrics (P/E, P/B, dividend yield)
- Recent earnings and financial health indicators
- Analyst ratings and price targets
- Recent news and material developments

**2.3 Technical Analysis:**
- Price trend (20-day, 50-day, 200-day moving averages)
- Relative strength
- Support and resistance levels
- Momentum indicators (RSI, MACD if available)

### Step 3: Portfolio-Level Analysis

Perform comprehensive portfolio analysis using frameworks from reference files.

#### 3.1 Asset Allocation Analysis

**Read references/asset-allocation.md** for allocation frameworks.

Analyze current allocation across multiple dimensions:

**By Asset Class:** Equities vs Fixed Income vs Cash vs Alternatives; compare to target allocation for the user's risk profile.

**By Sector:** Technology, Healthcare, Financials, Consumer, etc.; identify sector concentration risks; compare to benchmark sector weights (e.g., S&P 500).

**By Market Cap:** Large-cap vs Mid-cap vs Small-cap distribution; concentration in mega-caps.

**By Geography:** US vs International vs Emerging Markets; domestic concentration risk.

Always lead with the **multi-asset sleeve breakdown** from `get_portfolio`, so
non-equity sleeves are never silently dropped. Mark which sleeves this skill can
analyze at the position level (equities + cash) versus aggregate-only (options,
crypto, futures, …).

**Output Format:**
```markdown

---

## 6. Resources

**References:**

- `skills/robinhood-portfolio-manager/references/asset-allocation.md`
- `skills/robinhood-portfolio-manager/references/diversification-principles.md`
- `skills/robinhood-portfolio-manager/references/portfolio-risk-metrics.md`
- `skills/robinhood-portfolio-manager/references/position-evaluation.md`
- `skills/robinhood-portfolio-manager/references/rebalancing-strategies.md`
- `skills/robinhood-portfolio-manager/references/risk-profile-questionnaire.md`
- `skills/robinhood-portfolio-manager/references/robinhood-mcp-setup.md`
- `skills/robinhood-portfolio-manager/references/target-allocations.md`

**Scripts:**

- `skills/robinhood-portfolio-manager/scripts/check_robinhood_connection.py`
