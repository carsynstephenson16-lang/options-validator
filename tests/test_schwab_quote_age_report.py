"""Brief 32 -- descriptive quote-age sidecar for Schwab chain captures.

The report is display-only: no threshold, no gate, no GO/NO_GO effect. These
tests pin the statistics, the honest-semantics/authority fields, the lane-safe
filename, and the overwrite guard's two branches.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from data import recent_topup
from options_researcher import schwab_quote_age_report as quote_age

SESSION = "2026-08-10"


def _row(
    *,
    right: str,
    expiration: str,
    strike: float,
    bid: float,
    ask: float,
    open_interest: int,
    delta: float,
    timestamp: str | None,
    trade_timestamp: str | None,
) -> dict:
    return {
        "expiration": expiration,
        "strike": strike,
        "right": right,
        "contract_symbol": f"AAA-{expiration}-{right}-{strike:g}",
        "bid": bid,
        "ask": ask,
        "open_interest": open_interest,
        "iv": 0.30,
        "delta": delta,
        "gamma": 0.02,
        "theta": -0.03,
        "vega": 0.10,
        "multiplier": 100.0,
        "non_standard": False,
        "mini": False,
        "timestamp": pd.Timestamp(timestamp) if timestamp else pd.NaT,
        "trade_timestamp": pd.Timestamp(trade_timestamp) if trade_timestamp else pd.NaT,
    }


def synthetic_frame() -> pd.DataFrame:
    """Six rows: three selectable, both timestamp columns, nulls, prior day.

    The reference for both columns is the 19:45:00Z maximum, so every age below
    is exactly computable by hand -- see the asserted values in test one.
    """
    rows = [
        # selectable (liquid, |delta| in band)
        _row(
            right="C",
            expiration="2026-08-21",
            strike=100.0,
            bid=1.00,
            ask=1.05,
            open_interest=500,
            delta=0.40,
            timestamp="2026-08-10T19:45:00Z",
            trade_timestamp="2026-08-10T19:44:00Z",
        ),
        _row(
            right="P",
            expiration="2026-08-21",
            strike=100.0,
            bid=1.00,
            ask=1.05,
            open_interest=500,
            delta=-0.40,
            timestamp="2026-08-10T19:44:00Z",
            trade_timestamp=None,
        ),
        _row(
            right="C",
            expiration="2026-09-18",
            strike=105.0,
            bid=1.00,
            ask=1.05,
            open_interest=500,
            delta=0.35,
            timestamp="2026-08-10T19:40:00Z",
            trade_timestamp="2026-08-07T19:00:00Z",  # prior session
        ),
        # not selectable: spread blown out
        _row(
            right="P",
            expiration="2026-09-18",
            strike=105.0,
            bid=1.00,
            ask=1.50,
            open_interest=500,
            delta=-0.40,
            timestamp="2026-08-10T13:30:00Z",
            trade_timestamp="2026-08-10T19:30:00Z",
        ),
        # not selectable: open interest below the floor
        _row(
            right="C",
            expiration="2026-08-21",
            strike=110.0,
            bid=1.00,
            ask=1.05,
            open_interest=10,
            delta=0.30,
            timestamp="2026-08-10T19:35:00Z",
            trade_timestamp=None,
        ),
        # not selectable: |delta| outside the band
        _row(
            right="C",
            expiration="2026-08-21",
            strike=50.0,
            bid=1.00,
            ask=1.05,
            open_interest=500,
            delta=0.95,
            timestamp="2026-08-10T19:45:00Z",
            trade_timestamp="2026-08-10T19:45:00Z",
        ),
    ]
    return pd.DataFrame(rows)


def boundary_frame() -> pd.DataFrame:
    """Rows placed exactly on the selectability boundaries, for anti-drift.

    A "does the count match" test only discriminates if the fixture straddles
    every decision the mask makes. Each row below is here to make one specific
    realistic drift in data/recent_topup.py's private default mask show up as a
    divergence; a plausible fixture of ordinary mid-band contracts catches none
    of them. Baseline: five selectable rows (1, 3, 4, 8, 10).

    1.  open_interest EXACTLY at MIN_OPEN_INTEREST  -> catches `>=` weakened to `>`
    2.  open_interest one below the floor            (stays out either way)
    3.  |delta| EXACTLY at the low band edge       -> catches a band narrowing
    4.  |delta| EXACTLY at the high band edge      -> catches a band narrowing
    5.  |delta| just below the low edge              (stays out either way)
    6.  |delta| just above the high edge             (stays out either way)
    7.  spread straddling the mid-vs-ask denominator choice
                                                   -> catches (ask-bid)/ask
    8.  wide ABSOLUTE spread but narrow percentage -> catches an abs-dollar gate
    9.  bid = 0, narrow absolute spread            -> catches an abs-dollar gate
    10. zero spread                                  (boundary sanity)
    """
    common = {
        "timestamp": "2026-08-10T19:45:00Z",
        "trade_timestamp": "2026-08-10T19:44:00Z",
        "expiration": "2026-08-21",
    }
    specs = [
        # (strike, right, bid, ask, open_interest, delta)
        (100.0, "C", 1.00, 1.05, 100, 0.40),
        (101.0, "C", 1.00, 1.05, 99, 0.40),
        (102.0, "C", 1.00, 1.05, 500, 0.15),
        (103.0, "P", 1.00, 1.05, 500, -0.85),
        (104.0, "C", 1.00, 1.05, 500, 0.14),
        (105.0, "P", 1.00, 1.05, 500, -0.86),
        (106.0, "C", 0.90, 1.00, 500, 0.40),
        (107.0, "C", 10.00, 10.40, 500, 0.40),
        (108.0, "C", 0.00, 0.05, 500, 0.40),
        (109.0, "C", 2.00, 2.00, 500, 0.40),
    ]
    return pd.DataFrame(
        [
            _row(
                right=right,
                strike=strike,
                bid=bid,
                ask=ask,
                open_interest=open_interest,
                delta=delta,
                **common,
            )
            for strike, right, bid, ask, open_interest, delta in specs
        ]
    )


class SyntheticPackage:
    """A tmp chain dir + reports dir holding one synthetic AAA package."""

    def __init__(self, root: Path, frame: pd.DataFrame | None = None) -> None:
        self.root = root
        self.chain_dir = root / "chains"
        self.reports_dir = root / "reports"
        self.chain_dir.mkdir(parents=True, exist_ok=True)
        self.write(frame if frame is not None else synthetic_frame())

    def write(self, frame: pd.DataFrame) -> None:
        frame.to_parquet(self.chain_dir / f"AAA_{SESSION}.parquet", index=False)


class QuoteAgeStatisticsTests(unittest.TestCase):
    def test_synthetic_package_reports_both_columns_and_both_populations(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = SyntheticPackage(Path(tmp))
            report = quote_age.build_report(
                session=SESSION,
                symbols=["AAA"],
                chain_dir=package.chain_dir,
                manifest_hash="golden-manifest-hash",
            )

        # Authority pair is the repo's machine-checked one, verbatim.
        self.assertIs(report["display_only"], True)
        self.assertIs(report["verdict_eligible"], False)
        self.assertIn("WITHIN-PACKAGE DISPERSION", report["semantics"])
        self.assertIn("reads as fresh", report["semantics"])
        self.assertEqual(report["schema_version"], "schwab_quote_age_report/v1")
        self.assertEqual(report["session"], SESSION)
        self.assertEqual(report["max_as_of_session"], SESSION)
        self.assertEqual(report["manifest_hash"], "golden-manifest-hash")
        self.assertEqual(
            report["selectable_definition"]["abs_delta_band"],
            list(quote_age.SELECTABLE_ABS_DELTA),
        )

        symbol = report["symbols"]["AAA"]
        self.assertEqual(symbol["row_count"], 6)
        self.assertEqual(symbol["selectable_row_count"], 3)

        quote = symbol["columns"]["timestamp"]
        self.assertEqual(quote["age_reference_utc"], "2026-08-10T19:45:00+00:00")
        self.assertEqual(
            quote["all_rows"],
            {
                "row_count": 6,
                "null_count": 0,
                "min_utc": "2026-08-10T13:30:00+00:00",
                "max_utc": "2026-08-10T19:45:00+00:00",
                "prior_session_rows": 0,
                "after_session_rows": 0,
                "age_minutes": {"p50": 3.0, "p90": 192.5, "max": 375.0},
            },
        )
        self.assertEqual(
            quote["selectable"],
            {
                "row_count": 3,
                "null_count": 0,
                "min_utc": "2026-08-10T19:40:00+00:00",
                "max_utc": "2026-08-10T19:45:00+00:00",
                "prior_session_rows": 0,
                "after_session_rows": 0,
                "age_minutes": {"p50": 1.0, "p90": 4.2, "max": 5.0},
            },
        )

        trade = symbol["columns"]["trade_timestamp"]
        self.assertEqual(trade["age_reference_utc"], "2026-08-10T19:45:00+00:00")
        self.assertEqual(
            trade["all_rows"],
            {
                "row_count": 6,
                "null_count": 2,
                "min_utc": "2026-08-07T19:00:00+00:00",
                "max_utc": "2026-08-10T19:45:00+00:00",
                "prior_session_rows": 1,
                "after_session_rows": 0,
                "age_minutes": {"p50": 8.0, "p90": 3060.0, "max": 4365.0},
            },
        )
        self.assertEqual(
            trade["selectable"],
            {
                "row_count": 3,
                "null_count": 1,
                "min_utc": "2026-08-07T19:00:00+00:00",
                "max_utc": "2026-08-10T19:44:00+00:00",
                "prior_session_rows": 1,
                "after_session_rows": 0,
                "age_minutes": {"p50": 2183.0, "p90": 3928.6, "max": 4365.0},
            },
        )

        # One symbol, so the package block mirrors it row-for-row.
        package_block = report["package"]
        self.assertEqual(package_block["symbol_count"], 1)
        self.assertEqual(package_block["row_count"], 6)
        self.assertEqual(package_block["selectable_row_count"], 3)
        self.assertEqual(package_block["columns"]["timestamp"]["all_rows"], quote["all_rows"])
        self.assertEqual(
            package_block["columns"]["trade_timestamp"]["selectable"],
            trade["selectable"],
        )

    def test_all_rows_and_selectable_are_reported_apart_not_blended(self):
        """The whole point of two populations: the numbers must differ."""
        with tempfile.TemporaryDirectory() as tmp:
            package = SyntheticPackage(Path(tmp))
            report = quote_age.build_report(
                session=SESSION, symbols=["AAA"], chain_dir=package.chain_dir
            )
        column = report["symbols"]["AAA"]["columns"]["timestamp"]
        self.assertGreater(
            column["all_rows"]["age_minutes"]["max"],
            column["selectable"]["age_minutes"]["max"],
        )

    def test_selectable_mask_matches_the_recent_topup_default_audit_mask(self):
        """Anti-drift: the inline mask must stay equal to the source of truth.

        data/recent_topup.py's default mask is private (`_liquid_mask`) and
        that file is out of scope for this brief, so the definition is
        duplicated in the report module -- and pinned here, against
        recent_topup's PUBLIC audit_chain.

        Two levels of comparison, because a bare whole-frame count is weak:
        a one-row frame's `selectable` count IS that row's mask value, so
        looping gives an ELEMENT-WISE comparison through the public API and
        catches drifts that would leave the total unchanged. The boundary
        fixture supplies rows that straddle every decision the mask makes;
        see its docstring for which drift each row is there to catch.
        """
        self.assertEqual(quote_age.SELECTABLE_ABS_DELTA, recent_topup.SELECTABLE_ABS_DELTA)
        fixtures = (
            ("statistics fixture", synthetic_frame(), 3),
            ("boundary fixture", boundary_frame(), 5),
        )
        for label, frame, expected_selectable in fixtures:
            with self.subTest(fixture=label):
                mine = quote_age.selectable_mask(frame)

                # The fixture must actually discriminate, not pass vacuously.
                self.assertEqual(int(mine.sum()), expected_selectable)
                self.assertGreater(int(mine.sum()), 0)
                self.assertLess(int(mine.sum()), len(frame))

                self.assertEqual(int(mine.sum()), recent_topup.audit_chain(frame)["selectable"])
                self.assertEqual(
                    [int(value) for value in mine.tolist()],
                    [
                        int(recent_topup.audit_chain(frame.iloc[[position]])["selectable"])
                        for position in range(len(frame))
                    ],
                )

    def test_report_is_deterministic_and_carries_no_wall_clock_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = SyntheticPackage(Path(tmp))
            first = quote_age.build_report(
                session=SESSION, symbols=["AAA"], chain_dir=package.chain_dir
            )
            second = quote_age.build_report(
                session=SESSION, symbols=["AAA"], chain_dir=package.chain_dir
            )
        self.assertEqual(quote_age.report_text(first), quote_age.report_text(second))


class QuoteAgeSidecarNamingTests(unittest.TestCase):
    def test_filename_derives_from_the_receipt_stem_so_lanes_cannot_collide(self):
        self.assertEqual(quote_age.sidecar_filename("preclose.json"), "preclose.quote_age.json")
        self.assertEqual(quote_age.sidecar_filename("midday.json"), "midday.quote_age.json")
        self.assertNotEqual(
            quote_age.sidecar_path(Path("reports"), SESSION, "preclose.json"),
            quote_age.sidecar_path(Path("reports"), SESSION, "midday.json"),
        )
        self.assertEqual(
            quote_age.sidecar_path(Path("reports"), SESSION, "preclose.json"),
            Path("reports") / SESSION / "preclose.quote_age.json",
        )

    def test_a_receipt_filename_with_a_path_component_is_refused(self):
        for bad in ("sub/preclose.json", ".json", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(quote_age.SchwabQuoteAgeReportError):
                    quote_age.sidecar_filename(bad)


class QuoteAgeOverwriteGuardTests(unittest.TestCase):
    def _write(self, package: SyntheticPackage) -> Path:
        return quote_age.write_quote_age_report(
            session=SESSION,
            symbols=["AAA"],
            chain_dir=package.chain_dir,
            reports_dir=package.reports_dir,
            receipt_filename="preclose.json",
        )

    def test_identical_rewrite_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = SyntheticPackage(Path(tmp))
            path = self._write(package)
            self.assertTrue(path.is_file())
            first_bytes = path.read_bytes()

            with mock.patch.object(quote_age, "atomic_text_write") as writer:
                again = self._write(package)

            writer.assert_not_called()
            self.assertEqual(again, path)
            self.assertEqual(path.read_bytes(), first_bytes)
            self.assertIs(json.loads(path.read_text())["verdict_eligible"], False)

    def test_differing_rewrite_refuses_and_leaves_the_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = SyntheticPackage(Path(tmp))
            path = self._write(package)
            original = path.read_bytes()

            changed = synthetic_frame()
            changed.loc[0, "timestamp"] = pd.Timestamp("2026-08-10T19:59:00Z")
            package.write(changed)

            with self.assertRaises(FileExistsError):
                self._write(package)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
