"""tests/test_entry_watch.py -- H5's verified-Schwab OBSERVER.

Ledger seq 29 clause 1 retired H5's entry trigger. There is no trigger-grading
helper left to test; what these tests must prove instead is that no FIRE-shaped
output can be produced at all, that availability and IV accumulation are
counted PER NAME, and that unknowns are reported as unknown.
"""
import contextlib
import inspect
import io
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import pandas as pd
from test_schwab_chain_view import _chain_frame, _write_store

import config
from options_researcher import entry_watch as ew
from options_researcher import schwab_chain_view
from options_researcher.chains import is_monthly, third_friday
from options_researcher.h7_watch import evaluation_session


def _next_session(iso: str) -> str:
    """The first XNYS session strictly after `iso`."""
    from data.cache_runner import trading_days

    start = date.fromisoformat(iso)
    days = trading_days(iso, (start + timedelta(days=14)).isoformat())
    return next(day for day in days if day > iso)


def _monthly_in_window(iso: str) -> date:
    """The earliest standard monthly inside `chains.nearest_monthly`'s band."""
    base = date.fromisoformat(iso)
    year, month = base.year, base.month
    for _ in range(4):
        expiration = third_friday(year, month)
        if 15 <= (expiration - base).days <= 60:
            return expiration
        month, year = (1, year + 1) if month == 12 else (month + 1, year)
    raise AssertionError(f"no monthly expiration in window for {iso}")


def _next_monthly(after: date) -> date:
    month, year = (1, after.year + 1) if after.month == 12 else (after.month + 1, after.year)
    return third_friday(year, month)


def _non_monthlies(iso: str) -> tuple[str, str]:
    """Two distinct in-window expirations that are NOT standard monthlies."""
    base = date.fromisoformat(iso)
    found = [
        (base + timedelta(days=offset)).isoformat()
        for offset in range(20, 56)
        if not is_monthly(base + timedelta(days=offset))
    ]
    return found[0], found[-1]


# Derived from the registered floor, never hardcoded: seq 29 clause 5 makes the
# constant mechanical (set at merge), so a floor update must not red this file.
EVALUATION = config.H5_RESUME_FLOOR_SESSION
RUN_DATE = _next_session(EVALUATION)
PRE_FLOOR_RUN = EVALUATION  # running ON the floor evaluates the session BEFORE it
PRE_FLOOR_EVAL = evaluation_session(date.fromisoformat(PRE_FLOOR_RUN)).isoformat()
PRIOR_SESSION = PRE_FLOOR_EVAL
_WALL_CLOCK = datetime.fromisoformat(f"{_next_session(RUN_DATE)}T12:00:00+00:00")
MONTHLY_EXPIRATION = _monthly_in_window(EVALUATION)
FARTHER_EXPIRATION = _next_monthly(MONTHLY_EXPIRATION)
ATM_IV = 0.43210 + 0.01  # `_chain_frame` offsets the ATM put row by +0.01


def _h5_chain(iv: float = 0.43210, *,
              expirations: tuple[str, str] | None = None) -> pd.DataFrame:
    """A display-schema capture whose ATM monthly row is deterministic.

    Two distinct expirations: the capture manifest verifier refuses a
    single-expiration package, so this cannot be collapsed to one date.
    """
    near, far = expirations or (MONTHLY_EXPIRATION.isoformat(),
                                FARTHER_EXPIRATION.isoformat())
    frame = _chain_frame(iv=iv)
    frame["expiration"] = [near, near, far, far]
    return frame


