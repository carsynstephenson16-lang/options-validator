import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import config
from data.pandas_feed import adverse_buy, adverse_sell
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_real_scoring as real_scoring
from options_researcher import h7_window_registration as registration
from options_researcher.h7_scope import scope_identity
from research.hashing import sha256_file
from research.receipts import load_receipt

FINAL = "2026-10-26"
AFTER_FINAL = datetime(2026, 10, 27, 1, tzinfo=timezone.utc)


def _clock(value="2026-10-27T01:00:00+00:00"):
    return lambda: datetime.fromisoformat(value)


def _event(
    event_id,
    event_type,
    session,
    *,
    symbol=None,
    lane=None,
    causes=None,
    payload=None,
):
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at_utc": f"{session}T20:00:00+00:00",
        "evaluation_session": session,
        "symbol": symbol,
        "lane": lane,
        "causes": causes or [],
        "payload": payload or {},
    }


class RealScoringCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.base = self.root / "forward"
        self.artifacts = self.root / "reports"
        self.facts = self.root / "facts.log"
        scope = scope_identity()
        registration.register_window(
            owner={
                "H7_STAGE8_EXPLICIT_AUTHORIZATION": "fixture",
                "WINDOW_START_DECISION_SESSION": "2026-07-20",
                "WINDOW_DECISION_SESSION_COUNT": 70,
                "WINDOW_END_RULE_ACKNOWLEDGED": "fixture",
                "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
                "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2027-02-28",
                "THETADATA_CONFIRMATION_EVIDENCE": "fixture",
            },
            evidence={
                "review_evidence": "fixture",
                "activation_spec_sha256": "a" * 64,
                "code_commit": "b" * 40,
                "source_health_evidence_id": "sh:fixture",
                "data_gate_evidence_id": "dg:fixture",
                "darwin_durability_verified": True,
                "pre_append_state": "VALID EMPTY",
            },
            base_dir=self.base,
            universe_manifest={
                "scope_id": scope["scope_id"],
                "scope_hash": scope["scope_hash"],
                "included": ["AMD"],
                "excluded": [
                    {"symbol": symbol, "reason": "EARNINGS-UNKNOWN"}
                    for symbol in scope["symbols"]
                    if symbol != "AMD"
                ],
                "trim_rule": "source_health_ready_at_pinned_session",
            },
        )
        self.registration = ledger.read_events(self.base)[0]
        self._write_review_passes()

    def _write_review_passes(self):
        spec_hash = sha256_file(real_scoring.SPEC_PATH)
        self.facts.write_text(
            "\n".join(
                [
                    "2026-10-26T22:00:00+00:00\t"
                    f"{real_scoring.REVIEW_PASS_TAG} verdict=PASS "
                    f"spec_sha256={spec_hash}",
                    "2026-10-26T22:01:00+00:00\t"
                    f"{real_scoring.OWNER_PASS_TAG} owner=carsyn verdict=PASS "
                    f"spec_sha256={spec_hash}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def open(self):
        return real_scoring.open_real_scoring_session(
            base_dir=self.base,
            facts_path=self.facts,
            artifact_root=self.artifacts,
        )

    def append(self, event):
        return ledger.append_event(event, base_dir=self.base, clock=_clock())

    def _snapshot(self):
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def _append_opening(self, *, expiration="2026-08-21"):
        intent_id = "intent:AMD:a"
        open_id = "open:AMD:a"
        entry_price = adverse_buy(5.1)
        entry_commission = config.COMMISSION_PER_CONTRACT
        at_risk = entry_price * 100 + 2 * entry_commission
        action = {
            "lane": "a",
            "kind": "long_call",
            "expiration": expiration,
            "strike": 100.0,
        }
        frozen_leg = {
            "name": "long",
            "expiration": expiration,
            "strike": 100.0,
            "right": "C",
            "side": "buy",
            "quantity": config.H7_FORWARD_CONTRACTS,
        }
        self.append(
            _event(
                intent_id,
                "entry_intent",
                "2026-07-20",
                symbol="AMD",
                lane="a",
                causes=[self.registration.event_id],
                payload={
                    "position_id": intent_id,
                    "decision_session": "2026-07-20",
                    "planned_fill_session": "2026-07-21",
                    "decision_at_risk": at_risk,
                    "action": action,
                    "legs": [frozen_leg],
                },
            )
        )
        opening_leg = {
            **frozen_leg,
            "raw_bid": 5.0,
            "raw_ask": 5.1,
            "open_interest": 500,
            "raw_delta": 0.60,
            "fill_price": entry_price,
        }
        self.append(
            _event(
                open_id,
                "paper_fill",
                "2026-07-21",
                symbol="AMD",
                lane="a",
                causes=[intent_id],
                payload={
                    "transition": "open",
                    "position_id": intent_id,
                    "entry_intent_id": intent_id,
                    "decision_session": "2026-07-20",
                    "fill_session": "2026-07-21",
                    "structure": "long_call",
                    "action": action,
                    "legs": [opening_leg],
                    "net_debit_per_share": entry_price,
                    "commission": entry_commission,
                    "at_risk": at_risk,
                    "closes_identity": "sha256:entry-close",
                    "underlying_close": 100.0,
                    "underlying_close_session": "2026-07-21",
                    "underlying_close_identity": "sha256:entry-close",
                },
            )
        )
        return intent_id, open_id, action, opening_leg, at_risk

    def _append_market_close(self, *, offset=False):
        position_id, open_id, action, opening_leg, _ = self._append_opening()
        exit_id = "exit:AMD:a"
        trigger_source = "2026-07-21" if offset else "2026-07-22"
        trigger_decision = "2026-07-22"
        close_source = "2026-07-22" if offset else "2026-07-23"
        close_decision = "2026-07-23"
        self.append(
            _event(
                exit_id,
                "exit_intent",
                trigger_source,
                symbol="AMD",
                lane="a",
                causes=[open_id],
                payload={
                    "position_id": position_id,
                    "opening_fill_id": open_id,
                    "trigger_session": trigger_source,
                    "decision_session": trigger_decision,
                    "source_evaluation_session": trigger_source,
                    "planned_fill_session": "2026-07-23",
                    "primary_reason": "profit_target",
                    "trigger_reasons": ["profit_target"],
                },
            )
        )
        exit_price = adverse_sell(11.0)
        closing_leg = {
            **opening_leg,
            "side": "sell",
            "raw_bid": 11.0,
            "raw_ask": 11.1,
            "raw_delta": 0.70,
            "fill_price": exit_price,
        }
        self.append(
            _event(
                "close:AMD:a",
                "paper_fill",
                close_source,
                symbol="AMD",
                lane="a",
                causes=[exit_id],
                payload={
                    "transition": "close",
                    "position_id": position_id,
                    "opening_fill_id": open_id,
                    "exit_intent_id": exit_id,
                    "fill_session": close_source,
                    "decision_session": close_decision,
                    "source_evaluation_session": close_source,
                    "structure": action["kind"],
                    "primary_reason": "profit_target",
                    "legs": [closing_leg],
                    "net_close_credit_per_share": exit_price,
                    "commission": config.COMMISSION_PER_CONTRACT,
                    "closes_identity": "sha256:exit-close",
                    "underlying_close": 112.0,
                    "underlying_close_session": close_source,
                    "underlying_close_identity": "sha256:exit-close",
                },
            )
        )

    def _append_settlement(self, *, bound_close=True):
        expiration = "2026-08-21"
        position_id, open_id, action, opening_leg, _ = self._append_opening(
            expiration=expiration
        )
        underlying = 120.0 if bound_close else None
        intrinsic = 20.0 if bound_close else None
        cash = 20.0 if bound_close else 0.0
        itm = bound_close
        self.append(
            _event(
                "settlement:AMD:a",
                "paper_fill",
                expiration,
                symbol="AMD",
                lane="a",
                causes=[open_id],
                payload={
                    "transition": "close",
                    "position_id": position_id,
                    "opening_fill_id": open_id,
                    "exit_intent_id": None,
                    "fill_session": expiration,
                    "decision_session": expiration,
                    "source_evaluation_session": expiration,
                    "structure": action["kind"],
                    "primary_reason": "expiration_settlement",
                    "legs": [
                        {
                            "name": "long",
                            "expiration": expiration,
                            "strike": 100.0,
                            "right": "C",
                            "opening_side": "buy",
                            "closing_side": "sell",
                            "quantity": opening_leg["quantity"],
                            "intrinsic_per_share": intrinsic,
                            "settlement_cash_per_share": cash,
                            "in_the_money": itm,
                        }
                    ],
                    "net_close_credit_per_share": cash,
                    "commission": (
                        config.COMMISSION_PER_CONTRACT if itm else 0.0
                    ),
                    "closes_identity": "sha256:settlement-close",
                    "underlying_close": underlying,
                    "underlying_close_session": expiration,
                    "underlying_close_identity": "sha256:settlement-close",
                    "settlement_method": (
                        "intrinsic_at_close"
                        if bound_close
                        else "conservative_full_loss"
                    ),
                    "assignment_disclosure_required": True,
                },
            )
        )


class TestRealScoringAuthority(RealScoringCase):
    def test_forged_capability_is_refused(self):
        forged = replace(self.open(), _authority_token=object())

        with self.assertRaises(real_scoring.RealScoringRefused):
            real_scoring.preview_real_score(forged, now=AFTER_FINAL)

    def test_preview_is_read_only_and_explicitly_not_final(self):
        before = self._snapshot()
        with (
            patch.object(real_scoring, "REAL_FORWARD_STORE", self.base),
            patch.object(real_scoring, "DEFAULT_FACTS_PATH", self.facts),
            patch.object(real_scoring, "DEFAULT_ARTIFACT_ROOT", self.artifacts),
            patch.object(
                real_scoring,
                "_utc_now",
                return_value=AFTER_FINAL,
            ),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = real_scoring.main(["preview"])

        self.assertEqual(code, 0)
        self.assertIn("NOT FINAL", output.getvalue())
        self.assertEqual(self._snapshot(), before)

    def test_preview_before_window_completion_is_not_final_and_writes_nothing(self):
        before = self._snapshot()

        with self.assertRaises(real_scoring.RealScoringIncomplete):
            real_scoring.preview_real_score(
                self.open(),
                now=datetime(2026, 10, 26, 19, tzinfo=timezone.utc),
            )

        self.assertEqual(self._snapshot(), before)

    def test_finalize_requires_review_and_owner_pass_facts(self):
        self.facts.write_text("", encoding="utf-8")

        with self.assertRaisesRegex(
            real_scoring.RealScoringRefused, real_scoring.REVIEW_PASS_TAG
        ):
            real_scoring.finalize_real_score(
                self.open(), owner="carsyn", now=AFTER_FINAL
            )

    def test_changed_config_identity_is_refused_before_scoring(self):
        session = self.open()

        with (
            patch.object(real_scoring, "config_hash", return_value="f" * 64),
            self.assertRaises(real_scoring.RealScoringRefused),
        ):
            real_scoring.finalize_real_score(
                session, owner="carsyn", now=AFTER_FINAL
            )

    def test_wrong_registered_scorer_identity_is_refused(self):
        bad = self.root / "bad-forward"
        payload = json.loads(json.dumps(self.registration.payload))
        payload["frozen"]["scorer"]["module"] = "wrong.scorer"
        ledger.append_event(
            _event(
                "wr:bad",
                "window_registration",
                "2026-07-20",
                payload=payload,
            ),
            base_dir=bad,
            clock=_clock(),
        )

        with self.assertRaises(real_scoring.RealScoringRefused):
            real_scoring.open_real_scoring_session(
                base_dir=bad,
                facts_path=self.facts,
                artifact_root=self.artifacts,
            )


class TestRealScoringPublication(RealScoringCase):
    def test_market_close_uses_frozen_scorer_and_finalizes_idempotently(self):
        self._append_market_close()
        frozen_before = sha256_file(real_scoring.REPO_ROOT / "options_researcher" / "h7_forward_scoring.py")
        session = self.open()

        first = real_scoring.finalize_real_score(
            session, owner="carsyn", now=AFTER_FINAL
        )
        second = real_scoring.finalize_real_score(
            session, owner="carsyn", now=AFTER_FINAL
        )

        self.assertTrue(first.appended)
        self.assertFalse(second.appended)
        self.assertEqual(first.artifact_hash, second.artifact_hash)
        self.assertEqual(first.result["n_trades"], 1)
        self.assertEqual(
            first.result["frozen_scorer_market_only"]["n_trades"], 1
        )
        self.assertEqual(
            sha256_file(real_scoring.REPO_ROOT / "options_researcher" / "h7_forward_scoring.py"),
            frozen_before,
        )
        stored = ledger.read_events(self.base)[-1]
        self.assertEqual(stored.event_type, "window_score")
        self.assertEqual(
            stored.causes,
            [self.registration.event_id, "open:AMD:a", "close:AMD:a"],
        )

    def test_intrinsic_settlement_is_scored_without_fabricated_quotes(self):
        self._append_settlement(bound_close=True)

        result = real_scoring.finalize_real_score(
            self.open(), owner="carsyn", now=AFTER_FINAL
        )

        self.assertEqual(result.result["n_trades"], 1)
        self.assertEqual(result.result["settlement"]["position_count"], 1)
        trade = result.result["trades"][0]
        self.assertEqual(trade["settlement_method"], "intrinsic_at_close")
        self.assertEqual(trade["underlying_exit_close"], 120.0)
        self.assertNotIn("raw_bid", json.dumps(trade))

    def test_market_score_preserves_offset_source_dates_after_due_check(self):
        self._append_market_close(offset=True)

        result = real_scoring.finalize_real_score(
            self.open(), owner="carsyn", now=AFTER_FINAL
        )

        trade = result.result["trades"][0]
        self.assertEqual(trade["entry_date"], "2026-07-21")
        self.assertEqual(trade["exit_date"], "2026-07-22")
        self.assertEqual(trade["decision_session"], "2026-07-20")

    def test_missing_close_conservative_settlement_remains_scorable(self):
        self._append_settlement(bound_close=False)

        result = real_scoring.finalize_real_score(
            self.open(), owner="carsyn", now=AFTER_FINAL
        )

        trade = result.result["trades"][0]
        self.assertEqual(trade["settlement_method"], "conservative_full_loss")
        self.assertIsNone(trade["underlying_exit_close"])
        self.assertIsNone(trade["underlying_return"])

    def test_orphan_artifact_recovers_only_at_same_input_head(self):
        session = self.open()
        original_append = ledger.append_event

        with patch.object(
            ledger,
            "append_event",
            side_effect=ledger.LedgerHeadConflictError("fixture conflict"),
        ):
            with self.assertRaisesRegex(
                real_scoring.RealScoringRefused, "artifact is an orphan"
            ):
                real_scoring.finalize_real_score(
                    session, owner="carsyn", now=AFTER_FINAL
                )
        self.assertTrue(session.artifact_path.exists())
        self.assertFalse(
            any(
                event.event_type == "window_score"
                for event in ledger.read_events(self.base)
            )
        )

        with patch.object(ledger, "append_event", wraps=original_append):
            recovered = real_scoring.finalize_real_score(
                session, owner="carsyn", now=AFTER_FINAL
            )

        self.assertTrue(recovered.appended)

    def test_unresolved_intent_refuses(self):
        self.append(
            _event(
                "intent:unresolved",
                "entry_intent",
                "2026-07-20",
                symbol="AMD",
                lane="a",
                causes=[self.registration.event_id],
                payload={
                    "position_id": "intent:unresolved",
                    "decision_session": "2026-07-20",
                    "planned_fill_session": "2026-07-21",
                    "decision_at_risk": 100.0,
                },
            )
        )
        with self.assertRaises(real_scoring.RealScoringIncomplete):
            real_scoring.finalize_real_score(
                self.open(), owner="carsyn", now=AFTER_FINAL
            )

    def test_duplicate_closing_fill_refuses(self):
        self._append_market_close()
        first = next(
            event
            for event in ledger.read_events(self.base)
            if event.event_id == "close:AMD:a"
        )
        self.append(
            _event(
                "close:AMD:a:duplicate",
                "paper_fill",
                first.evaluation_session,
                symbol=first.symbol,
                lane=first.lane,
                causes=first.causes,
                payload=first.payload,
            )
        )

        with self.assertRaises(real_scoring.RealScoringIncomplete):
            real_scoring.finalize_real_score(
                self.open(), owner="carsyn", now=AFTER_FINAL
            )

    def test_conflicting_existing_artifact_is_never_overwritten(self):
        session = self.open()
        session.artifact_path.parent.mkdir(parents=True)
        session.artifact_path.write_text("{}\n", encoding="utf-8")
        before = session.artifact_path.read_bytes()

        with self.assertRaises(real_scoring.RealScoringRefused):
            real_scoring.finalize_real_score(
                session, owner="carsyn", now=AFTER_FINAL
            )

        self.assertEqual(session.artifact_path.read_bytes(), before)

    def test_receipt_contains_required_disclosures_and_identities(self):
        result = real_scoring.finalize_real_score(
            self.open(), owner="carsyn", now=AFTER_FINAL
        )

        receipt = load_receipt(result.artifact_path, expected_type="window_score")
        self.assertEqual(receipt["input_ledger_head"], self.registration.record_hash)
        self.assertEqual(receipt["owner_acknowledgement"], "carsyn")
        self.assertIn("assignment", receipt["disclosures"])
        self.assertIn("small_sample_interval", receipt["disclosures"])
        self.assertEqual(
            receipt["scorer"]["module"],
            "options_researcher.h7_forward_scoring",
        )


if __name__ == "__main__":
    unittest.main()
