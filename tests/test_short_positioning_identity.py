"""Effective-dated security identity tests.

A ticker is not an identity. Symbol reuse, share-class ambiguity, and
corporate actions must block derived history rather than silently join rows.
"""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from data.short_positioning.identity import (
    SecurityAliasV1,
    load_effective_dated_aliases,
    resolve_security_identity,
)


def _alias(**overrides) -> SecurityAliasV1:
    kwargs = {
        "schema_version": "security-alias/v1",
        "symbol": "ZQXA",
        "market": "NNM",
        "security_id": "SYN-0001",
        "security_id_scheme": "synthetic-test",
        "issue_name": "ZEPHYR QUANTA HOLDINGS INC COMMON STOCK",
        "effective_from": date(2020, 1, 1),
        "effective_to": None,
        "identity_status": "VERIFIED",
        "note": None,
    }
    kwargs.update(overrides)
    return SecurityAliasV1(**kwargs)


class ResolveIdentityTests(unittest.TestCase):
    def test_no_alias_yields_symbol_only_without_inventing_an_identifier(self):
        identity = resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=())
        self.assertEqual(identity.identity_status, "SYMBOL_ONLY")
        self.assertIsNone(identity.security_id)
        self.assertEqual(identity.symbol, "ZQXA")

    def test_single_covering_alias_is_verified(self):
        identity = resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=(_alias(),))
        self.assertEqual(identity.identity_status, "VERIFIED")
        self.assertEqual(identity.security_id, "SYN-0001")

    def test_alias_outside_its_window_does_not_apply(self):
        alias = _alias(effective_from=date(2027, 1, 1))
        identity = resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=(alias,))
        self.assertEqual(identity.identity_status, "SYMBOL_ONLY")
        self.assertIsNone(identity.security_id)

    def test_symbol_reuse_is_resolved_by_the_asof_date(self):
        first = _alias(
            security_id="SYN-OLD", effective_from=date(2018, 1, 1), effective_to=date(2021, 6, 30)
        )
        second = _alias(security_id="SYN-NEW", effective_from=date(2022, 1, 1))
        aliases = (first, second)

        self.assertEqual(
            resolve_security_identity("ZQXA", asof=date(2020, 5, 1), aliases=aliases).security_id,
            "SYN-OLD",
        )
        self.assertEqual(
            resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=aliases).security_id,
            "SYN-NEW",
        )

    def test_overlapping_aliases_are_ambiguous_and_carry_no_identifier(self):
        aliases = (
            _alias(security_id="SYN-A"),
            _alias(security_id="SYN-B", issue_name="ZEPHYR QUANTA HOLDINGS INC CLASS B"),
        )
        identity = resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=aliases)
        self.assertEqual(identity.identity_status, "AMBIGUOUS")
        self.assertIsNone(identity.security_id)

    def test_corporate_action_status_is_preserved(self):
        alias = _alias(identity_status="CORPORATE_ACTION", note="synthetic split under review")
        identity = resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=(alias,))
        self.assertEqual(identity.identity_status, "CORPORATE_ACTION")

    def test_a_declared_ambiguous_class_stays_ambiguous(self):
        alias = _alias(identity_status="AMBIGUOUS", note="two share classes share this ticker")
        identity = resolve_security_identity("ZQXA", asof=date(2026, 7, 17), aliases=(alias,))
        self.assertEqual(identity.identity_status, "AMBIGUOUS")

    def test_market_mismatch_does_not_silently_match(self):
        identity = resolve_security_identity(
            "ZQXA", asof=date(2026, 7, 17), aliases=(_alias(market="NYSE"),), market="NNM"
        )
        self.assertEqual(identity.identity_status, "SYMBOL_ONLY")


class LoadAliasTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_missing_alias_file_is_an_empty_mapping_not_an_error(self):
        self.assertEqual(load_effective_dated_aliases(self.root), ())

    def test_aliases_round_trip_from_the_local_mapping(self):
        path = self.root / "identity" / "aliases.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                [
                    {
                        "schema_version": "security-alias/v1",
                        "symbol": "ZQXA",
                        "market": "NNM",
                        "security_id": "SYN-0001",
                        "security_id_scheme": "synthetic-test",
                        "issue_name": "ZEPHYR QUANTA HOLDINGS INC COMMON STOCK",
                        "effective_from": "2020-01-01",
                        "effective_to": None,
                        "identity_status": "VERIFIED",
                        "note": None,
                    }
                ]
            )
        )
        aliases = load_effective_dated_aliases(self.root)
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0].security_id, "SYN-0001")
        self.assertEqual(aliases[0].effective_from, date(2020, 1, 1))


if __name__ == "__main__":
    unittest.main()