class _ObserverRunner:
    """Shared harness: run the REAL observer against a fixture capture store."""

    def _run(self, root: Path, *, run_date: str = RUN_DATE,
             close_loader=None) -> tuple[int, str]:
        if close_loader is None:
            close_loader = lambda *_args, **_kwargs: pd.Series(
                [100.0], index=[EVALUATION])
        stdout = io.StringIO()
        schwab_chain_view._reset_memo_for_tests()
        try:
            with (
                mock.patch.object(
                    schwab_chain_view, "_dirs",
                    return_value=(root / ".cache" / "schwab_chains",
                                  root / "reports" / "schwab_chains")),
                mock.patch("data.underlying_closes.load_closes",
                           side_effect=close_loader),
                mock.patch.object(ew, "datetime") as watch_datetime,
                contextlib.redirect_stdout(stdout),
            ):
                watch_datetime.now.return_value = _WALL_CLOCK
                rc = ew.main(as_of=run_date)
        finally:
            schwab_chain_view._reset_memo_for_tests()
        return rc, stdout.getvalue()

    def _gather_rows(self, root: Path) -> list[dict]:
        schwab_chain_view._reset_memo_for_tests()
        try:
            with (
                mock.patch.object(
                    schwab_chain_view, "_dirs",
                    return_value=(root / ".cache" / "schwab_chains",
                                  root / "reports" / "schwab_chains")),
                mock.patch("data.underlying_closes.load_closes",
                           return_value=pd.Series([100.0], index=[EVALUATION])),
                mock.patch.object(ew, "datetime") as watch_datetime,
            ):
                watch_datetime.now.return_value = _WALL_CLOCK
                return ew._gather(RUN_DATE)
        finally:
            schwab_chain_view._reset_memo_for_tests()


class NoFirePathTests(unittest.TestCase):
    """F-5: the module cannot produce a FIRE, by construction."""

    def test_injected_rows_are_refused_through_the_real_entry_point(self):
        rows = [{"symbol": "VST", "verdict": "FIRE", "close": 1.0}]
        with self.assertRaises(ValueError) as caught:
            ew.main(rows=rows)
        self.assertIn("refuses injected trigger rows", str(caught.exception))

    def test_the_refusal_is_reached_before_any_source_is_read(self):
        with mock.patch.object(
            ew, "_resolve_evaluation_session",
            side_effect=AssertionError("injected rows must refuse first"),
        ):
            with self.assertRaises(ValueError):
                ew.main(rows=[{"symbol": "VST", "verdict": "FIRE"}])

    def test_no_trigger_grading_helper_survives_in_the_module(self):
        """seq 29 clause 1: the retired rule has no evaluator anywhere."""
        for retired in ("trigger_status", "_exact_iv_rank", "_chain_edge",
                        "_data_gap_row", "_enforce_exact_row"):
            with self.subTest(name=retired):
                self.assertFalse(hasattr(ew, retired))
        source = inspect.getsource(ew)
        self.assertNotIn('"FIRE"', source)
        self.assertNotIn('"WAIT"', source)
        self.assertNotIn("H5_ENTRY_IVR_MAX", source)
        self.assertNotIn("passes_liquidity", source)

    def test_the_retired_trigger_survives_as_frozen_history_in_config(self):
        """seq 29: retired triggers "remain on the append-only record"."""
        self.assertEqual(config.H5_ENTRY_TRIGGERS, {"VST": 160.0, "AMZN": 220.0})
        self.assertEqual(config.H5_ENTRY_IVR_MAX, 0.5)

    def test_no_cached_thetadata_chain_path_survives(self):
        """The observer's only chain source is the verified Schwab view."""
        source = inspect.getsource(ew)
        self.assertNotIn(".cache/chains", source)


