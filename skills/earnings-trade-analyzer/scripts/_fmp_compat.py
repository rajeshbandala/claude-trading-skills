"""FMP v3 → /stable/ URL compatibility shim.

FMP deprecated /api/v3/ for users registered after 2025-08-31.
This module rewrites legacy v3-style URLs (and their parameters) at
request-time so existing skill code continues to work without
business-logic changes.

Usage in fmp_client.py:
    from _fmp_compat import v3_to_stable
    # in _rate_limited_get, at the entrance:
    url, params = v3_to_stable(url, params)

CRITICAL: /stable/ accepts BOTH underscore (legacy-style) AND hyphen
(modern-style) names — but for endpoints like economic_calendar and
stock_news, the underscore version is FREE while the hyphen version
is PAID. The rewriter intentionally PRESERVES underscore names to
keep free-tier access working.

Patched 2026-05-22 (v3→stable migration).
"""

from datetime import date as _date, timedelta as _td
from typing import Optional, Tuple

_STABLE = "https://financialmodelingprep.com/stable"

# Endpoints that take symbol via path on v3 but require ?symbol= on stable.
# Stable also renames some of these (etf-holder → etf-holdings, etc.)
_PATH_WITH_SYMBOL = {
    # name on v3                 -> name on stable
    "quote":                       "/quote",
    "profile":                     "/profile",
    "income-statement":            "/income-statement",
    "balance-sheet-statement":     "/balance-sheet-statement",
    "cash-flow-statement":         "/cash-flow-statement",
    "key-metrics":                 "/key-metrics",
    "key-metrics-ttm":             "/key-metrics-ttm",
    "ratios":                      "/ratios",
    "ratios-ttm":                  "/ratios-ttm",
    "enterprise-values":           "/enterprise-values",
    "market-capitalization":       "/market-capitalization",
    "institutional-holder":        "/institutional-ownership/symbol-ownership",  # renamed
    "etf-holder":                  "/etf-holdings",                              # renamed
    "rating":                      "/rating",
    "discounted-cash-flow":        "/discounted-cash-flow",
}


def v3_to_stable(url: str, params: Optional[dict] = None) -> Tuple[str, dict]:
    """Rewrite a legacy FMP v3 URL to its /stable/ equivalent.

    No-op for URLs that don't contain `/api/v3/`. Best-effort fallback
    (strip /api/v3/ → /stable/) for unmapped endpoints, which preserves
    underscore naming (intentionally — see module docstring).
    """
    if params is None:
        params = {}
    else:
        params = dict(params)  # don't mutate caller's dict

    if "/api/v3/" not in url:
        return url, params

    after = url.split("/api/v3/", 1)[1].rstrip("/")

    # 1) historical-price-full has two variants (one with sub-path)
    if after.startswith("historical-price-full/stock_dividend/"):
        symbol = after[len("historical-price-full/stock_dividend/"):]
        params["symbol"] = symbol
        return _STABLE + "/dividends", params

    if after.startswith("historical-price-full/"):
        symbol = after[len("historical-price-full/"):]
        params["symbol"] = symbol
        # Convert legacy `timeseries=N` to from/to date range.
        # New stable EOD endpoint ignores timeseries; bound payload with
        # 2x calendar days to cover N trading days (headroom for weekends).
        ts = params.pop("timeseries", None)
        if ts:
            today = _date.today()
            params.setdefault("from", (today - _td(days=int(ts) * 2)).isoformat())
            params.setdefault("to", today.isoformat())
        return _STABLE + "/historical-price-eod/full", params

    # 2) historical/earning_calendar/{symbol} → /stable/earnings?symbol=...
    if after.startswith("historical/earning_calendar/"):
        symbol = after[len("historical/earning_calendar/"):]
        params["symbol"] = symbol
        return _STABLE + "/earnings", params

    # 3) Path-with-symbol mappings (most common case)
    for v3_path, stable_path in _PATH_WITH_SYMBOL.items():
        if after.startswith(v3_path + "/"):
            symbol = after[len(v3_path) + 1:]
            params["symbol"] = symbol
            return _STABLE + stable_path, params
        if after == v3_path:
            # Symbol was already in query params, just swap the base path
            return _STABLE + stable_path, params

    # 4) Everything else: best-effort 1:1 path swap to /stable/.
    # /stable/ accepts underscore names (earning_calendar, economic_calendar,
    # stock_news, sp500_constituent, stock-screener etc.) — DON'T "modernize"
    # to hyphenated names because those often go behind a paid wall.
    return _STABLE + "/" + after, params


