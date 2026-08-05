"""Focused pure tests for paper-only Top-3 snapshot classification."""

from __future__ import annotations

import copy
import unittest

import config
from options_researcher import top3_snapshot as snapshots


def section(**overrides):
    value = {
        "symbol": "AMZN",
        "as_of": "2026-07-15",
        "features_as_of": "2026-07-15",
        "features_stale": False,
    }
    value.update(overrides)
    return value


def group(kind="put", **overrides):
    value = {"kind": kind}
    value.update(overrides)
    return value


def card(**overrides):
    value = {"strike": 225.0, "expiry": "2026-09-18", "credit": 494.0}
    value.update(overrides)
    return value


class CandidateIdTests(unittest.TestCase):
    def test_id_is_normalized_and_independent_of_narrative(self):
        first = snapshots.candidate_id(section(symbol="amzn"), group(), card())
        second = snapshots.candidate_id(
            section(symbol="AMZN"), group(), card(strike=225, why_now="changed")
        )
        self.assertEqual(first, "AMZN:put:2026-09-18:225.00")
        self.assertEqual(first, second)

    def test_invalid_identity_raises(self):
        with self.assertRaises(ValueError):
            snapshots.candidate_id(section(), group(), card(expiry="09/18/2026"))


class IntegrityTests(unittest.TestCase):
    def test_exact_feature_session_is_eligible(self):
        result = snapshots.integrity_status(section())
        self.assertEqual(result["status"], snapshots.ELIGIBLE)
        self.assertEqual(result["reason_codes"], [])

    def test_mismatch_and_stale_are_data_blocked(self):
        result = snapshots.integrity_status(
            section(features_as_of="2026-06-30", features_stale=True)
        )
        self.assertEqual(result["status"], snapshots.DATA_BLOCKED)
        self.assertEqual(result["reason_codes"],
                         ["FEATURES_SESSION_MISMATCH", "FEATURES_STALE"])

    def test_missing_feature_facts_are_data_blocked(self):
        result = snapshots.integrity_status(section(features_as_of=None,
                                                    features_stale=None))
        self.assertEqual(result["status"], snapshots.DATA_BLOCKED)
        self.assertIn("FEATURES_AS_OF_INVALID", result["reason_codes"])
        self.assertIn("FEATURES_STALENESS_UNKNOWN", result["reason_codes"])


class ChainAgeTests(unittest.TestCase):
    """Wall-clock staleness: a self-consistent card can still be far too old.

    ``features_stale`` only compares the feature row to the chain session, so an
    equally stale pair stays silent.  These cases pin the separate question of
    how old the chain session is relative to the evaluation date.
    """

    def test_omitting_today_preserves_prior_behaviour(self):
        # Callers that never opt in must not acquire a new blocker.
        result = snapshots.integrity_status(section(as_of="2026-07-27",
                                                    features_as_of="2026-07-27"))
        self.assertEqual(result["status"], snapshots.ELIGIBLE)
        self.assertEqual(result["reason_codes"], [])
        self.assertIsNone(result["chain_age_sessions"])

    def test_same_session_is_zero_sessions_old(self):
        result = snapshots.integrity_status(section(as_of="2026-08-04",
                                                    features_as_of="2026-08-04"),
                                            today="2026-08-04")
        self.assertEqual(result["status"], snapshots.ELIGIBLE)
        self.assertEqual(result["chain_age_sessions"], 0)

    def test_age_is_counted_in_trading_sessions_not_calendar_days(self):
        # 2026-07-27 Mon -> 2026-08-04 Tue spans 8 calendar days but 6 sessions.
        result = snapshots.integrity_status(section(as_of="2026-07-27",
                                                    features_as_of="2026-07-27"),
                                            today="2026-08-04")
        self.assertEqual(result["chain_age_sessions"], 6)

    def test_chain_past_block_threshold_is_data_blocked(self):
        # The exact production gap that made the board disagree with the broker.
        result = snapshots.integrity_status(section(as_of="2026-07-27",
                                                    features_as_of="2026-07-27"),
                                            today="2026-08-04")
        self.assertEqual(result["status"], snapshots.DATA_BLOCKED)
        self.assertIn("CHAIN_STALE_VS_TODAY", result["reason_codes"])

    def test_age_inside_block_threshold_stays_eligible(self):
        result = snapshots.integrity_status(section(as_of="2026-08-03",
                                                    features_as_of="2026-08-03"),
                                            today="2026-08-04")
        self.assertEqual(result["chain_age_sessions"], 1)
        self.assertEqual(result["status"], snapshots.ELIGIBLE)
        self.assertNotIn("CHAIN_STALE_VS_TODAY", result["reason_codes"])

    def test_chain_session_after_today_is_data_blocked(self):
        # A chain dated ahead of the evaluation date is never a fresher board.
        result = snapshots.integrity_status(section(as_of="2026-08-05",
                                                    features_as_of="2026-08-05"),
                                            today="2026-08-04")
        self.assertEqual(result["status"], snapshots.DATA_BLOCKED)
        self.assertIn("CHAIN_SESSION_IN_FUTURE", result["reason_codes"])

    def test_uninterpretable_today_fails_closed(self):
        result = snapshots.integrity_status(section(), today="04/08/2026")
        self.assertEqual(result["status"], snapshots.DATA_BLOCKED)
        self.assertIn("EVALUATION_DATE_INVALID", result["reason_codes"])
        self.assertIsNone(result["chain_age_sessions"])

    def test_stale_chain_removes_rank_eligibility_end_to_end(self):
        stale = snapshots.snapshot_candidate(
            section(as_of="2026-07-27", features_as_of="2026-07-27"),
            group(), card(), today="2026-08-04",
        )
        self.assertFalse(stale["rank_eligible"])
        self.assertEqual(stale["selection_status"], snapshots.DATA_BLOCKED)
        self.assertIn("CHAIN_STALE_VS_TODAY",
                      stale["integrity"]["reason_codes"])


