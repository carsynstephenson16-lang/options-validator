import contextlib
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import pandas as pd
from test_qm_signals import PARAMS, breakout_fixture, parabolic_fixture
from test_schwab_chain_view import _write_store

import config
from options_researcher import h10_observe, h10_watch, qm_signals, schwab_chain_view
from options_researcher.chains import third_friday
from options_researcher.h7_watch import evaluation_session


def _next_session(iso: str) -> str:
    """The first XNYS session strictly after `iso`."""
    from data.cache_runner import trading_days

    start = date.fromisoformat(iso)
    days = trading_days(iso, (start + timedelta(days=14)).isoformat())
    return next(day for day in days if day > iso)


# Every date below is DERIVED from the registered resume floor so a merge-time
# floor update (seq 28 clause 5 makes the constant mechanical, not frozen)
# cannot turn this suite red for a reason that has nothing to do with the
# behavior under test.
EVAL_ISO = config.H10B_RESUME_FLOOR_SESSION
AS_OF = _next_session(EVAL_ISO)  # the RUN date whose evaluated session is the floor
PRE_FLOOR_RUN = EVAL_ISO  # running ON the floor evaluates the session BEFORE it
PRE_FLOOR_EVAL = evaluation_session(date.fromisoformat(PRE_FLOOR_RUN)).isoformat()
_WALL_CLOCK = datetime.fromisoformat(f"{_next_session(AS_OF)}T12:00:00+00:00")
KNOWN_AS_OF = datetime.fromisoformat(f"{EVAL_ISO}T20:00:00+00:00")
_EXPIRY_TARGET = date.fromisoformat(EVAL_ISO) + timedelta(days=45)
EXPIRATION = third_friday(_EXPIRY_TARGET.year, _EXPIRY_TARGET.month).isoformat()
BOOK_HEADER = (
    "id,symbol,strike,expiration,contracts,entry_date,entry_cost,"
    "entry_receipt_hash,exit_date,exit_proceeds,exit_reason,exit_receipt_hash\n"
)


def _relabel(frame: pd.DataFrame, end_iso: str) -> pd.DataFrame:
    index = pd.bdate_range(end=end_iso, periods=len(frame))
    out = frame.copy()
    out.index = pd.Index([day.strftime("%Y-%m-%d") for day in index], name="date")
    return out


def _adjusted_quiet(_symbol: str, eval_iso: str) -> pd.DataFrame:
    closes = [100.0] * 80
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [value + 1.0 for value in closes],
            "low": [value - 1.0 for value in closes],
            "close": closes,
            "volume": [1_000_000.0] * len(closes),
        }
    )
    return _relabel(frame, eval_iso)


def _adjusted_breakout(_symbol: str, eval_iso: str) -> pd.DataFrame:
    return _relabel(breakout_fixture(), eval_iso)


def _adjusted_parabolic(_symbol: str, eval_iso: str) -> pd.DataFrame:
    frame = parabolic_fixture()
    first = next(
        position
        for position, stamp in enumerate(frame.index)
        if qm_signals.parabolic_qualifies(frame, stamp, PARAMS)
    )
    return _relabel(frame.iloc[: first + 1], eval_iso)


def _raw(_symbol: str, eval_iso: str) -> pd.DataFrame:
    closes = [100.0] * 5
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [101.0] * len(closes),
            "low": [99.0] * len(closes),
            "close": closes,
            "volume": [1_000_000.0] * len(closes),
        }
    )
    return _relabel(frame, eval_iso)


def _chain(_symbol: str, _eval_iso: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            (EXPIRATION, 92.0, "C", 0.60, 4.80, 5.00, 500, 0.5753),
            (EXPIRATION, 96.0, "C", 0.55, 4.80, 5.00, 500, 0.5753),
            (EXPIRATION, 100.0, "C", 0.50, 4.80, 5.00, 500, 0.5753),
            (EXPIRATION, 104.0, "C", 0.45, 4.80, 5.00, 500, 0.5753),
            (EXPIRATION, 108.0, "C", 0.40, 4.80, 5.00, 500, 0.5753),
            (EXPIRATION, 100.0, "P", -0.50, 4.80, 5.00, 500, 0.5753),
        ],
        columns=(
            "expiration",
            "strike",
            "right",
            "delta",
            "bid",
            "ask",
            "open_interest",
            "iv",
        ),
    )


