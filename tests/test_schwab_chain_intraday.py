"""Offline tests for the durable Schwab intraday chain pulls (10:00 / 13:00 ET).

Owner-directed 2026-09-02 (in-session): "I want a pull at 10am and a pull at
1pm." The pre-close lane keys every artifact by symbol + date and is
first-write-wins, so the extra pulls MUST live in their own namespace or the
15:45 capture would refuse to overwrite them and lose that day's H7 evidence.
Every test below is a guard on that isolation, on the preclose path staying
byte-identical, and on the ops plumbing (plist, wrapper, ritual commit paths,
alignment gate, irreplaceable-data guard, job-health digest) knowing the new
namespace exists.
"""

from __future__ import annotations

import io
import json
import plistlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

import config
from options_researcher import h7_schwab_window_registration as h7_reg
from options_researcher import intraday_capture as ic
from options_researcher import schwab_chain_capture as capture
from options_researcher import schwab_chain_view as chain_view
from tools import chain_consistency_audit
from tools import irreplaceable_data_guard as guard
from tools import job_health_digest as digest
from tools.schwab_chain_manifest import SchwabChainManifestError, verify_session

NY = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[1]
PRECLOSE_WRAPPER = ROOT / "tools" / "schwab_chain_capture.sh"
INTRADAY_WRAPPER = ROOT / "tools" / "schwab_chain_intraday_capture.sh"
INTRADAY_PLIST = (
    ROOT / "tools" / "launchagents" / "com.carsyn.options-validator.schwab-chain-intraday.plist"
)
PRECLOSE_PLIST = (
    ROOT / "tools" / "launchagents" / "com.carsyn.options-validator.schwab-chain-preclose.plist"
)
ALIGNMENT_PLIST = (
    ROOT / "tools" / "launchagents" / "com.carsyn.options-validator.alignment-check.plist"
)


def at(hh: int, mm: int, day: str = "2026-09-02") -> datetime:
    return datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}:00").replace(tzinfo=NY)


def _full_frame() -> pd.DataFrame:
    # Local copy of tests/test_schwab_chain_capture.py's fixture: CI runs
    # `unittest discover -s tests` with no `tests` package on sys.path, so a
    # cross-module `from tests.… import` fails there (PR #150 CI run
    # 33643183119) even though it works from the repo root locally.
    rows = []
    for expiration in ("2026-08-21", "2026-09-18"):
        for right, delta in (("C", 0.4), ("P", -0.4)):
            rows.append(
                {
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": right,
                    "contract_symbol": f"AAA-{expiration}-{right}-100",
                    "bid": 1.0,
                    "ask": 1.2,
                    "open_interest": 100,
                    "implied_vol": 0.30,
                    "delta": delta,
                    "gamma": 0.02,
                    "theta": -0.03,
                    "vega": 0.10,
                    "multiplier": 100.0,
                    "non_standard": False,
                    "mini": False,
                    "timestamp": pd.Timestamp("2026-08-10T19:44:30Z"),
                    "trade_timestamp": pd.Timestamp("2026-08-10T19:44:20Z"),
                }
            )
    return pd.DataFrame(rows)


class FakeClient:
    provider_name = "schwab"
    provider_version = "test"

    def __init__(self):
        self.calls = []

    def option_full_chain(self, symbol):
        self.calls.append(symbol)
        return _full_frame()


