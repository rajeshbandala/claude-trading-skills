# Cadence Playbook

The desk does not run itself — the user (or an external scheduler) triggers each
cycle. Run the block that matches the current ET time. If the user just says "run
the desk," infer the block from the clock. When the market is closed and the next
session is ahead, run the **pre-market** block.

If the clock is ambiguous or the environment time disagrees with the calendar date,
**state the ambiguity** and pick the block that best fits "market is closed, next
session ahead" (usually pre-market) rather than implying precision you don't have.

## Pre-market (~08:30 ET)

Goal: the day's plan and levels before the open.
1. Resolve accounts + executing account; pull watchlist universe and full book.
2. **Regime** + overnight/pre-market news + **gap scan** across watchlist + book.
3. Flag scheduled event risk (CPI/PPI/FOMC/jobs) and any earnings in the window.
4. Rank setups; mark *ready* vs *watch-only*; set trigger / stop / target / size.
5. Build the stop sheet for open positions; flag naked positions.
6. Post the pre-market briefing. Propose orders only through the gate; nothing
   fires pre-open (fractional/dollar orders need regular hours anyway).

## Midday (~12:00 ET)

Goal: check and adjust mid-session.
1. Position check + order-status check (`get_equity_orders`).
2. Did any watch-only setup trigger? Re-rank; size any new A-setup.
3. Update stops (trail winners past +1R); take partials at first target.
4. Re-check the daily loss limit and heat. Post a short midday update.

## Power hour (~15:15 ET)

Goal: manage into the close.
1. Trail stops; take partials; flatten anything that violated its thesis intraday.
2. Decide overnight holds explicitly, with reasoning and a defined stop.
3. Confirm no position is naked into the close. Post the power-hour plan.

## End of day (after close)

Goal: journal and reconcile.
1. Journal every fill (entry/exit, R achieved, plan vs. actual).
2. Today's realized + open P&L vs the 3% daily limit.
3. What the plan said vs. what happened; note process breaks.
4. Save the cycle report; post the EOD summary.

## Weekly (Fri close)

Goal: review the process, not just the P&L.
1. Win rate, avg win vs. avg loss, expectancy, max drawdown for the week.
2. Realized + open P&L vs the 6% weekly limit.
3. Watchlist cleanup: drop dead names, add fresh leaders.
4. Note recurring mistakes and one process fix for next week.

## Every block — always

- Mask account numbers to the last 4 digits in any output that leaves the chat.
- Lead with numbers; keep prose minimal.
- Report what you **did not** do and why (skipped entries, naked stops, limits hit).
- If a tool fails or data is stale, say so — don't guess.
