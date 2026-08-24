"""Offline tests for Brief 22 chain-consistency shadow observations."""

from __future__ import annotations

import contextlib
import hashlib
import io
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from data.chain_consistency import audit_pair

PREV = "2026-08-19"
CUR = "2026-08-20"
CALENDAR = ("2026-08-18", PREV, CUR, "2026-08-21")


def _chain() -> pd.DataFrame:
    """Small Schwab-shaped standard-contract fixture with two liquid puts."""
    return pd.DataFrame(
        {
            "expiration": ["2026-09-18", "2026-09-18"],
            "strike": [100.0, 105.0],
            "right": ["P", "P"],
            "contract_symbol": ["SYN260918P00100000", "SYN260918P00105000"],
            "bid": [1.00, 1.50],
            "ask": [1.05, 1.56],
            "open_interest": [config.MIN_OPEN_INTEREST + 50] * 2,
            "iv": [0.43, 0.44],
            "delta": [-0.40, -0.35],
            "gamma": [0.01, 0.01],
            "theta": [-0.02, -0.02],
            "vega": [0.10, 0.10],
            "multiplier": [100.0, 100.0],
            "non_standard": [False, False],
            "mini": [False, False],
            "timestamp": pd.to_datetime([f"{PREV}T19:45:00Z"] * 2),
            "trade_timestamp": pd.to_datetime([f"{PREV}T19:40:00Z"] * 2),
        }
    )


def _audit(
    prev: pd.DataFrame | None = None,
    cur: pd.DataFrame | None = None,
    *,
    prev_session: str = PREV,
    cur_session: str = CUR,
    calendar: tuple[str, ...] = CALENDAR,
    prev_close: float = 100.0,
    cur_close: float = 100.5,
):
    return audit_pair(
        _chain() if prev is None else prev,
        _chain() if cur is None else cur,
        prev_close,
        cur_close,
        prev_session=prev_session,
        cur_session=cur_session,
        calendar_sessions=calendar,
    )


