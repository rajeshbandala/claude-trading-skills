#!/usr/bin/env python3
"""
Connection checklist for the Robinhood Portfolio Manager skill.

Unlike a simple REST broker, Robinhood access in this skill runs through a
Robinhood MCP (Model Context Protocol) server, and authentication is handled by
that server (session / OAuth-style login, often with MFA) rather than by local
API-key environment variables. This script therefore does NOT make raw broker
API calls. Instead it prints a configuration checklist and the logical MCP tool
names the skill relies on, so the user can confirm their setup before invoking
the skill.

The actual portfolio data fetch and (optional) confirm-first order placement
happen via MCP tools inside the skill conversation, not in this script.

Usage:
    python3 check_robinhood_connection.py

Exit codes:
    0 - checklist printed successfully
    1 - unexpected error
"""

import sys

# Logical (un-prefixed) MCP tool names the skill uses. In-session these appear
# with a server-specific prefix, e.g. mcp__<server>__get_equity_positions.
READ_TOOLS = [
    ("get_accounts", "List brokerage accounts and identifiers"),
    ("get_portfolio", "Total portfolio/account value and cash balances"),
    ("get_equity_positions", "Current equity positions (symbol, qty, cost, value)"),
    ("get_equity_quotes", "Live quotes for held and candidate symbols"),
    ("get_equity_orders", "Open and historical orders (reconcile stops / pending)"),
    ("get_equity_tradability", "Whether a symbol is currently tradable"),
]

ORDER_TOOLS = [
    ("review_equity_order", "Dry-run preview of an order WITHOUT placing it"),
    ("place_equity_order", "Place a single order (ONLY after explicit approval)"),
    ("cancel_equity_order", "Cancel an existing order by id"),
]

# Watchlist tools. Reads are free; writes mutate user data — confirm first.
WATCHLIST_TOOLS = [
    ("get_watchlists", "List the user's watchlists (id + name)"),
    ("get_watchlist_items", "Items in a stock/ETF/crypto/index watchlist"),
    ("get_options_watchlist", "The options watchlist (use instead of items)"),
    ("add_to_watchlist", "Add symbols to a watchlist (write — confirm first)"),
    ("remove_from_watchlist", "Remove items from a watchlist (write — confirm)"),
]

SETUP_STEPS = [
    "Configure a Robinhood MCP server in your Claude client's MCP settings.",
    "Complete the server's login / authentication flow (may require MFA).",
    "Restart or reload Claude so the MCP server connects.",
    "In-session, confirm the tools resolve: ask Claude to 'List my Robinhood positions'.",
]


def print_checklist() -> None:
    """Print the Robinhood MCP setup checklist and expected tool surface."""
    line = "=" * 64
    print("Robinhood Portfolio Manager - Connection Checklist")
    print(line)
    print()
    print("NOTE: Robinhood access runs through an MCP server. Authentication is")
    print("handled by that server (session/OAuth, often with MFA), NOT by local")
    print("API-key environment variables. This script does not call the broker;")
    print("it verifies your setup steps and lists the tools the skill needs.")
    print()
    print("Real money: Robinhood has no paper/simulated mode. All execution in")
    print("this skill is confirm-first and one order at a time.")
    print()

    print("Setup steps:")
    for i, step in enumerate(SETUP_STEPS, 1):
        print(f"  {i}. {step}")
    print()

    print("Expected MCP tools (logical names; in-session prefixed as")
    print("mcp__<server>__<name> — the <server> prefix varies by environment):")
    print()
    print("  Read tools (analysis):")
    for name, desc in READ_TOOLS:
        print(f"    - {name:<24} {desc}")
    print()
    print("  Order tools (confirm-first execution only):")
    for name, desc in ORDER_TOOLS:
        print(f"    - {name:<24} {desc}")
    print()
    print("  Watchlist tools (reads free; writes confirm-first):")
    for name, desc in WATCHLIST_TOOLS:
        print(f"    - {name:<24} {desc}")
    print()
    print("  Note: equities are the only enumerable positions. Options/crypto")
    print("  appear only as aggregate values in get_portfolio (no position tool).")
    print()

    print(line)
    print("Next steps:")
    print("  1. If the tools above resolve in your Claude session, you're ready.")
    print("  2. Invoke the skill: 'Analyze my Robinhood portfolio'.")
    print("  3. If tools do not resolve, re-check your MCP server config and")
    print("     re-authenticate. See references/robinhood-mcp-setup.md.")


def main() -> int:
    """Print the checklist. Returns 0 on success, 1 on unexpected error."""
    try:
        print_checklist()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"ERROR: failed to print checklist: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
