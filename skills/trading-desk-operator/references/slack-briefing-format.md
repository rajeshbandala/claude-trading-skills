# Slack Briefing Format (`#trading`)

Confirm the target channel the first time (`slack_search_channels` → `#trading`),
then post each cycle with `slack_send_message`. Traders scan — **lead with numbers
and tables, keep prose minimal.** Mask account numbers to the last 4 digits.

## Template

```
📊 Desk — <block> — <date/time ET>

Regime: <uptrend/chop/downtrend> | Net exposure ceiling: <%>
<one line: key driver + nearest scheduled event risk>

Book — combined ≈ $<X> | Executing acct ••••XXXX: $<cash> cash, <n> positions
| Symbol | Qty | Avg | Last | Unreal P&L | % | Stop | Note |
| ...    | ... | ... | ...  | ...        |...| ...  | ...  |

Setups (ranked)
1. <TICKER> — <long/flat> | trigger <px> | stop <px> | target <px> | size <sh> | R:R <x> | <catalyst>
   why: <1 line>
2. ...

Risk
- Open portfolio heat: <%> of 6% cap | Daily P&L vs 3% limit: <status>
- Concentration flags: <names + %>

Actions pending confirm: <list, or "none">

Snapshot + plan — not a recommendation. Orders require explicit confirmation.
```

## Conventions

- **Block** = pre-market / midday / power-hour / end-of-day / weekly.
- Show the **executing account** explicitly (it's the only one that can trade);
  summarize read-only accounts as advisory in the book table or a one-liner.
- Mark **naked positions** (no stop) — that is the headline risk when present.
- Setups: only the top few. A small number of A-setups beats a long list. Every
  setup line carries trigger, stop, target, size, and R:R — no vague calls.
- "Actions pending confirm" lists exactly what awaits the user's yes (or "none").
- Always close with the disclaimer line. Never imply certainty or advice.
- Slack renders standard markdown tables; do **not** escape the structural `|`.
  Use a code block for fixed-width book/stop tables if alignment matters.
