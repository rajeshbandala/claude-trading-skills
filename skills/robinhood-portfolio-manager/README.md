# Robinhood Portfolio Manager

Comprehensive portfolio analysis and management skill that integrates with a Robinhood MCP Server to fetch current holdings, generate detailed portfolio reports with rebalancing recommendations, and — only with explicit, per-order confirmation — preview and place orders.

This is the Robinhood-broker sibling of the `portfolio-manager` (Alpaca) skill. The analysis frameworks are identical; the brokerage integration and the confirm-first execution workflow differ.

## Overview

Robinhood Portfolio Manager analyzes your investment portfolio across multiple dimensions:

- **Asset Allocation** — stocks, cash distribution vs target allocation
- **Diversification** — sector breakdown, position concentration, correlation
- **Risk Assessment** — portfolio beta, concentration, risk score
- **Performance Review** — winners/losers, unrealized P&L
- **Position Analysis** — HOLD/ADD/TRIM/SELL recommendations per holding
- **Rebalancing Plan** — prioritized actions to optimize allocation
- **Confirm-First Execution (optional)** — preview via `review_equity_order`, place one order at a time only after explicit approval

## Real money, human-in-the-loop

Robinhood has **no paper/simulated mode** — every connected account is live. This skill never auto-executes and never batches orders. Every order is previewed and requires explicit per-order confirmation.

## Prerequisites

1. **Funded Robinhood account** — <https://robinhood.com/>
2. **A Robinhood MCP Server** configured in your Claude client's MCP settings. Authentication is handled by the MCP server (session/OAuth-style login, often with MFA), not by local API keys.

See `references/robinhood-mcp-setup.md` for the full setup, tool surface, and troubleshooting.

### Optional: Manual data entry

If the MCP server is unavailable, provide positions via CSV:

```csv
symbol,quantity,cost_basis,current_price
AAPL,100,150.00,175.50
MSFT,50,280.00,310.25
```

Analysis runs without live quotes, order preview, or execution.

## MCP Tools Used

Tools are referenced by logical base name; in-session they appear prefixed as `mcp__<server>__<name>` (the prefix varies by environment).

| Tool | Purpose |
|------|---------|
| `get_accounts` | List accounts / identifiers |
| `get_portfolio` | Total value and cash balances |
| `get_equity_positions` | Current positions (fractional supported) |
| `get_equity_quotes` | Live quotes |
| `get_equity_orders` | Open/historical orders |
| `get_equity_tradability` | Tradable check |
| `review_equity_order` | Dry-run order preview (execution) |
| `place_equity_order` | Place one order after approval (execution) |
| `cancel_equity_order` | Cancel an order (execution) |

> No portfolio-history tool exists on the Robinhood MCP surface, so time-weighted
> historical return and maximum drawdown are unavailable from the live feed.
> Performance is derived from current positions (unrealized P&L vs cost basis).

## Usage

```
"Analyze my Robinhood portfolio"
"Review my current positions"
"Should I rebalance my portfolio?"
"Help me place this trade on Robinhood"   # triggers confirm-first execution
```

The skill fetches positions and balances, enriches with quotes, performs the analysis, and writes a report to `reports/robinhood_portfolio_analysis_YYYY-MM-DD.md`.

## Testing the connection

```bash
python3 skills/robinhood-portfolio-manager/scripts/check_robinhood_connection.py
```

Prints a setup checklist and the expected MCP tool surface. (It does not call the broker — Robinhood auth is handled by the MCP server.)

## Reference Materials

- `references/robinhood-mcp-setup.md` — Robinhood MCP setup, tools, troubleshooting
- `references/asset-allocation.md` — allocation theory and frameworks
- `references/diversification-principles.md` — diversification concepts and metrics
- `references/portfolio-risk-metrics.md` — risk measurement and interpretation
- `references/position-evaluation.md` — position analysis framework
- `references/rebalancing-strategies.md` — rebalancing methodologies
- `references/target-allocations.md` — model portfolios by risk profile
- `references/risk-profile-questionnaire.md` — risk tolerance assessment

## Limitations and Disclaimers

This tool provides informational analysis only, not personalized financial advice. Robinhood accounts are real-money accounts; all execution is manual and confirm-first. Data accuracy depends on the Robinhood MCP server and third-party market data — verify critical information independently. Tax estimates are approximate; consult a tax professional.

## Related Skills

- **Portfolio Manager** (`portfolio-manager`) — the Alpaca sibling of this skill
- **US Stock Analysis** — deep dive into individual positions
- **Position Sizer** — risk-based position sizing
- **Value Dividend Screener** — find replacement stocks for rebalancing
- **Trader Memory Core** — register and track theses from portfolio decisions
