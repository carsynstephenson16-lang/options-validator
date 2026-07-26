"""Focused tests for the versioned H7 real-scoring identity contract."""

from __future__ import annotations

import unittest

import config
from options_researcher import h7_scoring_identity as identity
from research.hashing import config_hash, cost_model_hash


def _stage_parameters() -> dict[str, object]:
    return {
        name: getattr(config, name)
        for name in identity.STAGE456_PARAMETER_NAMES
    }


def _scorer() -> dict[str, object]:
    return {
        "module": identity.FROZEN_SCORER_MODULE,
        "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
        "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT,
    }


def _legacy_frozen() -> dict[str, object]:
    return {
        "config_hash": config_hash(),
        "cost_model_hash": cost_model_hash(),
        "stage456_parameters": _stage_parameters(),
        "scorer": _scorer(),
    }


def _different(value: object) -> object:
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return f"{value}-changed"
    if isinstance(value, tuple):
        return (*value, "__changed__")
    if isinstance(value, (int, float)):
        return value + 1
    raise AssertionError(f"no test mutation for {type(value).__name__}")


class H7ScoringIdentityTests(unittest.TestCase):
    def test_legacy_registered_identity_matches_runtime(self):
        registered = identity.registered_scoring_identity(_legacy_frozen())
        runtime = identity.runtime_scoring_identity()

        self.assertEqual(registered, runtime)
        self.assertEqual(
            registered.contract, identity.SCORING_IDENTITY_CONTRACT
        )

    def test_canonical_json_normalizes_registered_lists_and_runtime_tuples(self):
        frozen = _legacy_frozen()
        stage = frozen["stage456_parameters"]
        assert isinstance(stage, dict)
        stage["H7_LANE_PRIORITY"] = list(config.H7_LANE_PRIORITY)

        self.assertEqual(
            identity.registered_scoring_identity(frozen),
            identity.runtime_scoring_identity(),
        )

    def test_every_frozen_stage_parameter_changes_identity(self):
        baseline = identity.registered_scoring_identity(_legacy_frozen())

        for name in identity.STAGE456_PARAMETER_NAMES:
            with self.subTest(name=name):
                frozen = _legacy_frozen()
                stage = frozen["stage456_parameters"]
                assert isinstance(stage, dict)
                stage[name] = _different(stage[name])
                scorer = frozen["scorer"]
                assert isinstance(scorer, dict)
                if name == "MIN_LOSSES_FOR_VERDICT":
                    scorer["min_losses_for_verdict"] = stage[name]
                elif name == "BOOTSTRAP_SAMPLES":
                    scorer["bootstrap_samples"] = stage[name]
                changed = identity.registered_scoring_identity(frozen)
                self.assertNotEqual(changed.identity_hash, baseline.identity_hash)

    def test_future_registration_contract_and_hash_are_verified(self):
        frozen = _legacy_frozen()
        expected = identity.registered_scoring_identity(frozen)
        frozen[identity.REGISTRATION_CONTRACT_FIELD] = expected.contract
        frozen[identity.REGISTRATION_HASH_FIELD] = expected.identity_hash

        self.assertEqual(
            identity.registered_scoring_identity(frozen), expected
        )

    def test_missing_stage_parameter_is_malformed(self):
        frozen = _legacy_frozen()
        stage = frozen["stage456_parameters"]
        assert isinstance(stage, dict)
        stage.pop("H7_FORWARD_CONTRACTS")

        with self.assertRaises(identity.ScoringIdentityError):
            identity.registered_scoring_identity(frozen)

    def test_stage_and_scorer_duplicates_must_agree(self):
        for name, scorer_name in (
            ("MIN_LOSSES_FOR_VERDICT", "min_losses_for_verdict"),
            ("BOOTSTRAP_SAMPLES", "bootstrap_samples"),
        ):
            with self.subTest(name=name):
                frozen = _legacy_frozen()
                scorer = frozen["scorer"]
                assert isinstance(scorer, dict)
                scorer[scorer_name] = scorer[scorer_name] + 1
                with self.assertRaises(identity.ScoringIdentityError):
                    identity.registered_scoring_identity(frozen)

    def test_scorer_mapping_rejects_extra_key(self):
        frozen = _legacy_frozen()
        scorer = frozen["scorer"]
        assert isinstance(scorer, dict)
        scorer["source_hash"] = "not-part-of-v1"

        with self.assertRaises(identity.ScoringIdentityError):
            identity.registered_scoring_identity(frozen)

    def test_partial_or_stale_persisted_identity_is_malformed(self):
        expected = identity.registered_scoring_identity(_legacy_frozen())
        cases = (
            {
                identity.REGISTRATION_CONTRACT_FIELD: expected.contract,
            },
            {
                identity.REGISTRATION_HASH_FIELD: expected.identity_hash,
            },
            {
                identity.REGISTRATION_CONTRACT_FIELD: "h7_scoring_identity/v999",
                identity.REGISTRATION_HASH_FIELD: expected.identity_hash,
            },
            {
                identity.REGISTRATION_CONTRACT_FIELD: expected.contract,
                identity.REGISTRATION_HASH_FIELD: "f" * 64,
            },
        )
        for persisted in cases:
            with self.subTest(persisted=persisted):
                frozen = {**_legacy_frozen(), **persisted}
                with self.assertRaises(identity.ScoringIdentityError):
                    identity.registered_scoring_identity(frozen)


if __name__ == "__main__":
    unittest.main()
