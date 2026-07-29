"""Offline tests for flow retrieval seams, normalization, and immutable storage."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import pandas as pd

from data.options_flow.adapter import fetch_session
from data.options_flow.normalize import normalize_open_interest, normalize_trade_quotes
from data.options_flow.raw_store import RawFlowStore
from research.receipts import load_receipt
from tools import options_flow, options_flow_analogs

FIXTURES = Path(__file__).parent / "fixtures" / "options_flow"


def _fixture(name: str) -> pd.DataFrame:
    return pd.DataFrame(json.loads(line) for line in (FIXTURES / name).read_text().splitlines())


class FakeFlowClient:
    def __init__(self):
        self.trade_calls = []
        self.oi_calls = []

    def option_history_trade_quote(self, **kwargs):
        self.trade_calls.append(kwargs)
        return _fixture("trade_quote.jsonl")

    def option_history_open_interest(self, **kwargs):
        self.oi_calls.append(kwargs)
        return _fixture("open_interest.jsonl")


class AdapterTests(unittest.TestCase):
    def test_fetch_uses_strict_prior_quote_and_never_default_client(self):
        client = FakeFlowClient()
        with mock.patch("data.options_flow.adapter.default_client") as default:
            result = fetch_session(
                "msft", "2025-01-02", client=client, acquired_at_utc="2025-01-03T00:00:00+00:00"
            )
        default.assert_not_called()
        self.assertEqual(result.symbol, "MSFT")
        self.assertEqual(client.trade_calls[0]["expiration"], "*")
        self.assertTrue(client.trade_calls[0]["exclusive"])
        self.assertEqual(client.trade_calls[0]["start_time"], "09:30:00")
        self.assertEqual(client.oi_calls[0]["date"].isoformat(), "2025-01-02")

    def test_crossed_quote_fails_closed(self):
        raw = _fixture("trade_quote.jsonl")
        raw.loc[0, "ask"] = 8.0
        with self.assertRaisesRegex(ValueError, "crossed quote"):
            normalize_trade_quotes(
                raw,
                symbol="MSFT",
                session="2025-01-02",
                acquired_at_utc="2025-01-03T00:00:00+00:00",
                source_version="fixture",
            )

    def test_naive_raw_timestamps_require_entitlement_probe_gate(self):
        raw = _fixture("trade_quote.jsonl")
        raw.loc[0, "trade_timestamp"] = "2025-01-02T13:30:00.100"
        with self.assertRaisesRegex(ValueError, "entitlement-probe gate"):
            normalize_trade_quotes(
                raw,
                symbol="MSFT",
                session="2025-01-02",
                acquired_at_utc="2025-01-03T00:00:00+00:00",
                source_version="fixture",
            )
        oi = _fixture("open_interest.jsonl")
        oi.loc[0, "timestamp"] = "2025-01-02T11:30:00.000"
        with self.assertRaisesRegex(ValueError, "entitlement-probe gate"):
            normalize_open_interest(
                oi,
                symbol="MSFT",
                acquired_at_utc="2025-01-03T00:00:00+00:00",
                source_version="fixture",
            )

    def test_capture_is_idempotent_and_receipt_bound(self):
        client = FakeFlowClient()
        fetch = fetch_session(
            "MSFT", "2025-01-02", client=client, acquired_at_utc="2025-01-03T00:00:00+00:00"
        )
        with tempfile.TemporaryDirectory() as temp:
            store = RawFlowStore(temp)
            first = store.write_fetch(fetch)
            second = store.write_fetch(fetch)
            self.assertEqual(first, second)
            receipt = load_receipt(Path(first["receipt"]), expected_type="options_flow_capture")
            self.assertEqual(receipt["symbol"], "MSFT")
            self.assertEqual(
                pd.read_parquet(
                    first["manifest"].replace("manifest.json", "trade_quote.parquet")
                ).shape[0],
                4,
            )

    def test_mutated_replay_is_refused(self):
        client = FakeFlowClient()
        fetch = fetch_session(
            "MSFT", "2025-01-02", client=client, acquired_at_utc="2025-01-03T00:00:00+00:00"
        )
        with tempfile.TemporaryDirectory() as temp:
            store = RawFlowStore(temp)
            store.write_fetch(fetch)
            changed = _fixture("trade_quote.jsonl")
            changed.loc[0, "price"] = 11.0
            changed_fetch = fetch.__class__(
                symbol=fetch.symbol,
                session=fetch.session,
                trade_quote=changed,
                open_interest=fetch.open_interest,
                acquired_at_utc=fetch.acquired_at_utc,
            )
            with self.assertRaises(FileExistsError):
                store.write_fetch(changed_fetch)

    def test_cli_dry_run_does_not_fetch(self):
        args = Namespace(
            dry_run=True,
            execute=False,
            symbols=["MSFT", "CEG", "VST"],
            max_symbols=2,
            start_date="2025-01-02",
            end_date="2025-01-06",
            output=Path("/tmp/options-flow-test-output"),
        )
        with (
            mock.patch(
                "tools.options_flow._trading_days",
                return_value=["2025-01-02", "2025-01-03", "2025-01-06"],
            ),
            mock.patch("tools.options_flow.fetch_session") as fetch,
        ):
            self.assertEqual(options_flow.run(args), 0)
        fetch.assert_not_called()

    def test_direct_script_help_resolves_repository_imports(self):
        command = [
            sys.executable,
            str(Path(__file__).parents[1] / "tools" / "options_flow.py"),
            "--help",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--execute", result.stdout)

    def test_offline_analog_cli_help_resolves_repository_imports(self):
        command = [
            sys.executable,
            str(Path(__file__).parents[1] / "tools" / "options_flow_analogs.py"),
            "--help",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--query-session", result.stdout)

    def test_offline_analog_cli_rejects_out_of_range_base_frequency(self):
        parser = options_flow_analogs.build_parser()
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            parser.parse_args(
                [
                    "panel.csv",
                    "--query-session",
                    "2025-01-02",
                    "--symbol",
                    "MSFT",
                    "--matched-base-positive-frequency",
                    "1.01",
                ]
            )
