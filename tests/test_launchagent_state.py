"""Offline contract tests for the advisory LaunchAgent observation."""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "com.carsyn.options-validator."


def module():
    return importlib.import_module("options_researcher.launchagent_state")


class LaunchagentStateTests(unittest.TestCase):
    def setUp(self):
        self.m = module()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.agents = self.root / "agents"
        self.agents.mkdir()

    def plist(self, relative, label):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(plistlib.dumps({"Label": label}))
        return path

    def runner(self, *, listed=(), loaded=(), disabled=(), fail=()):
        def run(argv, *, capture_output, text, check):
            self.assertEqual(argv[0], "/bin/launchctl")
            self.assertEqual((capture_output, text, check), (True, True, False))
            command = argv[1]
            if command == "list":
                self.assertEqual(len(argv), 2)
                output = "PID\tStatus\tLabel\n" + "".join(f"-\t0\t{x}\n" for x in listed)
                code = 1 if command in fail else 0
            elif command == "print":
                self.assertTrue(argv[2].startswith("gui/123/"))
                output = ""
                code = 0 if argv[2].removeprefix("gui/123/") in loaded else 113
            elif command == "print-disabled":
                self.assertEqual(argv[2], "gui/123")
                output = (
                    'disabled services = {\n "enabled.job" => enabled\n'
                    + "".join(f' "{x}" => disabled\n' for x in disabled)
                    + "}\n"
                )
                code = 1 if command in fail else 0
            else:
                self.fail(f"unexpected launchctl subcommand: {command}")
            return SimpleNamespace(returncode=code, stdout=output)

        return run

    def observe(self, run):
        return self.m.observe(root=self.root, agents_dir=self.agents, uid=123, run=run)

    def test_classify_all_sixteen_combinations(self):
        cases = {
            (False, False, False, False): None,
            (False, False, False, True): None,
            (False, False, True, False): "UNTRACKED",
            (False, False, True, True): "UNTRACKED",
            (False, True, False, False): "UNTRACKED",
            (False, True, False, True): "UNTRACKED",
            (False, True, True, False): "UNTRACKED",
            (False, True, True, True): "UNTRACKED",
            (True, False, False, False): "NOT_INSTALLED",
            (True, False, False, True): "NOT_INSTALLED",
            (True, False, True, False): "LOADED_NOT_INSTALLED",
            (True, False, True, True): "LOADED_NOT_INSTALLED",
            (True, True, False, False): "INSTALLED_NOT_LOADED",
            (True, True, False, True): "DISABLED",
            (True, True, True, False): "LOADED",
            (True, True, True, True): "DISABLED",
        }
        for inputs, expected in cases.items():
            with self.subTest(inputs=inputs):
                kwargs = dict(zip(("tracked", "installed", "loaded", "disabled"), inputs))
                if expected is None:
                    with self.assertRaises(ValueError):
                        self.m.classify(**kwargs)
                else:
                    self.assertEqual(self.m.classify(**kwargs), expected)

    def test_compare_universe_order_and_outside_prefix(self):
        labels = [PREFIX + str(i) for i in range(6)]
        a, b, c, d, e, f = labels
        outside = "com.carsyn.repo-reconcile"
        states = self.m.compare(
            tracked={x: f"tools/{x}.plist" for x in (a, b, c, e, f, outside)},
            installed={a, b, d, f, outside, "com.carsyn.pick-dashboard"},
            loaded={b, c, f, outside},
            disabled={b, PREFIX + "disabled-only"},
        )
        self.assertEqual([x.label for x in states], [a, b, c, d, e, f, outside])
        self.assertEqual(
            [x.state.value for x in states],
            [
                "INSTALLED_NOT_LOADED",
                "DISABLED",
                "LOADED_NOT_INSTALLED",
                "UNTRACKED",
                "NOT_INSTALLED",
                "LOADED",
                "LOADED",
            ],
        )
        self.assertIsNone(states[3].tracked_path)
        self.assertTrue(states[1].loaded and states[1].disabled)
        self.assertEqual(
            self.m.compare(
                tracked={}, installed={"other"}, loaded=set(), disabled={PREFIX + "disabled-only"}
            ),
            (),
        )

    def test_installed_excludes_backups_and_other_files(self):
        for name in ("a.plist", "b.plist.bak-20260101", "c.txt"):
            (self.agents / name).touch()
        self.assertEqual(self.m.installed_labels(self.agents), frozenset({"a"}))

    def test_discovery_four_roots_and_invalid_label(self):
        roots = (
            "tools/launchagents",
            "tools/launchd",
            "tools/repo_rag/launchd",
            "tools/anti-stranding",
        )
        expected = {}
        for index, directory in enumerate(roots):
            relative = f"{directory}/{index}.plist"
            self.plist(relative, str(index))
            expected[str(index)] = relative
        self.assertEqual(self.m.tracked_labels(self.root), expected)
        invalid = self.root / "tools/launchagents/bad.plist"
        for payload in ({}, {"Label": ""}, {"Label": 3}, ["label"]):
            invalid.write_bytes(plistlib.dumps(payload))
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, r"bad.plist.*0"):
                self.m.tracked_labels(self.root)

    def test_discovery_regex_fallback_and_ambiguous_or_missing_labels(self):
        path = self.root / "tools/launchagents/bad.plist"
        path.parent.mkdir(parents=True)
        for header in ('<?xml version="1.0"?><plist><!-- -- -->', "not XML "):
            path.write_text(header + "<key>Label</key><string>recovered</string>")
            self.assertEqual(
                self.m.tracked_labels(self.root),
                {"recovered": path.relative_to(self.root).as_posix()},
            )
        for body, count in (
            ("broken", 0),
            ("<key>Label</key><string>a</string><key>Label</key><string>b</string>", 2),
        ):
            path.write_text(body)
            with self.assertRaisesRegex(ValueError, rf"bad.plist.*{count}"):
                self.m.tracked_labels(self.root)

    def test_real_tree_resolves_all_twelve_labels(self):
        tracked = self.m.tracked_labels(ROOT)
        self.assertEqual(
            set(tracked),
            {
                PREFIX + name
                for name in (
                    "daily-ritual",
                    "alignment-check",
                    "intraday-capture",
                    "job-health-digest",
                    "research-refresh",
                    "repo-rag-health",
                    "schwab-chain-intraday",
                    "schwab-chain-preclose",
                    "live-dashboard",
                    "research-display-refresh",
                    "research-views",
                )
            }
            | {"com.carsyn.repo-reconcile"},
        )

    def test_adapter_shapes_and_missing_disabled_means_enabled(self):
        run = self.runner(listed={"label with spaces"}, loaded={"idle"}, disabled={"off"})
        self.assertEqual(self.m.listed_labels(run=run), {"label with spaces"})
        self.assertTrue(self.m.print_loaded("idle", uid=123, run=run))
        self.assertFalse(self.m.print_loaded("missing", uid=123, run=run))
        self.assertEqual(self.m.disabled_labels(uid=123, run=run), {"off"})

    def test_print_wins_over_list_for_tracked_labels(self):
        label = PREFIX + "tracked"
        self.plist(f"tools/launchd/{label}.plist", label)
        (self.agents / f"{label}.plist").touch()
        result = self.observe(self.runner(listed={label, PREFIX + "stray", "unrelated"}))
        self.assertEqual(
            [(s.label, s.state.value) for s in result.states],
            [
                (label, "INSTALLED_NOT_LOADED"),
                (PREFIX + "stray", "UNTRACKED"),
            ],
        )

    def test_partial_failures_keep_print_decisions(self):
        label = PREFIX + "tracked"
        self.plist(f"tools/launchd/{label}.plist", label)
        (self.agents / f"{label}.plist").touch()
        for failed in (("list",), ("print-disabled",), ("list", "print-disabled")):
            with self.subTest(failed=failed):
                observation = self.observe(self.runner(loaded={label}, fail=failed))
                self.assertIsNone(observation.unavailable_reason)
                self.assertEqual(observation.unavailable_inputs, failed)
                self.assertEqual(observation.states[0].state.value, "LOADED")

    def test_absent_binary_is_observation_level_unavailable(self):
        def missing(*args, **kwargs):
            raise FileNotFoundError("/bin/launchctl")

        result = self.observe(missing)
        self.assertEqual(result.states, ())
        self.assertIsNotNone(result.unavailable_reason)
        self.assertEqual(result.unavailable_inputs, ("list", "print", "print-disabled"))

    def test_receipt_counts_cover_all_states_and_unavailability(self):
        states = tuple(
            self.m.LabelState(str(i), "p", True, False, False, state)
            for i, state in enumerate(self.m.State)
        )
        observation = self.m.Observation(states, None, ("list",))
        receipt = self.m.build_receipt(
            as_of="",
            run_date="2026-09-09",
            run_at_utc="2026-09-09T13:09:00Z",
            observation=observation,
        )
        self.assertEqual(
            set(receipt), {"schema_version", "as_of", "run_date", "run_at_utc", "states", "summary"}
        )
        self.assertEqual(receipt["schema_version"], "daily_ritual/launchagent_state/v1")
        self.assertIsNone(receipt["as_of"])
        summary = receipt["summary"]
        counts = [
            summary[k]
            for k in (
                "loaded",
                "installed_not_loaded",
                "disabled",
                "loaded_not_installed",
                "untracked",
                "not_installed",
            )
        ]
        self.assertEqual(counts, [1] * 6)
        self.assertEqual(sum(counts), len(receipt["states"]))
        self.assertEqual(summary["unavailable_inputs"], ["list"])
        self.assertIsNone(summary["unavailable_reason"])

    def test_cli_writes_run_date_receipt_and_preserves_empty_as_of(self):
        for as_of in ("2026-09-08", ""):
            output = io.StringIO()
            with (
                patch.object(self.m, "observe", return_value=self.m.Observation((), None, ())),
                contextlib.redirect_stdout(output),
            ):
                code = self.m.main(
                    ["--root", str(self.root), "--as-of", as_of, "--run-date", "2026-09-09"]
                )
            self.assertEqual(code, 0)
            target = self.root / "reports/ritual/launchagent_state_2026-09-09.json"
            receipt = json.loads(target.read_text())
            self.assertEqual(receipt["run_date"], "2026-09-09")
            self.assertEqual(receipt["as_of"], as_of or None)
            self.assertTrue(target.read_text().endswith("\n"))
            if not as_of:
                self.assertIn("as_of unresolved", output.getvalue())

    def test_cli_all_states_and_unavailable_exit_zero_without_receipt(self):
        for state in self.m.State:
            observation = self.m.Observation(
                (self.m.LabelState(PREFIX + "test", "p", True, False, False, state),), None, ()
            )
            with (
                self.subTest(state=state),
                patch.object(self.m, "observe", return_value=observation),
                contextlib.redirect_stdout(io.StringIO()) as out,
            ):
                self.assertEqual(self.m.main(["--root", str(self.root), "--no-receipt"]), 0)
            self.assertIn("receipt=none (--no-receipt)", out.getvalue())
            if state.value in {"INSTALLED_NOT_LOADED", "DISABLED", "UNTRACKED"}:
                self.assertIn(state.value, out.getvalue())
        with (
            patch.object(
                self.m,
                "observe",
                return_value=self.m.Observation(
                    (), "launchctl absent", ("list", "print", "print-disabled")
                ),
            ),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            self.assertEqual(self.m.main(["--root", str(self.root), "--no-receipt"]), 0)
        self.assertIn("UNAVAILABLE", out.getvalue())
        self.assertFalse((self.root / "reports").exists())

    def test_receipt_write_failure_preserves_incident_lines_and_exit_zero(self):
        state = self.m.LabelState(
            PREFIX + "incident",
            "tools/launchd/incident.plist",
            True,
            False,
            False,
            self.m.State.INSTALLED_NOT_LOADED,
        )
        observation = self.m.Observation((state,), None, ())
        with (
            patch.object(self.m, "observe", return_value=observation),
            patch.object(self.m, "atomic_text_write", side_effect=OSError("disk full")),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            self.assertEqual(
                self.m.main(
                    ["--root", str(self.root), "--as-of", "2026-09-08", "--run-date", "2026-09-09"]
                ),
                0,
            )
        self.assertIn("INSTALLED_NOT_LOADED " + PREFIX + "incident", out.getvalue())
        self.assertIn("launchctl bootstrap", out.getvalue())
        self.assertIn("disk full", out.getvalue())
        self.assertIn("receipt=unavailable", out.getvalue())

    def test_cli_bad_arguments_and_io_errors_are_visible_advisories(self):
        for argv in (
            ["--root", str(self.root)],
            ["--unknown"],
            ["--root", str(self.root), "--run-date", "../escape"],
        ):
            with (
                self.subTest(argv=argv),
                contextlib.redirect_stdout(io.StringIO()) as out,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(self.m.main(argv), 0)
            self.assertIn("launchagents:", out.getvalue())
        for error in (ValueError("bad plist"), OSError("unreadable plist")):
            with (
                patch.object(self.m, "observe", side_effect=error),
                contextlib.redirect_stdout(io.StringIO()) as out,
            ):
                self.assertEqual(self.m.main(["--root", str(self.root), "--no-receipt"]), 0)
            self.assertIn(str(error), out.getvalue())