class LanePolicyTests(unittest.TestCase):
    def test_long_call_uses_defined_risk_cap(self):
        eligible = snapshots.lane_policy_status(
            section(), group("long_call"), card(cost=config.MAX_LOSS_PER_TRADE)
        )
        too_large = snapshots.lane_policy_status(
            section(), group("long_call"),
            card(cost=config.MAX_LOSS_PER_TRADE + 0.01),
        )
        self.assertEqual(eligible["status"], snapshots.ELIGIBLE)
        self.assertEqual(too_large["status"], snapshots.PLAN_ONLY)
        self.assertEqual(too_large["reason_codes"],
                         ["LONG_CALL_MAX_LOSS_EXCEEDS_CAP"])

    def test_csp_does_not_use_universal_max_loss_veto(self):
        result = snapshots.lane_policy_status(
            section(symbol="AMZN"), group("put"), card(strike=225.0),
            csp_open_count=0, assignment_capital_authorized=True,
        )
        self.assertEqual(result["status"], snapshots.ELIGIBLE)
        self.assertEqual(result["assignment_capital"], 22_500.0)
        self.assertNotIn("max_loss", result)

    def test_csp_name_slot_and_unknown_state_are_explicit(self):
        outside = snapshots.lane_policy_status(
            section(symbol="MSFT"), group("put"), card(), csp_open_count=0,
            assignment_capital_authorized=True,
        )
        full = snapshots.lane_policy_status(
            section(), group("put"), card(),
            csp_open_count=config.H4_CSP_MAX_POSITIONS,
            assignment_capital_authorized=True,
        )
        unknown = snapshots.lane_policy_status(
            section(), group("put"), card(), assignment_capital_authorized=True
        )
        self.assertEqual(outside["status"], snapshots.PLAN_ONLY)
        self.assertIn("CSP_SYMBOL_OUTSIDE_ALLOWED_NAMES", outside["reason_codes"])
        self.assertEqual(full["status"], snapshots.PLAN_ONLY)
        self.assertIn("CSP_SLOT_FULL", full["reason_codes"])
        self.assertEqual(unknown["status"], snapshots.WATCH)
        self.assertIn("CSP_OPEN_COUNT_UNKNOWN", unknown["reason_codes"])

    def test_csp_assignment_capital_requires_explicit_owner_authorization(self):
        unconfirmed = snapshots.lane_policy_status(
            section(), group("put"), card(), csp_open_count=0
        )
        denied = snapshots.lane_policy_status(
            section(), group("put"), card(), csp_open_count=0,
            assignment_capital_authorized=False,
        )
        authorized = snapshots.lane_policy_status(
            section(), group("put"), card(), csp_open_count=0,
            assignment_capital_authorized=True,
        )
        self.assertEqual(unconfirmed["status"], snapshots.WATCH)
        self.assertEqual(unconfirmed["reason_codes"],
                         ["CSP_ASSIGNMENT_CAPITAL_UNCONFIRMED"])
        self.assertEqual(denied["status"], snapshots.PLAN_ONLY)
        self.assertEqual(denied["reason_codes"],
                         ["CSP_ASSIGNMENT_CAPITAL_NOT_AUTHORIZED"])
        self.assertEqual(authorized["status"], snapshots.ELIGIBLE)

    def test_pmcc_requires_a_recorded_leaps_and_covered_call_requires_shares(self):
        preview = snapshots.lane_policy_status(
            section(), group("pmcc", preview=True), card()
        )
        pmcc_unknown = snapshots.lane_policy_status(
            section(), group("pmcc", preview=False), card()
        )
        pmcc_missing = snapshots.lane_policy_status(
            section(), group("pmcc", preview=False), card(), leaps_held=False
        )
        pmcc_covered = snapshots.lane_policy_status(
            section(), group("pmcc", preview=False), card(), leaps_held=True
        )
        unknown = snapshots.lane_policy_status(section(), group("cc"), card())
        uncovered = snapshots.lane_policy_status(
            section(), group("cc"), card(), covered_shares=99
        )
        covered = snapshots.lane_policy_status(
            section(), group("cc"), card(), covered_shares=100
        )
        self.assertEqual(preview["status"], snapshots.PLAN_ONLY)
        self.assertEqual(pmcc_unknown["status"], snapshots.WATCH)
        self.assertEqual(pmcc_unknown["reason_codes"],
                         ["PMCC_LEAPS_COVERAGE_UNKNOWN"])
        self.assertEqual(pmcc_missing["status"], snapshots.PLAN_ONLY)
        self.assertEqual(pmcc_missing["reason_codes"], ["PMCC_LEAPS_NOT_HELD"])
        self.assertEqual(pmcc_covered["status"], snapshots.ELIGIBLE)
        self.assertEqual(unknown["status"], snapshots.WATCH)
        self.assertEqual(uncovered["status"], snapshots.PLAN_ONLY)
        self.assertEqual(covered["status"], snapshots.ELIGIBLE)


