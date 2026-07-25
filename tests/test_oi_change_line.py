"""Offline unittest for the neutral "OI Δ1d" context line (v1: delta +
UNKNOWN taxonomy only). Pins display wording, the UNKNOWN status precedence,
board invariance (a merge blocker), and the causal/no-look-ahead property.

The line is a neutral activity fact: it never touches grades, scores,
ranking, selection, or ordering.
"""
from __future__ import annotations

import copy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

import config
from options_researcher.oi_change import (
    attach_oi_change,
    find_prior_chain,
    oi_change_fields,
    oi_change_line,
)


def _chain(rows: list[dict]) -> pd.DataFrame:
    """Minimal chain frame: only the keys oi_change reads plus open_interest."""
    return pd.DataFrame(
        rows, columns=["expiration", "strike", "right", "open_interest"]
    )


EXP = "2026-08-21"


class OiChangeFieldsTest(unittest.TestCase):
    def _fields(self, day_oi, prior_oi, *, gap=1, strike=100.0, right="C"):
        day = _chain([{"expiration": EXP, "strike": strike, "right": right,
                       "open_interest": day_oi}])
        prior = _chain([{"expiration": EXP, "strike": strike, "right": right,
                         "open_interest": prior_oi}])
        return oi_change_fields(day, prior, gap, expiration=EXP,
                                strike=strike, right=right)

    def test_ok_positive_negative_zero(self):
        pos = self._fields(1500, 1088)
        self.assertEqual(pos, {"oi_delta_1d": 412, "oi_change_status": "OK"})
        self.assertEqual(oi_change_line(pos),
                         "OI Δ1d: +412 contracts (as of prior close)")

        neg = self._fields(600, 900)
        self.assertEqual(neg, {"oi_delta_1d": -300, "oi_change_status": "OK"})
        self.assertEqual(oi_change_line(neg),
                         "OI Δ1d: -300 contracts (as of prior close)")

        zero = self._fields(500, 500)
        self.assertEqual(zero, {"oi_delta_1d": 0, "oi_change_status": "OK"})
        self.assertEqual(oi_change_line(zero),
                         "OI Δ1d: 0 contracts (as of prior close)")

    def test_absent_is_not_zero(self):
        # Target absent from the prior chain -> CONTRACT_ABSENT, never a
        # delta computed from a phantom 0. The chains DO share another key
        # (strike 105), so this is not a GRID_SHIFT.
        day = _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                       "open_interest": 400},
                      {"expiration": EXP, "strike": 105.0, "right": "C",
                       "open_interest": 400}])
        prior = _chain([{"expiration": EXP, "strike": 105.0, "right": "C",
                         "open_interest": 400}])
        fields = oi_change_fields(day, prior, 1, expiration=EXP,
                                  strike=100.0, right="C")
        self.assertEqual(fields["oi_change_status"], "CONTRACT_ABSENT")
        self.assertIsNone(fields["oi_delta_1d"])
        self.assertEqual(oi_change_line(fields),
                         "OI Δ1d: unavailable (UNKNOWN — CONTRACT_ABSENT)")

        # Present with open_interest 0.0 -> LOW_BASE (present, below base),
        # NOT CONTRACT_ABSENT.
        present_zero = self._fields(50, 0.0)
        self.assertEqual(present_zero["oi_change_status"], "LOW_BASE")

    def test_non_finite_oi_is_unusable_not_a_crash(self):
        # validate_chain_schema forbids NaN in the cache, so a non-finite OI
        # means corrupt input; it must classify as CONTRACT_ABSENT (unusable
        # data), never raise or produce a phantom delta.
        fields = self._fields(float("nan"), 500)
        self.assertEqual(fields["oi_change_status"], "CONTRACT_ABSENT")
        self.assertIsNone(fields["oi_delta_1d"])
        fields = self._fields(500, float("nan"))
        self.assertEqual(fields["oi_change_status"], "CONTRACT_ABSENT")

    def test_no_prior_chain(self):
        day = _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                       "open_interest": 400}])
        fields = oi_change_fields(day, None, None, expiration=EXP,
                                  strike=100.0, right="C")
        self.assertEqual(fields, {"oi_delta_1d": None,
                                  "oi_change_status": "NO_PRIOR_CHAIN"})
        self.assertEqual(oi_change_line(fields),
                         "OI Δ1d: unavailable (UNKNOWN — NO_PRIOR_CHAIN)")

    def test_stale_prior_chain(self):
        # gap beyond OI_CHANGE_MAX_PRIOR_GAP_DAYS -> STALE_PRIOR_CHAIN.
        fields = self._fields(1500, 1000, gap=config.OI_CHANGE_MAX_PRIOR_GAP_DAYS + 1)
        self.assertEqual(fields["oi_change_status"], "STALE_PRIOR_CHAIN")
        self.assertIsNone(fields["oi_delta_1d"])
        # A gap exactly at the max is still honest (not stale).
        ok = self._fields(1500, 1000, gap=config.OI_CHANGE_MAX_PRIOR_GAP_DAYS)
        self.assertEqual(ok["oi_change_status"], "OK")

    def test_grid_shift(self):
        # Zero shared (expiration, strike, right) keys -> GRID_SHIFT.
        day = _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                       "open_interest": 400}])
        prior = _chain([{"expiration": EXP, "strike": 99.78, "right": "C",
                         "open_interest": 400}])
        fields = oi_change_fields(day, prior, 1, expiration=EXP,
                                  strike=100.0, right="C")
        self.assertEqual(fields["oi_change_status"], "GRID_SHIFT")

    def test_low_base_boundary_inclusive(self):
        # prior OI 99 -> LOW_BASE; prior OI 100 -> OK (>= MIN_BASE).
        self.assertEqual(config.OI_CHANGE_MIN_BASE, 100)
        below = self._fields(500, config.OI_CHANGE_MIN_BASE - 1)
        self.assertEqual(below["oi_change_status"], "LOW_BASE")
        at = self._fields(500, config.OI_CHANGE_MIN_BASE)
        self.assertEqual(at["oi_change_status"], "OK")
        self.assertEqual(at["oi_delta_1d"], 400)

    def test_status_precedence_stale_beats_grid_shift(self):
        # Simultaneously stale AND grid-shifted: STALE_PRIOR_CHAIN wins
        # (check order NO_PRIOR_CHAIN -> STALE -> GRID_SHIFT -> ...).
        day = _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                       "open_interest": 400}])
        prior = _chain([{"expiration": EXP, "strike": 55.5, "right": "C",
                         "open_interest": 400}])
        fields = oi_change_fields(
            day, prior, config.OI_CHANGE_MAX_PRIOR_GAP_DAYS + 3,
            expiration=EXP, strike=100.0, right="C")
        self.assertEqual(fields["oi_change_status"], "STALE_PRIOR_CHAIN")