class H5ObserverAsOfContractTests(unittest.TestCase):
    """F-3: `--as-of` is a RUN date; the report is named for the SESSION."""

    @staticmethod
    def _clock():
        """Pin the wall clock: RUN_DATE is a future date on most run days."""
        patched = mock.patch.object(ew, "datetime")
        stub = patched.start()
        stub.now.return_value = _WALL_CLOCK
        return patched

    def test_as_of_is_a_run_date_and_resolves_the_prior_completed_session(self):
        patched = self._clock()
        self.addCleanup(patched.stop)
        resolved = ew._resolve_evaluation_session(RUN_DATE)
        self.assertEqual(resolved.isoformat(), EVALUATION)
        self.assertLess(resolved.isoformat(), RUN_DATE)

    def test_the_contract_matches_h10_watch_exactly(self):
        patched = self._clock()
        self.addCleanup(patched.stop)
        run = date.fromisoformat(RUN_DATE)
        self.assertEqual(ew._resolve_evaluation_session(run), evaluation_session(run))

    def test_future_run_dates_are_refused(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        with self.assertRaises(ValueError):
            ew._resolve_evaluation_session(future)

    def test_ritual_names_the_report_for_the_evaluation_session_it_evaluates(self):
        """The ritual passes $RUN_DATE and writes entry_watch_$AS_OF.txt.

        `ritual_receipt._h5` then demands `evaluation_session=$AS_OF` inside
        that file. If the two conventions ever disagreed, every capture receipt
        would silently read REFUSED.
        """
        source = Path("tools/daily_ritual.sh").read_text(encoding="utf-8")
        self.assertIn('EW_OUT="reports/h5/entry_watch_${AS_OF}.txt"', source)
        self.assertIn(
            'options_researcher.entry_watch --as-of "$RUN_DATE" --out "$EW_OUT"',
            source,
        )
        self.assertNotIn('options_researcher.entry_watch --as-of "$AS_OF"', source)


class H5SchwabObserverTests(_ObserverRunner, unittest.TestCase):
    def test_real_path_uses_unscaled_schwab_atm_iv_without_a_fire_output(self):
        """A feature-store read or a second IV divide breaks this report."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = {symbol: _h5_chain() for symbol in config.H5_ENTRY_TRIGGERS}
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=EVALUATION, frames=frames)
            with mock.patch("options_researcher.features.load_features",
                            side_effect=AssertionError("feature IV is forbidden")):
                rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("observational / non-verdict-bearing", output)
        self.assertIn(f"max_asof_session={EVALUATION}", output)
        self.assertIn("capture_available=True", output)
        self.assertIn(f"ATM Schwab IV {ATM_IV:.5f}", output)
        self.assertIn("1/126 finite Schwab observations", output)
        self.assertNotIn("FIRE", output)
        self.assertNotIn("WAIT", output)

    def test_pre_floor_run_refuses_before_loading_inputs(self):
        calls: list[str] = []

        def forbidden(*_args, **_kwargs):
            calls.append("close")
            raise AssertionError("floor refusal must precede source loading")

        with tempfile.TemporaryDirectory() as tmp:
            rc, output = self._run(Path(tmp), run_date=PRE_FLOOR_RUN,
                                   close_loader=forbidden)

        self.assertEqual(rc, 2, output)
        self.assertEqual(calls, [])
        self.assertIn(f"evaluation_session={PRE_FLOOR_EVAL}", output)
        self.assertIn(config.H5_RESUME_FLOOR_SESSION, output)
        self.assertNotIn("OBSERVED", output)

    def test_verified_history_counts_one_h5_atm_iv_per_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            symbols = sorted((*config.H5_ENTRY_TRIGGERS, "PLTR"))
            frames = {symbol: _h5_chain() for symbol in symbols}
            _write_store(root, symbols, session=PRIOR_SESSION, frames=frames)
            _write_store(root, symbols, session=EVALUATION, frames=frames)
            rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("2/126 finite Schwab observations", output)
        self.assertIn("VST: OBSERVED", output)
        self.assertIn("AMZN: OBSERVED", output)
        self.assertNotIn("PLTR:", output)

    def test_stale_or_future_capture_cannot_substitute_for_the_exact_session(self):
        for session in (PRIOR_SESSION, RUN_DATE):
            with self.subTest(session=session), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write_store(root, sorted(config.H5_ENTRY_TRIGGERS), session=session)
                rc, output = self._run(root)
            self.assertEqual(rc, 1, output)
            self.assertIn("exact verified Schwab capture", output)
            self.assertIn("capture_available=False", output)
            self.assertNotIn("OBSERVED", output)

    def test_missing_stale_future_or_nonfinite_price_fails_closed(self):
        sources = {
            "missing": FileNotFoundError("close missing"),
            "stale": pd.Series([100.0], index=[PRIOR_SESSION]),
            "future": pd.Series([100.0], index=[RUN_DATE]),
            "nonfinite": pd.Series([float("nan")], index=[EVALUATION]),
        }
        for name, source in sources.items():
            with self.subTest(source=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                             session=EVALUATION)
                if isinstance(source, Exception):
                    loader = mock.Mock(side_effect=source)
                else:
                    loader = mock.Mock(return_value=source)
                rc, output = self._run(root, close_loader=loader)

            self.assertEqual(rc, 1, output)
            self.assertIn("close", output)
            self.assertIn("capture_available=True", output)
            self.assertNotIn("OBSERVED", output)

    def test_unverified_exact_package_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=EVALUATION)
            _chain_frame(iv=0.61).to_parquet(
                root / ".cache" / "schwab_chains" / f"VST_{EVALUATION}.parquet")
            rc, output = self._run(root)

        self.assertEqual(rc, 1, output)
        self.assertIn("unverified", output)
        self.assertNotIn("OBSERVED", output)

    def test_malformed_verified_chain_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed = _h5_chain().drop(columns=["gamma"])
            frames = {symbol: malformed for symbol in config.H5_ENTRY_TRIGGERS}
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=EVALUATION, frames=frames)
            rc, output = self._run(root)

        self.assertEqual(rc, 1, output)
        self.assertIn("malformed", output)
        self.assertNotIn("OBSERVED", output)

    def test_nonfinite_atm_iv_does_not_increment_the_schwab_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frames = {symbol: _h5_chain(iv=float("nan"))
                      for symbol in config.H5_ENTRY_TRIGGERS}
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=EVALUATION, frames=frames)
            rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("ATM Schwab IV unavailable (non-finite quote)", output)
        self.assertIn("0/126 finite Schwab observations", output)


class PerNameDecouplingTests(_ObserverRunner, unittest.TestCase):
    """F-4: availability and IV accumulation are counted PER NAME (seq 29 §2)."""

    def test_a_session_that_captured_one_name_still_observes_that_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, ["VST"], session=EVALUATION,
                         frames={"VST": _h5_chain()})
            rc, output = self._run(root)

        # Fail-visible overall (one name has no data), but VST's observation
        # is NOT discarded because AMZN's capture is missing.
        self.assertEqual(rc, 1, output)
        self.assertIn("VST: OBSERVED", output)
        self.assertIn("AMZN: DATA_GAP", output)
        self.assertIn("omits AMZN", output)

    def test_the_missing_name_is_the_one_that_data_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, ["AMZN"], session=EVALUATION,
                         frames={"AMZN": _h5_chain()})
            rc, output = self._run(root)

        self.assertEqual(rc, 1, output)
        self.assertIn("AMZN: OBSERVED", output)
        self.assertIn("VST: DATA_GAP", output)
        self.assertIn("omits VST", output)

    def test_iv_accumulation_counts_only_the_sessions_that_captured_the_name(self):
        """A history session missing AMZN is not a hole in VST's 126."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, ["VST"], session=PRIOR_SESSION,
                         frames={"VST": _h5_chain()})
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=EVALUATION,
                         frames={s: _h5_chain() for s in config.H5_ENTRY_TRIGGERS})
            rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("VST: OBSERVED", output)
        self.assertIn("AMZN: OBSERVED", output)
        vst = next(line for line in output.splitlines() if line.startswith("VST:"))
        amzn = next(line for line in output.splitlines() if line.startswith("AMZN:"))
        # VST was captured on both sessions; AMZN only on the evaluation one.
        self.assertIn("2/126 finite Schwab observations", vst)
        self.assertIn("1/126 finite Schwab observations", amzn)