class SnapshotTests(unittest.TestCase):
    def test_research_is_separate_from_rank_eligibility_and_inputs_do_not_mutate(self):
        sec, grp, candidate = section(), group(), card()
        before = copy.deepcopy((sec, grp, candidate))
        complete = snapshots.snapshot_candidate(
            sec, grp, candidate, csp_open_count=0,
            assignment_capital_authorized=True,
            research={"status": "COMPLETE", "reason_codes": ["PRIMARY_SOURCE"]},
        )
        stale = snapshots.snapshot_candidate(
            sec, grp, candidate, csp_open_count=0,
            assignment_capital_authorized=True,
            research={"status": "STALE", "reason_codes": ["MEMO_TOO_OLD"]},
        )
        self.assertTrue(complete["rank_eligible"])
        self.assertTrue(stale["rank_eligible"])
        self.assertEqual(complete["research"]["status"], "COMPLETE")
        self.assertEqual(stale["research"]["status"], "STALE")
        self.assertEqual((sec, grp, candidate), before)

    def test_integrity_block_beats_policy_eligibility(self):
        result = snapshots.snapshot_candidate(
            section(features_as_of="2026-06-30", features_stale=True),
            group(), card(), csp_open_count=0,
            assignment_capital_authorized=True,
        )
        self.assertEqual(result["policy"]["status"], snapshots.ELIGIBLE)
        self.assertEqual(result["selection_status"], snapshots.DATA_BLOCKED)
        self.assertFalse(result["rank_eligible"])


if __name__ == "__main__":
    unittest.main()
