"""tests/test_qm_study.py -- offline unit tests for the QM event study CLI.

Fixtures are synthetic frames/chains (no network, no parquet, no config
QM_* values -- params are injected). Guardrails exercised: gate-first refusal,
hand-computed forward/MFE/MAE/baseline math, tradability liquidity gating and
"no chain" accounting, counts-only mode never running outcome paths.
"""

import contextlib
import io
import os
import tempfile
import unittest
from datetime import date, timedelta

import pandas as pd

from options_researcher import qm_signals, qm_study

PARAMS = {
    "QM_RUN_LOOKBACK": 60,
    "QM_RUN_MIN_PCT": 0.30,
    "QM_BASE_MIN_DAYS": 10,
    "QM_BASE_MAX_DAYS": 40,
    "QM_BASE_MAX_DEPTH": 0.25,
    "QM_BASE_SMA": 20,
    "QM_VOL_DRYUP_RATIO": 0.65,
    "QM_PARA_LOOKBACK": 40,
    "QM_PARA_MIN_PCT": 1.00,
    "QM_PARA_GREEN_DAYS": 3,
    "QM_PARA_EXT_PCT": 0.50,
    "QM_PARA_SMA": 20,
    "QM_HORIZONS": (1, 2),
    "QM_TRADABILITY_DTE": (30, 60),
    "QM_NTM_BAND": 0.10,
}


def _iso(n, start="2020-01-02"):
    return [d.date().isoformat() for d in pd.bdate_range(start, periods=n)]


def _frame(closes, highs=None, lows=None, vols=None):
    idx = _iso(len(closes))
    highs = highs if highs is not None else closes
    lows = lows if lows is not None else closes
    vols = vols if vols is not None else [1.0] * len(closes)
    return pd.DataFrame(
        {"open": closes, "high": highs, "low": lows, "close": closes, "volume": vols},
        index=idx,
    ).astype(float)


def _chain(center, base_iso, *, oi=900, bid=5.0, ask=5.1, dte_days=45):
    exp = (date.fromisoformat(base_iso) + timedelta(days=dte_days)).isoformat()
    rows = []
    for k in range(5):
        rows.append({
            "expiration": exp, "strike": center - 4 + 2 * k, "right": "C",
            "bid": bid, "ask": ask, "open_interest": oi,
            "iv": 0.4, "delta": 0.5, "gamma": 0.0, "theta": 0.0, "vega": 0.0,
        })
    return pd.DataFrame(rows)


def _boom(*_a, **_k):
    raise AssertionError("loader called after gate refusal / in counts-only mode")