class ScheduleTableTests(unittest.TestCase):
    def test_config_freezes_the_two_owner_typed_intraday_pull_times(self):
        self.assertEqual(
            config.SCHWAB_CHAIN_INTRADAY_TIMES,
            {"morning": "10:00", "midday": "13:00"},
        )

    def test_intraday_table_never_collides_with_the_preclose_tag(self):
        # "preclose" stays exclusively the 15:45 durable lane; the display
        # lane's INTRADAY_CAPTURE_TIMES is untouched (its consumers enumerate
        # it and would report a phantom missing slot otherwise).
        self.assertNotIn("preclose", config.SCHWAB_CHAIN_INTRADAY_TIMES)
        self.assertNotIn("morning", config.INTRADAY_CAPTURE_TIMES)
        self.assertEqual(config.INTRADAY_CAPTURE_TIMES["preclose"], "15:45")

    def test_validate_session_tag_accepts_an_alternate_schedule(self):
        schedule = capture.INTRADAY_SESSION_TIMES
        ok, reason = ic.validate_session_tag("morning", at(10, 4), schedule=schedule)
        self.assertTrue(ok, reason)
        ok, reason = ic.validate_session_tag("morning", at(10, 25), schedule=schedule)
        self.assertFalse(ok)
        self.assertIn("10:00", reason)
        # The default schedule still does not know the new tag.
        self.assertFalse(ic.validate_session_tag("morning", at(10, 0))[0])

    def test_nearest_session_tag_accepts_an_alternate_schedule(self):
        schedule = capture.INTRADAY_SESSION_TIMES
        self.assertEqual(ic.nearest_session_tag(at(12, 55), schedule=schedule), "midday")
        self.assertIsNone(ic.nearest_session_tag(at(11, 30), schedule=schedule))


class NearestCaptureTagTests(unittest.TestCase):
    def test_wall_clock_resolves_each_durable_slot(self):
        self.assertEqual(capture.nearest_capture_tag(at(10, 0)), "morning")
        self.assertEqual(capture.nearest_capture_tag(at(10, 9)), "morning")
        self.assertEqual(capture.nearest_capture_tag(at(13, 2)), "midday")
        self.assertEqual(capture.nearest_capture_tag(at(15, 45)), "preclose")
        self.assertEqual(capture.nearest_capture_tag(at(15, 52)), "preclose")

    def test_wall_clock_outside_every_tolerance_resolves_to_none(self):
        self.assertIsNone(capture.nearest_capture_tag(at(10, 20)))
        self.assertIsNone(capture.nearest_capture_tag(at(11, 30)))
        self.assertIsNone(capture.nearest_capture_tag(at(16, 10)))

    def test_tags_restriction_can_never_resolve_to_preclose(self):
        intraday = ("morning", "midday")
        # A missed 13:00 fire delivered inside the pre-close window.
        self.assertIsNone(capture.nearest_capture_tag(at(15, 45), tags=intraday))
        self.assertIsNone(capture.nearest_capture_tag(at(15, 40), tags=intraday))
        self.assertEqual(capture.nearest_capture_tag(at(13, 0), tags=intraday), "midday")
        self.assertEqual(capture.nearest_capture_tag(at(10, 5), tags=intraday), "morning")
        with self.assertRaises(ValueError):
            capture.nearest_capture_tag(at(13, 0), tags=("midday", "midmorning"))
        with self.assertRaises(ValueError):
            capture.nearest_capture_tag(at(13, 0), tags=())
        # The isolation guarantee lives in the module, not only in the
        # wrapper's grep: a restricted list can never smuggle "preclose".
        with self.assertRaises(ValueError):
            capture.nearest_capture_tag(at(15, 45), tags=("morning", "midday", "preclose"))

    def test_cli_tags_restriction_prints_none_inside_the_preclose_window(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = capture.main(
                ["--print-nearest-tag", "--tags", "morning,midday"], now_ny=at(15, 45)
            )
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip().splitlines()[-1], "NONE")

    def test_cli_helper_prints_tag_or_none_sentinel(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = capture.main(["--print-nearest-tag"], now_ny=at(13, 0))
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip().splitlines()[-1], "midday")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = capture.main(["--print-nearest-tag"], now_ny=at(11, 30))
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip().splitlines()[-1], "NONE")


