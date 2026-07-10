"""Assemble-level watcher tests on synthetic inputs. The watcher NEVER
trades: these tests pin lane-state routing, the earnings ban, the
one-open-position rule, and the IV router's lane handoff (cheap IV -> long
lanes; rich IV -> lane c only, per the registration)."""

import unittest
from datetime import date

import pandas as pd

from options_researcher import h7_watch


def _closes(path):
    idx = pd.bdate_range(end="2026-07-08", periods=len(path))
    return pd.Series([float(v) for v in path], index=idx, name="close")


def _chain(center: float, iv: float):
    """Two monthly expirations (2026-08-21 ~44 DTE, 2026-10-16 ~100 DTE from
    2026-07-08); strikes straddle `center`; the five nearest strikes quote
    tight (<5%) so admission passes with exactly the minimum count."""
    rows = []
    for k in range(8):
        strike = center - 8 + 2 * k
        bid = max(0.3, 8.0 - 0.4 * k)
        for exp in ("2026-08-21", "2026-10-16"):
            rows.append({
                "expiration": exp, "strike": strike, "right": "C",
                "bid": bid, "ask": bid + 0.2, "open_interest": 800,
                "iv": iv, "delta": max(0.05, 0.75 - 0.08 * k),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
            rows.append({
                "expiration": exp, "strike": strike, "right": "P",
                "bid": bid, "ask": bid + 0.2, "open_interest": 800,
                "iv": iv, "delta": -max(0.05, 0.75 - 0.08 * (7 - k)),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
    return pd.DataFrame(rows)


DEEP_RECLAIM = [130.0] * 200 + [62.0] * 25 + [70.0]


class TestH7WatchAssemble(unittest.TestCase):
    def test_deep_reclaim_cheap_iv_is_lane_a_entry(self):
        card = h7_watch.assemble_name(
            symbol="XXXX", closes=_closes(DEEP_RECLAIM),
            chain=_chain(center=70.0, iv=0.40),
            today=date(2026, 7, 8), calendar={}, open_positions=(),
        )
        self.assertEqual(card["lane_a"]["state"], "ENTRY-OK")
        self.assertEqual(card["lane_a"]["route"], "call")
        self.assertEqual(card["lane_c"]["state"], "QUIET")  # rich-IV lane has no edge here
        self.assertIn("benchmark_note", card)

    def test_deep_reclaim_rich_iv_routes_to_lane_c_not_a(self):
        card = h7_watch.assemble_name(
            symbol="XXXX", closes=_closes(DEEP_RECLAIM),
            chain=_chain(center=70.0, iv=0.90),
            today=date(2026, 7, 8), calendar={}, open_positions=(),
        )
        self.assertEqual(card["lane_a"]["state"], "QUIET")
        self.assertEqual(card["lane_c"]["state"], "ENTRY-OK")
        self.assertEqual(card["lane_c"]["route"], "h7c")

    def test_banned_symbol_reports_ban_not_entry(self):
        cal = {"XXXX": {"confirmed": [date(2026, 7, 10)], "estimated": []}}
        card = h7_watch.assemble_name(
            symbol="XXXX", closes=_closes(DEEP_RECLAIM),
            chain=_chain(center=70.0, iv=0.40),
            today=date(2026, 7, 8), calendar=cal, open_positions=(),
        )
        self.assertEqual(card["lane_a"]["state"], "EARNINGS-BAN")

    def test_open_position_blocks_new_entry(self):
        card = h7_watch.assemble_name(
            symbol="XXXX", closes=_closes(DEEP_RECLAIM),
            chain=_chain(center=70.0, iv=0.40),
            today=date(2026, 7, 8), calendar={}, open_positions=("XXXX",),
        )
        self.assertEqual(card["lane_a"]["state"], "POSITION-OPEN")

    def test_core_name_lane_c_excluded(self):
        card = h7_watch.assemble_name(
            symbol="VST", closes=_closes(DEEP_RECLAIM),
            chain=_chain(center=70.0, iv=0.40),
            today=date(2026, 7, 8), calendar={}, open_positions=(),
        )
        self.assertEqual(card["lane_c"]["state"], "EXCLUDED")

    def test_quiet_when_no_signal(self):
        flat = [100.0] * 260
        card = h7_watch.assemble_name(
            symbol="XXXX", closes=_closes(flat),
            chain=_chain(center=100.0, iv=0.40),
            today=date(2026, 7, 8), calendar={}, open_positions=(),
        )
        self.assertEqual(card["lane_a"]["state"], "QUIET")
        self.assertEqual(card["lane_b"]["state"], "QUIET")