def _schwab_view_chain(symbol: str, eval_iso: str) -> pd.DataFrame:
    """Fixture-backed verified-view frame with its full display schema."""
    frame = _chain(symbol, eval_iso).copy()
    frame["gamma"] = 0.02
    frame["theta"] = -0.04
    frame["vega"] = 0.12
    farther_monthly = frame.iloc[[0]].copy()
    farther_monthly.loc[:, "expiration"] = "2026-11-20"
    return pd.concat([frame, farther_monthly], ignore_index=True)


def _assertion(report: str = "2030-01-01", *, symbol: str = "PLTR") -> dict:
    return {
        "record_id": f"{symbol}-2026Q3-confirmed",
        "symbol": symbol,
        "event_id": f"{symbol}-2026Q3",
        "fiscal_period": "2026Q3",
        "record_type": "assertion",
        "event_class": "actual_quarterly_earnings",
        "status": "confirmed",
        "expected_date": date.fromisoformat(report),
        "occurred_date": None,
        "session_timing": "amc",
        "source_type": "company_ir",
        "source_url": "https://example.test/pltr-ir",
        "known_as_of_utc": datetime.fromisoformat("2026-07-01T12:00:00+00:00"),
        "checked_at_utc": datetime.fromisoformat("2026-07-01T12:00:00+00:00"),
        "supersedes": "",
        "promoted_from": "raw-1",
        "notes": "",
    }


def _write_book(path: Path, *, open_premium: float | None = None) -> None:
    text = BOOK_HEADER
    if open_premium is not None:
        text += f"h10-1,NVDA,100,2026-08-21,1,2026-07-01,{open_premium:.2f},{'a' * 64},,,,\n"
    path.write_text(text, encoding="utf-8")


def _run(
    root: Path,
    *,
    adjusted=_adjusted_quiet,
    preclose_loader=None,
    use_default_preclose_adapter: bool = False,
    assertions: list[dict] | None = None,
    universe: list[str] | None = None,
):
    book = root / "h10_positions.csv"
    if not book.exists():
        _write_book(book)
    receipts = root / "receipts"
    stdout = io.StringIO()
    if preclose_loader is None and not use_default_preclose_adapter:
        preclose_loader = lambda symbol, _session: (_chain(symbol, EVAL_ISO), EVAL_ISO)
    preclose_kwargs = (
        {} if use_default_preclose_adapter else {"load_preclose_chain": preclose_loader}
    )
    with (
        mock.patch.object(h10_watch, "datetime") as watch_datetime,
        contextlib.redirect_stdout(stdout),
    ):
        watch_datetime.now.return_value = _WALL_CLOCK
        rc = h10_watch.main(
            ["--as-of", AS_OF],
            universe=["PLTR"] if universe is None else universe,
            load_adjusted=adjusted,
            load_raw=_raw,
            **preclose_kwargs,
            params=PARAMS,
            gate=lambda: None,
            load_assertions_fn=lambda: [_assertion()] if assertions is None else assertions,
            book_path=book,
            receipt_dir=receipts,
            known_as_of=KNOWN_AS_OF,
        )
    receipt_path = receipts / f"h10_watch_{AS_OF}.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    return rc, stdout.getvalue(), receipt, receipt_path


class QuietTests(unittest.TestCase):
    def test_no_signal_is_explicitly_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, output, receipt, _ = _run(Path(tmp))

        self.assertEqual(rc, 0)
        self.assertIn("forward paper study H10b (H10a adjudicated)", output)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "NO_SIGNAL")
        self.assertEqual(row["signals"], {"H10a": None, "H10b": False})
        self.assertEqual(row["h10a_status"], h10_watch.H10A_ADJUDICATED)
        self.assertIsNone(row["candidate_contract"])
        self.assertFalse(row["book_action_required"])
        self.assertFalse(receipt["book_action_required"])