@contextlib.contextmanager
def _patched(**attrs):
    old = {k: getattr(qm_signals, k, None) for k in attrs}
    for k, v in attrs.items():
        setattr(qm_signals, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(qm_signals, k, v)


class GateTests(unittest.TestCase):
    def test_gate_refusal_exits_2_without_touching_data(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = qm_study.main(
                [],
                gate=lambda: "REFUSED: QM pre-registration incomplete",
                universe=["NVDA"], params=PARAMS,
                load_adjusted=_boom, load_raw=_boom, load_chain=_boom,
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf.getvalue())


class MetricTests(unittest.TestCase):
    def test_forward_returns_exact(self):
        f = _frame([10, 11, 12, 13, 14])
        fr = qm_study.forward_returns(f, f.index[0], (1, 2))
        self.assertAlmostEqual(fr[1], 0.1)
        self.assertAlmostEqual(fr[2], 0.2)

    def test_forward_returns_truncated_is_none(self):
        f = _frame([10, 11, 12, 13, 14])
        fr = qm_study.forward_returns(f, f.index[4], (1,))
        self.assertIsNone(fr[1])

    def test_mfe_mae_exact(self):
        f = _frame([10, 11, 12], highs=[10, 12, 15], lows=[10, 9, 8])
        mfe, mae = qm_study.mfe_mae(f, f.index[0], 2)
        self.assertAlmostEqual(mfe, 0.5)   # max high 15 / 10 - 1
        self.assertAlmostEqual(mae, -0.2)  # min low 8 / 10 - 1

    def test_mfe_mae_none_at_end(self):
        f = _frame([10, 11, 12], highs=[10, 12, 15], lows=[10, 9, 8])
        self.assertEqual(qm_study.mfe_mae(f, f.index[2], 2), (None, None))

    def test_baseline_stats_hand_checked(self):
        f = _frame([10, 11, 12], highs=[10, 12, 14], lows=[10, 9, 8])
        bs = qm_study.baseline_stats(f, (1,))
        # returns: pos0 -> 0.1, pos1 -> 12/11-1
        r = bs["returns"][1]
        self.assertEqual(r["n"], 2)
        self.assertAlmostEqual(r["mean"], (0.1 + (12 / 11 - 1)) / 2)
        # mfe: pos0 -> 12/10-1=0.2 ; pos1 -> 14/11-1
        self.assertEqual(bs["mfe"]["n"], 2)
        self.assertAlmostEqual(bs["mfe"]["mean"], (0.2 + (14 / 11 - 1)) / 2)
        # mae: pos0 -> 9/10-1=-0.1 ; pos1 -> 8/11-1
        self.assertAlmostEqual(bs["mae"]["mean"], (-0.1 + (8 / 11 - 1)) / 2)

    def test_aggregate_truncation_counted(self):
        f = _frame([10, 11, 12])
        agg = qm_study._aggregate_outcomes(f, [f.index[1]], (1, 2), 2)
        self.assertEqual(agg["truncated"], 1)      # h2 falls off the end
        self.assertEqual(agg["returns"][2]["n"], 0)
        self.assertEqual(agg["returns"][1]["n"], 1)


class TradabilityTests(unittest.TestCase):
    def test_passing_contract_true(self):
        base = _iso(2)[1]
        chain = _chain(center=100.0, base_iso=base)
        self.assertTrue(
            qm_study.fire_tradability(chain, base, 100.0, (30, 60), 0.10)
        )

    def test_all_illiquid_false(self):
        base = _iso(2)[1]
        chain = _chain(center=100.0, base_iso=base, oi=10)  # below MIN_OPEN_INTEREST
        self.assertFalse(
            qm_study.fire_tradability(chain, base, 100.0, (30, 60), 0.10)
        )

    def test_no_chain_string(self):
        self.assertEqual(
            qm_study.fire_tradability(None, "2020-01-03", 100.0, (30, 60), 0.10),
            "no chain",
        )

    def test_no_chain_accounting_through_study_path(self):
        f = _frame([50, 55, 60])
        trad = qm_study._aggregate_tradability(
            lambda _s, _i: {}, "AAA", f, [f.index[1]], (30, 60), 0.10
        )
        self.assertEqual(trad["no_chain"], 1)
        self.assertEqual(trad["tradable"], 0)
        self.assertEqual(trad["untradable"], 0)


class CountsOnlyTests(unittest.TestCase):
    def test_counts_only_never_runs_outcomes(self):
        f = _frame([50, 55, 60, 66, 70, 72])
        iso = f.index[1]
        cwd = os.getcwd()
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                # forward_returns raising proves the outcome path never runs.
                orig_fr = qm_study.forward_returns
                qm_study.forward_returns = _boom
                with _patched(
                    breakout_fires=lambda _f, _p: [{"t": iso}],
                    parabolic_fires=lambda _f, _p: [iso],
                ), contextlib.redirect_stdout(buf):
                    rc = qm_study.main(
                        ["--counts-only"],
                        universe=["AAA"], params=PARAMS, gate=lambda: None,
                        load_adjusted=lambda _s, _a, _b: f,
                        load_raw=_boom, load_chain=_boom,
                    )
                qm_study.forward_returns = orig_fr
                self.assertEqual(rc, 0)
                # nothing written to disk in counts-only mode
                self.assertFalse(
                    any("qm-base-rates.md" in p for p in os.listdir(".")
                        if os.path.isfile(p))
                )
                if os.path.isdir("reports"):
                    self.assertEqual(os.listdir("reports"), [])
            finally:
                os.chdir(cwd)
        out = buf.getvalue()
        self.assertIn("Fire counts", out)
        self.assertIn("AAA", out)
        self.assertNotIn("Outcomes vs baseline", out)
        self.assertNotIn("%", out)  # no forward-return numbers


class FullModeTests(unittest.TestCase):
    def test_full_mode_writes_report_with_caveats_and_fade_view(self):
        f = _frame([50, 55, 60, 66, 70, 72])
        iso = f.index[1]
        chain = _chain(center=55.0, base_iso=iso)
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "qm.md")
            with _patched(
                breakout_fires=lambda _f, _p: [{"t": iso}],
                parabolic_fires=lambda _f, _p: [iso],
            ), contextlib.redirect_stdout(buf):
                rc = qm_study.main(
                    ["--out", out],
                    universe=["AAA"], params=PARAMS, gate=lambda: None,
                    load_adjusted=lambda _s, _a, _b: f,
                    load_raw=lambda _s, _a, _b: f,
                    load_chain=lambda _s, i: {iso: chain},
                )
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out))
            with open(out) as fh:
                body = fh.read()
        stdout = buf.getvalue()
        self.assertIn("hindsight-selected after the AI boom", body)
        self.assertIn("fade view (sign-flipped)", body)
        self.assertIn("Outcomes vs baseline", body)
        # caveats echoed to stdout too
        self.assertIn("Caveats (read first)", stdout)
        self.assertIn("EOD approximation", stdout)

    def test_build_report_discloses_truncation(self):
        f = _frame([10, 11, 12])
        iso = f.index[1]
        res = [{
            "symbol": "AAA", "gap": None,
            "baseline": qm_study.baseline_stats(f, (1, 2)),
            "breakout": {
                "n": 1, "fires": [iso],
                "agg": qm_study._aggregate_outcomes(f, [iso], (1, 2), 2),
                "trad": {"tradable": 0, "untradable": 0, "no_chain": 1},
            },
            "parabolic": {
                "n": 0, "fires": [],
                "agg": qm_study._aggregate_outcomes(f, [], (1, 2), 2),
                "trad": {"tradable": 0, "untradable": 0, "no_chain": 0},
            },
        }]
        report = qm_study.build_report(
            "2026-07-14", res, counts_only=False, params={"QM_HORIZONS": (1, 2)}
        )
        self.assertIn("truncated", report)


if __name__ == "__main__":
    unittest.main()