class IntradayNamespaceTests(unittest.TestCase):
    def test_kwargs_isolate_every_artifact_from_the_preclose_namespace(self):
        kwargs = capture.intraday_capture_kwargs("morning")
        self.assertEqual(kwargs["chain_dir"], Path(".cache/schwab_chains_intraday/morning"))
        self.assertEqual(kwargs["reports_dir"], Path("reports/schwab_chains_intraday/morning"))
        self.assertEqual(kwargs["session_tag"], "morning")
        self.assertEqual(kwargs["receipt_filename"], "morning.json")
        self.assertEqual(kwargs["receipt_kind"], "schwab_chain_capture_intraday/v1")
        self.assertEqual(kwargs["convention"], "intraday_snapshot_v1")
        self.assertEqual(kwargs["fact_prefix"], "SCHWAB_INTRADAY_CHAIN_CAPTURE tag=morning")
        self.assertIs(kwargs["schedule"], capture.INTRADAY_SESSION_TIMES)
        # None of the preclose identity values leak through.
        self.assertNotEqual(kwargs["chain_dir"], capture.CHAIN_DIR)
        self.assertNotEqual(kwargs["reports_dir"], capture.REPORTS_DIR)
        self.assertFalse(str(kwargs["chain_dir"]).startswith(str(capture.CHAIN_DIR) + "/"))

    def test_kwargs_refuse_preclose_and_unknown_tags(self):
        with self.assertRaises(ValueError):
            capture.intraday_capture_kwargs("preclose")
        with self.assertRaises(ValueError):
            capture.intraday_capture_kwargs("midmorning")


class IntradayCaptureFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.preclose_chain_dir = self.root / "chains"
        self.preclose_reports_dir = self.root / "reports"
        self.intraday_root = self.root / "intraday"

    def _intraday(self, tag: str, now_ny: datetime, client=None):
        kwargs = capture.intraday_capture_kwargs(tag)
        kwargs["chain_dir"] = self.intraday_root / "cache" / tag
        kwargs["reports_dir"] = self.intraday_root / "reports" / tag
        with mock.patch.object(capture, "FACTS_DIR", self.root / "ledger", create=True):
            return capture.capture(
                client=client or FakeClient(),
                now_ny=now_ny,
                universe=["AAA", "BBB"],
                force=False,
                **kwargs,
            )

    def _preclose(self, now_ny: datetime):
        with mock.patch.object(capture, "FACTS_DIR", self.root / "ledger", create=True):
            return capture.capture(
                client=FakeClient(),
                now_ny=now_ny,
                universe=["AAA", "BBB"],
                chain_dir=self.preclose_chain_dir,
                reports_dir=self.preclose_reports_dir,
                force=False,
            )

    def test_morning_capture_writes_isolated_package_that_verifies(self):
        exit_code, receipt = self._intraday("morning", at(10, 1))

        self.assertEqual(exit_code, 0)
        assert receipt is not None
        chain_dir = self.intraday_root / "cache" / "morning"
        reports_dir = self.intraday_root / "reports" / "morning" / "2026-09-02"
        self.assertTrue((chain_dir / "AAA_2026-09-02.parquet").is_file())
        self.assertTrue((reports_dir / "manifest.json").is_file())
        self.assertTrue((reports_dir / "morning.json").is_file())
        self.assertEqual(receipt["receipt_kind"], "schwab_chain_capture_intraday/v1")
        self.assertEqual(receipt["scheduled_session_tag"], "morning")
        self.assertEqual(receipt["session_chain_convention"], "intraday_snapshot_v1")
        self.assertEqual(receipt["overall_status"], "ok")
        verified = verify_session(
            "2026-09-02",
            ["AAA", "BBB"],
            chain_dir,
            reports_dir / "manifest.json",
            reports_dir / "morning.json",
            convention="intraday_snapshot_v1",
            receipt_filename="morning.json",
            session_tag="morning",
            receipt_kind="schwab_chain_capture_intraday/v1",
            schedule=capture.INTRADAY_SESSION_TIMES,
        )
        self.assertEqual(verified["session_chain_convention"], "intraday_snapshot_v1")
        # Nothing landed in the preclose namespace.
        self.assertFalse(self.preclose_chain_dir.exists())
        self.assertFalse(self.preclose_reports_dir.exists())

    def test_intraday_package_never_verifies_as_preclose_evidence(self):
        self._intraday("morning", at(10, 1))
        chain_dir = self.intraday_root / "cache" / "morning"
        reports_dir = self.intraday_root / "reports" / "morning" / "2026-09-02"
        with self.assertRaises(SchwabChainManifestError):
            verify_session(
                "2026-09-02",
                ["AAA", "BBB"],
                chain_dir,
                reports_dir / "manifest.json",
                reports_dir / "morning.json",
            )

    def test_morning_refuses_outside_its_own_tolerance(self):
        client = FakeClient()
        exit_code, receipt = self._intraday("morning", at(10, 30), client=client)
        self.assertEqual(exit_code, 1)
        self.assertIsNone(receipt)
        self.assertEqual(client.calls, [])

    def test_three_pulls_on_one_day_coexist_without_conflict(self):
        self.assertEqual(self._intraday("morning", at(10, 0))[0], 0)
        self.assertEqual(self._intraday("midday", at(13, 0))[0], 0)
        self.assertEqual(self._preclose(at(15, 45))[0], 0)
        facts = (self.root / "ledger" / "facts.log").read_text().splitlines()
        prefixes = sorted(line.split("\t", 1)[1].split(" session=")[0] for line in facts)
        self.assertEqual(
            prefixes,
            [
                "SCHWAB_CHAIN_CAPTURE",
                "SCHWAB_INTRADAY_CHAIN_CAPTURE tag=midday",
                "SCHWAB_INTRADAY_CHAIN_CAPTURE tag=morning",
            ],
        )

    def test_intraday_parquet_dropped_into_preclose_dir_breaks_preclose_verification(self):
        # Brief 30 WP-E.2(a): the pre-close verifier's exact-set glob must
        # refuse a same-date foreign file, so cross-namespace leakage is loud.
        self.assertEqual(self._preclose(at(15, 45))[0], 0)
        self.assertEqual(self._intraday("morning", at(10, 0))[0], 0)
        stray = self.intraday_root / "cache" / "morning" / "AAA_2026-09-02.parquet"
        shutil.copyfile(stray, self.preclose_chain_dir / "ZZZ_2026-09-02.parquet")
        with self.assertRaises(SchwabChainManifestError):
            verify_session(
                "2026-09-02",
                ["AAA", "BBB"],
                self.preclose_chain_dir,
                self.preclose_reports_dir / "2026-09-02" / "manifest.json",
                self.preclose_reports_dir / "2026-09-02" / "preclose.json",
            )

    def test_registered_consumers_still_point_at_the_preclose_namespace_only(self):
        # Blindness pins (Brief 30 WP-E.3): every pre-close consumer keeps
        # its own literal path, none of which is under the intraday tree.
        self.assertEqual(chain_view.CHAIN_DIR, Path(".cache/schwab_chains"))
        self.assertEqual(chain_view.REPORTS_DIR, Path("reports/schwab_chains"))
        self.assertEqual(chain_consistency_audit.DEFAULT_CHAIN_DIR, Path(".cache/schwab_chains"))
        self.assertEqual(h7_reg.CACHE_NAMESPACE, ".cache/schwab_chains/")
        self.assertEqual(capture.CHAIN_DIR, Path(".cache/schwab_chains"))
        self.assertEqual(capture.REPORTS_DIR, Path("reports/schwab_chains"))

    def test_same_tag_same_day_rerun_is_first_write_wins(self):
        self.assertEqual(self._intraday("morning", at(10, 0))[0], 0)
        exit_code, _receipt = self._intraday("morning", at(10, 3))
        self.assertEqual(exit_code, 2)


