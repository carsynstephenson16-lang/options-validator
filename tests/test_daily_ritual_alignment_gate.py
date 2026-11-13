"""Behavioural + structural tests for the daily ritual's origin/main gate.

2026-09-11: Step 8 committed that morning's evidence and its push failed on a
network blip. 2026-09-14: the next run died at the alignment gate -- BEFORE
reaching the Step 8 push that would have healed it -- so one blip stalled the
ritual, and (through the same divergence) the 15:45 captures, until a human
pushed. The capture wrappers were given evidence-only divergence tolerance on
2026-08-14 (owner decision D-3); the ritual never was.

The gate now (a) refreshes origin/main with a bounded, prompt-free fetch when
the network allows, (b) refuses when BEHIND exactly as before, (c) when AHEAD
only by paths every capture gate already treats as evidence, retries the
ritual's OWN push once -- bare, no merge -- and proceeds only if HEAD then
equals origin/main, and (d) refuses everything else with the unchanged
CRITICAL text. It grants no new authority: Step 8 already pushes ops main to
origin/main at the end of every run.

The gate region is cut out of the real script and run under zsh against a real
temporary repository with a real bare origin, like the evidence-staging tests.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "daily_ritual.sh"
CAPTURE = ROOT / "tools" / "schwab_chain_capture.sh"
REGION = "alignment gate"
REFUSAL = (
    'crit "main is not exactly aligned with origin/main -- refusing cache publisher authority"'
)
PREDICATE = r"alignment_divergence_is_evidence_only\(\) \{.*?^\}"
ALLOW_LIST = r"EVIDENCE_ALLOW=\((.*?)\)"

_GIT_CONTEXT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _region(source: str, name: str) -> str:
    start = source.index(f"# ---- {name} ")
    end = source.index(f"# ---- end {name} ")
    assert start < end, name
    return source[start:end]


class AlignmentGateStructureTests(unittest.TestCase):
    def test_gate_sits_between_branch_guard_and_publisher_role(self):
        source = _source()
        branch_guard = source.index('if [ "$RITUAL_BRANCH" != "main" ]')
        gate = source.index(f"# ---- {REGION} ")
        gate_end = source.index(f"# ---- end {REGION} ")
        publisher = source.index("export OPTIONS_VALIDATOR_CACHE_ROLE=publisher")
        self.assertLess(branch_guard, gate)
        self.assertLess(gate, gate_end)
        self.assertLess(gate_end, publisher)
        # The gate is the ONLY place the ritual compares HEAD to origin/main
        # before publisher authority is granted.
        self.assertEqual(source[:publisher].count(REFUSAL), 1)
        self.assertGreater(source.index(REFUSAL), gate)

    def test_allow_list_and_predicate_are_byte_identical_to_the_capture_wrapper(self):
        gate = _region(_source(), REGION)
        capture = CAPTURE.read_text(encoding="utf-8")
        self.assertEqual(
            re.search(ALLOW_LIST, gate, re.S).group(1).split(),
            re.search(ALLOW_LIST, capture, re.S).group(1).split(),
        )
        self.assertEqual(
            re.search(PREDICATE, gate, re.S | re.M).group(),
            re.search(PREDICATE, capture, re.S | re.M).group(),
        )

    def test_gate_only_fetches_and_pushes_bounded_and_prompt_free_and_never_merges(self):
        gate = _region(_source(), REGION)
        code = "\n".join(line for line in gate.split("\n") if not line.strip().startswith("#"))
        for verb in ("merge", "pull", "reset", "rebase", "checkout", "stash"):
            with self.subTest(verb=verb):
                self.assertNotRegex(code, rf"\bgit\b[^\n]*\b{verb}\b")
        fetch = re.search(r"[^\n]*\bfetch -q origin main\b[^\n]*", code).group()
        push = re.search(r"[^\n]*\bpush -q origin main\b[^\n]*", code).group()
        for line in (fetch, push):
            with self.subTest(line=line.strip()):
                self.assertIn("GIT_TERMINAL_PROMPT=0", line)
                self.assertIn("http.lowSpeedLimit=1000", line)
                self.assertIn("http.lowSpeedTime=20", line)
        # Exactly one push site, and it is reachable only after the predicate.
        self.assertEqual(len(re.findall(r"\bpush -q origin main\b", code)), 1)
        self.assertLess(
            code.index("alignment_divergence_is_evidence_only \\"),
            code.index("push -q origin main"),
        )

    def test_refusal_keeps_the_exact_critical_text_and_exits_one(self):
        gate = _region(_source(), REGION)
        self.assertIn(REFUSAL, gate)
        after = gate[gate.index(REFUSAL) :]
        self.assertIn('echo "=== summary ==="', after)
        self.assertIn('printf "%b" "$SUMMARY"', after)
        self.assertIn("exit 1", after)


class AlignmentGateBehaviourTests(unittest.TestCase):
    def setUp(self) -> None:
        self.zsh = shutil.which("zsh")
        if self.zsh is None:
            self.skipTest("zsh is required to run the gate region")
        root = Path(tempfile.mkdtemp(prefix="ritual-gate-"))
        self.addCleanup(shutil.rmtree, root, True)
        home = root / "home"
        home.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k not in _GIT_CONTEXT_VARS}
        self.env.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
                "HOME": str(home),
            }
        )
        self.origin = root / "origin.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(self.origin)],
            check=True,
            capture_output=True,
            env=self.env,
        )
        self.repo = root / "checkout"
        self.repo.mkdir()
        self.log = root / "gate.log"
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Ritual gate test")
        self._git("config", "user.email", "ritual-gate-test@example.invalid")
        self._git("config", "core.hooksPath", "")
        self._write("code.py", "x = 1\n")
        self._write("reports/ritual/baseline.json", "{}\n")
        self._write("ledger/facts.log", "baseline\n")
        self._git("add", "--", ".")
        self._git("commit", "-q", "-m", "baseline")
        self._git("remote", "add", "origin", str(self.origin))
        self._git("push", "-q", "origin", "main")
        self.baseline = self._git("rev-parse", "HEAD")

    # --- fixture helpers ---------------------------------------------------
    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def _origin_main(self) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.origin), "rev-parse", "main"],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return result.stdout.strip()

    def _write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _commit_ahead(self, *paths: str) -> str:
        for index, relative in enumerate(paths):
            self._write(relative, f"payload {index}\n")
            self._git("add", "--", relative)
        self._git("commit", "-q", "-m", f"ahead {' '.join(paths)}")
        return self._git("rev-parse", "HEAD")

    def _advance_origin_behind_us(self) -> str:
        """origin/main gains a commit this checkout does not have."""
        self._write("remote_code.py", "y = 2\n")
        self._git("add", "--", "remote_code.py")
        self._git("commit", "-q", "-m", "remote code")
        remote_tip = self._git("rev-parse", "HEAD")
        self._git("push", "-q", "origin", "main")
        self._git("reset", "-q", "--hard", "HEAD~1")
        # Forget that we ever saw the remote tip, as a never-fetched ops
        # checkout would have.
        self._git("update-ref", "refs/remotes/origin/main", self.baseline)
        return remote_tip

    def _break_origin(self) -> None:
        self._git("remote", "set-url", "origin", str(self.repo.parent / "gone.git"))

    def _run_gate(self) -> tuple[int, str]:
        script = "\n".join(
            [
                f"TEST_LOG={shlex.quote(str(self.log))}",
                'note() { print -r -- "$1" >> "$TEST_LOG"; }',
                'crit() { CRITICAL=1; CRIT_COUNT=$((CRIT_COUNT + 1)); note "CRITICAL: $1"; }',
                'SUMMARY=""',
                "CRITICAL=0",
                "CRIT_COUNT=0",
                f"REPO={shlex.quote(str(self.repo))}",
                _region(_source(), REGION),
                'print -r -- "GATE_PASSED" >> "$TEST_LOG"',
            ]
        )
        result = subprocess.run(
            [self.zsh, "-c", script],
            cwd=self.repo,
            # The refusal branch notifies the desktop like the branch guard;
            # the env guard keeps a test run from raising real notifications.
            env={**self.env, "OPTIONS_VALIDATOR_NO_NOTIFY": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        log = self.log.read_text(encoding="utf-8") if self.log.exists() else ""
        return result.returncode, log

    # --- behaviour -----------------------------------------------------------
    def test_aligned_checkout_passes_silently(self):
        rc, log = self._run_gate()
        self.assertEqual(rc, 0)
        self.assertIn("GATE_PASSED", log)
        self.assertNotIn("CRITICAL", log)

    def test_behind_origin_refuses_with_the_unchanged_text(self):
        remote_tip = self._advance_origin_behind_us()
        rc, log = self._run_gate()
        self.assertEqual(rc, 1)
        self.assertNotIn("GATE_PASSED", log)
        self.assertIn(
            "CRITICAL: main is not exactly aligned with origin/main -- refusing cache publisher authority",
            log,
        )
        # The gate fetched, so it judged against the REAL remote tip, and it
        # neither merged nor pushed.
        self.assertEqual(self._git("rev-parse", "origin/main"), remote_tip)
        self.assertEqual(self._git("rev-parse", "HEAD"), self.baseline)
        self.assertEqual(self._origin_main(), remote_tip)

    def test_ahead_by_the_ritual_own_evidence_commit_pushes_it_and_passes(self):
        # Exact path shape of ops commit 6873263 (2026-09-11).
        tip = self._commit_ahead(
            "ledger/facts.log",
            "reports/ritual/run_status_2026-09-10.json",
            "reports/pick_tracker/dryrun/2026-09-10/scoreboard.json",
            "reports/closes_receipts/2026-09-11/guarded-all-cached.json",
        )
        rc, log = self._run_gate()
        self.assertEqual(rc, 0, log)
        self.assertIn("GATE_PASSED", log)
        self.assertNotIn("CRITICAL", log)
        self.assertIn("evidence-only", log)
        self.assertEqual(self._origin_main(), tip)
        self.assertEqual(self._git("rev-parse", "origin/main"), tip)

    def test_ahead_by_evidence_with_unreachable_origin_refuses_and_touches_nothing(self):
        tip = self._commit_ahead("reports/ritual/run_status.json", "ledger/facts.log")
        self._break_origin()
        rc, log = self._run_gate()
        self.assertEqual(rc, 1)
        self.assertNotIn("GATE_PASSED", log)
        self.assertIn("could not refresh origin/main", log)
        self.assertIn("CRITICAL: main is not exactly aligned", log)
        self.assertEqual(self._origin_main(), self.baseline)
        self.assertEqual(self._git("rev-parse", "HEAD"), tip)

    def test_ahead_by_code_refuses_and_never_pushes(self):
        for label, paths in (
            ("code only", ("tools/daily_ritual.sh",)),
            (
                "code mixed with evidence",
                ("reports/ritual/run_status.json", "options_researcher/h7_watch.py"),
            ),
            ("reports path in no allow-list", ("reports/not_evidence/new.json",)),
        ):
            with self.subTest(case=label):
                self.setUp()
                tip = self._commit_ahead(*paths)
                rc, log = self._run_gate()
                self.assertEqual(rc, 1, log)
                self.assertNotIn("GATE_PASSED", log)
                self.assertIn("CRITICAL: main is not exactly aligned", log)
                self.assertEqual(self._origin_main(), self.baseline)
                self.assertEqual(self._git("rev-parse", "HEAD"), tip)

    def test_code_suffixed_file_under_an_evidence_directory_refuses(self):
        # Review D (2026-09-15): the evidence directories are data-only by
        # convention; the predicate now enforces it by suffix wherever the
        # path sits, so a stray script can never be auto-pushed as evidence.
        for relative in (
            "reports/pick_tracker/evil.py",
            "reports/closes_receipts/2026-09-15/hook.sh",
            "ledger/facts.log.zsh",
        ):
            with self.subTest(path=relative):
                self.setUp()
                tip = self._commit_ahead(relative)
                rc, log = self._run_gate()
                self.assertEqual(rc, 1, log)
                self.assertNotIn("GATE_PASSED", log)
                self.assertEqual(self._origin_main(), self.baseline)
                self.assertEqual(self._git("rev-parse", "HEAD"), tip)

    def test_symlink_under_an_evidence_directory_refuses(self):
        # Review B/S1 (2026-09-15): the path test cannot see file MODE, so a
        # symlink (120000) at an evidence path pointing at code would pass it;
        # the raw-mode check refuses anything but regular files and deletions.
        link = self.repo / "reports" / "ritual" / "link.json"
        os.symlink("../../code.py", link)
        self._git("add", "--", "reports/ritual/link.json")
        self._git("commit", "-q", "-m", "symlink at an evidence path")
        tip = self._git("rev-parse", "HEAD")
        rc, log = self._run_gate()
        self.assertEqual(rc, 1, log)
        self.assertNotIn("GATE_PASSED", log)
        self.assertEqual(self._origin_main(), self.baseline)
        self.assertEqual(self._git("rev-parse", "HEAD"), tip)

    def test_deleting_an_evidence_file_still_counts_as_evidence(self):
        # Deletions report destination mode 000000 and must not trip the
        # regular-file check (a rotated receipt is still evidence).
        self._git("rm", "-q", "--", "reports/ritual/baseline.json")
        self._git("commit", "-q", "-m", "rotate a receipt")
        tip = self._git("rev-parse", "HEAD")
        rc, log = self._run_gate()
        self.assertEqual(rc, 0, log)
        self.assertIn("GATE_PASSED", log)
        self.assertEqual(self._origin_main(), tip)

    def test_evidence_directories_in_the_repo_hold_only_data_files(self):
        # The suffix rule above is only honest if the tracked tree obeys it.
        allowed = {".json", ".jsonl", ".md", ".gitkeep", ".txt", ".csv"}
        offenders = []
        for directory in ("reports/pick_tracker", "reports/closes_receipts"):
            for path in (ROOT / directory).rglob("*"):
                if path.is_file() and path.suffix not in allowed and path.name != ".gitkeep":
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_diverged_refuses_and_never_pushes(self):
        remote_tip = self._advance_origin_behind_us()
        self._commit_ahead("reports/ritual/run_status.json")
        rc, log = self._run_gate()
        self.assertEqual(rc, 1)
        self.assertNotIn("GATE_PASSED", log)
        self.assertIn("CRITICAL: main is not exactly aligned", log)
        self.assertEqual(self._origin_main(), remote_tip)

    def test_fetch_failure_with_matching_refs_passes_with_a_note(self):
        # An offline morning must still produce its data-phase artifacts:
        # the comparison falls back to the last fetched ref and says so.
        self._break_origin()
        rc, log = self._run_gate()
        self.assertEqual(rc, 0, log)
        self.assertIn("GATE_PASSED", log)
        self.assertIn("could not refresh origin/main", log)
        self.assertNotIn("CRITICAL", log)


if __name__ == "__main__":
    unittest.main()
