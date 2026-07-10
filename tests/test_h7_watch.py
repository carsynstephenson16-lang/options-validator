"""Assemble-level watcher tests. 7b-0 contract: ENTRY-OK is printed ONLY
when the corresponding strategies.h7_lanes.decide_lane_* returned an
executable action from the same inputs -- the watcher has no lane logic of
its own. Earnings coverage and the paper book fail CLOSED."""

import unittest
from datetime import date

import pandas as pd

from options_researcher import h7_watch

TODAY = date(2026, 7, 8)
# far-future confirmed report: covered, and outside the 5-session ban
CAL_OK = {"XXXX": {"confirmed": [date(2026, 9, 18)], "estimated": []},
          "VST": {"confirmed": [date(2026, 9, 18)], "estimated": []}}
DEEP_RECLAIM = [130.0] * 200 + [62.0] * 25 + [70.0]


def _closes(path):
    idx = pd.bdate_range(end="2026-07-08", periods=len(path))
    return pd.Series([float(v) for v in path], index=idx, name="close")


def _chain(center: float, iv: float):
    """Monthlies 2026-08-21 (~44 DTE) and 2026-10-16 (~100 DTE). Call deltas
    fall with strike, put |deltas| rise, put prices rise with strike, so an
    executable H7c bull put spread exists (short ~0.28 delta, credit >= 30%
    of width) and executable long structures exist in the 0.55-0.70 band."""
    rows = []
    for k in range(10):
        strike = center - 10 + 2.5 * k
        c_bid = max(0.5, 14.0 - 1.5 * k)
        p_bid = 2.0 + 1.1 * k
        for exp in ("2026-08-21", "2026-10-16"):
            rows.append({
                "expiration": exp, "strike": strike, "right": "C",
                "bid": c_bid, "ask": c_bid * 1.04, "open_interest": 900,
                "iv": iv, "delta": max(0.05, 0.90 - 0.09 * k),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
            rows.append({
                "expiration": exp, "strike": strike, "right": "P",
                "bid": p_bid, "ask": p_bid * 1.04, "open_interest": 900,
                "iv": iv, "delta": -min(0.95, 0.10 + 0.09 * k),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
    return pd.DataFrame(rows)


def _card(**over):
    args = dict(symbol="XXXX", closes=_closes(DEEP_RECLAIM),
                chain=_chain(center=70.0, iv=0.40), today=TODAY,
                calendar=CAL_OK, open_positions=())
    args.update(over)
    return h7_watch.assemble_name(**args)


class TestEntryOkIsDecideBacked(unittest.TestCase):
    def test_lane_a_entry_ok_carries_the_decide_action(self):
        card = _card()
        self.assertEqual(card["lane_a"]["state"], "ENTRY-OK")
        action = card["lane_a"]["action"]
        self.assertIsNotNone(action)
        self.assertEqual(action["lane"], "a")
        self.assertEqual(action["kind"], "long_call")
        self.assertLessEqual(action["cost"], 6000)

    def test_rich_iv_routes_to_lane_c_with_executable_spread(self):
        card = _card(chain=_chain(center=70.0, iv=0.90))
        self.assertEqual(card["lane_a"]["state"], "QUIET")
        self.assertEqual(card["lane_c"]["state"], "ENTRY-OK")
        action = card["lane_c"]["action"]
        self.assertEqual(action["kind"], "bull_put_spread")
        self.assertGreaterEqual(action["credit"], 0.30 * action["width"])

    def test_armed_but_unexecutable_is_never_entry_ok(self):
        # cheap IV, lane a armed and admitted -- but no call delta in the
        # 0.55-0.70 band, so decide_lane_a returns None. The old watcher
        # printed ENTRY-OK here; the 7b-0 contract forbids it.
        ch = _chain(center=70.0, iv=0.40)
        calls = ch.right == "C"
        ch.loc[calls, "delta"] = 0.90
        card = _card(chain=ch)
        self.assertEqual(card["lane_a"]["state"], "NO-EXECUTABLE")
        self.assertIsNone(card["lane_a"].get("action"))

    def test_every_entry_ok_state_has_an_action(self):
        # structural parity sweep across routes and lanes
        for iv in (0.40, 0.46, 0.90):
            card = _card(chain=_chain(center=70.0, iv=iv))
            for lane in ("lane_a", "lane_b", "lane_c"):
                if card[lane]["state"] == "ENTRY-OK":
                    self.assertIsNotNone(card[lane].get("action"),
                                         f"iv={iv} {lane}")


class TestFailClosedStates(unittest.TestCase):
    def test_uncovered_symbol_is_earnings_unknown(self):
        card = _card(calendar={})
        self.assertEqual(card["lane_a"]["state"], "EARNINGS-UNKNOWN")
        self.assertEqual(card["lane_c"]["state"], "EARNINGS-UNKNOWN")

    def test_stale_past_only_calendar_is_earnings_unknown(self):
        cal = {"XXXX": {"confirmed": [date(2026, 3, 10)], "estimated": []}}
        card = _card(calendar=cal)
        self.assertEqual(card["lane_a"]["state"], "EARNINGS-UNKNOWN")

    def test_banned_symbol_reports_ban_not_entry(self):
        cal = {"XXXX": {"confirmed": [date(2026, 7, 10)], "estimated": []}}
        card = _card(calendar=cal)
        self.assertEqual(card["lane_a"]["state"], "EARNINGS-BAN")

    def test_open_position_blocks_new_entry(self):
        card = _card(open_positions=("XXXX",))
        self.assertEqual(card["lane_a"]["state"], "POSITION-OPEN")

    def test_core_name_lane_c_excluded(self):
        card = _card(symbol="VST")
        self.assertEqual(card["lane_c"]["state"], "EXCLUDED")

    def test_quiet_when_no_signal(self):
        card = _card(closes=_closes([100.0] * 260),
                     chain=_chain(center=100.0, iv=0.40))
        self.assertEqual(card["lane_a"]["state"], "QUIET")
        self.assertEqual(card["lane_b"]["state"], "QUIET")

    def test_budget_spent_blocks_entry(self):
        card = _card(month_spent=6000.0)
        self.assertEqual(card["lane_a"]["state"], "BUDGET-SPENT")

    def test_lane_c_basket_cap(self):
        card = _card(chain=_chain(center=70.0, iv=0.90), open_h7c=1)
        self.assertEqual(card["lane_c"]["state"], "BASKET-CAP")