class FireTests(unittest.TestCase):
    def test_closed_h10a_is_never_evaluated_inside_its_former_window(self):
        calls: list[object] = []

        def forbidden_parabolic(*_args, **_kwargs):
            calls.append(object())
            raise AssertionError("closed H10a must not be evaluated")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(qm_signals, "parabolic_fires", forbidden_parabolic):
                rc, output, receipt, receipt_path = _run(root, adjusted=_adjusted_parabolic)
            h10b_path = root / "h10b_observations.jsonl"
            observe_output = io.StringIO()
            with contextlib.redirect_stdout(observe_output):
                observe_rc = h10_observe.main(
                    ["--as-of", AS_OF],
                    receipt_path=receipt_path,
                    observations_path=h10b_path,
                    legacy_observations_path=root / "observations.jsonl",
                    book_path=root / "h10_positions.csv",
                )
            observation_rows = [
                json.loads(line) for line in h10b_path.read_text(encoding="utf-8").splitlines()
            ]
            output_files = sorted(
                path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
            )

        self.assertEqual(rc, 0)
        self.assertEqual(observe_rc, 0, observe_output.getvalue())
        self.assertEqual(calls, [])
        self.assertIn("never trades", output)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "NO_SIGNAL")
        self.assertEqual(row["signals"], {"H10a": None, "H10b": False})
        self.assertEqual(row["h10a_status"], h10_watch.H10A_ADJUDICATED)
        self.assertEqual([item["hypothesis"] for item in observation_rows], ["H10b"])
        self.assertEqual(
            output_files,
            [
                "h10_positions.csv",
                "h10b_observations.jsonl",
                f"receipts/h10_watch_{AS_OF}.json",
            ],
        )

    def test_breakout_continuation_fire_selects_a_call_from_verified_preclose(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, output, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        self.assertIn("verdict gates on losses", output)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["signals"], {"H10a": None, "H10b": True})
        self.assertEqual(row["admitted_contracts"], 5)
        self.assertTrue(row["book_action_required"])
        candidate = row["candidate_contract"]
        self.assertEqual(candidate["right"], "C")
        self.assertEqual(candidate["strike"], 92.0)
        self.assertEqual(candidate["delta"], 0.60)
        self.assertEqual(candidate["entry_price"], 5.05)
        self.assertEqual(candidate["exit_price"], 4.75)
        self.assertEqual(candidate["entry_cost"], 505.65)
        self.assertEqual(candidate["iv"], 0.5753)
        self.assertEqual(candidate["spot"], 100.0)
        self.assertEqual(row["chain_timing_convention"], h10_watch.MIXED_TIMING_CONVENTION)

    def test_breakout_continuation_fire_is_recorded_as_h10b(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["signals"], {"H10a": None, "H10b": True})
        self.assertTrue(receipt["book_action_required"])

    def test_failed_h7_admission_is_an_explicit_skip(self):
        def four_contracts(symbol: str, eval_iso: str) -> pd.DataFrame:
            return _chain(symbol, eval_iso).iloc[:4].copy()

        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda _symbol, _session: (
                    four_contracts("PLTR", EVAL_ISO),
                    EVAL_ISO,
                ),
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "ADMISSION")
        self.assertEqual(row["admitted_contracts"], 4)
        self.assertFalse(row["book_action_required"])

    def test_after_cost_premium_cap_is_a_hard_contract_gate(self):
        def expensive(symbol: str, eval_iso: str) -> pd.DataFrame:
            frame = _chain(symbol, eval_iso)
            frame.loc[frame["right"] == "C", ["bid", "ask"]] = [5.80, 6.00]
            return frame

        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda _symbol, _session: (expensive("PLTR", EVAL_ISO), EVAL_ISO),
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "NO_CONTRACT")
        self.assertIsNone(row["candidate_contract"])

    def test_five_percent_spread_gate_counts_admission_and_never_filters_selection(self):
        """The 5% figure is the ADMISSION COUNT gate, not a selection filter.

        Registered design: admission counts NTM monthly contracts with
        spread <= H7_ADMIT_MAX_SPREAD_PCT (5%); the SELECTED contract is gated
        by the execution surface only (`passes_liquidity`, MAX_SPREAD_PCT 10%
        + MIN_OPEN_INTEREST, both legs). A 2026-08 change had applied the 5%
        figure to selection too, which silently tightened the registered entry
        stack; this pins the reverted behavior on both halves at once.
        """

        def one_wide_quote(symbol: str, eval_iso: str) -> pd.DataFrame:
            frame = _chain(symbol, eval_iso)
            # 7.25% spread: over the 5% admission gate, under the 10%
            # execution gate. It is the highest-delta call, so a selection
            # filter at 5% is the only thing that could displace it.
            frame.loc[0, ["bid", "ask"]] = [4.65, 5.0]
            frame.loc[len(frame)] = [
                EXPIRATION,
                102.0,
                "C",
                0.50,
                4.80,
                5.00,
                500,
                0.5753,
            ]
            return frame

        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda _symbol, _session: (
                    one_wide_quote("PLTR", EVAL_ISO),
                    EVAL_ISO,
                ),
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        candidate = row["candidate_contract"]
        # Selection keeps the wide-but-executable 0.60-delta call.
        self.assertEqual(candidate["strike"], 92.0)
        self.assertEqual(candidate["delta"], 0.60)
        # Admission still applies the 5% gate: 6 calls in the band, the wide
        # one excluded.
        self.assertEqual(row["admitted_contracts"], 5)

    def test_missing_verified_preclose_capture_skips_and_logs_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, output, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda _symbol, _session: None,
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "SCHWAB_CAPTURE")
        self.assertIn("SCHWAB_CAPTURE", output)


