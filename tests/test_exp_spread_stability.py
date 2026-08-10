from __future__ import annotations

import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


def _chain(session: str, rel_spread: float, *, expiration: str = "2026-02-20") -> pd.DataFrame:
    mid = 1.0
    return pd.DataFrame(
        [
            {
                "expiration": expiration,
                "strike": 100.0,
                "right": "P",
                "bid": mid - rel_spread / 2.0,
                "ask": mid + rel_spread / 2.0,
                "open_interest": 100,
                "iv": 0.30,
                "delta": -0.50,
                "session": session,
            }
        ]
    )


def _sessions(rel_spreads: list[float]) -> dict[str, pd.DataFrame]:
    dates = pd.bdate_range("2026-01-02", periods=len(rel_spreads))
    return {
        day.date().isoformat(): _chain(day.date().isoformat(), spread)
        for day, spread in zip(dates, rel_spreads, strict=True)
    }


class SpreadStabilityTest(unittest.TestCase):
    def test_baseline_excludes_today_red(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 20 + [1.00])
        card = exp_spread_stability(chains, asof=max(chains), earnings_weeks=set())
        self.assertAlmostEqual(card["baseline_median"], 0.10)
        self.assertAlmostEqual(card["ratio"], 10.0)

    def test_key_contract(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        card = exp_spread_stability(
            _sessions([0.10] * 20 + [0.20]),
            asof="2026-01-30",
            earnings_weeks=set(),
        )
        self.assertEqual(
            set(card),
            {
                "experiment_id",
                "state",
                "data_blocked",
                "reason",
                "asof",
                "max_asof",
                "rel_spread_today",
                "baseline_median",
                "ratio",
                "baseline_sessions_used",
                "today_is_earnings_week",
                "caveat",
            },
        )

    def test_known_median_ratio(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.08, 0.12] * 10 + [0.30])
        card = exp_spread_stability(chains, asof=max(chains), earnings_weeks=set())
        self.assertAlmostEqual(card["baseline_median"], 0.10)
        self.assertAlmostEqual(card["ratio"], 3.0)
        self.assertEqual(card["state"], "ELEVATED")
        self.assertEqual(card["baseline_sessions_used"], 20)

    def test_baseline_excludes_earnings_weeks(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 10 + [0.90] * 10 + [0.20])
        earnings = set(list(chains)[10:20])
        card = exp_spread_stability(chains, asof=max(chains), earnings_weeks=earnings)
        self.assertAlmostEqual(card["baseline_median"], 0.10)
        self.assertEqual(card["baseline_sessions_used"], 10)

    def test_today_earnings_week_still_renders_labeled(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 20 + [0.20])
        asof = max(chains)
        card = exp_spread_stability(chains, asof=asof, earnings_weeks={asof})
        self.assertFalse(card["data_blocked"])
        self.assertTrue(card["today_is_earnings_week"])

    def test_invalid_quotes_dropped(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 20 + [0.20])
        bad_day = list(chains)[5]
        chains[bad_day].loc[0, "bid"] = 0.0
        card = exp_spread_stability(chains, asof=max(chains), earnings_weeks=set())
        self.assertEqual(card["baseline_sessions_used"], 19)
        self.assertFalse(card["data_blocked"])

    def test_min_baseline_blocked(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 9 + [0.20])
        card = exp_spread_stability(chains, asof=max(chains), earnings_weeks=set())
        self.assertEqual(card["state"], "DATA_BLOCKED")
        self.assertEqual(card["reason"], "fewer than 10 usable baseline sessions")

    def test_role_based_reference_across_roll(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 20 + [0.20])
        dates = list(chains)
        for session in dates[:12]:
            chains[session] = _chain(session, 0.10, expiration="2026-02-20")
        for session in dates[12:]:
            chains[session] = _chain(
                session,
                0.10 if session != dates[-1] else 0.20,
                expiration="2026-03-20",
            )
        card = exp_spread_stability(chains, asof=dates[-1], earnings_weeks=set())
        self.assertFalse(card["data_blocked"])
        self.assertEqual(card["baseline_sessions_used"], 20)
        self.assertAlmostEqual(card["ratio"], 2.0)

    def test_no_lookahead_invariance(self):
        from options_researcher.exp_spread_stability import exp_spread_stability

        chains = _sessions([0.10] * 20 + [0.20, 0.95])
        cutoff = list(chains)[-2]
        full = exp_spread_stability(chains, asof=cutoff, earnings_weeks=set())
        truncated = exp_spread_stability(
            {day: frame for day, frame in chains.items() if day <= cutoff},
            asof=cutoff,
            earnings_weeks=set(),
        )
        self.assertEqual(full, truncated)

    def test_gating_v3_filter_semantics(self):
        from options_researcher.exp_spread_stability import load_earnings_weeks

        rows = pd.DataFrame(
            [
                {
                    "record_id": "BUS",
                    "symbol": "AAA",
                    "record_type": "assertion",
                    "event_class": "business_update",
                    "status": "confirmed",
                    "expected_date": "2026-01-06",
                    "occurred_date": "",
                    "known_as_of_utc": "2026-01-01T00:00:00+00:00",
                    "supersedes": "",
                },
                {
                    "record_id": "OLD",
                    "symbol": "AAA",
                    "record_type": "assertion",
                    "event_class": "actual_quarterly_earnings",
                    "status": "estimated",
                    "expected_date": "2026-01-07",
                    "occurred_date": "",
                    "known_as_of_utc": "2026-01-01T00:00:00+00:00",
                    "supersedes": "",
                },
                {
                    "record_id": "RET",
                    "symbol": "AAA",
                    "record_type": "retraction",
                    "event_class": "actual_quarterly_earnings",
                    "status": "retracted",
                    "expected_date": "",
                    "occurred_date": "",
                    "known_as_of_utc": "2026-01-02T00:00:00+00:00",
                    "supersedes": "OLD",
                },
                {
                    "record_id": "ACT",
                    "symbol": "AAA",
                    "record_type": "assertion",
                    "event_class": "actual_quarterly_earnings",
                    "status": "occurred",
                    "expected_date": "2026-01-06",
                    "occurred_date": "2026-01-14",
                    "known_as_of_utc": "2026-01-15T00:00:00+00:00",
                    "supersedes": "",
                },
                {
                    "record_id": "EST",
                    "symbol": "BBB",
                    "record_type": "assertion",
                    "event_class": "actual_quarterly_earnings",
                    "status": "estimated",
                    "expected_date": "2026-01-22",
                    "occurred_date": "",
                    "known_as_of_utc": "2026-01-10T00:00:00+00:00",
                    "supersedes": "",
                },
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gating.csv"
            rows.to_csv(path, index=False)
            weeks = load_earnings_weeks(asof="2026-01-31", path=path)
        self.assertNotIn("2026-01-07", weeks.get("AAA", set()))
        self.assertIn("2026-01-14", weeks["AAA"])
        self.assertNotIn("2026-01-06", weeks["AAA"])
        self.assertIn("2026-01-22", weeks["BBB"])

    def test_board_blocked_card(self):
        from options_researcher.exp_spread_stability import build_exp_spread_board

        with patch(
            "options_researcher.exp_spread_stability.load_earnings_weeks",
            side_effect=ValueError("bad gating"),
        ):
            cards = build_exp_spread_board(["AAA"], asof="2026-01-30")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["state"], "DATA_BLOCKED")
        self.assertIn("ValueError", cards[0]["reason"])

    def test_real_cache_board_not_all_blocked_if_present(self):
        cache = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))
        if not any(cache.glob("VST_????-??-??.parquet")):
            self.skipTest("local chain cache absent")

        import config
        from options_researcher.exp_spread_stability import build_exp_spread_board

        cards = build_exp_spread_board(list(config.ATTRACTIVENESS_UNIVERSE), asof="2026-07-27")
        self.assertTrue(any(not card["data_blocked"] for card in cards))

    def test_real_cache_sixty_session_replay_if_present(self):
        cache = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))
        paths = sorted(cache.glob("VST_????-??-??.parquet"))
        paths = [path for path in paths if path.stem[-10:] <= "2026-07-27"][-60:]
        if len(paths) < 60:
            self.skipTest("fewer than 60 cached VST sessions")

        from options_researcher.chains import load_range
        from options_researcher.exp_spread_stability import (
            exp_spread_stability,
            load_earnings_weeks,
        )

        chains = {}
        for path in paths:
            session = path.stem[-10:]
            chains.update(load_range("VST", session, session, allow_oos=True))
        earnings = load_earnings_weeks(asof="2026-07-27").get("VST", set())
        ratios = []
        sessions = sorted(chains)
        for index in range(20, len(sessions)):
            window = {day: chains[day] for day in sessions[index - 20 : index + 1]}
            card = exp_spread_stability(window, asof=sessions[index], earnings_weeks=earnings)
            if not card["data_blocked"]:
                ratios.append(card["ratio"])
        self.assertTrue(ratios)
        self.assertTrue(all(math.isfinite(ratio) for ratio in ratios))


if __name__ == "__main__":
    unittest.main()