class HonestUnknownsTests(_ObserverRunner, unittest.TestCase):
    """F-7: a DATA_GAP never claims a count it did not compute."""

    def test_data_gap_rows_report_an_uncounted_iv_history_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, ["VST"], session=EVALUATION,
                         frames={"VST": _h5_chain()})
            rows = self._gather_rows(root)

        gap = next(row for row in rows if row["symbol"] == "AMZN")
        self.assertEqual(gap["state"], "DATA_GAP")
        self.assertIsNone(gap["finite_schwab_iv_observations"])
        self.assertEqual(gap["finite_schwab_iv_observations_state"], "NOT_COUNTED")
        self.assertIsNone(gap["atm_schwab_iv"])
        self.assertEqual(gap["atm_schwab_iv_state"], "NOT_OBSERVED")

    def test_data_gap_lines_say_not_counted_instead_of_printing_a_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, ["VST"], session=EVALUATION,
                         frames={"VST": _h5_chain()})
            _rc, output = self._run(root)

        amzn = next(line for line in output.splitlines() if line.startswith("AMZN:"))
        self.assertIn("finite Schwab observations not counted", amzn)
        self.assertNotIn("0/126", amzn)

    def test_a_non_finite_quote_and_a_malformed_chain_are_different_states(self):
        non_finite = _h5_chain(iv=float("nan"))
        no_atm_row = _h5_chain()
        no_atm_row["right"] = ["C"] * len(no_atm_row)  # no put -> no ATM row

        value, defect = ew._atm_schwab_iv(non_finite, date.fromisoformat(EVALUATION))
        self.assertIsNone(value)
        self.assertIsNone(defect)

        value, defect = ew._atm_schwab_iv(no_atm_row, date.fromisoformat(EVALUATION))
        self.assertIsNone(value)
        self.assertIsNotNone(defect)

    def test_a_malformed_atm_row_renders_as_malformed_not_as_a_missing_quote(self):
        no_monthly = _h5_chain(expirations=_non_monthlies(EVALUATION))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(root, sorted(config.H5_ENTRY_TRIGGERS),
                         session=EVALUATION,
                         frames={s: no_monthly for s in config.H5_ENTRY_TRIGGERS})
            rc, output = self._run(root)

        self.assertEqual(rc, 0, output)
        self.assertIn("ATM Schwab IV MALFORMED", output)
        self.assertNotIn("ATM Schwab IV unavailable", output)