class ChainConsistencyPureTests(unittest.TestCase):
    def test_gap_session_is_reported_when_previous_is_not_calendar_adjacent(self):
        report = _audit(prev_session="2026-08-18")

        self.assertEqual(report.status, "GAP_SESSION")
        self.assertEqual(report.flag_counts["GAP_SESSION"], 1)

    def test_expiry_vanished_is_reported_for_admitted_unexpired_expiration(self):
        prev = _chain()
        cur = _chain()
        cur["expiration"] = "2026-10-16"

        report = _audit(prev, cur)

        self.assertEqual(report.status, "EXPIRY_VANISHED")
        self.assertEqual(report.flag_counts["EXPIRY_VANISHED"], 1)

    def test_strike_vanished_is_reported_for_admitted_unexpired_contract(self):
        report = _audit(_chain(), _chain().iloc[:1].copy())

        self.assertEqual(report.status, "STRIKE_VANISHED")
        self.assertEqual(report.flag_counts["STRIKE_VANISHED"], 1)

    def test_iv_jump_is_absent_after_the_predeclared_noise_kill(self):
        cur = _chain()
        cur.loc[0, "iv"] = 0.84

        report = _audit(_chain(), cur)

        self.assertEqual(report.status, "OK")
        self.assertNotIn("IV_JUMP", report.flag_counts)
        self.assertFalse(hasattr(config, "CONSISTENCY_IV_JUMP_ABS"))

    def test_delta_jump_is_reported_only_under_small_underlying_move(self):
        cur = _chain()
        cur.loc[0, "delta"] = -0.75

        report = _audit(_chain(), cur)

        self.assertEqual(report.status, "DELTA_JUMP")
        self.assertEqual(report.flag_counts["DELTA_JUMP"], 1)

    def test_spread_blowout_requires_double_prior_fraction_and_max_spread_breach(self):
        cur = _chain()
        cur.loc[0, ["bid", "ask"]] = [0.50, 1.50]

        report = _audit(_chain(), cur)

        self.assertEqual(report.status, "SPREAD_BLOWOUT")
        self.assertEqual(report.flag_counts["SPREAD_BLOWOUT"], 1)

    def test_ok_has_no_fired_flags(self):
        report = _audit()

        self.assertEqual(report.status, "OK")
        self.assertTrue(all(count == 0 for count in report.flag_counts.values()))

    def test_evaluated_counts_make_jump_rates_auditable(self):
        report = _audit()
        missing_iv = _audit(_chain(), _chain().drop(columns="iv"))

        self.assertEqual(report.evaluated_counts["DELTA_JUMP"], 2)
        self.assertEqual(report.evaluated_counts["SPREAD_BLOWOUT"], 2)
        self.assertEqual(missing_iv.evaluated_counts["DELTA_JUMP"], 2)

    def test_injected_corruptions_each_fire_only_the_intended_observation(self):
        cases: list[tuple[str, pd.DataFrame, str]] = []
        delta = _chain()
        delta.loc[0, "delta"] = 0.75
        cases.append(("delta", delta, "DELTA_JUMP"))
        vanished = _chain().iloc[:1].copy()
        cases.append(("vanished", vanished, "STRIKE_VANISHED"))
        spread = _chain()
        spread.loc[0, ["bid", "ask"]] = [0.50, 1.50]
        cases.append(("spread", spread, "SPREAD_BLOWOUT"))

        for name, cur, expected in cases:
            with self.subTest(corruption=name):
                report = _audit(_chain(), cur)
                fired = {flag for flag, count in report.flag_counts.items() if count}
                self.assertEqual(fired, {expected})

    def test_precedence_uses_worst_flag(self):
        cur = _chain().iloc[:1].copy()

        report = _audit(_chain(), cur, prev_session="2026-08-18")

        self.assertEqual(report.status, "GAP_SESSION")
        self.assertEqual(report.flag_counts["STRIKE_VANISHED"], 1)

    def test_missing_required_column_is_visible_not_silently_skipped(self):
        evaluated = _audit()
        missing = _audit(_chain(), _chain().drop(columns="delta"))

        self.assertNotIn("DELTA_JUMP", evaluated.not_evaluable_flags)
        self.assertIn("DELTA_JUMP", missing.not_evaluable_flags)
        self.assertEqual(missing.flag_counts["DELTA_JUMP"], 0)

    def test_missing_contract_key_is_visible_instead_of_raising(self):
        report = _audit(_chain(), _chain().drop(columns="right"))

        self.assertEqual(report.status, "NOT_EVALUABLE")
        self.assertIn("EXPIRY_VANISHED", report.not_evaluable_flags)
        self.assertIn("STRIKE_VANISHED", report.not_evaluable_flags)
        self.assertIn("DELTA_JUMP", report.not_evaluable_flags)
        self.assertIn("SPREAD_BLOWOUT", report.not_evaluable_flags)

    def test_new_listing_never_flags(self):
        cur = _chain()
        cur.loc[len(cur)] = cur.iloc[0].to_dict()
        cur.loc[len(cur) - 1, "strike"] = 110.0
        cur.loc[len(cur) - 1, "contract_symbol"] = "SYN260918P00110000"

        report = _audit(_chain(), cur)

        self.assertEqual(report.status, "OK")

    def test_expired_contract_is_excluded(self):
        prev = _chain()
        prev.loc[0, "expiration"] = "2026-08-19"
        cur = _chain().iloc[1:].copy()

        report = _audit(prev, cur)

        self.assertEqual(report.status, "OK")

    def test_examples_are_bounded(self):
        prev = pd.concat([_chain()] * (config.CONSISTENCY_MAX_EXAMPLES + 2), ignore_index=True)
        prev["strike"] = list(range(100, 100 + len(prev)))
        cur = prev.copy()
        cur["delta"] = cur["delta"] + 0.31

        report = _audit(prev, cur)

        self.assertEqual(report.flag_counts["DELTA_JUMP"], len(prev))
        self.assertEqual(len(report.flag_examples["DELTA_JUMP"]), config.CONSISTENCY_MAX_EXAMPLES)


