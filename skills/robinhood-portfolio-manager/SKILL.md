---
name: robinhood-portfolio-manager
description: Comprehensive portfolio analysis using Robinhood MCP Server integration to fetch holdings and positions, then analyze asset allocation, risk metrics, individual stock positions, diversification, and generate rebalancing recommendations. Optionally place orders with a strict confirm-first, one-order-at-a-time guardrail. Use when user requests portfolio review, position analysis, risk assessment, performance evaluation, rebalancing suggestions, or guided order placement for their Robinhood account.
---

# Robinhood Portfolio Manager

## Overview

Analyze and manage investment portfolios by integrating with a Robinhood MCP Server to fetch current holdings data, then performing comprehensive analysis covering asset allocation, diversification, risk metrics, individual position evaluation, and rebalancing recommendations. Generate detailed portfolio reports with actionable insights, and — only when the user explicitly opts in — execute approved orders one at a time through a confirm-first workflow.

This skill leverages the Robinhood brokerage API through MCP (Model Context Protocol) to access live portfolio data, ensuring analysis is based on actual current positions rather than manually entered data.

Robinhood accounts are **real-money** accounts (there is no paper/simulated mode). All execution is human-in-the-loop by design: this skill never auto-executes and never batches orders.

## When to Use

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

## Prerequisites

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

## Workflow

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
## Asset Allocation

### Sleeve Breakdown (from get_portfolio)
| Sleeve | Value | Weight | Position-level detail? |
|--------|-------|--------|------------------------|
| Equities | $XX,XXX | XX.X% | ✅ enumerated below |
| Cash | $XX,XXX | XX.X% | ✅ (buying power: $X) |
| Options | $XX,XXX | XX.X% | ❌ aggregate only — not in MCP; see Robinhood app |
| Crypto | $XX,XXX | XX.X% | ❌ aggregate only — not in MCP; see Robinhood app |

> Flag any aggregate-only sleeve >10% as **un-enumerated risk** — its leverage,
> direction, and expiries are invisible to this skill and can dominate account risk.

### Current Equity Allocation vs Target
| Asset Class | Current | Target | Variance |
|-------------|---------|--------|----------|
| US Equities | XX.X% | YY.Y% | +/- Z.Z% |

### Sector Breakdown
[Table with sector percentages]

### Top 10 Holdings
| Rank | Symbol | % of Portfolio | Sector |
|------|--------|----------------|--------|
| 1 | AAPL | X.X% | Technology |
```

#### 3.2 Diversification Analysis

**Read references/diversification-principles.md** for diversification theory.

Evaluate diversification quality: position concentration (flag any single position >10-15%, compute HHI), sector concentration (flag any sector >30-40%), correlation between major positions, and position count (optimal 15-30; flag <10 or >50).

**Output:**
```markdown
## Diversification Assessment

**Concentration Risk:** [Low / Medium / High]
- Top 5 holdings represent XX% of portfolio
- Largest single position: [SYMBOL] at XX%

**Sector Diversification:** [Excellent / Good / Fair / Poor]
- Dominant sector: [Sector Name] at XX%

**Position Count:** [Optimal / Under-diversified / Over-diversified]
- Total positions: XX stocks

**Correlation Concerns:**
- [Highly correlated position pairs and improvement suggestions]
```

#### 3.3 Risk Analysis

**Read references/portfolio-risk-metrics.md** for risk measurement frameworks.

Calculate and interpret: estimated portfolio beta (weighted average of position betas), individual position volatilities, positions with significant unrealized losses, percentage in high-volatility stocks (beta > 1.5), and single-stock / sector concentration risk.

> Maximum drawdown from a portfolio-history series is **not available** from the
> Robinhood live feed. Report current drawdown only as the aggregate unrealized
> loss from cost basis, and clearly label it as such.

**Output:**
```markdown
## Risk Assessment

**Overall Risk Profile:** [Conservative / Moderate / Aggressive]
**Portfolio Beta:** X.XX (vs market at 1.00)

