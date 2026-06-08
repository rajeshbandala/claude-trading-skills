"""Risk engine for the Trading Desk Operator skill.

Two deterministic, offline calculations used every desk cycle:

  size   Risk-based sizing for one candidate on the *executing* (Agentic)
         account. Returns BOTH a whole-share plan (which can carry a resting
         GTC stop) and a fractional plan (no resting stop on Robinhood -> a
         managed/manual exit), plus a 2R target and buying-power / max-risk
         guards. Built for small accounts where 1 share of a high-priced
         leader can already blow through the per-trade risk cap.

  stops  Stop sheet + portfolio heat for an existing book. Given positions
         with a current price and (optionally) a stop, compute risk-if-hit
         per name, flag winners whose stop locks a gain, auto-generate a
         pragmatic stop where one is missing, and total open heat vs the cap.

No API keys, no network. Order *placement* happens through the Robinhood MCP
tools at runtime (see references/execution-protocol.md); this script only does
the math so the numbers are reproducible.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime


# --------------------------------------------------------------------------- #
# size
# --------------------------------------------------------------------------- #
def size_position(
    account_equity: float,
    entry: float,
    stop: float,
    risk_pct: float = 1.0,
    max_risk_pct: float = 2.0,
    target_r: float = 2.0,
    buying_power: float | None = None,
) -> dict:
    """Size a long entry by risk for the executing account.

    risk_per_share = entry - stop
    dollar_risk    = account_equity * risk_pct / 100
    whole_shares   = floor(dollar_risk / risk_per_share), capped by buying power
    fractional     = dollar_risk / risk_per_share, capped by buying power
    target         = entry + target_r * risk_per_share
    """
    if account_equity <= 0:
        raise ValueError("account_equity must be positive")
    if entry <= 0:
        raise ValueError("entry must be positive")
    if stop <= 0:
        raise ValueError("stop must be positive")
    if stop >= entry:
        raise ValueError("stop must be below entry for a long trade")
    if risk_pct <= 0:
        raise ValueError("risk_pct must be positive")
    if target_r <= 0:
        raise ValueError("target_r must be positive")

    bp = account_equity if buying_power is None else buying_power
    if bp < 0:
        raise ValueError("buying_power cannot be negative")

    risk_per_share = entry - stop
    dollar_risk = account_equity * risk_pct / 100.0
    target = entry + target_r * risk_per_share

    # Whole-share plan (can carry a resting GTC stop).
    raw_whole = math.floor(dollar_risk / risk_per_share)
    max_by_bp = math.floor(bp / entry)
    whole_shares = max(0, min(raw_whole, max_by_bp))
    whole_risk = whole_shares * risk_per_share
    whole_notional = whole_shares * entry

    # A single share already exceeding the hard risk cap means there is no
    # risk-defined whole-share trade in this account for this stop distance.
    one_share_risk_pct = risk_per_share / account_equity * 100.0
    whole_share_blocked = one_share_risk_pct > max_risk_pct

    # Fractional plan (NO resting stop on Robinhood -> managed exit only).
    frac_shares = dollar_risk / risk_per_share
    if max_by_bp == 0 and bp < entry:
        frac_shares = min(frac_shares, bp / entry)
    frac_shares = min(frac_shares, bp / entry) if entry > 0 else frac_shares
    frac_shares = round(frac_shares, 6)
    frac_notional = round(frac_shares * entry, 2)
    frac_risk = round(frac_shares * risk_per_share, 2)

    # Recommendation logic.
    if whole_shares >= 1 and not whole_share_blocked:
        recommendation = "whole_share"
    elif whole_share_blocked:
        recommendation = "fractional_or_skip"
    else:
        recommendation = "fractional"

    return {
        "schema_version": "1.0",
        "kind": "size",
        "inputs": {
            "account_equity": round(account_equity, 2),
            "buying_power": round(bp, 2),
            "entry": entry,
            "stop": stop,
            "risk_pct": risk_pct,
            "max_risk_pct": max_risk_pct,
            "target_r": target_r,
        },
        "risk_per_share": round(risk_per_share, 4),
        "dollar_risk_budget": round(dollar_risk, 2),
        "target_price": round(target, 4),
        "reward_per_share": round(target - entry, 4),
        "rr": round(target_r, 2),
        "whole_share_plan": {
            "shares": whole_shares,
            "notional": round(whole_notional, 2),
            "risk_dollars": round(whole_risk, 2),
            "risk_pct": round(whole_risk / account_equity * 100.0, 3),
            "carries_resting_stop": True,
            "blocked": whole_share_blocked,
            "blocked_reason": (
                f"one share risk {one_share_risk_pct:.2f}% exceeds max_risk_pct {max_risk_pct:.2f}%"
                if whole_share_blocked
                else None
            ),
        },
        "fractional_plan": {
            "shares": frac_shares,
            "notional": frac_notional,
            "risk_dollars": frac_risk,
            "risk_pct": round(frac_risk / account_equity * 100.0, 3),
            "carries_resting_stop": False,
            "note": "Robinhood holds no resting stop on fractional shares; exit must be managed/market.",
        },
        "recommendation": recommendation,
    }


# --------------------------------------------------------------------------- #
# stops
# --------------------------------------------------------------------------- #
def build_stop_sheet(
    positions: list[dict],
    account_equity: float,
    default_stop_pct: float = 8.0,
    heat_cap_pct: float = 6.0,
) -> dict:
    """Build a stop sheet + portfolio heat summary for an existing book.

    Each position needs at least ``symbol``, ``quantity`` and ``current_price``.
    Optional: ``stop_price`` (auto-generated from default_stop_pct when absent)
    and ``avg_price`` (to mark winners whose stop locks a gain).
    """
    if account_equity <= 0:
        raise ValueError("account_equity must be positive")

    rows: list[dict] = []
    total_open_risk = 0.0
    for p in positions:
        symbol = p["symbol"]
        qty = float(p["quantity"])
        cur = float(p["current_price"])
        if qty <= 0 or cur <= 0:
            continue
        stop = p.get("stop_price")
        auto = False
        if stop is None:
            stop = round(cur * (1.0 - default_stop_pct / 100.0), 2)
            auto = True
        else:
            stop = float(stop)

        risk_per_share = cur - stop
        # Stop above current would trigger immediately -> treat as 0 open risk.
        risk_if_hit = max(0.0, risk_per_share) * qty
        total_open_risk += risk_if_hit

        avg = p.get("avg_price")
        locks_gain = avg is not None and stop > float(avg)

        rows.append(
            {
                "symbol": symbol,
                "quantity": qty,
                "current_price": round(cur, 4),
                "stop_price": round(stop, 4),
                "stop_auto_generated": auto,
                "risk_per_share": round(risk_per_share, 4),
                "risk_if_hit": round(risk_if_hit, 2),
                "risk_pct_of_equity": round(risk_if_hit / account_equity * 100.0, 3),
                "locks_gain": bool(locks_gain),
            }
        )

    heat_pct = total_open_risk / account_equity * 100.0
    return {
        "schema_version": "1.0",
        "kind": "stops",
        "account_equity": round(account_equity, 2),
        "heat_cap_pct": heat_cap_pct,
        "rows": rows,
        "total_open_risk": round(total_open_risk, 2),
        "open_heat_pct": round(heat_pct, 3),
        "within_heat_cap": heat_pct <= heat_cap_pct,
    }


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def render_size_md(r: dict) -> str:
    w = r["whole_share_plan"]
    f = r["fractional_plan"]
    lines = [
        "# Desk Risk — Position Size",
        "**Generated:** {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "",
        "- Entry **${}** | Stop **${}** | Target(2R) **${}** | Risk/sh **${}**".format(
            r["inputs"]["entry"], r["inputs"]["stop"], r["target_price"], r["risk_per_share"]
        ),
        "- Account ${} | BP ${} | Risk budget ${} ({}%)".format(
            r["inputs"]["account_equity"],
            r["inputs"]["buying_power"],
            r["dollar_risk_budget"],
            r["inputs"]["risk_pct"],
        ),
        "",
        "| Plan | Shares | Notional | $ Risk | % Equity | Resting stop? |",
        "|------|--------|----------|--------|----------|---------------|",
        "| Whole-share | {} | ${} | ${} | {}% | yes |".format(
            w["shares"], w["notional"], w["risk_dollars"], w["risk_pct"]
        ),
        "| Fractional | {} | ${} | ${} | {}% | no (managed exit) |".format(
            f["shares"], f["notional"], f["risk_dollars"], f["risk_pct"]
        ),
        "",
        "**Recommendation:** {}".format(r["recommendation"]),
    ]
    if w["blocked"]:
        lines.append("> ⚠️ {}".format(w["blocked_reason"]))
    return "\n".join(lines) + "\n"


def render_stops_md(r: dict) -> str:
    lines = [
        "# Desk Risk — Stop Sheet",
        "**Generated:** {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "**Account equity:** ${}".format(r["account_equity"]),
        "",
        "| Symbol | Qty | Cur | Stop | Risk/sh | Risk if hit | % Eq | Note |",
        "|--------|-----|-----|------|---------|-------------|------|------|",
    ]
    for row in r["rows"]:
        note = []
        if row["stop_auto_generated"]:
            note.append("auto-stop")
        if row["locks_gain"]:
            note.append("locks gain")
        lines.append(
            "| {} | {} | ${} | ${} | ${} | ${} | {}% | {} |".format(
                row["symbol"],
                row["quantity"],
                row["current_price"],
                row["stop_price"],
                row["risk_per_share"],
                row["risk_if_hit"],
                row["risk_pct_of_equity"],
                ", ".join(note) or "-",
            )
        )
    lines += [
        "",
        "**Total open risk:** ${} | **Open heat:** {}% of {}% cap → {}".format(
            r["total_open_risk"],
            r["open_heat_pct"],
            r["heat_cap_pct"],
            "OK" if r["within_heat_cap"] else "OVER CAP",
        ),
    ]
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict, output_dir: str, stem: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    json_path = os.path.join(output_dir, f"{stem}_{ts}.json")
    with open(json_path, "w") as fh:
        json.dump(result, fh, indent=2)
    md = render_size_md(result) if result["kind"] == "size" else render_stops_md(result)
    md_path = os.path.join(output_dir, f"{stem}_{ts}.md")
    with open(md_path, "w") as fh:
        fh.write(md)
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    print()
    print(md)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trading Desk Operator risk engine")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("size", help="Risk-size one candidate for the executing account")
    s.add_argument("--account-equity", type=float, required=True)
    s.add_argument("--entry", type=float, required=True)
    s.add_argument("--stop", type=float, required=True)
    s.add_argument("--risk-pct", type=float, default=1.0)
    s.add_argument("--max-risk-pct", type=float, default=2.0)
    s.add_argument("--target-r", type=float, default=2.0)
    s.add_argument("--buying-power", type=float, default=None)
    s.add_argument("--output-dir", type=str, default="reports/")

    st = sub.add_parser("stops", help="Build a stop sheet + heat from a positions JSON")
    st.add_argument(
        "--positions",
        type=str,
        required=True,
        help="Path to JSON: list of {symbol, quantity, current_price[, stop_price, avg_price]}",
    )
    st.add_argument("--account-equity", type=float, required=True)
    st.add_argument("--default-stop-pct", type=float, default=8.0)
    st.add_argument("--heat-cap-pct", type=float, default=6.0)
    st.add_argument("--output-dir", type=str, default="reports/")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "size":
            result = size_position(
                account_equity=args.account_equity,
                entry=args.entry,
                stop=args.stop,
                risk_pct=args.risk_pct,
                max_risk_pct=args.max_risk_pct,
                target_r=args.target_r,
                buying_power=args.buying_power,
            )
            _write_outputs(result, args.output_dir, "desk_size")
        else:
            with open(args.positions) as fh:
                positions = json.load(fh)
            if not isinstance(positions, list):
                raise ValueError("positions JSON must be a list of position objects")
            result = build_stop_sheet(
                positions=positions,
                account_equity=args.account_equity,
                default_stop_pct=args.default_stop_pct,
                heat_cap_pct=args.heat_cap_pct,
            )
            _write_outputs(result, args.output_dir, "desk_stops")
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
