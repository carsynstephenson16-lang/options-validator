"""Offline contract tests for the ritual's tiered authority gates.

The invariants below are quoted verbatim from brief 11 §8
(`docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md`):

> **P1 (mutation fence).** In `tools/daily_ritual.sh`, the byte index of
> `"$PYTHON" -m data.ritual_authority require-data` is strictly less than the
> byte index of the first occurrence of **every** mutation surface in the
> script.
>
> **P2 (H7 fence).** The byte index of
> `"$PYTHON" -m data.ritual_authority require-full` is strictly less than the
> byte index of the first occurrence of **every** H7 surface in the script,
> where "H7 surface" means a **`python -m <module>` invocation site** whose
> module is in `H7_TIER_SURFACES`. Import-probe and value-resolution
> `python -c` sites are **not** H7 surfaces for P2 — see the explicit
> classification in §8.1.
>
> **P3 (tier ordering).** `status` precedes `require-data`, and `require-data`
> precedes `require-full`. The `status` mode `exec`s and therefore reaches no
> gate; no other mode may bypass either gate.
>
> **P4 (closure).** Every `python -m` invocation site, every `python -c`
> invocation site, and every mutation verb present in the script is classified
> in exactly one of the **three** registries the test declares, each with its
> **own matcher**. An unclassified surface fails the test. A test that only
> checks a hand-written list of tokens is vacuous the moment a new step is
> added; P4 is what makes P1 and P2 binding over time.

Each registry has its OWN matcher and is compared only against its OWN
extracted set; the three are never merged into one comparison. Registries 2
and 3 are keyed by line number, so a moved or added site fails closed.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

RITUAL = Path(__file__).resolve().parents[1] / "tools" / "daily_ritual.sh"

# ---- registry 1: `python -m <module>` invocation sites ----------------------
DATA_TIER_MODULES = (
    "options_researcher.ritual_status",  # RUNNING marker and terminal status
    "options_researcher.qm_dashboard",  # OHLCV refresh (data-tier island)
    "options_researcher.dashboard",
    "options_researcher.attractiveness_dashboard",
    "options_researcher.ritual_receipt",
)
H7_TIER_SURFACES = (
    "options_researcher.h7_source_health",
    "options_researcher.h7_data_gate",
    "options_researcher.h7_exit_session",  # fill and monitor collapse to the module
    "options_researcher.h7_watch",
    "options_researcher.h7_entry_preflight",
)
GATE_GO_SURFACES = (  # membership per owner decision D-1 (F1: all stay fenced)
    "options_researcher.h6_features",
    "options_researcher.h6_watch",
    "options_researcher.entry_watch",
    "options_researcher.h8_watch",
    "options_researcher.h10_watch",
    "options_researcher.h10_observe",
)
GATE_SITES = ("data.ritual_authority",)  # the gate itself, never a gated surface

MODULE_SITE_RE = re.compile(r"python -m ([A-Za-z0-9_.]+)")

# ---- registry 2: every `python -c` invocation site, classified --------------
# Line 115 is DELIBERATELY data-tier-permitted even though it imports
# options_researcher.h7_watch: it reads a session calendar and mutates nothing,
# and AS_OF gates the entire data phase. A naive H7 matcher that greps for the
# substring "h7_watch" would fail P2 on a correct script (mutation M9).
PYTHON_DASH_C_CLASSIFICATION = {
    115: "DATA_TIER_PERMITTED",  # AS_OF via options_researcher.h7_watch.evaluation_session
    116: "DATA_TIER_PERMITTED",  # SCOPE_ID via options_researcher.h7_scope.scope_identity
    194: "FULL_TIER",  # research.receipts.load_receipt — reads the gate receipt
    301: "DATA_TIER",  # options_researcher.features.build_all (watch universe)
    304: "DATA_TIER",  # options_researcher.features.build_all (display extras)
    377: "FULL_TIER_PROBE",  # `import options_researcher.h8_watch` availability probe
    388: "FULL_TIER_PROBE",  # `import options_researcher.h10_watch` availability probe
}

# ---- registry 3: every mutation verb site ----------------------------------
MUTATION_VERB_PATTERNS = {
    'mkdir -p "$LOGDIR"': r'mkdir -p "\$LOGDIR"',
    'mkdir -p "$PF_RECEIPT_DIR"': r'mkdir -p "\$PF_RECEIPT_DIR"',
    "mkdir -p reports/h5": r"mkdir -p reports/h5",
    "mkdir -p reports/h8_forward": r"mkdir -p reports/h8_forward",
    "git add": r"\bgit\s+add\b",
    "git commit": r"\bgit\s+commit\b",
    "git fetch": r"\bgit\s+fetch\b",
    "git merge": r"\bgit\s+merge\b",
    "git push": r"\bgit(?:\s+-c\s+\S+)*\s+push\b",
    "restic backup": r"\brestic\s+backup\b",
}
MUTATION_VERB_SITES = {
    'mkdir -p "$LOGDIR"': (63,),  # data tier
    'mkdir -p "$PF_RECEIPT_DIR"': (332,),  # full tier (region B)
    "mkdir -p reports/h5": (365,),  # full tier (region B, GATE_GO)
    "mkdir -p reports/h8_forward": (378,),  # full tier (region B, GATE_GO)
    "git add": (475,),  # data tier, allow-list scoped (§6.4)
    "git commit": (478,),  # data tier
    "git fetch": (488,),  # data tier
    "git merge": (489,),  # data tier — mutates the working tree unattended
    "git push": (490,),  # data tier
    "restic backup": (507,),  # data tier
}
# Any mkdir/git/restic verb anywhere in the script must be registered above.
ANY_MUTATION_VERB_RE = re.compile(
    r"\bmkdir\b|\bgit\s+add\b|\bgit\s+commit\b|\bgit\s+fetch\b|\bgit\s+merge\b"
    r"|\bgit(?:\s+-c\s+\S+)*\s+push\b|\brestic\s+backup\b"
)

REQUIRE_DATA = '"$PYTHON" -m data.ritual_authority require-data'
REQUIRE_FULL = '"$PYTHON" -m data.ritual_authority require-full'


def _source() -> str:
    return RITUAL.read_text(encoding="utf-8")


def _module_site_index(source: str, module: str) -> int:
    """Byte index of the first `python -m <module>` invocation site.

    Deliberately NOT a bare substring search: several modules also appear
    inside `python -c` import strings, which are classified in registry 2 and
    are not invocation sites (brief 11 §8.1, blocker B-1).
    """
    for match in MODULE_SITE_RE.finditer(source):
        if match.group(1) == module:
            return match.start()
    raise AssertionError(f"no `python -m {module}` invocation site in the script")


def _region(source: str, name: str) -> tuple[int, int]:
    start = source.index(f"# ---- {name} ")
    end = source.index(f"# ---- end {name} ")
    assert start < end, name
    return start, end


def _code_lines(source: str) -> list[tuple[int, str]]:
    """1-based (line number, text) pairs, comment-only lines excluded."""
    return [
        (number, line)
        for number, line in enumerate(source.split("\n"), 1)
        if not line.strip().startswith("#")
    ]


class DailyRitualProvenanceTests(unittest.TestCase):
    @staticmethod
    def _tree_identity(path: Path) -> tuple:
        if not path.exists():
            return ("missing",)
        if path.is_file():
            return ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        return (
            "directory",
            tuple(
                (str(item.relative_to(path)), hashlib.sha256(item.read_bytes()).hexdigest())
                for item in sorted(path.rglob("*"))
                if item.is_file()
            ),
        )

    # ---- P1 -----------------------------------------------------------------
    def test_require_data_precedes_every_mutation_surface(self):
        source = _source()
        self.assertIn(REQUIRE_DATA, source)
        gate = source.index(REQUIRE_DATA)
        for module in DATA_TIER_MODULES + H7_TIER_SURFACES + GATE_GO_SURFACES:
            with self.subTest(module=module):
                self.assertLess(gate, _module_site_index(source, module))
        for verb, pattern in MUTATION_VERB_PATTERNS.items():
            with self.subTest(verb=verb):
                match = re.search(pattern, source)
                self.assertIsNotNone(match, verb)
                self.assertLess(gate, match.start())

    # ---- P2 -----------------------------------------------------------------
    def test_require_full_precedes_every_h7_surface(self):
        source = _source()
        self.assertIn(REQUIRE_FULL, source)
        gate = source.index(REQUIRE_FULL)
        # Under owner decision D-1 = F1 the GATE_GO lanes stay fenced too.
        for module in H7_TIER_SURFACES + GATE_GO_SURFACES:
            with self.subTest(module=module):
                self.assertLess(gate, _module_site_index(source, module))

    # ---- P3 -----------------------------------------------------------------
    def test_tier_ordering_status_then_data_then_full(self):
        source = _source()
        status = source.index("data.ritual_authority status")
        require_data = source.index("data.ritual_authority require-data")
        require_full = source.index("data.ritual_authority require-full")
        self.assertLess(status, require_data)
        self.assertLess(require_data, require_full)
        # status exec's, so it reaches no gate at all.
        self.assertLess(source.index('if [ "$RITUAL_MODE" = "status" ]; then'), require_data)
        self.assertIn('exec env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority status', source)
        self.assertIn('PYTHON="$REPO/.venv/bin/python"', source)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1 "$PYTHON"', source)
        self.assertNotIn('$UV" run python -m data.ritual_authority', source)

    # ---- P4 -----------------------------------------------------------------
    def test_every_script_surface_is_classified(self):
        source = _source()

        module_sites = [match.group(1) for match in MODULE_SITE_RE.finditer(source)]
        self.assertEqual(
            set(module_sites),
            set(DATA_TIER_MODULES + H7_TIER_SURFACES + GATE_GO_SURFACES),
        )
        # The gate is not a gated surface: requiring it to precede itself is
        # incoherent. It is invoked as `"$PYTHON" -m`, so the `python -m`
        # matcher cannot capture it — assert BOTH facts rather than relying on
        # that regex accident.
        for gate_module in GATE_SITES:
            self.assertNotIn(gate_module, module_sites)
            self.assertIn(f'"$PYTHON" -m {gate_module}', source)

        dash_c_lines = [
            number for number, line in _code_lines(source) if "python -c" in line
        ]
        self.assertEqual(set(dash_c_lines), set(PYTHON_DASH_C_CLASSIFICATION))

        verb_lines: dict[str, tuple[int, ...]] = {}
        for verb, pattern in MUTATION_VERB_PATTERNS.items():
            hits = tuple(
                number
                for number, line in _code_lines(source)
                if re.search(pattern, line)
            )
            if hits:
                verb_lines[verb] = hits
        self.assertEqual(verb_lines, MUTATION_VERB_SITES)

        # Closure over the verb families themselves: an unregistered mkdir/git/
        # restic verb anywhere in executable text fails here (mutation M10).
        registered = {
            number for numbers in MUTATION_VERB_SITES.values() for number in numbers
        }
        seen = {
            number
            for number, line in _code_lines(source)
            if ANY_MUTATION_VERB_RE.search(line)
        }
        self.assertEqual(seen, registered)

    def test_dash_c_sites_are_classified_and_data_tier_ones_are_unfenced(self):
        source = _source()
        offsets = {}
        for number, line in _code_lines(source):
            if "python -c" in line:
                offsets[number] = source.index(line)
        region_a = _region(source, "full-tier region A")
        island = _region(source, "data-tier island")
        region_b = _region(source, "full-tier region B")
        require_full = source.index(REQUIRE_FULL)

        for number, classification in PYTHON_DASH_C_CLASSIFICATION.items():
            with self.subTest(line=number, classification=classification):
                offset = offsets[number]
                if classification == "DATA_TIER_PERMITTED":
                    self.assertLess(offset, require_full)
                elif classification == "DATA_TIER":
                    self.assertTrue(island[0] < offset < island[1])
                    self.assertFalse(region_a[0] < offset < region_a[1])
                    self.assertFalse(region_b[0] < offset < region_b[1])
                elif classification == "FULL_TIER":
                    self.assertTrue(region_a[0] < offset < region_a[1])
                else:
                    self.assertEqual(classification, "FULL_TIER_PROBE")
                    self.assertTrue(region_b[0] < offset < region_b[1])

    def test_data_tier_island_is_outside_the_full_fence(self):
        source = _source()
        region_a = _region(source, "full-tier region A")
        island = _region(source, "data-tier island")
        region_b = _region(source, "full-tier region B")
        self.assertLess(region_a[1], island[0])
        self.assertLess(island[1], region_b[0])

        for token in (
            'options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF"',
            "build_all('$AS_OF', symbols=watch_universe())",
            "build_all('$AS_OF', symbols=ATTRACTIVENESS_EXTRA_NAMES)",
        ):
            with self.subTest(token=token):
                offset = source.index(token)
                self.assertFalse(region_a[0] < offset < region_a[1])
                self.assertFalse(region_b[0] < offset < region_b[1])
                self.assertTrue(island[0] < offset < island[1])

    def test_frozen_operator_order_is_preserved(self):
        source = _source()
        ordered = (
            _module_site_index(source, "options_researcher.h7_source_health"),
            _module_site_index(source, "options_researcher.h7_data_gate"),
            source.index("options_researcher.h7_exit_session fill"),
            source.index("options_researcher.h7_exit_session monitor"),
            _module_site_index(source, "options_researcher.qm_dashboard"),
            source.index("build_all('$AS_OF', symbols=watch_universe())"),
            source.index("build_all('$AS_OF', symbols=ATTRACTIVENESS_EXTRA_NAMES)"),
            _module_site_index(source, "options_researcher.h7_watch"),
            _module_site_index(source, "options_researcher.h6_features"),
            _module_site_index(source, "options_researcher.h6_watch"),
            _module_site_index(source, "options_researcher.entry_watch"),
            _module_site_index(source, "options_researcher.h8_watch"),
            _module_site_index(source, "options_researcher.h10_watch"),
            _module_site_index(source, "options_researcher.h10_observe"),
            _module_site_index(source, "options_researcher.dashboard"),
        )
        self.assertEqual(list(ordered), sorted(ordered))

    def test_ritual_contains_no_provider_acquisition_or_key_preflight(self):
        source = _source()
        self.assertNotIn("_resolve_api_key", source)
        self.assertNotIn("data/recent_topup.py", source)

    def test_status_preserves_log_tree_and_lockfile_bytes(self):
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        repo = RITUAL.parents[1]
        guarded = (repo / ".tmp" / "daily_ritual", repo / "uv.lock")
        before = tuple(self._tree_identity(path) for path in guarded)
        result = subprocess.run(
            [zsh, str(RITUAL), "status"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        after = tuple(self._tree_identity(path) for path in guarded)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(set(payload), {"data_phase", "flags", "full_ritual"})
        self.assertEqual(
            set(payload["flags"]),
            {"exact_session_source_active", "h7_active", "ritual_data_phase_active"},
        )
        self.assertIn("ready", payload["data_phase"])
        self.assertIn("ready", payload["full_ritual"])
        self.assertEqual(after, before)

    def test_ops_publisher_requires_current_main(self):
        source = _source()
        branch_guard = source.index('if [ "$RITUAL_BRANCH" != "main" ]')
        current_main_guard = source.index("rev-parse origin/main 2>/dev/null")
        publisher_role = source.index("export OPTIONS_VALIDATOR_CACHE_ROLE=publisher")
        source_health = _module_site_index(source, "options_researcher.h7_source_health")
        self.assertLess(branch_guard, current_main_guard)
        self.assertLess(current_main_guard, publisher_role)
        self.assertLess(publisher_role, source_health)

    def test_authority_gate_replaces_provider_topup_dependency(self):
        source = _source()
        require_data = source.index("data.ritual_authority require-data")
        require_full = source.index("data.ritual_authority require-full")
        source_health = _module_site_index(source, "options_researcher.h7_source_health")
        data_gate = _module_site_index(source, "options_researcher.h7_data_gate")
        self.assertLess(require_data, require_full)
        self.assertLess(require_full, source_health)
        self.assertLess(source_health, data_gate)
        self.assertNotIn("H7_DATA_READY", source)

    def test_h6_and_h8_nonzero_results_are_critical(self):
        source = _source()
        self.assertIn('crit "h6_features: NONZERO EXIT"', source)
        self.assertIn('crit "h6_watch: NONZERO EXIT"', source)
        self.assertIn('crit "h8_watch: NONZERO EXIT"', source)

    def test_h5_rerun_failure_is_critical_before_terminal_publish(self):
        source = _source()
        failure = 'crit "h5 entry watch: NONZERO EXIT"'
        terminal = source.index('if [ "$CRITICAL" -eq 1 ]; then')
        self.assertIn(failure, source)
        self.assertLess(source.index(failure), terminal)
        self.assertNotIn('note "WARNING: h5 entry watch failed to run"', source)

    def test_h10_rerun_failures_are_critical_before_terminal_publish(self):
        source = _source()
        terminal = source.index('if [ "$CRITICAL" -eq 1 ]; then')
        failures = (
            'crit "h10_watch: NONZERO EXIT"',
            'crit "h10_observe: NONZERO EXIT"',
            'crit "h10_watch: module unavailable"',
        )
        for failure in failures:
            with self.subTest(failure=failure):
                self.assertIn(failure, source)
                self.assertLess(source.index(failure), terminal)
        self.assertNotIn('note "h10_watch: NONZERO EXIT"', source)
        self.assertNotIn('note "h10_observe: NONZERO EXIT"', source)

    def test_ritual_terminal_status_is_separate_from_capture_receipt(self):
        source = _source()
        running = source.index("--status RUNNING")
        capture = source.index('"$UV" run python -m options_researcher.ritual_receipt')
        terminal = source.index('--status "$RITUAL_TERMINAL_STATUS"')
        durability = source.index("# Step 8 — DURABILITY")
        self.assertLess(running, capture)
        self.assertLess(capture, terminal)
        self.assertLess(terminal, durability)
        self.assertIn('RITUAL_TERMINAL_STATUS="BROKEN"', source)
        self.assertIn('RITUAL_TERMINAL_STATUS="OK"', source)

    def test_durability_allow_list_is_tier_scoped(self):
        source = _source()
        durability = source[source.index("# Step 8 — DURABILITY"):]
        full_branch = durability.index('if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then')
        git_add = durability.index("git add --")
        self.assertLess(full_branch, git_add)

        for path in (
            "ledger/facts.log",
            "ledger/h7_forward",
            "ledger/h7_forward_schwab",
            "reports/h7_receipts",
            "reports/h7_data_gate",
            "reports/h5",
            "reports/h6_forward",
            "reports/h8_forward",
            "reports/h10",
            "reports/schwab_chains",
        ):
            with self.subTest(path=path):
                self.assertIn(path, durability)
                self.assertGreater(durability.index(path), full_branch)
                self.assertLess(durability.index(path), git_add)

        # Data-tier paths are staged unconditionally, ahead of the branch.
        for path in (
            "reports/ritual",
            "reports/intraday_capture",
            "reports/live_probe",
            "reports/cache_runs",
        ):
            with self.subTest(path=path):
                self.assertLess(durability.index(path), full_branch)

        # The commit message must not describe data-phase artifacts as H7
        # evidence (caution C6).
        self.assertIn(
            "data(ritual): daily ritual data-phase artifacts ${RUN_DATE}", durability
        )
        self.assertIn("data(h7): daily ritual evidence ${RUN_DATE}", durability)
        self.assertGreater(
            durability.index("data(h7): daily ritual evidence ${RUN_DATE}"), full_branch
        )
        self.assertLess(
            durability.index("data(ritual): daily ritual data-phase artifacts ${RUN_DATE}"),
            full_branch,
        )

    def test_paused_lanes_are_noted_not_critical(self):
        source = _source()

        def _executable(start_marker: str, end_marker: str) -> str:
            block = source[source.index(start_marker) : source.index(end_marker)]
            return "\n".join(
                line for line in block.split("\n") if not line.strip().startswith("#")
            )

        # Region A's else-branch: a deliberately paused lane is not a failure.
        # The pre-restructure crit here would have fired every single day under
        # the data tier and trained the operator to ignore CRITICAL lines.
        region_a_else = _executable(
            "# A deliberately paused lane is not a failure",
            "# ---- end full-tier region A",
        )
        self.assertIn('note "H7 lanes: PAUSED', region_a_else)
        self.assertIn("GATE_GO=0", region_a_else)
        self.assertIn("H7_EXIT_READY=0", region_a_else)
        self.assertNotIn("crit ", region_a_else)

        region_b_else = _executable(
            'elif [ "$FULL_AUTHORITY_RC" -ne 0 ]; then',
            "# ---- end full-tier region B",
        )
        self.assertIn('note "H5/H6/H8/H10 lanes: PAUSED', region_b_else)
        self.assertNotIn("crit ", region_b_else)

    def test_starved_label_requires_single_capture_critical(self):
        source = _source()
        title_logic = source[source.index('TITLE="options-validator daily ritual"') :]
        self.assertIn(
            'if [ "$DATA_STARVED" -eq 1 ] && [ "$STARVED_CRIT" -eq 1 ] '
            '&& [ "$CRIT_COUNT" -eq 1 ]; then',
            title_logic,
        )
        self.assertIn('TITLE="[DATA-STARVED] $TITLE"', title_logic)
        self.assertIn('TITLE="[BROKEN] $TITLE"', title_logic)
        # Pure counter comparison: no text matching on $SUMMARY in the title
        # logic, or a future CRITICAL whose text merely mentions the capture
        # receipt would silently downgrade a genuinely broken run.
        self.assertNotIn("SUMMARY", title_logic.split("osascript")[0])
        self.assertIn("CRIT_COUNT=$((CRIT_COUNT + 1))", source)
        # STARVED_CRIT is set at exactly one site: the capture receipt failure.
        self.assertEqual(source.count("STARVED_CRIT=1"), 1)
        capture = source.index('"$UV" run python -m options_researcher.ritual_receipt')
        self.assertGreater(source.index("STARVED_CRIT=1"), capture)
        self.assertLess(
            source.index("STARVED_CRIT=1"),
            source.index('crit "capture receipt: REFUSED'),
        )

    def test_starved_title_flips_to_broken_on_a_second_critical(self):
        """Execute the title logic itself, so the invariant is behavioral.

        A genuinely CRITICAL run must never be relabeled as merely starved: the
        instant a second CRITICAL exists from any source, [BROKEN] wins.
        """
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        source = _source()
        start = source.index('TITLE="options-validator daily ritual"')
        end = source.index("/usr/bin/osascript", start)
        block = source[start:end]

        cases = (
            # CRITICAL, DATA_STARVED, STARVED_CRIT, CRIT_COUNT, expected
            (1, 1, 1, 1, "[DATA-STARVED] options-validator daily ritual"),
            (1, 1, 1, 2, "[BROKEN] options-validator daily ritual"),
            (1, 1, 0, 1, "[BROKEN] options-validator daily ritual"),
            (1, 0, 1, 1, "[BROKEN] options-validator daily ritual"),
            (0, 1, 1, 1, "options-validator daily ritual"),
        )
        for critical, starved, starved_crit, count, expected in cases:
            with self.subTest(critical=critical, count=count):
                script = "\n".join(
                    [
                        f"CRITICAL={critical}",
                        f"DATA_STARVED={starved}",
                        f"STARVED_CRIT={starved_crit}",
                        f"CRIT_COUNT={count}",
                        block,
                        'echo "$TITLE"',
                    ]
                )
                completed = subprocess.run(
                    [zsh, "-c", script], capture_output=True, text=True, timeout=30
                )
                self.assertEqual(completed.stdout.strip(), expected, completed.stderr)

    def test_cache_edge_note_is_shell_only_and_fails_soft(self):
        source = _source()
        self.assertIn("canonical chain cache edge: ${CHAIN_EDGE:-none}", source)
        self.assertIn("DATA_STARVED=1", source)
        self.assertIn("chain-dependent lanes are STARVED", source)
        self.assertLess(
            source.index("CHAIN_EDGE="),
            _module_site_index(source, "options_researcher.ritual_status"),
        )

    def test_push_failure_is_critical_with_a_realign_instruction(self):
        source = _source()
        self.assertIn(
            'crit "evidence: PUSH FAILED — ops HEAD is AHEAD of origin/main; '
            "the 15:45 Schwab capture WILL REFUSE until this is realigned. "
            'Run: git -C ${REPO} push origin main"',
            source,
        )
        self.assertNotIn('note "evidence: push deferred', source)
        # Bounded and prompt-free, retried exactly once before declaring failure.
        self.assertIn("GIT_TERMINAL_PROMPT=0", source)
        self.assertIn("http.lowSpeedLimit=1000", source)
        self.assertIn("http.lowSpeedTime=20", source)
        self.assertIn("if push_evidence_once; then", source)
        self.assertIn("elif push_evidence_once; then", source)


if __name__ == "__main__":
    unittest.main()
