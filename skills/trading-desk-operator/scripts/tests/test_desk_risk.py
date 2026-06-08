"""Tests for the Trading Desk Operator risk engine."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desk_risk import build_stop_sheet, size_position  # noqa: E402


# --------------------------------------------------------------------------- #
# size_position
# --------------------------------------------------------------------------- #
def test_size_basic_whole_share_and_target():
    r = size_position(account_equity=500, entry=94.6, stop=88.0, risk_pct=1.0)
    # risk/share = 6.6, budget = $5 -> 0 whole shares affordable within 1% risk,
    # but 1 share risk (6.6/500 = 1.32%) is under the 2% cap, so not blocked.
    assert r["risk_per_share"] == pytest.approx(6.6, abs=1e-6)
    assert r["target_price"] == pytest.approx(94.6 + 2 * 6.6, abs=1e-6)
    assert r["whole_share_plan"]["blocked"] is False
    # buying power 500 affords 5 whole shares, but risk budget caps to 0;
    # min(floor(5/6.6)=0, floor(500/94.6)=5) = 0
    assert r["whole_share_plan"]["shares"] == 0
    # fractional fills the $5 budget
    assert r["fractional_plan"]["risk_dollars"] == pytest.approx(5.0, abs=0.01)
    assert r["fractional_plan"]["carries_resting_stop"] is False


def test_size_one_share_exceeds_max_risk_is_blocked():
    # NVDA-like: entry 208, stop 197 -> risk/share 11; on $500 that is 2.2% > 2% cap.
    r = size_position(account_equity=500, entry=208, stop=197, risk_pct=1.0, max_risk_pct=2.0)
    assert r["whole_share_plan"]["blocked"] is True
    assert "exceeds max_risk_pct" in r["whole_share_plan"]["blocked_reason"]
    assert r["recommendation"] == "fractional_or_skip"


def test_size_whole_share_recommended_when_affordable():
    # Big account, cheap stop distance -> whole-share plan is the recommendation.
    r = size_position(account_equity=100000, entry=50, stop=48, risk_pct=1.0)
    # risk/share 2, budget 1000 -> 500 shares; bp 100k affords 2000; min = 500
    assert r["whole_share_plan"]["shares"] == 500
    assert r["recommendation"] == "whole_share"
    assert r["whole_share_plan"]["risk_dollars"] == pytest.approx(1000.0, abs=0.01)


def test_size_buying_power_caps_shares():
    # Risk math wants more shares than buying power allows.
    r = size_position(account_equity=100000, entry=100, stop=99, risk_pct=1.0, buying_power=250)
    # risk/share 1, budget 1000 -> 1000 shares by risk, but bp 250 -> 2 shares
    assert r["whole_share_plan"]["shares"] == 2
    assert r["fractional_plan"]["notional"] <= 250.0


def test_size_target_r_custom():
    r = size_position(account_equity=10000, entry=20, stop=18, risk_pct=1.0, target_r=3.0)
    assert r["rr"] == 3.0
    assert r["target_price"] == pytest.approx(20 + 3 * 2, abs=1e-6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"account_equity": 0, "entry": 10, "stop": 9},
        {"account_equity": 500, "entry": 10, "stop": 11},  # stop above entry
        {"account_equity": 500, "entry": 10, "stop": 10},  # stop == entry
        {"account_equity": 500, "entry": -1, "stop": 9},
        {"account_equity": 500, "entry": 10, "stop": 9, "risk_pct": 0},
    ],
)
def test_size_invalid_inputs_raise(kwargs):
    with pytest.raises(ValueError):
        size_position(**kwargs)


# --------------------------------------------------------------------------- #
# build_stop_sheet
# --------------------------------------------------------------------------- #
def test_stops_explicit_and_heat():
    positions = [
        {
            "symbol": "HOOD",
            "quantity": 150,
            "current_price": 83.17,
            "stop_price": 79.5,
            "avg_price": 107.6,
        },
        {
            "symbol": "QUBT",
            "quantity": 501,
            "current_price": 10.12,
            "stop_price": 8.9,
            "avg_price": 14.15,
        },
    ]
    r = build_stop_sheet(positions, account_equity=98700, heat_cap_pct=6.0)
    hood = next(x for x in r["rows"] if x["symbol"] == "HOOD")
    assert hood["risk_if_hit"] == pytest.approx(150 * (83.17 - 79.5), abs=0.01)
    assert hood["locks_gain"] is False  # stop 79.5 < avg 107.6
    assert r["total_open_risk"] == pytest.approx(
        150 * (83.17 - 79.5) + 501 * (10.12 - 8.9), abs=0.02
    )
    assert r["within_heat_cap"] is True


def test_stops_auto_generated_when_missing():
    positions = [{"symbol": "LYFT", "quantity": 503, "current_price": 13.65}]
    r = build_stop_sheet(positions, account_equity=98700, default_stop_pct=8.0)
    row = r["rows"][0]
    assert row["stop_auto_generated"] is True
    assert row["stop_price"] == pytest.approx(round(13.65 * 0.92, 2), abs=1e-9)


def test_stops_winner_locks_gain_flag():
    positions = [
        {
            "symbol": "GOOGL",
            "quantity": 10,
            "current_price": 366.02,
            "stop_price": 350.0,
            "avg_price": 304.06,
        },
    ]
    r = build_stop_sheet(positions, account_equity=59000)
    assert r["rows"][0]["locks_gain"] is True


def test_stops_stop_above_current_is_zero_risk():
    # A stop already above the current price would trigger immediately.
    positions = [{"symbol": "X", "quantity": 10, "current_price": 50, "stop_price": 55}]
    r = build_stop_sheet(positions, account_equity=10000)
    assert r["rows"][0]["risk_if_hit"] == 0.0
    assert r["total_open_risk"] == 0.0


def test_stops_over_cap_flagged():
    positions = [{"symbol": "BIG", "quantity": 1000, "current_price": 100, "stop_price": 90}]
    r = build_stop_sheet(positions, account_equity=100000, heat_cap_pct=6.0)
    # risk = 1000 * 10 = 10,000 = 10% of 100k > 6% cap
    assert r["open_heat_pct"] == pytest.approx(10.0, abs=0.01)
    assert r["within_heat_cap"] is False


def test_stops_skips_empty_positions():
    positions = [
        {"symbol": "ZERO", "quantity": 0, "current_price": 10, "stop_price": 9},
        {"symbol": "OK", "quantity": 5, "current_price": 10, "stop_price": 9},
    ]
    r = build_stop_sheet(positions, account_equity=10000)
    assert len(r["rows"]) == 1
    assert r["rows"][0]["symbol"] == "OK"
