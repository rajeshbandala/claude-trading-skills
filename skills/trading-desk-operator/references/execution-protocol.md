# Execution Protocol (confirm-first gate)

Default mode is **propose, don't fire.** Orders place with real money on a live
account. The gate exists to keep a human on the trigger.

## Executing-account-only rule

- Place / review / cancel orders **only** on the account with
  `agentic_allowed: true` (the *executing account*). The order tools reject
  non-agentic accounts — do not call them there.
- Every other account is **read-only**: analyze it, build a stop sheet for it, but
  present those actions as **advisory** for the user to place manually in the app.
- Confirm the order targets the executing account's `account_number` before placing.

## The gate (every proposed trade)

1. **Resolve & quote.** `search` the ticker; pull a live quote with
   `get_equity_quotes`; confirm `get_equity_tradability` on the executing account.
2. **Build the order.** Side, quantity (from the risk math in
   `risk-management.md`), order type, **stop-loss**, and **target/limit-sell**.
   For entries needing price protection, prefer a **marketable limit** at/near the
   ask over a plain market order.
3. **Simulate.** Call `review_equity_order`. Present estimated cost, buying-power
   impact, the R-multiple, and any alerts (PDT, halt, insufficient BP).
4. **Get explicit confirmation.** Wait for the user's "yes" on **that specific
   order**. A generic "do it" / "go ahead" is **not** a bypass — restate exactly
   what you're about to place and get the yes.
5. **Place.** On yes → `place_equity_order` with a **fresh `ref_id` (UUID) per
   logical order**. Re-send the *same* `ref_id` only when retrying a transient
   transport failure (idempotency). Use a new `ref_id` for a genuinely new order.
6. **Bracket.** Place/track the protective stop and the target as the order's
   bracket. (On Robinhood a fractional fill cannot carry a resting stop — manage
   that exit manually; see the fractional caveat in `risk-management.md`.)
7. **Log.** Record symbol, side, qty, prices, R, `ref_id`, and order id.

## Order-type cheatsheet

- **Entry with protection:** marketable limit (`type=limit`, limit at/just through
  the ask), `time_in_force=gfd` (or `gtc` to rest).
- **Protective stop:** `stop_market` (whole shares) — surer fill than `stop_limit`,
  which can gap through. Use `gtc`.
- **Target:** `limit` sell at the 2R level, `gtc`.
- **Fractional / dollar-based:** only `type=market` in **regular hours**; no resting
  stop, no shorts. Do not propose fractional outside the regular session.

## Rejections and failures

- If `review_equity_order` or `place_equity_order` is rejected, **report the
  reason and stop.** Do not silently resubmit. Re-propose only with a fix and a
  fresh confirmation.
- Never loop a plan placing multiple orders automatically (unless bounded
  auto-execution is explicitly enabled, below). One order at a time.

## Bounded auto-execution (OFF by default)

Unattended real-money execution can compound mistakes fast — keeping a human on the
trigger is the recommended default. Enable auto-execution **only** when the user
explicitly opts in **and** sets hard bounds, e.g.:

- Auto-execute **only A-rated** setups.
- **≤ $X notional** per trade and **≤ N trades** per session.
- **Never** through earnings.
- **Halt for the day** on the daily loss limit.

Even when enabled:
- Still run `review_equity_order` before every `place_equity_order`.
- Still **skip and report** (don't auto-fire) anything ambiguous, illiquid, halted,
  or that breaches a risk limit.
- Respect every limit in `risk-management.md` — they override the auto rule.
- Log every auto-placed order and surface them in the cycle briefing.

Stop auto-execution the moment the user asks, or on any limit breach.