class ChainConsistencyCliTests(unittest.TestCase):
    def setUp(self):
        from tools import chain_consistency_audit as cli

        self.cli = cli
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chain_dir = self.root / ".cache" / "schwab_chains"
        self.chain_dir.mkdir(parents=True)
        self.out_dir = self.root / ".tmp" / "chain_consistency" / "test_receipts"
        self.addCleanup(self.tmp.cleanup)

    def _write_pair(
        self,
        symbol: str = "SYN",
        *,
        sessions: tuple[str, ...] = (PREV, CUR),
        cur: pd.DataFrame | None = None,
    ) -> None:
        for session in sessions:
            frame = _chain()
            if session == CUR and cur is not None:
                frame = cur
            frame.to_parquet(self.chain_dir / f"{symbol}_{session}.parquet", index=False)
        close_dir = self.root / ".cache" / "underlying"
        close_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "date": list(sessions),
                "close": [100.0 + index * 0.5 for index, _ in enumerate(sessions)],
            }
        ).to_parquet(close_dir / f"{symbol}.parquet", index=False)

    def _closes(self, _symbol: str, _start: str, _end: str, *, allow_oos: bool):
        self.assertTrue(allow_oos)
        return pd.Series([100.0, 100.5], index=[PREV, CUR], dtype=float)

    def _run(self, args: list[str] | None = None) -> int:
        with (
            mock.patch.object(self.cli, "load_closes", side_effect=self._closes),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return self.cli.main(["--out-dir", str(self.out_dir), *(args or [])], root=self.root)

    def test_receipt_is_deterministic_and_loads_with_expected_type(self):
        from research.hashing import canonical_json
        from research.receipts import load_receipt

        self._write_pair()
        self.assertEqual(self._run(), 0)
        first_path = next(self.out_dir.glob("*.json"))
        first = load_receipt(first_path, expected_type="chain_consistency_audit")
        self.assertEqual(self._run(), 0)
        receipts = sorted(self.out_dir.glob("*.json"))
        self.assertEqual(len(receipts), 1)
        second = load_receipt(receipts[0], expected_type="chain_consistency_audit")
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertNotIn("created_at", first)

    def test_missing_column_is_labeled_in_receipt_but_present_column_is_evaluated(self):
        from research.receipts import load_receipt

        cur = _chain().drop(columns="delta")
        self._write_pair(cur=cur)
        self.assertEqual(self._run(), 0)
        receipt = load_receipt(
            next(self.out_dir.glob("*.json")), expected_type="chain_consistency_audit"
        )
        report = receipt["symbols"]["SYN"]["report"]
        self.assertIn("DELTA_JUMP", report["not_evaluable_flags"])

    def test_default_pair_uses_latest_available_sessions_and_reports_gap(self):
        self._write_pair(sessions=("2026-08-19", "2026-08-21"))
        with (
            mock.patch.object(
                self.cli,
                "load_closes",
                return_value=pd.Series([100.0, 100.5], index=["2026-08-19", "2026-08-21"]),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.cli.main(["--out-dir", str(self.out_dir)], root=self.root), 0)
        from research.receipts import load_receipt

        receipt = load_receipt(
            next(self.out_dir.glob("*.json")), expected_type="chain_consistency_audit"
        )
        self.assertEqual(receipt["symbols"]["SYN"]["report"]["status"], "GAP_SESSION")

    def test_one_session_symbol_reports_insufficient_history(self):
        self._write_pair(symbol="ONE", sessions=(CUR,))
        self.assertEqual(self._run(), 0)
        from research.receipts import load_receipt

        receipt = load_receipt(
            next(self.out_dir.glob("*.json")), expected_type="chain_consistency_audit"
        )
        self.assertEqual(receipt["symbols"]["ONE"]["status"], "INSUFFICIENT_HISTORY")

    def test_singleton_receipt_max_as_of_session_covers_available_input(self):
        self._write_pair(symbol="ONE", sessions=(CUR,))
        self.assertEqual(self._run(), 0)
        from research.receipts import load_receipt

        receipt = load_receipt(
            next(self.out_dir.glob("*.json")), expected_type="chain_consistency_audit"
        )
        self.assertEqual(receipt["max_as_of_session"], CUR)

    def test_receipt_binds_the_exact_cached_underlying_close_input(self):
        from data import underlying_closes
        from research.receipts import load_receipt

        self._write_pair()
        close_dir = self.root / ".cache" / "underlying"
        close_dir.mkdir(parents=True, exist_ok=True)
        close_path = close_dir / "SYN.parquet"
        pd.DataFrame({"date": [PREV, CUR], "close": [100.0, 100.5]}).to_parquet(
            close_path, index=False
        )

        with (
            mock.patch.object(underlying_closes, "CACHE_DIR", str(close_dir)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.cli.main(["--out-dir", str(self.out_dir)], root=self.root), 0)

        receipt = load_receipt(
            next(self.out_dir.glob("*.json")), expected_type="chain_consistency_audit"
        )
        close_record = receipt["symbols"]["SYN"]["input_files"]["underlying_close"]
        self.assertEqual(close_record["path"], ".cache/underlying/SYN.parquet")
        self.assertEqual(
            close_record["sha256"], hashlib.sha256(close_path.read_bytes()).hexdigest()
        )

    def test_output_dir_rejects_traversal_outside_permitted_root(self):
        escaped = self.root / ".tmp" / "escape"

        with self.assertRaisesRegex(ValueError, "must be under"):
            self.cli._output_dir(self.root, ".tmp/chain_consistency/../escape")

        self.assertFalse(escaped.exists())

    def test_output_dir_rejects_symlink_parent_escape(self):
        allowed = self.root / ".tmp" / "chain_consistency"
        allowed.mkdir(parents=True)
        escaped = self.root / "escaped"
        escaped.mkdir()
        (allowed / "link").symlink_to(escaped, target_is_directory=True)
        escaped_receipt = escaped / "receipt.json"

        with self.assertRaisesRegex(ValueError, "must be under"):
            self.cli._output_dir(self.root, ".tmp/chain_consistency/link/receipt")

        self.assertFalse(escaped_receipt.exists())

    def test_output_dir_rejects_symlinked_permitted_root_escape(self):
        temporary = self.root / ".tmp"
        temporary.mkdir()
        escaped = self.root / "escaped"
        escaped.mkdir()
        (temporary / "chain_consistency").symlink_to(escaped, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "must be under"):
            self.cli._output_dir(self.root, None)

        self.assertFalse((escaped / "receipt.json").exists())

    def test_exit_zero_when_flags_are_present_and_nonzero_for_unreadable_input(self):
        self._write_pair(sessions=("2026-08-19", "2026-08-21"))
        with (
            mock.patch.object(
                self.cli,
                "load_closes",
                return_value=pd.Series([100.0, 100.5], index=["2026-08-19", "2026-08-21"]),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.cli.main(["--out-dir", str(self.out_dir)], root=self.root), 0)

        broken = self.chain_dir / f"BROKEN_{PREV}.parquet"
        broken.write_bytes(b"not parquet")
        _chain().to_parquet(self.chain_dir / f"BROKEN_{CUR}.parquet", index=False)
        with (
            mock.patch.object(self.cli, "load_closes", side_effect=self._closes),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(self.cli.main(["--out-dir", str(self.out_dir)], root=self.root), 1)

    def test_full_fixture_cli_run_attempts_no_network_or_acquisition(self):
        from data import thetadata_adapter, underlying_closes

        self._write_pair()
        with (
            mock.patch.object(socket, "socket", side_effect=AssertionError("network attempted")),
            mock.patch.object(underlying_closes, "fetch_underlying_eod") as fetch_eod,
            mock.patch.object(underlying_closes, "fetch_underlying_eod_av") as fetch_av,
            mock.patch.object(underlying_closes, "fetch_underlying_eod_yahoo") as fetch_yahoo,
            mock.patch.object(thetadata_adapter, "get_eod_chain") as get_chain,
            mock.patch.object(thetadata_adapter, "blind_cache_chain") as blind_cache,
            mock.patch.object(self.cli, "load_closes", side_effect=self._closes),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(self.cli.main(["--out-dir", str(self.out_dir)], root=self.root), 0)
        for mocked in (fetch_eod, fetch_av, fetch_yahoo, get_chain, blind_cache):
            self.assertEqual(mocked.call_count, 0)

    def test_cli_has_no_reveal_or_production_scoring_import(self):
        source = Path(self.cli.__file__).read_text(encoding="utf-8")

        self.assertNotIn("research.experiments", source)
        self.assertNotIn("data.cache_runner", source)
        self.assertNotIn("options_researcher", source)

    def test_direct_script_invocation_resolves_repository_imports(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "tools" / "chain_consistency_audit.py"), "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
