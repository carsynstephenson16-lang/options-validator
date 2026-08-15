"""Contract tests for the read-only per-symbol hypothesis evidence gatherer."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import config
from options_researcher.h7_cohort import (
    CohortUnavailableError,
    RegisteredCohort,
)
from options_researcher.h7_scope import scope_identity, watch_universe
from options_researcher.hypothesis_evidence import (
    EvidenceRow,
    gather_hypothesis_evidence,
)

EVALUATION = "2026-07-24"
RUN_DATE = "2026-07-27"
_FORBIDDEN_WATCHER_IMPORT_SUFFIXES = (
    "entry_watch",
    "h6_watch",
    "h7_watch",
    "h8_watch",
    "h10_watch",
)


def _has_prohibited_watcher_import(source: str) -> bool:
    """Reject direct, from-module, and package-alias watcher imports."""
    tree = ast.parse(source)
    candidates = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module is not None:
            candidates.add(node.module)
        for alias in node.names:
            candidates.add(
                f"{node.module}.{alias.name}"
                if node.module is not None
                else alias.name
            )
    return any(
        name.endswith(_FORBIDDEN_WATCHER_IMPORT_SUFFIXES)
        for name in candidates
    )


def _cohort(_base_dir: Path) -> RegisteredCohort:
    return RegisteredCohort(
        included=("AMD", "AMZN", "PLTR"),
        excluded={"AVGO": "EARNINGS-UNKNOWN"},
        event_id="wr:fixture",
        decision_window_start="2026-07-20",
        decision_window_end="2026-10-26",
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _ritual(*, as_of: str = EVALUATION, run_date: str = RUN_DATE) -> dict:
    return {
        "as_of": as_of,
        "run_date": run_date,
        "hypotheses": {
            "H5": {
                "status": "NO_SIGNAL",
                "detail": "no signal",
                "evidence": f"reports/h5/entry_watch_{as_of}.txt",
            },
            "H6": {
                "status": "CAPTURED",
                "detail": "1 signal(s) captured",
                "evidence": f"reports/h6_forward/{as_of}.json",
            },
            "H7": {
                "status": "REFUSED",
                "detail": "preflight exit 1",
                "evidence": (
                    "reports/h7_receipts/h7-forward-15-v1/"
                    f"preflight/{as_of}.txt"
                ),
            },
            "H8": {
                "status": "CAPTURED",
                "detail": "1 signal(s) captured",
                "evidence": f"reports/h8_forward/{as_of}.json",
            },
            "H10": {
                "status": "NO_SIGNAL",
                "detail": "no signal",
                "evidence": (
                    f"reports/h10/receipts/h10_watch_{run_date}.json"
                ),
            },
        },
    }


def _h6(
    symbol: str = "AMZN",
    *,
    status: str = "ELIGIBLE",
    reasons: tuple[str, ...] | None = None,
) -> dict:
    raw_reasons = (
        tuple() if status == "ELIGIBLE" else ("<raw H6 reason>",)
    ) if reasons is None else reasons
    return {
        "schema": "h6_exact_session_watch_receipt_v1",
        "snapshot": {
            "evaluation_session": EVALUATION,
            "mode": "FORWARD_PAPER_ONLY",
            "live_orders": False,
            "errors": [],
            "entries": [
                {
                    "symbol": symbol,
                    "evaluation_session": EVALUATION,
                    "status": status,
                    "timing": {
                        "state": "POST_REPORT",
                        "reason": "inside first five post-report sessions",
                    },
                    "reasons": list(raw_reasons),
                }
            ],
        },
    }


def _h8(
    symbol: str = "AMZN",
    *,
    status: str = "ENTRY-OK",
    window_state: str = "IN_WINDOW",
    reasons: tuple[str, ...] | None = None,
) -> dict:
    raw_reasons = (
        ("blocked by registered gate",)
        if status == "BLOCKED"
        else tuple()
    ) if reasons is None else reasons
    return {
        "evaluation_session": EVALUATION,
        "mode": "FORWARD_PAPER_ONLY",
        "orders_enabled": False,
        "entries": [
            {
                "symbol": symbol,
                "evaluation_session": EVALUATION,
                "status": status,
                "window": {
                    "state": window_state,
                    "reason": "inside registered entry window",
                },
                "reasons": list(raw_reasons),
            }
        ],
        "exits": [],
        "errors": [],
    }


def _h10(
    *,
    evaluation_session: str = EVALUATION,
    run_date: str = RUN_DATE,
    symbol: str = "PLTR",
) -> dict:
    return {
        "as_of": run_date,
        "evaluation_session": evaluation_session,
        "book_action_required": True,
        "evaluations": [
            {
                "symbol": symbol,
                "status": "FIRED",
                "reason": None,
                "signals": {"H10a": True, "H10b": False},
                "book_action_required": True,
            }
        ],
    }


def _h7_source(symbol: str = "AMD") -> dict:
    return {
        "receipt_schema": "h7-receipt/v1",
        "receipt_type": "source_health",
        "receipt_hash": "a" * 64,
        "evaluation_session": EVALUATION,
        "scope": scope_identity(),
        "symbols": {
            symbol: {
                "symbol": symbol,
                "gate": "BANNED",
                "gate_reason": "<earnings window>",
            }
        },
    }


def _h7_watcher(symbol: str = "AMD") -> dict:
    return {
        "receipt_schema": "h7-receipt/v1",
        "receipt_type": "watcher_decision",
        "evaluation_session": EVALUATION,
        "requested_run_date": RUN_DATE,
        "source_health_receipt_hash": "a" * 64,
        "scope": scope_identity(),
        "errors": [],
        "rows": [
            {
                "symbol": symbol,
                "lane": "lane_a",
                "state": "EARNINGS-BAN",
            },
            {
                "symbol": symbol,
                "lane": "lane_b",
                "state": "WATCH-ONLY",
            },
            {
                "symbol": symbol,
                "lane": "lane_c",
                "state": "EXCLUDED",
            },
        ],
    }


def _intraday(
    symbols: tuple[str, ...],
    *,
    tag: str = "preclose",
    day: str = EVALUATION,
) -> dict:
    return {
        "receipt_kind": "intraday_capture/v1",
        "session_tag": tag,
        "scheduled_et": config.INTRADAY_CAPTURE_TIMES[tag],
        "captured_at_et": f"{day}T15:45:00-04:00",
        "universe": list(watch_universe()),
        "names": {
            symbol: {
                "symbol": symbol,
                "status": "ok",
                "iv_label": "<descriptive only>",
            }
            for symbol in symbols
        },
    }


def _row(evidence: dict[str, object], symbol: str, family: str) -> EvidenceRow:
    symbol_evidence = evidence[symbol]
    assert hasattr(symbol_evidence, "hypotheses")
    return next(
        row
        for row in symbol_evidence.hypotheses
        if row.family == family
    )


class HypothesisEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.scope_id = str(scope_identity()["scope_id"])

    def _write_complete_fixture(self) -> None:
        _write_json(
            self.root
            / "reports"
            / "ritual"
            / f"capture_receipt_{EVALUATION}.json",
            _ritual(),
        )
        h5 = (
            self.root
            / "reports"
            / "h5"
            / f"entry_watch_{EVALUATION}.txt"
        )
        h5.parent.mkdir(parents=True, exist_ok=True)
        h5.write_text(
            "H5 LEAPS ENTRY TRIGGER WATCH\n"
            f"AMZN: WAIT  close $230 (as of {EVALUATION}) "
            "-- waiting on: <trigger>\n",
            encoding="utf-8",
        )
        _write_json(
            self.root / "reports" / "h6_forward" / f"{EVALUATION}.json",
            _h6(status="BLOCKED"),
        )
        _write_json(
            self.root / "reports" / "h8_forward" / f"{EVALUATION}.json",
            _h8(),
        )
        _write_json(
            self.root
            / "reports"
            / "h10"
            / "receipts"
            / f"h10_watch_{RUN_DATE}.json",
            _h10(),
        )
        _write_json(
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "source_health"
            / f"{EVALUATION}.json",
            _h7_source(),
        )
        _write_json(
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "watcher"
            / f"{EVALUATION}.json",
            _h7_watcher(),
        )
        _write_json(
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "preclose.json",
            _intraday(tuple(watch_universe())),
        )

    def test_all_receipt_schemas_keep_ritual_and_raw_states_separate(self):
        self._write_complete_fixture()

        evidence = gather_hypothesis_evidence(
            ("AMZN", "AMD", "PLTR"),
            root=self.root,
            cohort_loader=_cohort,
        )

        self.assertEqual(
            tuple(row.family for row in evidence["AMZN"].hypotheses),
            ("H5", "H6", "H7", "H8", "H10a", "H10b"),
        )

        h5 = _row(evidence, "AMZN", "H5")
        self.assertEqual(h5.family_state, "NO_SIGNAL")
        self.assertEqual(h5.symbol_states[0].state, "WAIT")
        self.assertIn("<trigger>", h5.detail)
        self.assertEqual(h5.evaluation_session, EVALUATION)
        self.assertEqual(h5.run_date, RUN_DATE)

        h6 = _row(evidence, "AMZN", "H6")
        self.assertEqual(h6.family_state, "CAPTURED")
        self.assertEqual(
            [(state.label, state.state) for state in h6.symbol_states],
            [
                ("entry", "BLOCKED"),
                ("timing", "POST_REPORT"),
            ],
        )
        self.assertIn("<raw H6 reason>", h6.detail)

        h7 = _row(evidence, "AMD", "H7")
        self.assertEqual(h7.membership, "H7 registered cohort")
        self.assertEqual(h7.family_state, "REFUSED")
        self.assertEqual(
            [(state.label, state.state) for state in h7.symbol_states],
            [
                ("source", "BANNED"),
                ("lane_a", "EARNINGS-BAN"),
                ("lane_b", "WATCH-ONLY"),
                ("lane_c", "EXCLUDED"),
            ],
        )
        self.assertEqual(
            [source.kind for source in h7.sources],
            ["source_health", "watcher", "ritual"],
        )

        h8 = _row(evidence, "AMZN", "H8")
        self.assertEqual(h8.family_state, "CAPTURED")
        self.assertEqual(h8.symbol_states[0].state, "ENTRY-OK")
        self.assertEqual(h8.symbol_states[1].state, "IN_WINDOW")

        h10a = _row(evidence, "PLTR", "H10a")
        h10b = _row(evidence, "PLTR", "H10b")
        self.assertEqual(h10a.family_state, "NO_SIGNAL")
        self.assertEqual(
            [(state.label, state.state) for state in h10a.symbol_states],
            [("watcher", "FIRED"), ("signal", "true")],
        )
        self.assertEqual(
            [(state.label, state.state) for state in h10b.symbol_states],
            [("watcher", "FIRED"), ("signal", "false")],
        )

        intraday = evidence["PLTR"].intraday
        self.assertTrue(intraday.descriptive_only)
        self.assertFalse(intraday.expected_daily)
        self.assertEqual(intraday.family_state, "ok")
        self.assertEqual(intraday.symbol_states[0].state, "ok")
        self.assertIn("<descriptive only>", intraday.detail)

    def test_untracked_has_no_borrowed_paths_and_tracked_omission_is_unknown(
        self,
    ):
        _write_json(
            self.root / "reports" / "h6_forward" / f"{EVALUATION}.json",
            _h6(symbol="PLTR"),
        )
        _write_json(
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "preclose.json",
            _intraday(("AMZN",)),
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN", "NBIS", "ZZZZ"),
            root=self.root,
            cohort_loader=_cohort,
        )

        tracked = _row(evidence, "AMZN", "H6")
        self.assertEqual(tracked.symbol_states[0].state, "UNKNOWN")
        self.assertEqual(
            tracked.sources[0].path,
            f"reports/h6_forward/{EVALUATION}.json",
        )

        for symbol in ("NBIS", "ZZZZ"):
            for row in evidence[symbol].hypotheses:
                self.assertEqual(row.membership, "not tracked")
                self.assertEqual(row.family_state, "NOT TRACKED")
                self.assertEqual(row.sources, ())
                self.assertIsNone(row.evaluation_session)
                self.assertIsNone(row.run_date)
            self.assertEqual(
                evidence[symbol].intraday.family_state, "NOT TRACKED"
            )
            self.assertEqual(evidence[symbol].intraday.sources, ())

    def test_malformed_newest_receipt_is_unknown_without_older_fallback(self):
        _write_json(
            self.root / "reports" / "h6_forward" / "2026-07-23.json",
            {
                **_h6(),
                "snapshot": {
                    **_h6()["snapshot"],
                    "evaluation_session": "2026-07-23",
                },
            },
        )
        newest = (
            self.root / "reports" / "h6_forward" / f"{EVALUATION}.json"
        )
        newest.write_text("{not-json", encoding="utf-8")

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = _row(evidence, "AMZN", "H6")
        self.assertEqual(row.symbol_states[0].state, "UNKNOWN")
        self.assertEqual(row.evaluation_session, EVALUATION)
        self.assertEqual(
            row.sources[0].path,
            f"reports/h6_forward/{EVALUATION}.json",
        )
        self.assertNotIn("2026-07-23", row.sources[0].path)
        from options_researcher.hypothesis_evidence import (
            summarize_hypothesis_evidence,
        )
        h6_summary = summarize_hypothesis_evidence(evidence)[1]
        self.assertEqual(h6_summary.ritual_state, "UNKNOWN")
        self.assertEqual(
            [(count.state, count.count) for count in h6_summary.raw_state_counts],
            [("UNKNOWN", 1)],
        )

    def test_h7_refuses_cross_session_or_hash_mismatched_receipt_sets(self):
        self._write_complete_fixture()
        source_path = (
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "source_health"
            / f"{EVALUATION}.json"
        )
        watcher_path = (
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "watcher"
            / f"{EVALUATION}.json"
        )
        watcher = json.loads(watcher_path.read_text(encoding="utf-8"))
        watcher["source_health_receipt_hash"] = "b" * 64
        _write_json(watcher_path, watcher)

        evidence = gather_hypothesis_evidence(
            ("AMD",),
            root=self.root,
            cohort_loader=_cohort,
        )
        row = _row(evidence, "AMD", "H7")
        self.assertEqual(
            [state.state for state in row.symbol_states],
            ["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"],
        )
        self.assertIn("malformed newest H7 receipt set", row.detail)

        newer_date = "2026-07-25"
        newer_source = json.loads(source_path.read_text(encoding="utf-8"))
        newer_source["evaluation_session"] = newer_date
        newer_source["receipt_hash"] = "c" * 64
        _write_json(
            source_path.with_name(f"{newer_date}.json"),
            newer_source,
        )
        watcher["source_health_receipt_hash"] = "a" * 64
        _write_json(watcher_path, watcher)

        evidence = gather_hypothesis_evidence(
            ("AMD",),
            root=self.root,
            cohort_loader=_cohort,
        )
        row = _row(evidence, "AMD", "H7")
        self.assertEqual(
            [state.state for state in row.symbol_states],
            ["UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN"],
        )
        self.assertEqual(
            [source.date for source in row.sources[:2]],
            [newer_date, EVALUATION],
        )

    def test_invalid_real_schema_vocabularies_fail_closed(self):
        self._write_complete_fixture()
        ritual_path = (
            self.root
            / "reports"
            / "ritual"
            / f"capture_receipt_{EVALUATION}.json"
        )
        ritual = json.loads(ritual_path.read_text(encoding="utf-8"))
        for result in ritual["hypotheses"].values():
            result["status"] = "BOGUS"
        _write_json(ritual_path, ritual)

        _write_json(
            self.root / "reports" / "h6_forward" / f"{EVALUATION}.json",
            _h6(status="BOGUS"),
        )
        _write_json(
            self.root / "reports" / "h8_forward" / f"{EVALUATION}.json",
            _h8(status="BOGUS"),
        )
        h10 = _h10()
        h10["evaluations"][0]["status"] = "BOGUS"
        _write_json(
            self.root
            / "reports"
            / "h10"
            / "receipts"
            / f"h10_watch_{RUN_DATE}.json",
            h10,
        )
        source = _h7_source()
        source["symbols"]["AMD"]["gate"] = "BOGUS"
        _write_json(
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "source_health"
            / f"{EVALUATION}.json",
            source,
        )
        watcher = _h7_watcher()
        watcher["rows"][0]["state"] = "BOGUS"
        _write_json(
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "watcher"
            / f"{EVALUATION}.json",
            watcher,
        )
        intraday = _intraday(tuple(watch_universe()))
        intraday["names"]["PLTR"]["status"] = "BOGUS"
        _write_json(
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "preclose.json",
            intraday,
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN", "AMD", "PLTR"),
            root=self.root,
            cohort_loader=_cohort,
        )

        for symbol, family in (
            ("AMZN", "H6"),
            ("AMZN", "H8"),
            ("AMD", "H7"),
            ("PLTR", "H10a"),
            ("PLTR", "H10b"),
        ):
            with self.subTest(symbol=symbol, family=family):
                row = _row(evidence, symbol, family)
                self.assertEqual(row.family_state, "UNKNOWN")
                self.assertTrue(
                    all(state.state == "UNKNOWN" for state in row.symbol_states)
                )
        self.assertEqual(evidence["PLTR"].intraday.family_state, "UNKNOWN")
        self.assertEqual(
            evidence["PLTR"].intraday.symbol_states[0].state,
            "UNKNOWN",
        )

    def test_h6_h8_status_reason_invariants_fail_closed(self):
        h6_path = (
            self.root / "reports" / "h6_forward" / f"{EVALUATION}.json"
        )
        h8_path = (
            self.root / "reports" / "h8_forward" / f"{EVALUATION}.json"
        )
        _write_json(
            h6_path,
            _h6(status="ELIGIBLE", reasons=("impossible reason",)),
        )
        _write_json(
            h8_path,
            _h8(status="ENTRY-OK", reasons=("impossible reason",)),
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )
        for family in ("H6", "H8"):
            row = _row(evidence, "AMZN", family)
            self.assertEqual(row.symbol_states[0].state, "UNKNOWN")

    def test_receipt_identity_and_safety_fields_fail_closed(self):
        self._write_complete_fixture()
        h6_path = (
            self.root / "reports" / "h6_forward" / f"{EVALUATION}.json"
        )
        h6 = json.loads(h6_path.read_text(encoding="utf-8"))
        h6["snapshot"]["live_orders"] = True
        _write_json(h6_path, h6)

        h8_path = (
            self.root / "reports" / "h8_forward" / f"{EVALUATION}.json"
        )
        h8 = json.loads(h8_path.read_text(encoding="utf-8"))
        h8["entries"][0]["evaluation_session"] = "2026-07-23"
        _write_json(h8_path, h8)

        h10_path = (
            self.root
            / "reports"
            / "h10"
            / "receipts"
            / f"h10_watch_{RUN_DATE}.json"
        )
        h10 = json.loads(h10_path.read_text(encoding="utf-8"))
        h10["evaluations"][0]["book_action_required"] = False
        _write_json(h10_path, h10)

        source_path = (
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "source_health"
            / f"{EVALUATION}.json"
        )
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source["symbols"]["AMD"]["symbol"] = "PLTR"
        _write_json(source_path, source)

        evidence = gather_hypothesis_evidence(
            ("AMZN", "AMD", "PLTR"),
            root=self.root,
            cohort_loader=_cohort,
        )

        for symbol, family in (
            ("AMZN", "H6"),
            ("AMZN", "H8"),
            ("AMD", "H7"),
            ("PLTR", "H10a"),
            ("PLTR", "H10b"),
        ):
            with self.subTest(symbol=symbol, family=family):
                row = _row(evidence, symbol, family)
                self.assertTrue(
                    all(state.state == "UNKNOWN" for state in row.symbol_states)
                )

        for invalid_top_level in (False, 1):
            h10 = _h10()
            h10["book_action_required"] = invalid_top_level
            _write_json(h10_path, h10)
            evidence = gather_hypothesis_evidence(
                ("PLTR",),
                root=self.root,
                cohort_loader=_cohort,
            )
            for family in ("H10a", "H10b"):
                row = _row(evidence, "PLTR", family)
                self.assertEqual(row.symbol_states[0].state, "UNKNOWN")

        _write_json(h6_path, _h6(status="BLOCKED", reasons=()))
        _write_json(h8_path, _h8(status="BLOCKED", reasons=()))
        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )
        for family in ("H6", "H8"):
            row = _row(evidence, "AMZN", family)
            self.assertEqual(row.symbol_states[0].state, "UNKNOWN")

    def test_h10_newest_run_date_uses_its_semantic_evaluation_session(self):
        _write_json(
            self.root
            / "reports"
            / "h10"
            / "receipts"
            / "h10_watch_2026-07-24.json",
            _h10(
                evaluation_session="2026-07-23",
                run_date="2026-07-24",
            ),
        )
        _write_json(
            self.root
            / "reports"
            / "h10"
            / "receipts"
            / f"h10_watch_{RUN_DATE}.json",
            _h10(),
        )

        evidence = gather_hypothesis_evidence(
            ("PLTR",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = _row(evidence, "PLTR", "H10a")
        self.assertEqual(row.evaluation_session, EVALUATION)
        self.assertEqual(row.run_date, RUN_DATE)
        self.assertEqual(row.sources[0].date, EVALUATION)

    def test_h8_preserves_real_out_of_window_vocabulary(self):
        _write_json(
            self.root / "reports" / "h8_forward" / f"{EVALUATION}.json",
            _h8(status="OUT_OF_WINDOW", window_state="OUT_OF_WINDOW"),
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = _row(evidence, "AMZN", "H8")
        self.assertEqual(
            [(state.label, state.state) for state in row.symbol_states],
            [
                ("entry", "OUT_OF_WINDOW"),
                ("window", "OUT_OF_WINDOW"),
            ],
        )

    def test_missing_expected_daily_receipts_use_exact_fail_visible_text(self):
        evidence = gather_hypothesis_evidence(
            ("AMZN", "PLTR", "AMD"),
            root=self.root,
            cohort_loader=_cohort,
        )

        expected = {
            ("AMZN", "H5"): "NO RECEIPT H5 — expected daily",
            ("AMZN", "H6"): "NO RECEIPT H6 — expected daily",
            ("AMD", "H7"): "NO RECEIPT H7 — expected daily",
            ("AMZN", "H8"): "NO RECEIPT H8 — expected daily",
            ("PLTR", "H10a"): "NO RECEIPT H10a — expected daily",
            ("PLTR", "H10b"): "NO RECEIPT H10b — expected daily",
        }
        for (symbol, family), text in expected.items():
            with self.subTest(symbol=symbol, family=family):
                row = _row(evidence, symbol, family)
                self.assertEqual(row.detail, text)
                self.assertNotIn("stale", row.detail.lower())

    def test_friday_receipt_on_weekend_or_monday_is_not_called_stale(self):
        friday = "2026-07-24"
        monday = "2026-07-27"
        _write_json(
            self.root
            / "reports"
            / "ritual"
            / f"capture_receipt_{friday}.json",
            _ritual(as_of=friday, run_date=monday),
        )
        path = (
            self.root
            / "reports"
            / "h5"
            / f"entry_watch_{friday}.txt"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"AMZN: WAIT close $230 (as of {friday})\n",
            encoding="utf-8",
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = _row(evidence, "AMZN", "H5")
        self.assertEqual(row.evaluation_session, friday)
        self.assertEqual(row.run_date, monday)
        self.assertNotIn("stale", row.detail.lower())

    def test_build_only_cohort_is_unknown_and_only_typed_error_is_caught(self):
        def unavailable(_base_dir: Path) -> RegisteredCohort:
            raise CohortUnavailableError("ledger is VALID EMPTY")

        evidence = gather_hypothesis_evidence(
            ("AMD",),
            root=self.root,
            cohort_loader=unavailable,
        )
        h7 = _row(evidence, "AMD", "H7")
        self.assertEqual(h7.family_state, "UNKNOWN")
        self.assertIn("BUILD-ONLY", h7.membership)
        self.assertEqual(h7.sources, ())

        def unexpected(_base_dir: Path) -> RegisteredCohort:
            raise RuntimeError("unexpected cohort bug")

        with self.assertRaisesRegex(RuntimeError, "unexpected cohort bug"):
            gather_hypothesis_evidence(
                ("AMD",),
                root=self.root,
                cohort_loader=unexpected,
            )

    def test_newest_intraday_slot_is_semantic_and_malformed_stays_unknown(self):
        _write_json(
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "midday.json",
            _intraday(("AMZN",), tag="midday"),
        )
        newest = (
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "preclose.json"
        )
        newest.write_text("{bad-json", encoding="utf-8")

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = evidence["AMZN"].intraday
        self.assertEqual(row.family_state, "UNKNOWN")
        self.assertEqual(
            row.sources[0].path,
            f"reports/intraday_capture/{EVALUATION}/preclose.json",
        )
        self.assertTrue(row.descriptive_only)

    def test_intraday_receipt_requires_exact_ordered_canonical_universe(self):
        path = (
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "preclose.json"
        )
        receipt = _intraday(("AMZN",))
        receipt["universe"] = ["AMZN"]
        _write_json(path, receipt)

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )
        self.assertEqual(evidence["AMZN"].intraday.family_state, "UNKNOWN")

        receipt["universe"] = [
            *watch_universe(),
            *config.ATTRACTIVENESS_EXTRA_NAMES,
        ]
        _write_json(path, receipt)
        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )
        self.assertEqual(evidence["AMZN"].intraday.family_state, "UNKNOWN")

    def test_intraday_receipt_requires_matching_row_identity(self):
        receipt = _intraday(tuple(watch_universe()))
        receipt["names"]["AMZN"]["symbol"] = "PLTR"
        _write_json(
            self.root
            / "reports"
            / "intraday_capture"
            / EVALUATION
            / "preclose.json",
            receipt,
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = evidence["AMZN"].intraday
        self.assertEqual(row.family_state, "UNKNOWN")
        self.assertEqual(row.symbol_states[0].state, "UNKNOWN")

    def test_cohort_loader_receives_the_requested_root_store(self):
        seen: list[Path] = []

        def rooted_loader(base_dir: Path) -> RegisteredCohort:
            seen.append(base_dir)
            return _cohort(base_dir)

        gather_hypothesis_evidence(
            ("AMD",),
            root=self.root,
            cohort_loader=rooted_loader,
        )

        self.assertEqual(
            seen,
            [self.root / "ledger" / "h7_forward"],
        )

    def test_h7_excluded_member_keeps_reason_without_inventing_lanes(self):
        _write_json(
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "source_health"
            / f"{EVALUATION}.json",
            _h7_source(symbol="AVGO"),
        )
        _write_json(
            self.root
            / "reports"
            / "h7_receipts"
            / self.scope_id
            / "watcher"
            / f"{EVALUATION}.json",
            _h7_watcher(symbol="AMD"),
        )

        evidence = gather_hypothesis_evidence(
            ("AVGO",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = _row(evidence, "AVGO", "H7")
        self.assertEqual(row.membership, "H7 excluded EARNINGS-UNKNOWN")
        self.assertEqual(row.symbol_states[0].state, "BANNED")
        self.assertEqual(
            [state.state for state in row.symbol_states[1:]],
            ["UNKNOWN", "UNKNOWN", "UNKNOWN"],
        )

    def test_h5_rejects_non_receipt_state_vocabulary_as_unknown(self):
        path = (
            self.root
            / "reports"
            / "h5"
            / f"entry_watch_{EVALUATION}.txt"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"AMZN: BLOCKED close $230 (as of {EVALUATION})\n",
            encoding="utf-8",
        )

        evidence = gather_hypothesis_evidence(
            ("AMZN",),
            root=self.root,
            cohort_loader=_cohort,
        )

        row = _row(evidence, "AMZN", "H5")
        self.assertEqual(row.symbol_states[0].state, "UNKNOWN")
        self.assertIn("omits tracked symbol", row.detail)

    def test_family_summary_is_stable_and_keeps_only_agreed_dates(self):
        """A tracker rollup must not turn row disagreement into a current date."""
        from options_researcher.hypothesis_evidence import (
            summarize_hypothesis_evidence,
        )

        self._write_complete_fixture()
        evidence = gather_hypothesis_evidence(
            ("AMZN",), root=self.root, cohort_loader=_cohort
        )
        summaries = summarize_hypothesis_evidence(evidence)

        self.assertEqual(
            [summary.family for summary in summaries],
            ["H5", "H6", "H7", "H8", "H10a", "H10b"],
        )
        h6 = summaries[1]
        self.assertEqual(h6.ritual_state, "CAPTURED")
        self.assertEqual(h6.evaluation_session, EVALUATION)
        self.assertEqual(h6.run_date, RUN_DATE)
        self.assertEqual(
            [(count.state, count.count) for count in h6.raw_state_counts],
            [("BLOCKED", 1), ("POST_REPORT", 1)],
        )
        self.assertEqual(summaries[4].registered_window_end, config.H10A_WINDOW_END)
        self.assertEqual(
            summaries[4].registered_window_metadata, "registered-window metadata"
        )

        changed_h6 = replace(
            _row(evidence, "AMZN", "H6"), evaluation_session="2026-07-25"
        )
        changed_evidence = replace(
            evidence["AMZN"],
            hypotheses=tuple(
                changed_h6 if row.family == "H6" else row
                for row in evidence["AMZN"].hypotheses
            ),
        )
        disagreed = summarize_hypothesis_evidence({
            "AMZN": evidence["AMZN"],
            "SECOND": changed_evidence,
        })
        self.assertIsNone(disagreed[1].evaluation_session)

    def test_gather_and_summary_never_write_or_import_watchers(self):
        """Receipt aggregation stays read-only even when write APIs are hostile."""
        import hashlib
        import os

        from options_researcher import hypothesis_evidence
        from options_researcher.hypothesis_evidence import (
            summarize_hypothesis_evidence,
        )

        self.assertFalse(
            _has_prohibited_watcher_import(
                Path(hypothesis_evidence.__file__).read_text(encoding="utf-8")
            )
        )

        self._write_complete_fixture()
        before = {
            path.relative_to(self.root): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*") if path.is_file()
        }
        with (
            mock.patch.object(Path, "write_text", side_effect=AssertionError("write")),
            mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write")),
            mock.patch.object(Path, "unlink", side_effect=AssertionError("write")),
            mock.patch.object(Path, "rename", side_effect=AssertionError("write")),
            mock.patch.object(os, "replace", side_effect=AssertionError("write")),
        ):
            summarize_hypothesis_evidence(
                gather_hypothesis_evidence(("AMZN",), root=self.root, cohort_loader=_cohort)
            )
        after = {
            path.relative_to(self.root): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)

    def test_watcher_import_guard_rejects_package_form(self):
        """A package import alias must be treated as the watcher module it loads."""
        for source in (
            "import options_researcher.h6_watch\n",
            "from options_researcher.h6_watch import run\n",
            "from options_researcher import h6_watch\n",
        ):
            with self.subTest(source=source):
                self.assertTrue(_has_prohibited_watcher_import(source))


if __name__ == "__main__":
    unittest.main()