class PrecloseCaptureIntegrityTests(unittest.TestCase):
    def _run_default_adapter(self, root: Path):
        chain_dir = root / ".cache" / "schwab_chains"
        reports_dir = root / "reports" / "schwab_chains"
        schwab_chain_view._reset_memo_for_tests()
        try:
            with mock.patch.object(
                schwab_chain_view,
                "_dirs",
                return_value=(chain_dir, reports_dir),
            ):
                return _run(
                    root,
                    adjusted=_adjusted_breakout,
                    use_default_preclose_adapter=True,
                )
        finally:
            schwab_chain_view._reset_memo_for_tests()

    def test_default_adapter_uses_only_current_verified_full_universe_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = _schwab_view_chain("PLTR", EVAL_ISO)
            _write_store(
                root,
                list(config.H7_WATCHLIST),
                session=EVAL_ISO,
                frames={symbol: frame for symbol in config.H7_WATCHLIST},
            )
            rc, _, receipt, _ = self._run_default_adapter(root)

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["chain_session"], EVAL_ISO)
        self.assertEqual(row["candidate_contract"]["iv"], 0.5753)

    def test_stale_preclose_session_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda *_args: (_chain("PLTR", EVAL_ISO), PRE_FLOOR_EVAL),
            )

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "SKIPPED")
        self.assertEqual(receipt["evaluations"][0]["reason"], "SCHWAB_CAPTURE")

    def test_future_preclose_session_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda *_args: (_chain("PLTR", EVAL_ISO), AS_OF),
            )

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "SKIPPED")
        self.assertEqual(receipt["evaluations"][0]["reason"], "SCHWAB_CAPTURE")

    def test_partial_current_capture_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_store(
                root,
                ["PLTR"],
                session=EVAL_ISO,
                frames={"PLTR": _schwab_view_chain("PLTR", EVAL_ISO)},
            )
            rc, _, receipt, _ = self._run_default_adapter(root)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "SKIPPED")
        self.assertEqual(receipt["evaluations"][0]["reason"], "SCHWAB_CAPTURE")

    def test_failed_current_capture_never_falls_back_to_an_older_verified_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older_session = PRE_FLOOR_EVAL
            frame = _schwab_view_chain("PLTR", older_session)
            _write_store(
                root,
                list(config.H7_WATCHLIST),
                session=older_session,
                frames={symbol: frame for symbol in config.H7_WATCHLIST},
            )
            failed_current = root / "reports" / "schwab_chains" / EVAL_ISO
            failed_current.mkdir(parents=True)
            (failed_current / "preclose.json").write_text("{}\n", encoding="utf-8")
            rc, _, receipt, _ = self._run_default_adapter(root)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "SKIPPED")
        self.assertEqual(receipt["evaluations"][0]["reason"], "SCHWAB_CAPTURE")

    def test_delta_gate_is_on_absolute_delta_as_registered(self):
        """H10's registered band is |delta| 0.40-0.60 (`abs_delta`).

        A sign-flipped call quote is a provider defect, not a different
        contract: the registered wording bands the magnitude, and the recorded
        delta is that magnitude. A 2026-08 change had dropped the `.abs()`,
        which silently narrowed the registered band.
        """
        frame = _chain("PLTR", EVAL_ISO)
        frame.loc[frame["right"] == "C", "delta"] = -0.50
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda *_args: (frame, EVAL_ISO),
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["candidate_contract"]["delta"], 0.50)

    def test_nonfinite_iv_inside_the_candidate_band_is_its_own_skip_reason(self):
        """A malformed band row is NOT reported as a missing capture."""
        frame = _chain("PLTR", EVAL_ISO)
        frame.loc[0, "iv"] = float("nan")  # 92-strike call, inside the band
        with tempfile.TemporaryDirectory() as tmp:
            rc, output, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda *_args: (frame, EVAL_ISO),
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "MALFORMED_ROWS")
        self.assertNotEqual(row["reason"], "SCHWAB_CAPTURE")
        self.assertIn("MALFORMED_ROWS", output)

    def test_nonfinite_field_outside_the_candidate_band_does_not_skip_the_session(self):
        """One garbage row elsewhere in a 3000-row chain is not a lost session."""
        frame = _chain("PLTR", EVAL_ISO)
        far = date.fromisoformat(EXPIRATION) + timedelta(days=365)
        frame.loc[len(frame)] = [
            far.isoformat(),  # far outside the 30-60 DTE band
            200.0,  # and outside the +/-10% strike band
            "C",
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
        ]
        frame.loc[frame["right"].eq("P"), "iv"] = float("nan")  # puts are never candidates
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda *_args: (frame, EVAL_ISO),
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["candidate_contract"]["strike"], 92.0)

    def test_nonfinite_strike_on_a_band_dated_call_is_malformed_not_ignored(self):
        """A NaN strike cannot be ruled out of the band, so it fails closed."""
        frame = _chain("PLTR", EVAL_ISO)
        frame.loc[len(frame)] = [
            EXPIRATION,
            float("nan"),
            "C",
            0.50,
            4.80,
            5.00,
            500,
            0.5753,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=lambda *_args: (frame, EVAL_ISO),
            )

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "SKIPPED")
        self.assertEqual(receipt["evaluations"][0]["reason"], "MALFORMED_ROWS")

    def test_manifest_error_from_view_is_skipped(self):
        from tools.schwab_chain_manifest import SchwabChainManifestError

        def malformed_view(*_args):
            raise SchwabChainManifestError("fixture malformed")

        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                preclose_loader=malformed_view,
            )

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "SKIPPED")
        self.assertEqual(receipt["evaluations"][0]["reason"], "SCHWAB_CAPTURE")


