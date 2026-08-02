"""Executable options-flow quality-audit tests."""

import json
import unittest
from pathlib import Path

import pandas as pd

from data.options_flow.audit import audit_options_data, render_audit
from data.options_flow.normalize import normalize_trade_quotes

FIXTURES = Path(__file__).parent / "fixtures" / "options_flow"


class FlowAuditTests(unittest.TestCase):
    def _trades(self) -> pd.DataFrame:
        raw = pd.DataFrame(
            json.loads(line) for line in (FIXTURES / "trade_quote.jsonl").read_text().splitlines()
        )
        return normalize_trade_quotes(
            raw,
            symbol="MSFT",
            session="2025-01-02",
            acquired_at_utc="2025-01-03T00:00:00Z",
            source_version="fixture",
        )

    def test_clean_fixture_passes_and_prints_required_sections(self):
        result = audit_options_data(
            self._trades(),
            expected_sessions=["2025-01-02"],
        )
        self.assertEqual(result.verdict, "PASS")
        rendered = render_audit(result)
        self.assertIn("Data audited:", rendered)
        self.assertIn("Verdict: PASS", rendered)
        self.assertIn("Ledger note:", rendered)

    def test_future_or_stale_quote_blocks(self):
        changed = self._trades()
        changed.loc[0, "quote_timestamp"] = changed.loc[0, "trade_timestamp"] + pd.Timedelta(
            seconds=1
        )
        result = audit_options_data(changed)
        self.assertEqual(result.verdict, "BLOCK")
        self.assertTrue(any(finding.check == 9 for finding in result.findings))

    def test_dead_quote_blocks_tradeable_row_with_explicit_finding(self):
        changed = self._trades()
        changed.loc[0, ["bid", "ask", "trade_price"]] = 0.0

        result = audit_options_data(changed)

        self.assertEqual(result.verdict, "BLOCK")
        self.assertTrue(
            any(
                finding.check == 15
                and finding.severity == "BLOCK"
                and "dead market" in finding.message
                for finding in result.findings
            )
        )