**High-Risk Positions:**
| Symbol | % of Portfolio | Beta | Risk Factor |
|--------|----------------|------|-------------|
| [TICKER] | XX% | X.XX | [High volatility / Recent loss / etc] |

**Risk Concentrations:**
- XX% in single sector ([Sector])
- XX% in stocks with beta > 1.5

**Risk Score:** XX/100 ([Low/Medium/High] risk)
```

#### 3.4 Performance Analysis

Evaluate performance using available data: overall unrealized P&L ($ and %), best/worst performers, winners vs losers ratio, and positions near 52-week highs/lows. Time-weighted returns require user-supplied history (not available from the live feed).

**Output:**
```markdown
## Performance Review

**Total Portfolio Value:** $XXX,XXX
**Total Unrealized P&L:** $XX,XXX (+XX.X%)
**Cash Balance:** $XX,XXX (XX% of portfolio)

**Best Performers:**
| Symbol | Gain | Position Value |
|--------|------|----------------|
| [TICKER] | +XX.X% | $XX,XXX |

**Worst Performers:**
| Symbol | Loss | Position Value |
|--------|------|----------------|
| [TICKER] | -XX.X% | $XX,XXX |
```

### Step 4: Individual Position Analysis

For key positions (top 10-15 by portfolio weight), perform detailed analysis.

**Read references/position-evaluation.md** for the position analysis framework.

For each significant position cover: thesis validation, valuation assessment (vs history and sector peers), technical health, position sizing (overweight/underweight vs optimal), and an explicit action recommendation:
- **HOLD** - Position is well-sized and thesis intact
- **ADD** - Underweight given opportunity, thesis strengthening
- **TRIM** - Overweight or valuation stretched
- **SELL** - Thesis broken, better opportunities elsewhere

**Output per position:**
```markdown
### [SYMBOL] - [Company Name] (XX.X% of portfolio)

**Position Details:**
- Shares: XXX
- Avg Cost: $XX.XX
- Current Price: $XX.XX
- Market Value: $XX,XXX
- Unrealized P/L: $X,XXX (+XX.X%)

**Position Assessment:**
- **Thesis Status:** [Intact / Weakening / Broken / Strengthening]
- **Valuation:** [Undervalued / Fair / Overvalued]
- **Position Sizing:** [Optimal / Overweight / Underweight]

**Recommendation:** [HOLD / ADD / TRIM / SELL]
**Rationale:** [1-2 sentence explanation]
```

### Step 5: Rebalancing Recommendations

**Read references/rebalancing-strategies.md** for rebalancing approaches.

Identify rebalancing triggers (drift from target weights, concentration > threshold, broken thesis, excess cash), then develop a prioritized plan:
1. **Immediate** - Risk reduction (trim concentrated positions)
2. **High Priority** - Major allocation drift (>10% from target)
3. **Medium Priority** - Moderate drift (5-10% from target)
4. **Low Priority** - Fine-tuning and opportunistic adjustments

**Output:**
```markdown
## Rebalancing Recommendations

### Summary
- **Rebalancing Needed:** [Yes / No / Optional]
- **Primary Reason:** [Concentration risk / Sector drift / Cash deployment]
- **Estimated Trades:** X sell orders, Y buy orders

### Recommended Actions

#### HIGH PRIORITY: Risk Reduction
**TRIM [SYMBOL]** from XX% to YY% of portfolio
- **Shares to Sell:** XX shares (~$XX,XXX)
- **Rationale:** [Overweight / Valuation extended]

#### CASH DEPLOYMENT
**Current Cash:** $XX,XXX (XX% of portfolio)
- **Recommendation:** [Deploy / Keep for opportunities]
```

### Step 6: Generate Portfolio Report

Create a comprehensive markdown report saved to the `reports/` directory (create it if it does not exist).

**Filename:** `reports/robinhood_portfolio_analysis_YYYY-MM-DD.md`

**Report Structure:**
```markdown
# Robinhood Portfolio Analysis Report