class CapTests(unittest.TestCase):
    def test_monthly_cap_is_reserved_across_symbols_in_one_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_book(root / "h10_positions.csv", open_premium=1_400.00)
            rc, _, receipt, _ = _run(
                root,
                adjusted=_adjusted_breakout,
                universe=["PLTR", "NVDA"],
                assertions=[
                    _assertion("2030-01-01"),
                    _assertion("2030-01-01", symbol="NVDA"),
                ],
            )

        self.assertEqual(rc, 0)
        rows = receipt["evaluations"]
        self.assertEqual([row["status"] for row in rows], ["FIRED", "SKIPPED"])
        self.assertEqual(rows[1]["reason"], "CAP")
        self.assertTrue(rows[0]["book_action_required"])
        self.assertFalse(rows[1]["book_action_required"])

    def test_cap_exceeded_is_skipped_with_cap_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_book(root / "h10_positions.csv", open_premium=1_500.00)
            rc, _, receipt, _ = _run(root, adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "CAP")
        self.assertIsNotNone(row["candidate_contract"])
        self.assertFalse(row["book_action_required"])

    def test_header_only_book_allows_an_eligible_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluations"][0]["status"], "FIRED")


class EarningsSkipTests(unittest.TestCase):
    def test_known_report_inside_option_life_skips_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(
                Path(tmp),
                adjusted=_adjusted_breakout,
                assertions=[_assertion("2026-09-01")],
            )

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "EARNINGS")
        self.assertFalse(row["book_action_required"])

    def test_unhealthy_source_is_a_per_name_entry_ban(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout, assertions=[])

        self.assertEqual(rc, 0)
        row = receipt["evaluations"][0]
        self.assertEqual(row["status"], "SKIPPED")
        self.assertEqual(row["reason"], "SOURCE_HEALTH")


