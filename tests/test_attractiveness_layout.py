"""tests/test_attractiveness_layout.py

Characterization tests for the attractiveness board's display contract.

Nothing here asserts a ranking, a signal, or an authority change. The
authority/disclaimer sentences are pinned verbatim, the page is pinned as
JavaScript-free, and the pick-tracker source-row digest is pinned as the only
HTML comment on the page -- so a later layout edit cannot quietly drop any of
the three.
"""
import unittest

from options_researcher import attractiveness_dashboard as ad
from options_researcher.schwab_chain_view import THETADATA_CHAIN_SOURCE


def _put_section(symbol, *, as_of="2026-08-25", chain_source=THETADATA_CHAIN_SOURCE,
                 credit=100.0, **overrides):
    section = {
        "symbol": symbol,
        "as_of": as_of,
        "close": 100.0,
        "iv_rank": 0.5,
        "chain_source": chain_source,
        "close_as_of": as_of,
        "close_kind": "eod_close",
        "features_as_of": as_of,
        "features_stale": False,
        "groups": [{
            "kind": "put",
            "title": "SELL A PUT?",
            "cards": [{
                "strike": 95.0,
                "expiry": "2026-09-18",
                "dte": 24,
                "credit": credit,
                "annualized_yield": 0.30,
                "cushion": 0.05,
                "grades": {"yield": "GREEN", "liquidity": "GREEN"},
                "verdict": "display only",
            }],
            "empty": None,
        }],
    }
    section.update(overrides)
    return section


def _board(symbols, *, eligible=True, today="2026-08-25", **assemble_kwargs):
    data = ad.assemble(
        symbol_sections=[_put_section(symbol) for symbol in symbols],
        rv21_by_symbol={},
        today=today,
        composite_signals=[],
        **assemble_kwargs,
    )
    if eligible:
        for section in data["symbols"]:
            section["groups"][0]["cards"][0]["top3_snapshot"].update({
                "rank_eligible": True,
                "selection_status": "ELIGIBLE",
                "policy": {"status": "ELIGIBLE", "reason_codes": []},
            })
    return data


def _composite_card(symbol, *, grade="A", trend="UP", vol="RICH",
                    regime="TYPICAL", internals="CONFIRM", as_of="2026-08-25"):
    return {
        "symbol": symbol,
        "grade": grade,
        "max_asof": as_of,
        "trend": {"state": trend, "data_blocked": trend == "DATA_BLOCKED"},
        "vol_premium": {"state": vol, "data_blocked": False},
        "regime": {"state": regime, "data_blocked": False},
        "internals": {"state": internals, "data_blocked": False},
    }


class AuthorityWordingSurvivesLayoutTests(unittest.TestCase):
    """Every authority/disclaimer sentence must survive the redesign verbatim."""

    _SENTENCES = (
        "Composite signal board — display-only",
        "Not verdict-bearing, not FIRE-capable; writes nothing to ledger/ or "
        "positions.",
        "This is a read-only receipt summary and cannot activate, rank, or "
        "place a trade.",
        "Descriptive only; no verdict, ranking, sizing, or trade authority.",
        "DESCRIPTIVE ONLY — NOT A TRADE RANKING",
        "QM does not select, rank, validate, or change the edge or verdict of "
        "any option contract.",
        "This does not select, order, gate, or validate a mechanical pick.",
        "Experimental re-ordering by market context. The rule-based list above "
        "is the registered baseline. This lane is display-only and carries no "
        "verdict or trade authority; once the pick tracker is live its picks "
        "will be tracked descriptively against the baseline.",
        "owner-pinned visibility — not ranked; these cards do not compete with "
        "or reorder the Top-5 shortlist.",
        "This is a fit ranking, not a prediction",
        "Trend does not rank these contracts.",
        "Payoffs are at-expiration scenarios, not predictions.",
    )

    def test_disclaimers_are_present_verbatim(self):
        data = _board(["VST", "AAA"])
        data["composite_signals"] = [_composite_card("AAA")]
        html = ad.render(
            data,
            context={"as_of": "2026-08-25", "provenance": "fixture",
                     "market": {"summary": "Fixture."}, "symbols": {}},
            qm_context={
                "status": "DATA_BLOCKED",
                "quant_want": {"trend": {"status": "UP",
                                         "plain_language": "fixture trend"}},
                "source_commit": "fixture",
            },
            research_views_status={"state": "absent"},
        )
        for sentence in self._SENTENCES:
            with self.subTest(sentence=sentence[:48]):
                self.assertIn(sentence, html)


class PickTrackerBindingTests(unittest.TestCase):
    """The tracker's source-row digest must still bind the new HTML."""

    def test_digest_comment_round_trips_through_the_new_layout(self):
        from options_researcher import pick_tracker

        html = ad.render(_board(["AAA"]))
        digest = "a" * 64
        bound = pick_tracker._bind_source_rows_html(html.encode(), digest)

        self.assertEqual(pick_tracker._html_source_rows_digest(bound), digest)
        self.assertIn(b"<!-- pick-tracker-source-rows-sha256:", bound)
        self.assertTrue(bound.decode().startswith("<!doctype html>"))

    def test_layout_adds_no_second_html_comment_that_could_shadow_the_digest(self):
        html = ad.render(_board(["AAA"]))

        self.assertEqual(html.count("<!--"), 0)


class NoScriptTests(unittest.TestCase):
    def test_board_stays_javascript_free(self):
        data = _board(["AAA"])
        data["composite_signals"] = [_composite_card("AAA")]
        html = ad.render(data)

        self.assertNotIn("<script", html.lower())
        self.assertNotIn("onclick", html.lower())


if __name__ == "__main__":  # pragma: no cover - manual runs
    unittest.main()