class CliRoutingTests(unittest.TestCase):
    def test_default_and_explicit_preclose_use_the_untouched_defaults(self):
        for argv in ([], ["--session-tag", "preclose"]):
            with self.subTest(argv=argv):
                with mock.patch.object(capture, "capture", return_value=(0, None)) as run:
                    self.assertEqual(capture.main(argv), 0)
                run.assert_called_once_with(force=False)

    def test_intraday_tag_routes_to_the_isolated_namespace(self):
        with mock.patch.object(capture, "capture", return_value=(0, None)) as run:
            self.assertEqual(capture.main(["--session-tag", "midday"]), 0)
        run.assert_called_once_with(force=False, **capture.intraday_capture_kwargs("midday"))

    def test_unknown_tag_is_an_argparse_error(self):
        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                capture.main(["--session-tag", "midmorning"])
        self.assertEqual(raised.exception.code, 2)


class WrapperTests(unittest.TestCase):
    def test_preclose_wrapper_gains_only_the_evidence_allow_entry(self):
        source = PRECLOSE_WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("--session-tag", source)
        self.assertNotIn("--print-nearest-tag", source)
        self.assertIn(
            '"$UV" run python -m options_researcher.schwab_chain_capture 2>&1)"', source
        )
        self.assertIn("reports/schwab_chains_intraday", _evidence_allow(source))

    def test_intraday_wrapper_is_restricted_to_its_own_slots(self):
        source = INTRADAY_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("--print-nearest-tag --tags morning,midday", source)
        self.assertIn("grep -Eo '^(morning|midday|NONE)$' | tail -1", source)
        self.assertIn('--session-tag "$TAG"', source)
        self.assertNotIn("preclose|", source)
        self.assertNotIn("options_researcher.intraday_capture", source)
        self.assertNotIn("tools/intraday_capture.sh", source)

    def test_intraday_wrapper_keeps_the_preclose_gates_and_resolves_the_slot_after_them(self):
        source = INTRADAY_WRAPPER.read_text(encoding="utf-8")
        self.assertIn('if [ "$BRANCH" != "main" ]', source)
        self.assertIn("GIT_TERMINAL_PROMPT=0", source)
        self.assertIn('if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]', source)
        self.assertIn("LIVE_MARKET_DATA_PROVIDER=schwab", source)
        self.assertIn("SCHWAB_TRADING_ENABLED=false", source)
        self.assertLess(source.index("# --- end alignment gate"), source.index("--print-nearest-tag"))
        self.assertIn("reports/schwab_chains_intraday", _evidence_allow(source))
        self.assertEqual(_evidence_allow(source), _evidence_allow(PRECLOSE_WRAPPER.read_text()))

    def test_intraday_wrapper_treats_no_slot_as_a_loud_refusal_not_a_benign_skip(self):
        source = INTRADAY_WRAPPER.read_text(encoding="utf-8")
        start = source.index('if [ "$TAG" = "NONE" ]')
        block = source[start : source.index("\nfi\n", start)]
        self.assertIn("exit 1", block)
        self.assertNotIn("exit 0", block)
        self.assertIn("[BROKEN]", block)

    def test_intraday_wrapper_logs_to_its_own_directory(self):
        source = INTRADAY_WRAPPER.read_text(encoding="utf-8")
        self.assertIn('LOGDIR="$REPO/.tmp/schwab_chain_intraday"', source)
        self.assertNotIn(".tmp/schwab_chain_capture", source)

    def _run_status_tail(self, *, rc: int, cap_out: str) -> subprocess.CompletedProcess:
        source = INTRADAY_WRAPPER.read_text(encoding="utf-8")
        block = source[source.index("CRITICAL=0") :]
        script = "\n".join(
            [
                "set -u",
                "REPO=" + shlex.quote(str(ROOT)),
                "STAMP=test-stamp",
                "TAG=morning",
                "RC=" + str(rc),
                "CAP_OUT=" + shlex.quote(cap_out),
                block,
            ]
        )
        return subprocess.run(["/bin/bash", "-c", script], capture_output=True, text=True, timeout=30)

    def test_intraday_wrapper_names_the_expired_token_case_distinctly(self):
        completed = self._run_status_tail(
            rc=1, cap_out="schwab_chain_capture auth EXPIRED: Refresh token is invalid"
        )
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("CRITICAL: SCHWAB REAUTH REQUIRED", completed.stdout)

    def test_intraday_wrapper_ok_and_conflict_branches(self):
        ok = self._run_status_tail(rc=0, cap_out="schwab_chain_capture complete: 15/15 x")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("SCHWAB CHAIN STATUS: OK", ok.stdout)
        self.assertNotIn("CRITICAL", ok.stdout)
        conflict = self._run_status_tail(
            rc=2, cap_out="schwab_chain_capture receipt CONFLICT: reports/x/morning.json"
        )
        self.assertEqual(conflict.returncode, 2, conflict.stderr)
        self.assertIn("SCHWAB CHAIN RECEIPT CONFLICT", conflict.stdout)
        self.assertIn("SAME-DAY RETRY IS UNSAFE", conflict.stdout)