**Account:** [Account identifier if available]
**Report Date:** YYYY-MM-DD
**Portfolio Value:** $XXX,XXX
**Total P&L:** $XX,XXX (+XX.X%)

---

## Executive Summary
[3-5 bullet points: overall health, strengths, key risks, primary recommendations]

## Holdings Overview
[Summary table of all positions]

## Asset Allocation
[Section from Step 3.1]

## Diversification Analysis
[Section from Step 3.2]

## Risk Assessment
[Section from Step 3.3]

## Performance Review
[Section from Step 3.4]

## Position Analysis
[Detailed analysis of top 10-15 positions from Step 4]

## Rebalancing Recommendations
[Section from Step 5]

## Action Items
**Immediate:** [ ] ...
**Medium-Term:** [ ] ...
**Monitoring:** [ ] ...

## Appendix: Full Holdings
[Complete table with all positions and metrics]
```

### Step 7: Confirm-First Order Execution (Optional)

Run this step **only** when the user explicitly asks to place, modify, or cancel an order. Analysis (Steps 1-6) never triggers execution.

**Hard guardrails (always apply):**
- **One order at a time.** Never submit a batch. Never loop over a rebalancing plan placing orders automatically.
- **Preview before placing.** Always call `review_equity_order` first and show the user the preview.
- **Explicit per-order approval.** Place an order only after the user confirms *that specific order*. A general "go ahead and rebalance" is NOT approval to place orders.
- **No silent retries.** If an order is rejected, report the rejection and stop; do not resubmit without new approval.

**7.1 Pre-trade checks:**
```
Use get_equity_tradability for the symbol to confirm it is currently tradable.
Use get_equity_quotes for a current price reference.
For a SELL: confirm shares_available_for_sells (NOT quantity) on the position covers the order.
For a BUY: confirm get_portfolio data.buying_power.buying_power covers the order.
Use get_equity_orders (state=open/new/confirmed, symbol=…) to check for conflicting open orders.
```
Confirm the order is placed against the same `account_number` the user selected
in Step 1.0; the Agentic account (`agentic_allowed=true`) is the one intended for
agent-placed orders.

**7.2 Build and preview the order:**
- Construct a single order from the user's intent and the relevant recommendation (symbol, side, quantity, order type, limit price / stop if applicable, time-in-force).
- Call `review_equity_order` to obtain a dry-run preview (estimated cost/proceeds, fees, buying-power impact).
- Present the preview to the user in a compact table and ask for explicit confirmation.

**7.3 Place on approval:**
- On explicit confirmation, call `place_equity_order` with exactly the previewed parameters.
- Report the returned order id and status. Do not proceed to any next order without returning to 7.1 for it.

**7.4 Cancel (if requested):**
- Use `get_equity_orders` to locate the order id, confirm the target with the user, then call `cancel_equity_order`.

**Execution preview output:**
```markdown
### Order Preview (NOT yet placed)
| Field | Value |
|-------|-------|
| Symbol | XXXX |
| Side | BUY / SELL |
| Quantity | XX (shares) |
| Order Type | market / limit |
| Limit Price | $XX.XX |
| Time in Force | day / gtc |
| Est. Value | $XX,XXX |
| Tradable | yes / no |

