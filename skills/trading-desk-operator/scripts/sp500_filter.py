"""S&P 500 membership gate for the Trading Desk Operator skill.

Discovered candidates (from news / technical screening) must be S&P 500
constituents before they can be proposed. This filter is the deterministic
fast path: it checks tickers against a bundled constituents snapshot
(``assets/sp500_constituents.json``) or a user-supplied list.

The snapshot is a *cache*, not the source of truth — index membership drifts
(~20 changes/year). Anything NOT found here is reported as ``unverified`` (not
silently rejected) so the operator can confirm it live via WebSearch before
including it. When the snapshot is older than ``--max-age-days`` relative to
``--as-of``, the result is flagged ``stale`` and live verification is advised
for every pick. No network, no API keys.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

DEFAULT_CONSTITUENTS = Path(__file__).resolve().parent.parent / "assets" / "sp500_constituents.json"


def normalize(ticker: str) -> str:
    """Uppercase, strip, and unify share-class separators (BRK-B -> BRK.B)."""
    return ticker.strip().upper().replace("-", ".")


def load_constituents(path: Path) -> dict:
    """Load the constituents snapshot. Returns {symbols:set, as_of, source, count}."""
    with open(path) as fh:
        data = json.load(fh)
    symbols = {normalize(s) for s in data.get("symbols", [])}
    if not symbols:
        raise ValueError(f"no symbols found in constituents file: {path}")
    return {
        "symbols": symbols,
        "as_of": data.get("as_of"),
        "source": data.get("source"),
        "count": len(symbols),
    }


def _days_old(as_of: str | None, ref: date) -> int | None:
    if not as_of:
        return None
    try:
        d = datetime.strptime(as_of, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (ref - d).days


def filter_tickers(
    tickers: list[str],
    constituents: dict,
    as_of_ref: date | None = None,
    max_age_days: int = 120,
) -> dict:
    """Split tickers into members / unverified against the snapshot.

    ``in_sp500``   — found in the snapshot (members).
    ``unverified`` — not found; confirm live via WebSearch before including.
    ``stale``      — snapshot older than max_age_days; verify every pick live.
    """
    members = constituents["symbols"]
    in_sp500: list[str] = []
    unverified: list[str] = []
    seen: set[str] = set()
    for raw in tickers:
        t = normalize(raw)
        if not t or t in seen:
            continue
        seen.add(t)
        (in_sp500 if t in members else unverified).append(t)

    ref = as_of_ref or date.today()
    age = _days_old(constituents.get("as_of"), ref)
    stale = age is not None and age > max_age_days

    return {
        "schema_version": "1.0",
        "kind": "sp500_filter",
        "as_of": constituents.get("as_of"),
        "snapshot_count": constituents["count"],
        "snapshot_age_days": age,
        "stale": stale,
        "max_age_days": max_age_days,
        "in_sp500": sorted(in_sp500),
        "unverified": sorted(unverified),
        "source": constituents.get("source"),
    }


def render_md(r: dict) -> str:
    lines = [
        "# S&P 500 Membership Gate",
        f"**Snapshot as_of:** {r['as_of']} ({r['snapshot_count']} names)"
        + (f" — ⚠️ STALE ({r['snapshot_age_days']}d > {r['max_age_days']}d)" if r["stale"] else ""),
        "",
        "**In S&P 500 (snapshot-confirmed):** " + (", ".join(r["in_sp500"]) or "none"),
        "",
        "**Unverified (confirm live via WebSearch before proposing):** "
        + (", ".join(r["unverified"]) or "none"),
    ]
    if r["stale"]:
        lines += [
            "",
            "> Snapshot is stale — verify EVERY pick's membership live, not just the unverified ones.",
        ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="S&P 500 membership gate")
    parser.add_argument(
        "--tickers",
        required=True,
        help="Comma-separated candidate tickers (e.g. AAPL,MSFT,SOFI)",
    )
    parser.add_argument(
        "--constituents",
        type=Path,
        default=DEFAULT_CONSTITUENTS,
        help="Path to constituents JSON (default: bundled snapshot)",
    )
    parser.add_argument(
        "--as-of", type=str, default=None, help="Reference date YYYY-MM-DD for staleness"
    )
    parser.add_argument("--max-age-days", type=int, default=120)
    parser.add_argument(
        "--output-dir", type=str, default=None, help="If set, also write JSON+MD reports"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        constituents = load_constituents(args.constituents)
        ref = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else None
        result = filter_tickers(
            [t for t in args.tickers.split(",")],
            constituents,
            as_of_ref=ref,
            max_age_days=args.max_age_days,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    md = render_md(result)
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        with open(os.path.join(args.output_dir, f"sp500_filter_{ts}.json"), "w") as fh:
            json.dump(result, fh, indent=2)
        with open(os.path.join(args.output_dir, f"sp500_filter_{ts}.md"), "w") as fh:
            fh.write(md)
    print(md)


if __name__ == "__main__":
    main()