def _evidence_allow(source: str) -> list[str]:
    start = source.index("EVIDENCE_ALLOW=(")
    return source[start + len("EVIDENCE_ALLOW=(") : source.index(")", start)].split()


class PlistTests(unittest.TestCase):
    def test_intraday_plist_fires_its_own_wrapper_at_10_and_13_et(self):
        payload = plistlib.loads(INTRADAY_PLIST.read_bytes())
        preclose = plistlib.loads(PRECLOSE_PLIST.read_bytes())
        self.assertEqual(payload["Label"], "com.carsyn.options-validator.schwab-chain-intraday")
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                "/Users/carsynstephenson/options-validator-ops/tools/schwab_chain_intraday_capture.sh",
            ],
        )
        self.assertEqual(payload["WorkingDirectory"], preclose["WorkingDirectory"])
        self.assertEqual(payload["EnvironmentVariables"], preclose["EnvironmentVariables"])
        self.assertNotEqual(payload["StandardOutPath"], preclose["StandardOutPath"])
        self.assertNotEqual(payload["StandardErrorPath"], preclose["StandardErrorPath"])
        self.assertIn(".tmp/schwab_chain_intraday/", payload["StandardOutPath"])
        self.assertEqual(
            payload["StartCalendarInterval"],
            [
                {"Weekday": weekday, "Hour": hour, "Minute": 0}
                for weekday in range(1, 6)
                for hour in (10, 13)
            ],
        )
        self.assertFalse(payload["RunAtLoad"])
        self.assertNotIn("KeepAlive", payload)
        self.assertNotIn("tools/intraday_capture.sh", str(payload["ProgramArguments"]))

    def test_preclose_plist_is_unchanged(self):
        payload = plistlib.loads(PRECLOSE_PLIST.read_bytes())
        self.assertEqual(
            payload["StartCalendarInterval"],
            [{"Weekday": weekday, "Hour": 15, "Minute": 45} for weekday in range(1, 6)],
        )
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                "/Users/carsynstephenson/options-validator-ops/tools/schwab_chain_capture.sh",
            ],
        )

    def test_alignment_check_runs_15_minutes_before_every_durable_pull(self):
        alignment = plistlib.loads(ALIGNMENT_PLIST.read_bytes())
        checks = {
            (entry["Weekday"], entry["Hour"] * 60 + entry["Minute"])
            for entry in alignment["StartCalendarInterval"]
        }
        for plist in (PRECLOSE_PLIST, INTRADAY_PLIST):
            for entry in plistlib.loads(plist.read_bytes())["StartCalendarInterval"]:
                capture_minute = entry["Hour"] * 60 + entry["Minute"]
                self.assertIn((entry["Weekday"], capture_minute - 15), checks, entry)