class ReceiptTests(unittest.TestCase):
    def test_receipt_schema_keys_are_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(
            set(receipt),
            {"as_of", "evaluation_session", "evaluations", "book_action_required"},
        )
        row = receipt["evaluations"][0]
        self.assertEqual(
            set(row),
            {
                "symbol",
                "signals",
                "h10a_status",
                "window_status",
                "status",
                "reason",
                "admitted_contracts",
                "candidate_contract",
                "book_action_required",
                "chain_session",
                "chain_timing_convention",
            },
        )
        self.assertEqual(set(row["signals"]), {"H10a", "H10b"})
        self.assertEqual(set(row["window_status"]), {"H10b"})
        self.assertEqual(row["window_status"], {"H10b": "OPEN"})
        self.assertEqual(
            set(row["candidate_contract"]),
            {
                "symbol",
                "right",
                "strike",
                "expiration",
                "dte",
                "delta",
                "bid",
                "ask",
                "open_interest",
                "spot",
                "entry_price",
                "exit_price",
                "entry_cost",
                "iv",
            },
        )

    def test_same_as_of_is_idempotent_and_only_receipt_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book = root / "h10_positions.csv"
            _write_book(book)
            before_book = book.read_bytes()
            first_rc, _, _, path = _run(root, adjusted=_adjusted_breakout)
            first_bytes = path.read_bytes()
            second_rc, _, _, second_path = _run(root, adjusted=_adjusted_breakout)
            second_bytes = second_path.read_bytes()
            after_book = book.read_bytes()
            files = sorted(
                item.relative_to(root).as_posix() for item in root.rglob("*") if item.is_file()
            )

        self.assertEqual((first_rc, second_rc), (0, 0))
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(before_book, after_book)
        self.assertEqual(
            files,
            ["h10_positions.csv", f"receipts/h10_watch_{AS_OF}.json"],
        )


