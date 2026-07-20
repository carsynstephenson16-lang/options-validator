import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research.hashing import sha256_file
from tools import thetadata_cutoff_preflight as preflight

SESSIONS = ("2026-07-01", "2026-07-02")
CUTOFF = date(2026, 7, 3)


def calendar(start: str, end: str) -> list[str]:
    return [day for day in SESSIONS if start <= day <= end]


def clean_identity() -> dict:
    return {"commit": "test", "dirty": False, "dirty_paths": []}


def pass_audit(**kwargs) -> dict:
    sessions = kwargs["sessions"]
    return {
        "verdict": "PASS WITH WARNINGS",
        "counts": {
            "symbols": len(kwargs["symbols"]),
            "sessions": len(sessions),
            "expected_symbol_sessions": len(kwargs["symbols"]) * len(sessions),
            "blocks": 0,
            "warnings": 1,
        },
        "window": {"start": kwargs["start"], "end": kwargs["end"]},
    }


def h6_ready(*args, **kwargs) -> dict:
    return {"ready": True, "symbols": {}}


def pass_data_gate(requested: date, *, scope: dict, **kwargs) -> dict:
    prior = max(day for day in SESSIONS if day < requested.isoformat())
    count = len(scope["symbols"])
    return {
        "evaluation_session": prior,
        "whole_universe_verdict": "GO",
        "go_count": count,
        "no_go_count": 0,
    }


def source_health(as_of: str, *, symbols: list[str]) -> dict:
    return {
        "evaluation_session": as_of,
        "healthy_count": len(symbols) - 1,
        "unhealthy_count": 1,
        "unhealthy_symbols": [symbols[0]],
        "activation_ready": False,
    }


def blocked_data_gate(requested: date, **kwargs) -> dict:
    result = pass_data_gate(requested, **kwargs)
    result.update(
        {"whole_universe_verdict": "NO_GO", "go_count": 11, "no_go_count": 1}
    )
    return result


class CutoffPreflightTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.chains = self.root / "chains"
        self.closes = self.root / "closes"
        self.chains.mkdir()
        self.closes.mkdir()
        self.frozen_symbols = list(preflight.FROZEN_CUTOFF_SCOPE)
        self.current_symbols = list(preflight.scope_identity()["symbols"])
        self.symbols = self.frozen_symbols
        self.facts: dict[tuple[str, str], dict] = {}

    def seed(self, sessions: tuple[str, ...], *, symbols: list[str] | None = None) -> None:
        symbols = self.symbols if symbols is None else symbols
        for session in sessions:
            for symbol in symbols:
                path = self.chains / f"{symbol}_{session}.parquet"
                path.write_bytes(f"{symbol}-{session}".encode())
                self.facts[(symbol, session)] = {
                    "fetched": datetime(2026, 7, 2, tzinfo=timezone.utc),
                    "sha256": sha256_file(path),
                }

    def preflight_report(self, today: date, *, scope_mode: str = "frozen", **overrides) -> dict:
        kwargs = {
            "cutoff": CUTOFF,
            "today": today,
            "chain_dir": self.chains,
            "close_dir": self.closes,
            "facts": self.facts,
            "trading_days_fn": calendar,
            "audit_fn": pass_audit,
            "audit_identity_fn": clean_identity,
            "data_gate_fn": pass_data_gate,
            "source_health_fn": source_health,
            "source_identity_fn": clean_identity,
            "ledger_verify_fn": lambda **_: SimpleNamespace(
                valid=True, empty=True, count=0, head=None
            ),
            "h6_readiness_fn": h6_ready,
            "scope_mode": scope_mode,
        }
        kwargs.update(overrides)
        return preflight.build_preflight(**kwargs)

    def test_before_cutoff_waits_and_derives_terminal_session(self):
        self.seed((SESSIONS[0],))
        report = self.preflight_report(date(2026, 7, 2))
        self.assertEqual(report["terminal_session"], "2026-07-02")
        self.assertEqual(report["status"], "WAITING_FOR_CUTOFF")
        self.assertEqual(report["scope"], self.frozen_symbols)
        self.assertNotIn("scope_identity", report)
        self.assertNotIn("historical_scope", report)
        self.assertFalse(report["paid_pull_authorized"])
        self.assertEqual(report["cache"]["future_sessions"], ["2026-07-02"])

    def test_cutoff_day_requires_explicit_pull_when_terminal_data_missing(self):
        self.seed((SESSIONS[0],))
        report = self.preflight_report(CUTOFF)
        self.assertEqual(report["status"], "OWNER_AUTHORIZED_PULL_REQUIRED")
        self.assertEqual(
            report["cache"]["actionable_missing_by_session"],
            {"2026-07-02": self.frozen_symbols},
        )

    def test_complete_terminal_cache_is_ready_for_receipts(self):
        self.seed(SESSIONS)
        report = self.preflight_report(CUTOFF)
        self.assertEqual(report["status"], "READY_FOR_RECEIPTS")
        self.assertTrue(report["cache"]["terminal_complete"])
        self.assertEqual(report["current_exit_audit"]["verdict"], "PASS WITH WARNINGS")
        self.assertFalse(report["current_source_health"]["activation_ready"])
        self.assertIn("2026-07-02", report["commands"]["write_h6_receipt"])

    def test_present_chain_provenance_mismatch_blocks(self):
        self.seed(SESSIONS)
        self.facts[(self.symbols[0], SESSIONS[0])]["sha256"] = "0" * 64
        report = self.preflight_report(CUTOFF)
        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(len(report["provenance"]["mismatches"]), 1)

    def test_nonempty_real_ledger_blocks(self):
        self.seed(SESSIONS)
        report = self.preflight_report(
            CUTOFF,
            ledger_verify_fn=lambda **_: SimpleNamespace(
                valid=True, empty=False, count=1, head="a" * 64
            ),
        )
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("real H7 forward ledger", " ".join(report["blockers"]))

    def test_current_or_future_session_file_blocks_as_not_final(self):
        self.seed(SESSIONS)
        report = self.preflight_report(date(2026, 7, 2))
        self.assertEqual(report["status"], "BLOCK")
        self.assertEqual(len(report["provenance"]["premature_present"]), 12)

    def test_current_data_gate_must_cover_the_selected_scope(self):
        self.seed(SESSIONS)
        report = self.preflight_report(CUTOFF, data_gate_fn=blocked_data_gate)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("Stage-2 data gate", " ".join(report["blockers"]))

    def test_current_scope_is_explicit_and_versioned(self):
        self.seed(SESSIONS, symbols=self.current_symbols)
        report = self.preflight_report(CUTOFF, scope_mode="current")
        self.assertEqual(report["status"], "READY_FOR_RECEIPTS")
        self.assertEqual(report["scope"], self.current_symbols)
        self.assertEqual(report["scope_identity"], preflight.scope_identity())
        self.assertEqual(report["historical_scope"], self.frozen_symbols)

    def test_cli_defaults_to_frozen_and_accepts_current_scope(self):
        report = {"status": "WAITING_FOR_CUTOFF"}
        for arguments, expected_mode in (
            (["--today", "2026-07-03", "--json"], "frozen"),
            (["--today", "2026-07-03", "--scope", "current", "--json"], "current"),
        ):
            with patch.object(preflight, "build_preflight", return_value=report) as build:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(preflight.main(arguments), 0)
            self.assertEqual(build.call_args.kwargs["scope_mode"], expected_mode)

    def test_frozen_scope_stays_exact_and_current_scope_is_derived(self):
        self.assertEqual(len(preflight.HISTORICAL_CUTOFF_SCOPE), 12)
        self.assertEqual(
            len(preflight.HISTORICAL_CUTOFF_SCOPE),
            len(set(preflight.HISTORICAL_CUTOFF_SCOPE))
        )
        self.assertNotIn("IREN", preflight.FROZEN_CUTOFF_SCOPE)
        self.assertEqual(
            preflight.FROZEN_CUTOFF_SCOPE,
            (
                "CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD", "AVGO",
                "VST", "CEG", "MSFT", "AMZN",
            ),
        )
        self.assertFalse(hasattr(preflight, "CURRENT_CUTOFF_SCOPE"))
        self.assertEqual(len(preflight.scope_identity()["symbols"]), 15)
        self.assertIn("IREN", preflight.scope_identity()["symbols"])


if __name__ == "__main__":
    unittest.main()