# ---- Standalone test ----
if __name__ == "__main__":
    cases = [
        # (input_url, input_params, expected_url_contains, expected_params_subset)
        ("https://financialmodelingprep.com/api/v3/quote/AAPL", {}, "/stable/quote", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/profile/MSFT", {}, "/stable/profile", {"symbol": "MSFT"}),
        ("https://financialmodelingprep.com/api/v3/income-statement/AAPL", {"period": "quarter", "limit": 8}, "/stable/income-statement", {"symbol": "AAPL", "period": "quarter"}),
        ("https://financialmodelingprep.com/api/v3/balance-sheet-statement/AAPL", {}, "/stable/balance-sheet-statement", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/cash-flow-statement/AAPL", {}, "/stable/cash-flow-statement", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/key-metrics/AAPL", {}, "/stable/key-metrics", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/ratios/AAPL", {}, "/stable/ratios", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/historical-price-full/AAPL", {"timeseries": 365}, "/stable/historical-price-eod/full", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/historical-price-full/stock_dividend/AAPL", {}, "/stable/dividends", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/institutional-holder/AAPL", {}, "/stable/institutional-ownership/symbol-ownership", {"symbol": "AAPL"}),
        ("https://financialmodelingprep.com/api/v3/etf-holder/SPY", {}, "/stable/etf-holdings", {"symbol": "SPY"}),
        ("https://financialmodelingprep.com/api/v3/market-capitalization/AAPL", {}, "/stable/market-capitalization", {"symbol": "AAPL"}),
        # No-rename free endpoints — preserve underscore
        ("https://financialmodelingprep.com/api/v3/stock-screener", {"marketCapMoreThan": 1e9}, "/stable/stock-screener", {}),
        ("https://financialmodelingprep.com/api/v3/sp500_constituent", {}, "/stable/sp500_constituent", {}),
        ("https://financialmodelingprep.com/api/v3/earning_calendar", {}, "/stable/earning_calendar", {}),
        ("https://financialmodelingprep.com/api/v3/economic_calendar", {}, "/stable/economic_calendar", {}),
        ("https://financialmodelingprep.com/api/v3/stock_news", {}, "/stable/stock_news", {}),
        # Renames with sym-in-path
        ("https://financialmodelingprep.com/api/v3/historical/earning_calendar/AAPL", {}, "/stable/earnings", {"symbol": "AAPL"}),
        # No-op cases
        ("https://financialmodelingprep.com/stable/profile?symbol=AAPL", {}, "/stable/profile", {}),
        ("https://example.com/other", {}, "example.com/other", {}),
    ]

    pass_cnt = fail_cnt = 0
    for url_in, p_in, expected_url_sub, expected_p_sub in cases:
        url_out, p_out = v3_to_stable(url_in, p_in)
        ok_url = expected_url_sub in url_out
        ok_params = all(p_out.get(k) == v for k, v in expected_p_sub.items())
        if ok_url and ok_params:
            pass_cnt += 1
            short_in = url_in.split('/api/v3/')[-1] if '/api/v3/' in url_in else url_in.split('financialmodelingprep.com')[-1] if 'financialmodelingprep' in url_in else url_in
            short_out = url_out.split('financialmodelingprep.com')[-1] if 'financialmodelingprep' in url_out else url_out
            print(f"✓ {short_in[:50]:<50} → {short_out}")
        else:
            fail_cnt += 1
            print(f"✗ {url_in}")
            print(f"    → {url_out}  params={p_out}")
            print(f"    expected URL contains {expected_url_sub!r}, params⊇{expected_p_sub}")

    print(f"\n{pass_cnt} pass, {fail_cnt} fail")
