# Robinhood MCP Server Setup Guide

This guide explains how to connect and use a Robinhood MCP (Model Context Protocol) Server with the Robinhood Portfolio Manager skill.

## What is the Robinhood MCP Server?

A Robinhood MCP Server is a Model Context Protocol server that gives Claude access to your Robinhood brokerage account through a standardized tool interface. This lets the Robinhood Portfolio Manager skill fetch current positions, account balances, and live quotes directly from your account, and — only with explicit, per-order confirmation — preview and place orders.

> **Real money only.** Robinhood does not offer a paper/simulated trading mode.
> Every account this skill connects to is a live account. Treat all execution
> with caution; this skill is built to keep a human in the loop for every order.

## Prerequisites

### 1. Robinhood Account

You need a funded Robinhood brokerage account. Sign up / log in at <https://robinhood.com/>.

### 2. A Robinhood MCP Server

You need a Robinhood MCP server configured in your Claude environment. MCP servers are configured outside this skill (in your Claude client's MCP settings). The exact server package and authentication flow depend on which Robinhood MCP implementation you use — follow that server's own installation and login instructions.

Authentication for Robinhood MCP servers is typically handled by the server itself (session/OAuth-style login, often including device approval or MFA), **not** by simple API key environment variables. This skill does not read Robinhood credentials directly; it only calls the MCP tools the server exposes.

⚠️ **Security note:** Never commit Robinhood credentials, session tokens, or MCP
configuration containing secrets to version control. Keep any config file that
contains secrets in your `.gitignore`.

## Connecting in Claude

1. Configure the Robinhood MCP server in your Claude client's MCP settings (see that server's docs).
2. Complete the server's login/authentication flow (this may involve MFA / device approval).
3. Restart or reload Claude so the MCP server connects.
4. Verify the tools resolve in your session (see Verification below).

## Available MCP Tools

Once connected, the skill uses the following tools. They are referred to by
their **logical base names**; in-session they appear with a server-specific
prefix (for example `mcp__<server>__get_equity_positions`). The prefix varies by
environment — do not hardcode it.

All read tools return a `{"data": {...}, "guide": "..."}` envelope — read from
`data` and honor any `guide` text the server returns.

- **`get_accounts`** — List brokerage accounts. Returns `data.accounts[]` with
  `account_number`, `brokerage_account_type`, `type` (margin/cash), `nickname`,
  `is_default`, `agentic_allowed`. With multiple accounts, ask the user to choose;
  mask all but the last 4 digits when displaying, pass the full value to tools.
- **`get_portfolio`** (needs `account_number`) — `data.total_value`, `cash`,
  `buying_power.buying_power` (authoritative spendable), and per-asset-class values.
- **`get_equity_positions`** (needs `account_number`) — `data.positions[]` with
  `symbol`, `quantity` (fractional supported), `average_buy_price` (avg cost; may
  be omitted while reconciling), `shares_available_for_sells` (use for sellable
  shares), `intraday_quantity`, `type`. **No market price/P&L** — pair with
  `get_equity_quotes`. Paginate via the `next`/`cursor` field.
- **`get_equity_quotes`** — Live quotes + official last-session close for up to
  ~20 symbols per call (above 20, closes are omitted with `closes_error` set).
- **`get_equity_orders`** (needs `account_number`) — Open and historical orders;
  filter by `state`, `symbol`, `created_at_gte`; used to reconcile stops and
  detect conflicting pending orders. Paginates via `cursor`.
- **`get_equity_tradability`** — Whether a given symbol is currently tradable.

### Order tools (confirm-first execution only)

- **`review_equity_order`** — Dry-run preview of an order (estimated cost/proceeds, fees, buying-power impact) **without placing it**.
- **`place_equity_order`** — Place a single order. Used **only** after explicit per-order user approval.
- **`cancel_equity_order`** — Cancel an existing order by id.

> **No portfolio-history tool.** The Robinhood MCP surface does not expose a
> portfolio-history time series. Time-weighted historical return and maximum
> drawdown are therefore unavailable from the live feed. The skill derives
> performance context from current positions (unrealized P&L vs. cost basis) and
> labels it accordingly.

## Verification and Testing

### Step 1: Run the connection checklist script

```bash
python3 skills/robinhood-portfolio-manager/scripts/check_robinhood_connection.py
```

This prints a configuration checklist and the expected logical tool names. Because Robinhood auth runs through the MCP server (not local API keys), the script does not make raw broker API calls — it guides you through confirming the server is configured.

### Step 2: Confirm tools resolve in-session

Ask Claude:
```
"List my Robinhood positions"
```
A working connection returns your holdings via `get_equity_positions`. If the tools do not resolve, the MCP server is not connected — re-check your client's MCP settings and re-authenticate.

### Step 3: Trigger the skill

```
"Analyze my Robinhood portfolio"
```
The skill should fetch positions and balances, enrich with quotes, and produce a report under `reports/robinhood_portfolio_analysis_<date>.md`.

## Troubleshooting

### "Robinhood MCP Server not connected" / tools do not resolve
1. Verify the Robinhood MCP server is configured in your Claude client's MCP settings.
2. Re-run the server's login/authentication flow (session tokens expire; MFA may be required again).
3. Restart or reload Claude to reinitialize MCP servers.
4. Confirm network connectivity.

### Authentication / login failures
1. Re-authenticate through the MCP server's login flow.
2. Complete any device-approval / MFA prompts.
3. Check whether your session token has expired and refresh it.

### "No positions found"
1. Confirm positions exist in the Robinhood app.
2. Confirm you authenticated the correct account.
3. Ask Claude to fetch positions again to refresh.

### Order rejected (Step 7 execution)
1. Read the broker's rejection reason (insufficient buying power, not tradable, market closed, etc.).
2. Resolve the underlying issue.
3. Re-preview with `review_equity_order` and re-confirm before any new `place_equity_order`.

## Security Best Practices

1. **Keep a human in the loop.** This skill previews every order and requires explicit per-order confirmation. Never wire it into unattended automation that places orders.
2. **Protect credentials and tokens.** Never commit Robinhood credentials, session tokens, or MCP config secrets to version control. Use `.gitignore`.
3. **Review activity regularly.** Check order history in the Robinhood app and via `get_equity_orders`.
4. **Re-authenticate periodically.** Refresh sessions and rotate any long-lived secrets your MCP server uses.

## Alternative: Manual Data Entry

If the Robinhood MCP server is unavailable, the skill can analyze manually provided portfolio data.

**CSV Format:**
```csv
symbol,quantity,cost_basis,current_price
AAPL,100,150.00,175.50
MSFT,50,280.00,310.25
GOOGL,25,135.00,142.00
```

**Usage:**
1. Export positions from the Robinhood app (or enter them manually) as CSV.
2. Provide the file to Claude: "Analyze my portfolio using this CSV file".
3. The skill parses the data and performs the same analysis (without live quotes, order preview, or execution).

**Limitations:** no real-time updates, no order preview/execution, manual refresh required.

## Additional Resources

- **MCP Protocol:** <https://modelcontextprotocol.io/>
- **Claude Code MCP docs:** <https://code.claude.com/docs/en/claude-code-on-the-web>
- **Robinhood:** <https://robinhood.com/>
