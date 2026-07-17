"""H9 census — counts and data sufficiency only; structurally no P&L."""
import inspect
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from options_researcher import h9_census as cz
from options_researcher.h9_events import H9Event


def entry_chain(rows):
    cols = ["expiration", "strike", "right", "bid", "ask", "open_interest",
            "iv", "delta", "gamma", "theta", "vega"]
    data = [
        {"expiration": e, "strike": k, "right": r, "bid": b, "ask": a,
         "open_interest": oi, "iv": 0.5, "delta": d, "gamma": 0.0,
         "theta": 0.0, "vega": 0.0}
        for (e, k, r, b, a, oi, d) in rows
    ]
    return pd.DataFrame(data, columns=cols)


def event(symbol="MSFT", occurred="2026-04-29", t_pre="2026-04-29",
          t_dec="2026-04-30", t_entry="2026-05-01"):
    return H9Event(symbol=symbol, occurred_date=date.fromisoformat(occurred),
                   accepted_utc=datetime(2026, 4, 29, 20, 3, tzinfo=timezone.utc),
                   t_pre=t_pre, t_dec=t_dec, t_entry=t_entry)


GOOD_ROW = ("2026-06-19", 400.0, "C", 9.8, 10.0, 500, 0.40)  # monthly, in-band


class CensusStructureTests(unittest.TestCase):
    def test_census_result_has_no_price_or_pnl_fields(self):
        fields = set(cz.CensusResult.__dataclass_fields__)
        self.assertFalse(fields & {"pnl", "returns", "prices", "marks", "proceeds"})

    def test_census_module_never_imports_exit_pricing(self):
        src = inspect.getsource(cz)
        self.assertNotIn("adverse_sell", src)
        self.assertNotIn("scoreboard", src)


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.chain_dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def touch_chain(self, symbol, iso):
        (self.chain_dir / f"{symbol}_{iso}.parquet").touch()

    def test_missing_entry_chain_excluded(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        with mock.patch.object(cz, "_entry_chain", side_effect=FileNotFoundError):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.reasons.get("missing_entry_chain"), 1)
        self.assertEqual(res.eligible_count, 0)

    def test_window_edge_excluded(self):
        e = event(t_entry=None)
        res = cz.run_census([e], chain_dir=self.chain_dir)
        self.assertEqual(res.reasons.get("window_edge"), 1)

    def test_eligible_event_counted_with_manifest(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        self.touch_chain("MSFT", "2026-05-01")
        with mock.patch.object(cz, "_entry_chain",
                               return_value=entry_chain([GOOD_ROW])):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.eligible_count, 1)
        self.assertEqual(res.per_symbol["MSFT"]["eligible"], 1)
        self.assertTrue(res.floor_met is False)  # 1 < H9_MIN_ELIGIBLE_EVENTS

    def test_no_contract_in_bands_excluded(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        bad = ("2026-06-19", 400.0, "C", 9.8, 10.0, 500, 0.10)  # delta below band
        with mock.patch.object(cz, "_entry_chain", return_value=entry_chain([bad])):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.reasons.get("no_contract_in_bands"), 1)

    def test_exit_window_gaps_are_warn_not_exclusion(self):
        closes = pd.Series({"2026-04-29": 100.0, "2026-04-30": 103.0})
        with mock.patch.object(cz, "_entry_chain",
                               return_value=entry_chain([GOOD_ROW])):
            with mock.patch.object(cz, "_closes", return_value=closes):
                res = cz.run_census([event()], chain_dir=self.chain_dir)
        self.assertEqual(res.eligible_count, 1)
        self.assertGreater(res.exit_window_gap_days, 0)
