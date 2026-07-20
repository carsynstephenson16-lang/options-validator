"""Frozen H7 cohort loader tests.

The live window's included names are committed in the immutable seq-0
``window_registration`` event.  Runtime code must read that event rather than
falling back to the mutable 15-name operational scope.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from data.cache_runner import session_close_utc
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_window_registration as registration
from options_researcher.h7_cohort import (
    CohortUnavailableError,
    load_registered_cohort,
)
from options_researcher.h7_scope import scope_identity

INCLUDED = ("AMD", "AMZN", "CEG", "ET", "MSFT", "NOW", "PLTR", "TEM", "VST")


def _owner_inputs() -> dict:
    return {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "synthetic cohort fixture",
        "WINDOW_START_DECISION_SESSION": "2026-08-03",
        "WINDOW_DECISION_SESSION_COUNT": 70,
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS sessions from start",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "synthetic fixture",
    }


def _evidence() -> dict:
    return {
        "review_evidence": "synthetic fixture",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:fixture",
        "data_gate_evidence_id": "dg:fixture",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }


def _register_fixture_window(base: Path) -> dict[str, str]:
    full_scope = scope_identity()
    excluded = tuple(symbol for symbol in full_scope["symbols"]
                     if symbol not in INCLUDED)
    excluded_reasons = {symbol: "EARNINGS-UNKNOWN" for symbol in excluded}
    manifest = {
        "scope_id": full_scope["scope_id"],
        "scope_hash": full_scope["scope_hash"],
        "included": list(INCLUDED),
        "excluded": [{"symbol": symbol, "reason": excluded_reasons[symbol]}
                     for symbol in excluded],
        "trim_rule": "source_health_ready_at_pinned_session",
    }
    result = registration.register_window(
        owner=_owner_inputs(), evidence=_evidence(), base_dir=base,
        universe_manifest=manifest)
    assert result.seq == 0
    return excluded_reasons


class CohortLoaderTests(unittest.TestCase):
    def test_loads_frozen_included_and_excluded_from_seq0(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "forward"
            expected_excluded = _register_fixture_window(base)

            cohort = load_registered_cohort(base_dir=base)

        self.assertEqual(cohort.included, INCLUDED)
        self.assertEqual(cohort.excluded, expected_excluded)
        self.assertTrue(cohort.event_id)

    def test_empty_store_raises_typed_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CohortUnavailableError):
                load_registered_cohort(base_dir=Path(tmp) / "empty")

    def test_first_event_not_registration_raises_typed_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "forward"
            ledger.append_event({
                "schema_version": 1,
                "event_id": "source-health:fixture",
                "event_type": "source_health",
                "occurred_at_utc": session_close_utc("2026-07-10").isoformat(),
                "evaluation_session": "2026-07-10",
                "symbol": None,
                "lane": None,
                "causes": [],
                "payload": {},
            }, base_dir=base, expected_head=None)

            with self.assertRaises(CohortUnavailableError):
                load_registered_cohort(base_dir=base)
