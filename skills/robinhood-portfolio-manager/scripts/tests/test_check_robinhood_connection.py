"""Tests for the Robinhood connection checklist script."""

import check_robinhood_connection as crc


def test_main_returns_zero(capsys):
    """main() prints the checklist and returns success exit code."""
    rc = crc.main()
    captured = capsys.readouterr()
    assert rc == 0
    # Sanity-check key content is present in the printed checklist.
    assert "Robinhood Portfolio Manager" in captured.out
    assert "confirm-first" in captured.out


def test_checklist_lists_all_expected_tools(capsys):
    """Every logical read, order, and watchlist tool name appears in the output."""
    crc.print_checklist()
    out = capsys.readouterr().out
    for name, _desc in crc.READ_TOOLS + crc.ORDER_TOOLS + crc.WATCHLIST_TOOLS:
        assert name in out


def test_checklist_notes_equity_only_position_enumeration(capsys):
    """The checklist must flag that options/crypto are aggregate-only."""
    crc.print_checklist()
    out = capsys.readouterr().out
    assert "get_watchlists" in out
    assert "aggregate" in out.lower()


def test_order_tools_are_confirm_first_only():
    """place_equity_order must be present and described as approval-gated."""
    order_names = {name for name, _ in crc.ORDER_TOOLS}
    assert {"review_equity_order", "place_equity_order", "cancel_equity_order"} == order_names
    place_desc = dict(crc.ORDER_TOOLS)["place_equity_order"]
    assert "approval" in place_desc.lower()