class FindPriorChainTest(unittest.TestCase):
    def _write(self, cache: Path, symbol: str, day: str, oi: int = 400) -> None:
        _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                 "open_interest": oi}]).to_parquet(
            cache / f"{symbol}_{day}.parquet")

    def test_picks_latest_strictly_before_day(self):
        with TemporaryDirectory() as tmp:
            cache = Path(tmp)
            self._write(cache, "VST", "2026-07-20", oi=10)
            self._write(cache, "VST", "2026-07-22", oi=20)
            self._write(cache, "VST", "2026-07-23", oi=30)  # same day, skip
            self._write(cache, "VST", "2026-07-25", oi=40)  # future, skip
            result = find_prior_chain("VST", "2026-07-23", cache_dir=str(cache))
            assert result is not None
            prior_day, frame = result
            self.assertEqual(prior_day, "2026-07-22")
            self.assertEqual(int(frame["open_interest"].iloc[0]), 20)

    def test_none_when_empty(self):
        with TemporaryDirectory() as tmp:
            self.assertIsNone(
                find_prior_chain("VST", "2026-07-23", cache_dir=tmp))

    def test_none_when_only_same_and_future(self):
        with TemporaryDirectory() as tmp:
            cache = Path(tmp)
            self._write(cache, "VST", "2026-07-23")
            self._write(cache, "VST", "2026-07-24")
            self.assertIsNone(
                find_prior_chain("VST", "2026-07-23", cache_dir=str(cache)))


def _card(strike: float, expiry: str, leader: bool) -> dict:
    return {"strike": strike, "expiry": expiry, "dte": 27,
            "annualized_yield": 0.42, "grades": {"liquidity": "GREEN"},
            "verdict": "a promise stated in dollars", "rank_leader": leader}