**Confirm to place this single order?** (yes / no)
```

### Step 8: Watchlist Integration (Optional)

Use Robinhood watchlists to connect analysis to a tracked candidate pipeline.
Reads are free; **writes (add/remove/create/update) modify the user's data — confirm
before each write**, even though they place no orders.

**8.1 Read watchlists to inform analysis:**
- `get_watchlists` → the user's lists (each with an `id`); `get_watchlist_items`
  (per `list_id`) → tracked symbols. Use `get_equity_quotes` for prices (items carry none).
- `get_options_watchlist` for tracked option contracts (do **not** use
  `get_watchlist_items` for options — wrong shape, the upstream 400s).
- Cross-reference watchlist names against current holdings: flag tracked names that
  could fill diversification gaps from Step 5, and holdings you may be exiting.

**8.2 Stage rebalancing candidates (confirm-first write):**
- After Step 5, offer to add suggested replacement / diversifier names to a
  watchlist via `add_to_watchlist` (`symbols=[…]`, `list_id=…`) or a new
  `create_watchlist`. Present the exact list + symbols and get a yes before writing.
- `remove_from_watchlist` to clear names you've exited or rejected — confirm first.

> Watchlist writes are low-stakes (no money) but still mutate the user's account
> data; never batch-add speculatively without showing the list first.

## Analysis Frameworks

### Target Allocation Templates

**Read references/target-allocations.md** for model portfolios (Conservative, Moderate, Growth, Aggressive), each with asset class targets, sector guidelines, market cap distribution, and position sizing rules. Use these as comparison benchmarks when the user hasn't specified an allocation strategy.

### Risk Profile Assessment

If the user's target allocation is unknown, assess an appropriate risk profile from age, timeline, current allocation, and position types. **Read references/risk-profile-questionnaire.md** for the assessment framework.

## Output Guidelines

- **Tone:** Objective and analytical; actionable recommendations with clear rationale; acknowledge uncertainty; quantify whenever possible.
- **Data Presentation:** Tables for comparisons; percentages for allocations/returns; dollar amounts for absolute values.
- **Recommendation Clarity:** Explicit action verbs (TRIM, ADD, HOLD, SELL); specific quantities; priority levels; supporting rationale.

## Reference Files

Load these references as needed during analysis:

**references/robinhood-mcp-setup.md** — When: user needs help connecting the Robinhood MCP server or understanding the available tools. Contains: configuration steps, tool surface, namespace note, verification, security notes, and manual-CSV fallback.

**references/asset-allocation.md** — Allocation theory and frameworks.

**references/diversification-principles.md** — Diversification concepts and metrics.

**references/portfolio-risk-metrics.md** — Risk measurement and interpretation.

**references/position-evaluation.md** — Individual position analysis framework.

**references/rebalancing-strategies.md** — Rebalancing methodologies and timing.

**references/target-allocations.md** — Model portfolios by risk profile.

**references/risk-profile-questionnaire.md** — Risk tolerance assessment.

## Error Handling

**If the Robinhood MCP Server is not connected:**
1. Inform the user that Robinhood MCP integration is required.
2. Provide setup guidance from `references/robinhood-mcp-setup.md`.
3. Offer the fallback: manual data entry (user provides a CSV of positions).

**If MCP tools return incomplete data:** proceed with available data, note limitations in the report, and suggest manual verification for missing positions.

**If position data seems stale:** flag the issue, recommend refreshing the MCP connection, and caveat the findings.

**If the user has no positions:** acknowledge the empty portfolio and offer portfolio-construction guidance (e.g., value-dividend-screener or us-stock-analysis for ideas).

**If an order is rejected (Step 7):** report the broker's rejection reason and stop. Do not retry without new explicit approval.

## Limitations and Disclaimers

**Include in all reports:**

*This analysis is for informational purposes only and does not constitute financial advice. Investment decisions should be made based on individual circumstances, risk tolerance, and financial goals. Past performance does not guarantee future results. Consult a qualified financial advisor before making investment decisions.*

*Robinhood accounts are real-money accounts with no paper/simulated mode. All order execution is manual and confirm-first; this skill never auto-executes or batches orders. Data accuracy depends on the Robinhood MCP server and third-party market data; verify critical information independently. Tax implications are estimates only; consult a tax professional.*

*This skill enumerates equity positions only. Options, crypto, futures, and other non-equity sleeves are visible solely as aggregate dollar values from `get_portfolio` — their position-level detail (contracts, strikes, expiries, lots) is not available through this MCP surface and is therefore excluded from position-level analysis. Review those sleeves in the Robinhood app.*