class OpsPlumbingTests(unittest.TestCase):
    def test_guard_protects_both_new_namespaces(self):
        self.assertIn(".cache/schwab_chains_intraday", guard.DEFAULT_NAMESPACES)
        self.assertIn("reports/schwab_chains_intraday", guard.DEFAULT_NAMESPACES)
        self.assertIn("reports/schwab_chains_intraday", guard.TRACKED_NAMESPACES)
        inventory = json.loads((ROOT / guard.DEFAULT_INVENTORY).read_text())
        # Brief 30 WP-D.3: the gitignored cache key is recorded while absent
        # (no invented floor; the first supervised capture trips the guard's
        # "newly populated, unbaselined" refusal and the real floor is then
        # committed), and the git-tracked receipts namespace carries no floor.
        cache = inventory["namespaces"][".cache/schwab_chains_intraday"]
        self.assertEqual(cache, {"present": False, "file_count": 0, "total_bytes": 0})
        tracked = inventory["namespaces"]["reports/schwab_chains_intraday"]
        self.assertFalse(tracked["present"])
        self.assertEqual(tracked["file_count"], 0)

    def test_daily_ritual_commits_the_intraday_receipts(self):
        source = (ROOT / "tools" / "daily_ritual.sh").read_text(encoding="utf-8")
        start = source.index("DATA_TIER_PATHS=(")
        paths = source[start + len("DATA_TIER_PATHS=(") : source.index(")", start)].split()
        self.assertIn("reports/schwab_chains_intraday", paths)

    def test_alignment_check_tolerates_the_intraday_receipts(self):
        source = (ROOT / "tools" / "ops_alignment_check.sh").read_text(encoding="utf-8")
        start = source.index("EVIDENCE_ALLOW=(")
        allow = source[start + len("EVIDENCE_ALLOW=(") : source.index(")", start)].split()
        self.assertIn("reports/schwab_chains_intraday", allow)


class DigestRowTests(unittest.TestCase):
    AS_OF = "2026-08-21"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _install(self, tag: str, overall_status: str = "ok", **overrides):
        path = self.root / "reports" / "schwab_chains_intraday" / tag / self.AS_OF / f"{tag}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "receipt_kind": "schwab_chain_capture_intraday/v1",
            "session": self.AS_OF,
            "scheduled_session_tag": tag,
            "force": False,
            "overall_status": overall_status,
        }
        payload.update(overrides)
        path.write_text(json.dumps(payload) + "\n")

    def _rows(self):
        return {row.job: row for row in digest.collect_health(self.root, self.AS_OF)}

    def test_missing_receipts_report_missing_for_each_slot(self):
        rows = self._rows()
        for tag in ("morning", "midday"):
            self.assertEqual(rows[f"Schwab intraday ({tag})"].status, digest.HealthStatus.MISSING)

    def test_ok_receipt_reports_ok_and_failed_receipt_reports_failed(self):
        self._install("morning")
        self._install("midday", overall_status="failed")
        rows = self._rows()
        self.assertEqual(rows["Schwab intraday (morning)"].status, digest.HealthStatus.OK)
        self.assertEqual(rows["Schwab intraday (midday)"].status, digest.HealthStatus.FAILED)
        self.assertEqual(
            rows["Schwab intraday (morning)"].path,
            f"reports/schwab_chains_intraday/morning/{self.AS_OF}/morning.json",
        )

    def test_receipt_identity_must_match_the_slot(self):
        for field, value in (
            ("receipt_kind", "schwab_chain_capture/v1"),
            ("scheduled_session_tag", "midday"),
            ("force", True),
            ("session", "2026-08-20"),
        ):
            with self.subTest(field=field):
                self._install("morning", **{field: value})
                self.assertEqual(
                    self._rows()["Schwab intraday (morning)"].status,
                    digest.HealthStatus.FAILED,
                )

    def test_no_session_day_lists_both_slots(self):
        rows = {row.job for row in digest.collect_health(self.root, "2026-08-22")}
        self.assertIn("Schwab intraday (morning)", rows)
        self.assertIn("Schwab intraday (midday)", rows)


if __name__ == "__main__":
    unittest.main()
