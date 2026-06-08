"""Tests for the S&P 500 membership gate."""

import json
import os
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sp500_filter import (  # noqa: E402
    DEFAULT_CONSTITUENTS,
    filter_tickers,
    load_constituents,
    normalize,
)


@pytest.fixture
def fixture_constituents(tmp_path):
    data = {"as_of": "2026-01-15", "source": "test", "symbols": ["AAPL", "MSFT", "BRK.B"]}
    p = tmp_path / "c.json"
    p.write_text(json.dumps(data))
    return load_constituents(p)


def test_normalize_unifies_share_class():
    assert normalize(" brk-b ") == "BRK.B"
    assert normalize("aapl") == "AAPL"


def test_member_and_unverified_split(fixture_constituents):
    r = filter_tickers(["AAPL", "SOFI", "MSFT"], fixture_constituents, as_of_ref=date(2026, 2, 1))
    assert r["in_sp500"] == ["AAPL", "MSFT"]
    assert r["unverified"] == ["SOFI"]
    assert r["stale"] is False


def test_share_class_normalization_matches(fixture_constituents):
    # BRK-B should match BRK.B in the snapshot
    r = filter_tickers(["BRK-B"], fixture_constituents, as_of_ref=date(2026, 2, 1))
    assert r["in_sp500"] == ["BRK.B"]
    assert r["unverified"] == []


def test_dedup_and_case_insensitive(fixture_constituents):
    r = filter_tickers(["aapl", "AAPL", "msft"], fixture_constituents, as_of_ref=date(2026, 2, 1))
    assert r["in_sp500"] == ["AAPL", "MSFT"]


def test_staleness_flag(fixture_constituents):
    # snapshot as_of 2026-01-15; ref far later -> stale beyond max_age_days
    r = filter_tickers(
        ["AAPL"], fixture_constituents, as_of_ref=date(2026, 12, 1), max_age_days=120
    )
    assert r["stale"] is True
    assert r["snapshot_age_days"] > 120


def test_not_stale_within_window(fixture_constituents):
    r = filter_tickers(["AAPL"], fixture_constituents, as_of_ref=date(2026, 2, 1), max_age_days=120)
    assert r["stale"] is False


def test_empty_symbols_raises(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"as_of": "2026-01-15", "symbols": []}))
    with pytest.raises(ValueError):
        load_constituents(p)


# --------------------------------------------------------------------------- #
# Bundled snapshot sanity (kept loose so membership edits don't break tests)
# --------------------------------------------------------------------------- #
def test_bundled_snapshot_loads_and_has_core_names():
    c = load_constituents(Path(DEFAULT_CONSTITUENTS))
    assert c["count"] > 100
    for core in ("AAPL", "MSFT", "NVDA", "JPM", "XOM", "BRK.B"):
        assert core in c["symbols"]


def test_bundled_snapshot_no_duplicates():
    raw = json.loads(Path(DEFAULT_CONSTITUENTS).read_text())["symbols"]
    norm = [normalize(s) for s in raw]
    assert len(norm) == len(set(norm)), "duplicate tickers in bundled snapshot"
