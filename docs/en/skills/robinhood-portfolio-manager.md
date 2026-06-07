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
- Any request involving portfolio-level analysis, management, or guided order placement on Robinhood

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
- `get_accounts` - List brokerage accounts and identifiers
- `get_portfolio` - Total portfolio/account value and cash balances
- `get_equity_positions` - All current equity positions (symbol, quantity, average cost, market value)
- `get_equity_quotes` - Live quotes for held and candidate symbols
- `get_equity_orders` - Existing/open and historical orders (used to reconcile stops and pending trades)
- `get_equity_tradability` - Whether a symbol is currently tradable

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
Use get_accounts and get_portfolio to fetch:
- Account identifier(s)
- Total portfolio/account value
- Cash balance and buying power
- Account status
```

---

## 5. Workflow

### Step 1: Fetch Portfolio Data via Robinhood MCP

Use the Robinhood MCP Server tools to gather current portfolio information:

**1.1 Get Account Information:**
```
Use get_accounts and get_portfolio to fetch:
- Account identifier(s)
- Total portfolio/account value
- Cash balance and buying power
- Account status
```

**1.2 Get Current Positions:**
```
Use get_equity_positions to fetch all holdings:
- Symbol ticker
- Quantity held (supports fractional shares)
- Average entry price (cost basis)
- Current market value
- Unrealized P&L ($ and %)
- Position size as % of portfolio
```

**1.3 Enrich with Live Quotes:**
```
Use get_equity_quotes for held symbols to obtain:
- Current price (for positions where market value is stale or missing)
- Bid/ask context for sizing and execution planning
```

> **No portfolio-history endpoint:** Unlike some brokers, the Robinhood MCP
> surface does not provide a portfolio-history time series. Derive performance
> context from current positions (unrealized P&L vs. cost basis) and note in the
> report that time-weighted historical return / drawdown is unavailable from the
> live feed. If the user wants historical return, ask them to supply it manually.

**Data Validation:**
- Verify all positions have valid ticker symbols
- Confirm market values sum to approximately the portfolio value from `get_portfolio`
- Check for any stale or inactive positions
- Handle edge cases (fractional shares, cash, non-equity holdings if present)

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
