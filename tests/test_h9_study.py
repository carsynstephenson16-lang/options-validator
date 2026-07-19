"""H9 trigger + lifecycle on injected fixtures. No real data."""
import unittest
from datetime import date, datetime, timezone

import pandas as pd

from options_researcher import h9_study as st
from options_researcher.h9_events import H9Event


def chain(rows):
    cols = ["expiration", "strike", "right", "bid", "ask", "open_interest",
            "iv", "delta", "gamma", "theta", "vega"]
    return pd.DataFrame(
        [{"expiration": e, "strike": k, "right": r, "bid": b, "ask": a,
          "open_interest": oi, "iv": 0.5, "delta": d, "gamma": 0.0,
          "theta": 0.0, "vega": 0.0} for (e, k, r, b, a, oi, d) in rows],
        columns=cols)


def ev(t_pre="2026-04-29", t_dec="2026-04-30", t_entry="2026-05-01"):
    return H9Event(symbol="MSFT", occurred_date=date(2026, 4, 29),
                   accepted_utc=datetime(2026, 4, 29, 20, 3, tzinfo=timezone.utc),
                   t_pre=t_pre, t_dec=t_dec, t_entry=t_entry)


ENTRY = ("2026-06-19", 400.0, "C", 9.8, 10.0, 500, 0.40)  # monthly