class AttachOiChangeTest(unittest.TestCase):
    NEW_KEYS = ("oi_delta_1d", "oi_change_status", "oi_change_line")

    def test_board_invariance(self):
        chain_day = _chain([
            {"expiration": EXP, "strike": 100.0, "right": "C",
             "open_interest": 1500},
            {"expiration": EXP, "strike": 110.0, "right": "C",
             "open_interest": 900},
        ])
        cards = [_card(100.0, EXP, True), _card(110.0, EXP, False)]
        before = copy.deepcopy(cards)
        with TemporaryDirectory() as tmp:
            cache = Path(tmp)
            _chain([
                {"expiration": EXP, "strike": 100.0, "right": "C",
                 "open_interest": 1088},
                {"expiration": EXP, "strike": 110.0, "right": "C",
                 "open_interest": 900},
            ]).to_parquet(cache / "VST_2026-08-01.parquet")
            attach_oi_change(cards, right="C", chain_day=chain_day,
                             symbol="VST", day="2026-08-02",
                             cache_dir=str(cache))
        # (a) order identical, (c) rank_leader flags unchanged.
        self.assertEqual([c["strike"] for c in cards],
                         [b["strike"] for b in before])
        self.assertEqual([c["rank_leader"] for c in cards],
                         [b["rank_leader"] for b in before])
        # (b) every pre-existing key/value byte-identical after stripping the
        # three new keys.
        for card, base in zip(cards, before):
            stripped = {k: v for k, v in card.items() if k not in self.NEW_KEYS}
            self.assertEqual(stripped, base)
        # The line was actually attached and computed.
        self.assertEqual(cards[0]["oi_change_status"], "OK")
        self.assertEqual(cards[0]["oi_delta_1d"], 412)
        self.assertEqual(cards[0]["oi_change_line"],
                         "OI Δ1d: +412 contracts (as of prior close)")
        self.assertEqual(cards[1]["oi_delta_1d"], 0)

    def test_empty_list_is_noop(self):
        with TemporaryDirectory() as tmp:
            attach_oi_change([], right="C", chain_day=_chain([]),
                             symbol="VST", day="2026-08-02", cache_dir=tmp)

    def test_causality_ignores_future_dated_file(self):
        # A parquet dated AFTER `day` must never be read (no look-ahead).
        # With only a future file present, the prior chain is absent.
        chain_day = _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                             "open_interest": 1500}])
        cards = [_card(100.0, EXP, True)]
        with TemporaryDirectory() as tmp:
            cache = Path(tmp)
            _chain([{"expiration": EXP, "strike": 100.0, "right": "C",
                     "open_interest": 1}]).to_parquet(
                cache / "VST_2026-08-05.parquet")
            attach_oi_change(cards, right="C", chain_day=chain_day,
                             symbol="VST", day="2026-08-02",
                             cache_dir=str(cache))
        self.assertEqual(cards[0]["oi_change_status"], "NO_PRIOR_CHAIN")
        self.assertIsNone(cards[0]["oi_delta_1d"])


class TopPicksInvarianceTest(unittest.TestCase):
    """Merge blocker from the ratified brief: Top-3 selection must be
    byte-identical with the OI fields present vs. absent on every card."""

    @staticmethod
    def _pick_card(strike: float, expiry: str, *, rank_leader: bool,
                   annualized_yield: float) -> dict:
        return {"strike": strike, "expiry": expiry, "dte": 45,
                "rank_leader": rank_leader,
                "grades": {"yield": "GREEN", "liquidity": "GREEN"},
                "credit": 200.0, "annualized_yield": annualized_yield}

    def _data(self) -> dict:
        return {"symbols": [
            {"symbol": "AAA", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [
                 {"kind": "put", "title": "P", "empty": None, "cards": [
                     self._pick_card(95.0, EXP, rank_leader=True,
                                     annualized_yield=0.30),
                     self._pick_card(90.0, EXP, rank_leader=False,
                                     annualized_yield=0.50),
                 ]},
             ]},
        ]}

    def test_top_picks_identical_with_and_without_oi_fields(self):
        from options_researcher import attractiveness_dashboard as ad

        plain = ad.select_top_picks(self._data(), n=3)
        self.assertTrue(plain)  # a vacuous empty-vs-empty pass proves nothing
        with_fields = self._data()
        for sec in with_fields["symbols"]:
            for grp in sec["groups"]:
                for card in grp["cards"]:
                    card["oi_delta_1d"] = 412
                    card["oi_change_status"] = "OK"
                    card["oi_change_line"] = (
                        "OI Δ1d: +412 contracts (as of prior close)")
        decorated = ad.select_top_picks(with_fields, n=3)
        # Same picks, same order, same scores -- compare everything except the
        # embedded card dict (which by construction carries the new keys).
        strip = [{k: v for k, v in p.items() if k != "card"} for p in plain]
        strip_dec = [{k: v for k, v in p.items() if k != "card"}
                     for p in decorated]
        self.assertEqual(strip, strip_dec)


class ConstantsPinnedTest(unittest.TestCase):
    def test_ratified_values(self):
        self.assertEqual(config.OI_CHANGE_MIN_BASE, 100)
        self.assertEqual(config.OI_CHANGE_MAX_PRIOR_GAP_DAYS, 4)
        self.assertEqual(config.OI_CHANGE_PCTL_WINDOW, 252)
        self.assertEqual(config.OI_CHANGE_PCT_MIN_OBS, 126)
        self.assertEqual(config.OI_CHANGE_NOTABLE_PCTL, 0.95)


if __name__ == "__main__":
    unittest.main()
