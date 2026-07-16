"""Focused contract tests for advisory-only Top-3 research annotations."""
from __future__ import annotations

import unittest
from copy import deepcopy
from types import MappingProxyType

from options_researcher.top3_context import (
    AnnotationValidationError,
    normalize_research_annotations,
)


class Top3ContextTests(unittest.TestCase):
    candidate = "AMZN:put:260:2026-07-27"

    def _claim(self, **overrides):
        claim = {
            "id": "earnings-date",
            "text": "Amazon announced its earnings date.",
            "classification": "fact",
            "source_url": "https://ir.aboutamazon.com/",
            "unknown_rationale": None,
            "source_tier": "issuer_ir",
            "fact_date": "2026-07-15",
            "date_certainty": "confirmed",
            "countercase": "The release may change the earnings date.",
        }
        claim.update(overrides)
        return claim

    def _annotation(self, **overrides):
        annotation = {
            "research_as_of_utc": "2026-07-16T09:30:00-04:00",
            "market_as_of_date": "2026-07-15",
            "claims": [self._claim()],
        }
        annotation.update(overrides)
        return annotation

    def _normalize(self, annotation=None):
        return normalize_research_annotations(
            [self.candidate], {self.candidate: annotation or self._annotation()}
        )

    def test_primary_source_claim_normalizes_to_immutable_advisory_record(self):
        normalized = self._normalize()

        annotation = normalized[self.candidate]
        self.assertIsInstance(normalized, MappingProxyType)
        self.assertEqual(annotation["research_as_of_utc"], "2026-07-16T13:30:00Z")
        self.assertEqual(annotation["market_as_of_date"], "2026-07-15")
        self.assertTrue(annotation["advisory_only"])
        self.assertEqual(annotation["claims"][0]["source_tier"], "issuer_ir")
        self.assertEqual(annotation["claims"][0]["date_certainty"], "confirmed")
        self.assertNotIn("score", annotation)
        self.assertNotIn("rank", annotation)

    def test_estimated_event_from_secondary_source_is_allowed(self):
        annotation = self._annotation(
            claims=[
                self._claim(
                    id="estimated-earnings",
                    classification="inference",
                    source_url="https://example.com/earnings-estimate",
                    source_tier="secondary",
                    fact_date="2026-07-30",
                    date_certainty="estimated",
                )
            ]
        )

        normalized = self._normalize(annotation)

        claim = normalized[self.candidate]["claims"][0]
        self.assertEqual(claim["classification"], "inference")
        self.assertEqual(claim["date_certainty"], "estimated")
        self.assertEqual(claim["source_tier"], "secondary")

    def test_missing_source_and_unknown_rationale_is_rejected(self):
        annotation = self._annotation(
            claims=[self._claim(source_url=None, unknown_rationale=None)]
        )

        with self.assertRaisesRegex(AnnotationValidationError, "claim_source_missing") as ctx:
            self._normalize(annotation)

        self.assertEqual(ctx.exception.code, "claim_source_missing")

    def test_secondary_source_cannot_mark_date_confirmed(self):
        annotation = self._annotation(
            claims=[self._claim(source_tier="secondary", date_certainty="confirmed")]
        )

        with self.assertRaisesRegex(
            AnnotationValidationError, "confirmed_date_requires_primary_source"
        ) as ctx:
            self._normalize(annotation)

        self.assertEqual(ctx.exception.code, "confirmed_date_requires_primary_source")

    def test_output_and_nested_claims_are_immutable_without_mutating_input(self):
        raw = self._annotation()
        before = deepcopy(raw)

        normalized = self._normalize(raw)

        with self.assertRaises(TypeError):
            normalized[self.candidate] = {}  # type: ignore[index]
        with self.assertRaises(TypeError):
            normalized[self.candidate]["advisory_only"] = False  # type: ignore[index]
        with self.assertRaises(TypeError):
            normalized[self.candidate]["claims"][0]["text"] = "changed"  # type: ignore[index]
        self.assertIsInstance(normalized[self.candidate]["claims"], tuple)
        self.assertEqual(raw, before)

    def test_unmatched_candidate_key_is_rejected_deterministically(self):
        with self.assertRaisesRegex(AnnotationValidationError, "candidate_key_unmatched") as ctx:
            normalize_research_annotations([self.candidate], {"VST:put:220": self._annotation()})

        self.assertEqual(ctx.exception.code, "candidate_key_unmatched")


if __name__ == "__main__":
    unittest.main()