class GatherMemoTests(_ObserverRunner, unittest.TestCase):
    """F-8: one `_gather()` re-verifies and re-reads nothing."""

    def test_verification_and_parquet_reads_happen_once_per_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            symbols = sorted(config.H5_ENTRY_TRIGGERS)
            for session in (PRIOR_SESSION, EVALUATION):
                _write_store(root, symbols, session=session,
                             frames={s: _h5_chain() for s in symbols})

            schwab_chain_view._reset_memo_for_tests()
            real_verified = schwab_chain_view.verified_sessions
            real_load = schwab_chain_view.load_chain
            verified_calls: list[int] = []
            load_calls: list[tuple[str, str]] = []

            def counting_verified(*args, **kwargs):
                verified_calls.append(1)
                return real_verified(*args, **kwargs)

            def counting_load(symbol, session, **kwargs):
                load_calls.append((symbol, session))
                return real_load(symbol, session, **kwargs)

            try:
                with (
                    mock.patch.object(
                        schwab_chain_view, "_dirs",
                        return_value=(root / ".cache" / "schwab_chains",
                                      root / "reports" / "schwab_chains")),
                    mock.patch.object(schwab_chain_view, "verified_sessions",
                                      counting_verified),
                    mock.patch.object(schwab_chain_view, "load_chain",
                                      counting_load),
                    mock.patch("data.underlying_closes.load_closes",
                               return_value=pd.Series([100.0], index=[EVALUATION])),
                    mock.patch.object(ew, "datetime") as watch_datetime,
                ):
                    watch_datetime.now.return_value = _WALL_CLOCK
                    rows = ew._gather(RUN_DATE)
            finally:
                schwab_chain_view._reset_memo_for_tests()

        self.assertEqual(len(rows), 2)
        # One verified-view read for the whole invocation...
        self.assertEqual(len(verified_calls), 1)
        # ...and one parquet read per (symbol, session), never per use.
        self.assertEqual(len(load_calls), len(set(load_calls)))
        self.assertEqual(
            set(load_calls),
            {(symbol, session)
             for symbol in config.H5_ENTRY_TRIGGERS
             for session in (PRIOR_SESSION, EVALUATION)},
        )

    def test_the_memo_does_not_survive_between_gather_calls(self):
        """A process-lifetime cache would serve a stale view after a capture."""
        self.assertIsNot(ew._VerifiedViewCache(), ew._VerifiedViewCache())
        self.assertIn("_VerifiedViewCache()", inspect.getsource(ew._gather))


if __name__ == "__main__":
    unittest.main()