class TriggerTests(unittest.TestCase):
    def test_reaction_below_min_is_no_trade(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 101.0})
        self.assertEqual(st.trigger(ev(), closes), "reaction_below_min")

    def test_negative_reaction_is_no_trade(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 95.0})
        self.assertEqual(st.trigger(ev(), closes), "reaction_below_min")

    def test_positive_reaction_triggers_call(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        self.assertEqual(st.trigger(ev(), closes), "call")


class SelectionTests(unittest.TestCase):
    def test_highest_delta_in_band_wins(self):
        rows = [ENTRY, ("2026-06-19", 390.0, "C", 12.0, 12.4, 500, 0.48),
                ("2026-06-19", 380.0, "C", 15.0, 15.5, 500, 0.55)]  # out of band
        pick = st.select_contract(chain(rows), "2026-05-01")
        self.assertEqual(pick["delta"], 0.48)

    def test_premium_cap_binds(self):
        pick = st.select_contract(chain([ENTRY]), "2026-05-01")
        self.assertIsNone(st.entry_cost_if_within_cap(pick))
        cheap = ("2026-06-19", 430.0, "C", 4.8, 5.0, 500, 0.32)
        pick2 = st.select_contract(chain([cheap, ENTRY]), "2026-05-01")
        # highest-delta preference picks 0.40, which breaches the cap ->
        # cancel, not re-pick (spec §3 cancel semantics)
        self.assertEqual(pick2["delta"], 0.40)
        self.assertIsNone(st.entry_cost_if_within_cap(pick2))


class LifecycleTests(unittest.TestCase):
    def _provider(self, marks):
        def get(symbol, iso):
            if iso not in marks:
                raise FileNotFoundError(iso)
            b, a = marks[iso]
            return chain([("2026-06-19", 430.0, "C", b, a, 500, 0.32)])
        return get

    def test_take_profit_decided_then_filled_next_session(self):
        marks = {"2026-05-01": (4.8, 5.0),
                 "2026-05-04": (11.0, 11.2),
                 "2026-05-05": (10.0, 10.2)}
        trade = st.simulate_trade(ev(), self._provider(marks),
                                  next_report_iso=None)
        self.assertEqual(trade["exit_reason"], "take_profit")
        self.assertEqual(trade["exit_fill_session"], "2026-05-05")
        self.assertAlmostEqual(trade["pnl"],
                               (10.0 * 0.99 * 100 - 0.65) - (5.0 * 1.01 * 100 + 0.65),
                               delta=1.5)

    def test_missing_exit_chain_visible_gap_then_next_valid(self):
        marks = {"2026-05-01": (4.8, 5.0),
                 "2026-05-04": (11.0, 11.2),
                 "2026-05-06": (9.5, 9.7)}
        trade = st.simulate_trade(ev(), self._provider(marks), next_report_iso=None)
        self.assertEqual(trade["exit_fill_session"], "2026-05-06")
        self.assertIn("2026-05-05", trade["gaps"])

    def test_pre_next_report_exit_outranks_tp(self):
        marks = {"2026-05-01": (4.8, 5.0),
                 "2026-05-04": (11.0, 11.2),
                 "2026-05-05": (11.0, 11.2)}
        trade = st.simulate_trade(ev(), self._provider(marks),
                                  next_report_iso="2026-05-06")
        self.assertEqual(trade["exit_reason"], "pre_next_report")


class WorthlessQuoteTests(unittest.TestCase):
    def _provider(self, marks):
        def get(symbol, iso):
            if iso not in marks:
                raise FileNotFoundError(iso)
            b, a = marks[iso]
            return chain([("2026-06-19", 430.0, "C", b, a, 500, 0.32)])
        return get

    def test_present_zero_bid_books_max_loss_not_gap(self):
        marks = {"2026-05-01": (4.8, 5.0)}
        # every later session through expiration shows a PRESENT row, bid 0
        from data.cache_runner import trading_days
        for s in trading_days("2026-05-01", "2026-06-30")[1:]:
            marks[s] = (0.0, 0.05)
        trade = st.simulate_trade(ev(), self._provider(marks), next_report_iso=None)
        self.assertIsNotNone(trade["pnl"])
        self.assertAlmostEqual(trade["pnl"], -trade["capital_at_risk"], places=2)
        self.assertTrue(trade["worthless_quote_exit"])
        self.assertNotEqual(trade["exit_reason"], "unresolved_data_gap")

    def test_report_too_close_to_entry_fails_loud(self):
        marks = {"2026-05-01": (4.8, 5.0), "2026-05-04": (5.0, 5.2)}
        with self.assertRaises(ValueError):
            st.simulate_trade(ev(), self._provider(marks),
                              next_report_iso="2026-05-04")

    def test_protective_exit_decides_on_calendar_despite_missing_chain(self):
        # dte-21 session chain missing entirely; decision still fires there,
        # fill lands on the next session with a valid quote
        marks = {"2026-05-01": (4.8, 5.0)}
        from data.cache_runner import trading_days
        days = trading_days("2026-05-01", "2026-06-30")
        dte21 = next(s for s in days[1:]
                     if (date(2026, 6, 19) - date.fromisoformat(s)).days <= 21)
        after = [s for s in days if s > dte21]
        marks[after[0]] = (4.0, 4.2)
        trade = st.simulate_trade(ev(), self._provider(marks), next_report_iso=None)
        self.assertEqual(trade["exit_reason"], "dte_close")
        self.assertEqual(trade["exit_fill_session"], after[0])


class StrikeToleranceTests(unittest.TestCase):
    def test_float_jitter_still_matches(self):
        entry = chain([("2026-06-19", 430.0, "C", 4.8, 5.0, 500, 0.32)])
        jitter = chain([("2026-06-19", 430.0000000001, "C", 11.0, 11.2, 500, 0.32)])
        def get(symbol, iso):
            return {"2026-05-01": entry}.get(iso, jitter)
        trade = st.simulate_trade(ev(), get, next_report_iso=None)
        self.assertEqual(trade["exit_reason"], "take_profit")
        self.assertFalse(trade["worthless_quote_exit"])


class AdjudicationTests(unittest.TestCase):
    def test_vocabulary_mapping(self):
        self.assertEqual(st.map_verdict({"verdict": "FAIL (CI90 upper < 0)"}),
                         "REJECTED")
        self.assertEqual(st.map_verdict({"verdict": "INSUFFICIENT SAMPLE (n_loss=3)"}),
                         "INSUFFICIENT_SAMPLE")
        self.assertEqual(st.map_verdict({"verdict": "NO EDGE"}),
                         "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST")
        self.assertEqual(st.map_verdict({"verdict": "PASS (CI90 lower > 0)"}),
                         "NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST")
