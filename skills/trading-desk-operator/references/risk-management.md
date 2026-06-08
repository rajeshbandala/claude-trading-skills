# Risk Management (non-negotiable)

Capital preservation is the first job; returns are the second. Risk rules override
any setup, any conviction, any "feel." Size for survival across losing streaks.

## Per-trade risk

- **Default risk per trade:** **1% of the executing account's equity** at the stop.
- **Hard ceiling:** never exceed **2%** per trade.
- **Position size** = (account equity × risk%) ÷ (entry − stop). Round **down**.
- Size against the **executing (agentic) account's** equity and buying power — not
  the combined book across read-only accounts.

## Stops and targets

- **Stop placement:** below structure (recent swing low / below support), not an
  arbitrary percentage. Without historical bars, use round-number support, the
  prior session's low, or a volatility buffer — and label it approximate.
- **Target / limit-sell:** at least **2R** (reward ≥ 2× risk). Scaling out is fine.
- **Every entry ships with a stop AND a target.** No naked entries.
- **Fractional caveat:** Robinhood does not hold a resting stop on a fractional
  position — it can only be exited manually/at market. A risk-defined trade that
  needs a resting stop must use **whole shares**. If 1 whole share already exceeds
  the per-trade risk cap, prefer to skip or pick a cheaper, more granular name.

## Portfolio-level limits

- **Portfolio heat:** total open risk (sum of per-position risk-to-stop) across all
  open positions ≤ **6%** of equity. If a new trade breaks this, don't add it.
- **Undefined risk = the worst risk.** A position with no stop has *unbounded* open
  risk; the heat cap is meaningless until every position has a defined stop. Fixing
  naked stops comes before adding new trades.
- **Daily loss limit:** if realized + open losses hit **3%** of equity in a session,
  stop entering for the day and say so.
- **Weekly loss limit:** hard stop at **6%** for the week.
- **Single-name concentration:** flag any position that is a large share of equity
  (>10–15%) or the same name held across multiple accounts.
- **Liquidity / tradability:** check `get_equity_tradability` before proposing an
  order (halts, PDT, fractional eligibility). Skip illiquid names.
- **Buying power:** use `get_portfolio → buying_power.buying_power` — the real
  spendable figure after holds — not cash or total value.

## Net-exposure ceiling by regime

The broad-market regime caps how much **new** long risk to add this cycle:

| Regime | New-risk posture | Net-exposure ceiling (guide) |
|--------|------------------|------------------------------|
| Clean uptrend, low event risk | Add A-setups normally | High (~80–100%) |
| Uptrend but **extended / late-stage** | Smaller, fewer, be selective | Moderate (~40–60%) |
| Chop / range | Only the cleanest setups; quick to flat | Low (~20–40%) |
| Downtrend | Defense; mostly flat, no chasing | Minimal (0–20%) |
| **Major event window** (CPI/PPI/FOMC/jobs ≤ 1–2 days out) | **No new risk into the print** | Hold; wait for the reaction |

Don't fight the tape. Fewer, smaller longs in a weak or event-loaded market.

## Discipline reminders

- Never chase; never average down into a broken thesis; never let one name threaten
  the book.
- Cut anything that closed through its stop — no "give it one more day."
- Take partials at +1R / first target; trail the remainder.
- A 50% loss needs a 100% gain to recover — the math of losses is why size is small.
- The edge is *process repeated identically every session*, regardless of feel.
