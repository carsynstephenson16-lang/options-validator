"""tests/test_research_context_assemble.py — offline; no network, no live data."""
import unittest

from tools.research_context_assemble import (
    AssemblyError,
    build_context,
    check_dashboard_html,
    clean_claims,
    clean_symbol_blurb,
)


def _claim(**over):
    base = {
        "id": "c1", "text": "t", "classification": "fact",
        "source_url": "https://investor.nvidia.com/x", "unknown_rationale": None,
        "source_tier": "issuer_ir", "fact_date": "2026-07-24",
        "date_certainty": "confirmed", "countercase": "could fail",
    }
    base.update(over)
    return base


class CleanClaimsTest(unittest.TestCase):
    def test_banned_host_is_hard_error(self):
        bad = _claim(source_url="https://www.reddit.com/r/options/x",
                     source_tier="secondary", date_certainty="estimated")
        with self.assertRaises(AssemblyError):
            clean_claims("NVDA", [bad])

    def test_confirmed_without_primary_tier_is_hard_error(self):
        bad = _claim(source_tier="secondary")
        with self.assertRaises(AssemblyError):
            clean_claims("NVDA", [bad])

    def test_extra_fields_are_dropped_not_fatal(self):
        messy = _claim(confidence="high")  # agents sometimes add extras
        cleaned = clean_claims("NVDA", [messy])
        self.assertNotIn("confidence", cleaned[0])
        self.assertEqual(cleaned[0]["id"], "c1")

    def test_good_claim_passes_through(self):
        cleaned = clean_claims("NVDA", [_claim()])
        self.assertEqual(cleaned[0]["source_tier"], "issuer_ir")


class CleanBlurbTest(unittest.TestCase):
    def test_banned_catalyst_source_is_hard_error(self):
        blurb = {"news_summary": "x", "catalysts": [
            {"date": None, "what": "w", "source": "https://www.fool.com/a",
             "confirmed": False}], "sources": []}
        with self.assertRaises(AssemblyError):
            clean_symbol_blurb("VST", blurb)

    def test_keeps_only_known_keys(self):
        blurb = {"news_summary": "x", "sentiment": "bull", "extra": 1,
                 "sources": ["https://insidelines.pjm.com/a"]}
        cleaned = clean_symbol_blurb("VST", blurb)
        self.assertNotIn("extra", cleaned)
        self.assertEqual(cleaned["sentiment"], "bull")


class BuildContextTest(unittest.TestCase):
    def _inputs(self):
        return {
            "market": {"market": {"summary": "s. more.", "regime": "mixed",
                                  "notes": ["n1"]},
                       "symbols": {}, "market_sources": []},
            "symbol_research": {
                "NVDA": {"symbol": "NVDA", "news_summary": "x",
                         "sentiment": "bull", "catalysts": [],
                         "move_thesis": "y", "sources": [],
                         "claims": [_claim()]},
            },
        }

    def test_builds_validated_context(self):
        ctx = build_context(
            as_of="2026-07-24", researched_on="2026-07-25",
            candidate_ids=["NVDA:long_call:2026-08-07:212.50"],
            inputs=self._inputs(),
        )
        self.assertEqual(ctx["as_of"], "2026-07-24")
        ann = ctx["annotations"]["NVDA:long_call:2026-08-07:212.50"]
        self.assertEqual(ann["market_as_of_date"], "2026-07-24")
        self.assertTrue(ann["claims"])
        self.assertIn("LLM-asserted", ctx["provenance"])

    def test_candidate_without_research_is_omitted_not_invented(self):
        ctx = build_context(
            as_of="2026-07-24", researched_on="2026-07-25",
            candidate_ids=["NVDA:long_call:2026-08-07:212.50",
                           "NOW:long_call:2026-08-07:103.00"],
            inputs=self._inputs(),
        )
        self.assertNotIn("NOW:long_call:2026-08-07:103.00", ctx["annotations"])

    def test_never_emits_legacy_top_picks(self):
        ctx = build_context(
            as_of="2026-07-24", researched_on="2026-07-25",
            candidate_ids=["NVDA:long_call:2026-08-07:212.50"],
            inputs=self._inputs(),
        )
        self.assertNotIn("top_picks", ctx)
        self.assertNotIn("legacy_top_picks_unusable", ctx)

    def test_schema_violation_surfaces_as_assembly_error(self):
        inputs = self._inputs()
        inputs["symbol_research"]["NVDA"]["claims"][0]["countercase"] = ""
        with self.assertRaises(AssemblyError):
            build_context(as_of="2026-07-24", researched_on="2026-07-25",
                          candidate_ids=["NVDA:long_call:2026-08-07:212.50"],
                          inputs=inputs)


class CheckHtmlTest(unittest.TestCase):
    def test_flags_every_stale_marker(self):
        html = ("annotations are from 2026-07-15 ... do not match any card "
                "... Research evidence incomplete ... Research evidence stale")
        problems = check_dashboard_html(html)
        self.assertEqual(len(problems), 4)

    def test_clean_html_passes(self):
        self.assertEqual(check_dashboard_html("all good ✓ Research evidence · complete"), [])


if __name__ == "__main__":
    unittest.main()