class FutureAsOfTests(unittest.TestCase):
    def test_future_as_of_refuses_before_loaders_or_receipt(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        calls: list[str] = []

        def spy(symbol: str, _session: str):
            calls.append(symbol)
            raise AssertionError("future refusal must precede data loading")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_book(root / "h10_positions.csv")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = h10_watch.main(
                    ["--as-of", future],
                    universe=["PLTR"],
                    load_adjusted=spy,
                    load_raw=spy,
                    load_preclose_chain=spy,
                    params=PARAMS,
                    gate=lambda: None,
                    load_assertions_fn=lambda: [],
                    book_path=root / "h10_positions.csv",
                    receipt_dir=root / "receipts",
                    known_as_of=KNOWN_AS_OF,
                )

        self.assertEqual(rc, 2)
        self.assertEqual(calls, [])
        self.assertIn("future", stdout.getvalue().lower())
        self.assertFalse((root / "receipts").exists())


def _chain_for(eval_iso: str) -> pd.DataFrame:
    """Same shape as `_chain` above, but with an expiration relative to
    `eval_iso` so the DTE band still admits candidates far from AS_OF."""
    target = date.fromisoformat(eval_iso) + timedelta(days=45)
    expiration = third_friday(target.year, target.month).isoformat()
    return pd.DataFrame(
        [
            (expiration, 92.0, "C", 0.60, 4.80, 5.00, 500, 0.5753),
            (expiration, 96.0, "C", 0.55, 4.80, 5.00, 500, 0.5753),
            (expiration, 100.0, "C", 0.50, 4.80, 5.00, 500, 0.5753),
            (expiration, 104.0, "C", 0.45, 4.80, 5.00, 500, 0.5753),
            (expiration, 108.0, "C", 0.40, 4.80, 5.00, 500, 0.5753),
            (expiration, 100.0, "P", -0.50, 4.80, 5.00, 500, 0.5753),
        ],
        columns=(
            "expiration",
            "strike",
            "right",
            "delta",
            "bid",
            "ask",
            "open_interest",
            "iv",
        ),
    )


class H10bWindowTests(unittest.TestCase):
    def test_window_status_open_on_h10b_end_date(self):
        self.assertEqual(h10_watch._window_status(config.H10B_WINDOW_END), {"H10b": "OPEN"})

    def test_window_status_closed_strictly_after_h10b_end_date(self):
        self.assertEqual(h10_watch._window_status("2027-01-07"), {"H10b": "WINDOW_CLOSED"})

    def test_breakout_fire_allowed_on_h10b_window_end_date(self):
        eval_iso = config.H10B_WINDOW_END
        frame = _adjusted_breakout("PLTR", eval_iso)
        signals = h10_watch._signals_at_session(frame, eval_iso, PARAMS)
        self.assertTrue(signals["H10b"])

    def test_breakout_fire_suppressed_the_session_after_h10b_window_end(self):
        eval_iso = "2027-01-07"  # the trading day after H10B_WINDOW_END
        frame = _adjusted_breakout("PLTR", eval_iso)
        signals = h10_watch._signals_at_session(frame, eval_iso, PARAMS)
        self.assertFalse(signals["H10b"])

    def test_evaluation_row_fires_and_reports_open_on_window_end_date(self):
        eval_iso = config.H10B_WINDOW_END
        row = h10_watch._evaluation(
            "PLTR",
            eval_iso=eval_iso,
            params=PARAMS,
            load_adjusted=_adjusted_breakout,
            load_raw=_raw,
            load_preclose_chain=lambda _symbol, _session: (_chain_for(eval_iso), eval_iso),
            assertions=[_assertion("2030-01-01")],
            known_as_of=datetime.fromisoformat(f"{eval_iso}T20:00:00+00:00"),
            open_premium=0.0,
        )

        self.assertEqual(row["status"], "FIRED")
        self.assertEqual(row["signals"], {"H10a": None, "H10b": True})
        self.assertEqual(row["window_status"], {"H10b": "OPEN"})

    def test_evaluation_row_suppresses_fire_and_reports_window_closed(self):
        eval_iso = "2027-01-07"  # the trading day after H10B_WINDOW_END
        row = h10_watch._evaluation(
            "PLTR",
            eval_iso=eval_iso,
            params=PARAMS,
            load_adjusted=_adjusted_breakout,
            load_raw=_raw,
            load_preclose_chain=lambda _symbol, _session: (_chain_for(eval_iso), eval_iso),
            assertions=[_assertion("2030-01-01")],
            known_as_of=datetime.fromisoformat(f"{eval_iso}T20:00:00+00:00"),
            open_premium=0.0,
        )

        self.assertEqual(row["status"], "NO_SIGNAL")
        self.assertEqual(row["signals"], {"H10a": None, "H10b": False})
        self.assertFalse(row["book_action_required"])
        self.assertIsNone(row["candidate_contract"])
        self.assertEqual(row["window_status"], {"H10b": "WINDOW_CLOSED"})


class ResumeFloorTests(unittest.TestCase):
    def test_pre_floor_evaluation_refuses_before_loaders_or_receipt(self):
        calls: list[str] = []

        def forbidden(_symbol: str, _eval_iso: str):
            calls.append("adjusted")
            raise AssertionError("floor refusal must precede data loading")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_book(root / "h10_positions.csv")
            stdout = io.StringIO()
            with (
                mock.patch.object(h10_watch, "datetime") as watch_datetime,
                contextlib.redirect_stdout(stdout),
            ):
                watch_datetime.now.return_value = _WALL_CLOCK
                rc = h10_watch.main(
                    ["--as-of", PRE_FLOOR_RUN],
                    universe=["PLTR"],
                    load_adjusted=forbidden,
                    load_raw=forbidden,
                    load_preclose_chain=lambda _symbol, _session: None,
                    params=PARAMS,
                    gate=lambda: None,
                    load_assertions_fn=lambda: [],
                    book_path=root / "h10_positions.csv",
                    receipt_dir=root / "receipts",
                    known_as_of=KNOWN_AS_OF,
                )

        self.assertEqual(rc, 2)
        self.assertEqual(calls, [])
        self.assertIn(f"evaluation_session={PRE_FLOOR_EVAL}", stdout.getvalue())
        self.assertFalse((root / "receipts").exists())

    def test_floor_session_records_the_evaluated_session_not_cli_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, receipt, _ = _run(Path(tmp), adjusted=_adjusted_breakout)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["evaluation_session"], config.H10B_RESUME_FLOOR_SESSION)


if __name__ == "__main__":
    unittest.main()
