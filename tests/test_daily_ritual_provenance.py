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
import tempfile
import unittest
from pathlib import Path

RITUAL = Path(__file__).resolve().parents[1] / "tools" / "daily_ritual.sh"

# ---- registry 1: `python -m <module>` invocation sites ----------------------
DATA_TIER_MODULES = (
    "options_researcher.ritual_status",  # RUNNING marker and terminal status
    # Display-only Schwab refresh-token age advisory (2026-09-02). It prints
    # one operator line, never touches the network, always exits 0, and is
    # invoked with `|| true` -- it can affect no status and gate nothing.
    # Registered here as a data-tier module by tier, although its call site
    # sits just BEFORE the Schwab preclose lane marker rather than inside the
    # data-tier island (placing it inside broke the lane's first-statement
    # invariant); only PYTHON_DASH_C_CLASSIFICATION is position-enforced.
    "options_researcher.schwab_token_age",
    "options_researcher.qm_dashboard",  # OHLCV refresh (data-tier island)
    "options_researcher.dashboard",
    "options_researcher.attractiveness_dashboard",
    "options_researcher.pick_tracker",
    "options_researcher.ritual_receipt",
)
H7_TIER_SURFACES = (
    "options_researcher.h7_source_health",
    "options_researcher.h7_data_gate",
    "options_researcher.h7_exit_session",  # fill and monitor collapse to the module
    "options_researcher.h7_watch",
    "options_researcher.h7_entry_preflight",
)
GATE_GO_SURFACES = (  # membership per owner decision D-1 (F1) as amended below
    "options_researcher.h6_features",
    "options_researcher.h6_watch",
    "options_researcher.h8_watch",
)
# Brief 17 WP-F: ledger seq 28 clause 1 + seq 29 clause 2 record the
# owner-confirmed D-1=F1 override for H10b and H5's watch ONLY -- the verified
# Schwab 15:45 preclose capture is a qualifying exact-session source for those
# two lanes, so they no longer sit behind the H7 data gate. H6 and H8 stay in
# GATE_GO_SURFACES above, unchanged.
SCHWAB_LANE_SURFACES = (
    "options_researcher.entry_watch",
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
    120: "DATA_TIER_PERMITTED",  # AS_OF via options_researcher.h7_watch.evaluation_session
    121: "DATA_TIER_PERMITTED",  # SCOPE_ID via options_researcher.h7_scope.scope_identity
    199: "FULL_TIER",  # research.receipts.load_receipt — reads the gate receipt
    290: "DATA_TIER",  # data.recent_topup.refresh_closes_guarded
    314: "DATA_TIER",  # options_researcher.features.build_all (watch universe)
    317: "DATA_TIER",  # options_researcher.features.build_all (display extras)
    365: "FULL_TIER_PROBE",  # `import options_researcher.h8_watch` availability probe
    # Brief 17 WP-F: the Schwab lane's own read-only sites. The verified-view
    # read is the lane's fail-closed gate; it mutates nothing.
    406: "SCHWAB_LANE",  # schwab_chain_view.verified_sessions — lane gate
    449: "SCHWAB_LANE",  # `import options_researcher.h10_watch` availability probe
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
    # `git push` is preceded by `-c` config flags, so the verb is not adjacent
    # to `git`. The matcher must therefore span them -- but it must ALSO not
    # match the push-failure crit message, which contains the realign command
    # `git -C ${REPO} push origin main` as prose inside a quoted string.
    # Relying on `-C` != `-c` for that is a case accident; instead the matcher
    # is anchored to COMMAND position: the verb may only follow the start of a
    # line, a `&&`/`||`/`;`/`|` separator, or an env-assignment prefix -- never
    # arbitrary text such as the middle of a message string.
    "git push": r"(?:^|&&|\|\||;|\|)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*git(?:\s+-c\s+\S+)*\s+push\b",
    "restic backup": r"\brestic\s+backup\b",
}
MUTATION_VERB_SITES = {
    'mkdir -p "$LOGDIR"': (68,),  # data tier
    'mkdir -p "$PF_RECEIPT_DIR"': (345,),  # full tier (region B)
    "mkdir -p reports/h8_forward": (366,),  # full tier (region B, GATE_GO)
    "mkdir -p reports/h5": (428,),  # Schwab preclose lane (brief 17 WP-F)
    "git add": (582,),  # data tier, allow-list scoped (§6.4)
    "git commit": (585,),  # data tier
    "git fetch": (595,),  # data tier
    "git merge": (596,),  # data tier — mutates the working tree unattended
    "git push": (597,),  # data tier
    "restic backup": (614,),  # data tier
}
# Any mutation verb anywhere in the script must be registered above. The
# families are deliberately WIDER than what the script uses today (`git reset`,
# `git checkout`, `git rm`, `git clean`, bare `rm`, `restic forget` are all
# absent right now) so P4's "every mutation verb is classified" claim keeps
# holding when someone adds one -- the closure test fails before the verb can
# run unattended.
ANY_MUTATION_VERB_RE = re.compile(
    r"\bmkdir\b"
    r"|\bgit\s+(?:add|commit|fetch|merge|reset|checkout|rm|clean)\b"
    r"|(?:^|&&|\|\||;|\|)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*git(?:\s+-c\s+\S+)*\s+push\b"
    r"|(?:^|&&|\|\||;|\|)\s*rm\b"
    r"|\brestic\s+(?:backup|forget)\b"
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


def _region_opener(source: str, name: str) -> str:
    """The single line immediately following a region's opening marker."""
    marker = source.index(f"# ---- {name} ")
    body = source.index("\n", marker) + 1
    return source[body : source.index("\n", body)]


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
        for module in (
            DATA_TIER_MODULES + H7_TIER_SURFACES + GATE_GO_SURFACES + SCHWAB_LANE_SURFACES
        ):
            with self.subTest(module=module):
                self.assertLess(gate, _module_site_index(source, module))
        for verb, pattern in MUTATION_VERB_PATTERNS.items():
            with self.subTest(verb=verb):
                match = re.search(pattern, source)
                self.assertIsNotNone(match, verb)
                self.assertLess(gate, match.start())

    def test_pick_tracker_is_fail_soft_between_board_and_capture_receipt(self):
        source = _source()
        dashboard = source.index("python -m options_researcher.attractiveness_dashboard")
        record = source.index("python -m options_researcher.pick_tracker record")
        evaluate = source.index("python -m options_researcher.pick_tracker evaluate")
        receipt = source.index("python -m options_researcher.ritual_receipt")
        self.assertLess(dashboard, record)
        self.assertLess(record, evaluate)
        self.assertLess(evaluate, receipt)
        record_line = next(
            line
            for line in source.splitlines()
            if "python -m options_researcher.pick_tracker record" in line
        )
        evaluate_line = next(
            line
            for line in source.splitlines()
            if "python -m options_researcher.pick_tracker evaluate" in line
        )
        self.assertIn('|| note "pick tracker recorder: FAILED (isolated)"', record_line)
        self.assertIn("IMMUTABLE_HISTORY_CONFLICT", evaluate_line)
        self.assertIn('note "pick tracker evaluator: FAILED (isolated)"', evaluate_line)
        branch_start = evaluate_line.index("; if ")
        conflict_branch = evaluate_line.index("; elif ", branch_start)
        generic_branch = evaluate_line.index("; else ", conflict_branch)
        generic_note = evaluate_line.index(
            'note "pick tracker evaluator: FAILED (isolated)"', generic_branch
        )
        branch_end = evaluate_line.rindex("; fi")
        self.assertLess(branch_start, conflict_branch)
        self.assertLess(conflict_branch, generic_branch)
        self.assertLess(generic_branch, generic_note)
        self.assertLess(generic_note, branch_end)
        # Word-boundary match: a bare ``exit`` (no trailing space) evades
        # ``assertNotIn("exit ", ...)`` and would make the isolated evaluator
        # fail the whole ritual (review finding NEW-A, 2026-08-27).
        self.assertNotRegex(evaluate_line[branch_start:branch_end], r"\bexit\b")
        invocation = evaluate_line.split("2>&1", 1)[0]
        self.assertNotIn("--supersede-reason", invocation)

    def test_pick_tracker_immutability_conflict_is_named_in_ritual_output(self):
        """Execute the real evaluator line; generic isolation must not hide conflicts."""
        zsh = shutil.which("zsh")
        if not zsh:
            self.skipTest("zsh is required")
        source = _source()
        evaluate_line = next(
            line
            for line in source.splitlines()
            if "python -m options_researcher.pick_tracker evaluate" in line
        )
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "uv-stub"
            stub.write_text(
                "#!/bin/zsh\n"
                "print -u2 -- 'TrackerConflict: IMMUTABLE_HISTORY_CONFLICT: outcomes.json'\n"
                "exit 1\n"
            )
            stub.chmod(0o755)
            completed = subprocess.run(
                [
                    zsh,
                    "-c",
                    "\n".join(
                        (
                            f'UV="{stub}"',
                            'AS_OF="2026-08-27"',
                            f'LOGDIR="{tmp}"',
                            'note() { print -r -- "$1"; }',
                            evaluate_line,
                        )
                    ),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertIn("pick tracker evaluator: IMMUTABLE_HISTORY_CONFLICT", output)
        self.assertNotIn("pick tracker evaluator: FAILED (isolated)", output)

    # ---- P2 -----------------------------------------------------------------
    def test_require_full_precedes_every_h7_surface(self):
        source = _source()
        self.assertIn(REQUIRE_FULL, source)
        gate = source.index(REQUIRE_FULL)
        # Under owner decision D-1 = F1 the remaining GATE_GO lanes (H6/H8)
        # stay fenced. H10b and the H5 observer are the amended exception
        # (brief 17 WP-F) and are asserted separately, by containment in the
        # Schwab lane, not by this fence.
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
        self.assertIn(
            'exec env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority status', source
        )
        self.assertIn('PYTHON="$REPO/.venv/bin/python"', source)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1 "$PYTHON"', source)
        self.assertNotIn('$UV" run python -m data.ritual_authority', source)

    # ---- P4 -----------------------------------------------------------------
    def test_every_script_surface_is_classified(self):
        source = _source()

        module_sites = [match.group(1) for match in MODULE_SITE_RE.finditer(source)]
        self.assertEqual(
            set(module_sites),
            set(DATA_TIER_MODULES + H7_TIER_SURFACES + GATE_GO_SURFACES + SCHWAB_LANE_SURFACES),
        )
        # The gate is not a gated surface: requiring it to precede itself is
        # incoherent. It is invoked as `"$PYTHON" -m`, so the `python -m`
        # matcher cannot capture it — assert BOTH facts rather than relying on
        # that regex accident.
        for gate_module in GATE_SITES:
            self.assertNotIn(gate_module, module_sites)
            self.assertIn(f'"$PYTHON" -m {gate_module}', source)

        dash_c_lines = [number for number, line in _code_lines(source) if "python -c" in line]
        self.assertEqual(set(dash_c_lines), set(PYTHON_DASH_C_CLASSIFICATION))

        verb_lines: dict[str, tuple[int, ...]] = {}
        for verb, pattern in MUTATION_VERB_PATTERNS.items():
            hits = tuple(number for number, line in _code_lines(source) if re.search(pattern, line))
            if hits:
                verb_lines[verb] = hits
        self.assertEqual(verb_lines, MUTATION_VERB_SITES)

        # Closure over the verb families themselves: an unregistered mkdir/git/
        # restic verb anywhere in executable text fails here (mutation M10).
        registered = {number for numbers in MUTATION_VERB_SITES.values() for number in numbers}
        seen = {number for number, line in _code_lines(source) if ANY_MUTATION_VERB_RE.search(line)}
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
        schwab = _region(source, "Schwab preclose lane")
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
                elif classification == "SCHWAB_LANE":
                    self.assertTrue(schwab[0] < offset < schwab[1])
                    self.assertFalse(region_a[0] < offset < region_a[1])
                    self.assertFalse(region_b[0] < offset < region_b[1])
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

    def test_every_fenced_surface_lies_inside_a_full_tier_region(self):
        """The fence must CONTAIN the H7 surfaces, not merely precede them.

        P2's ordering assertion is satisfied by a gate that is evaluated early
        and then never consulted, so ordering alone does not prove the surfaces
        are fenced. This is the containment half.
        """
        source = _source()
        region_a = _region(source, "full-tier region A")
        region_b = _region(source, "full-tier region B")
        for module in H7_TIER_SURFACES + GATE_GO_SURFACES:
            with self.subTest(module=module):
                offset = _module_site_index(source, module)
                inside_a = region_a[0] < offset < region_a[1]
                inside_b = region_b[0] < offset < region_b[1]
                self.assertTrue(
                    inside_a or inside_b,
                    f"{module} is not inside either full-tier region",
                )

    def test_full_tier_regions_are_opened_by_the_authority_guard(self):
        """Both regions must be guarded by FULL_AUTHORITY_RC, verbatim.

        Rebinding region A's guard to the top gate's own `AUTHORITY_RC` (which
        is always 0 past the require-data gate) would un-fence every H7 surface
        while leaving the region markers, the ordering tests and the
        containment test above all satisfied. Only the literal binds it.
        Region B's `FULL_AUTHORITY_RC` conjunct is pinned here for the same
        reason: without it the H6/H8 lanes run whenever GATE_GO is 1, under an
        authority tier that never granted them.
        """
        source = _source()
        self.assertEqual(
            _region_opener(source, "full-tier region A"),
            'if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then',
        )
        self.assertEqual(
            _region_opener(source, "full-tier region B"),
            'if [ "$FULL_AUTHORITY_RC" -eq 0 ] && [ "$GATE_GO" -eq 1 ]; then',
        )
        # The gate is evaluated exactly once and its own return code is the
        # only thing either region reads.
        self.assertEqual(source.count("FULL_AUTHORITY_RC=$?"), 1)
        self.assertLess(
            source.index("FULL_AUTHORITY_RC=$?"),
            _region(source, "full-tier region A")[0],
        )

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
            # Brief 17 WP-F moved entry_watch (now the H5 observer) and the
            # H10b watcher into the unfenced Schwab preclose lane, which sits
            # after region B — so the H5 observer now follows h8_watch. Every
            # refresh-before-consumer relation the frozen order protects (QM
            # OHLCV and the feature rebuild ahead of both consumers) is intact.
            _module_site_index(source, "options_researcher.h8_watch"),
            _module_site_index(source, "options_researcher.entry_watch"),
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
        failure = 'crit "h5 observe: NONZERO EXIT"'
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

    def test_terminal_status_marks_only_single_starved_capture_critical(self):
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        source = _source()
        start = source.index('  if [ "$CRITICAL" -eq 0 ]; then')
        end = source.index('\n  "$UV" run python -m options_researcher.ritual_status', start)
        block = source[start:end]
        cases = (
            (0, 1, 1, 1, "OK"),
            (1, 1, 1, 1, "OK_STARVED"),
            (1, 1, 1, 2, "BROKEN"),
            (1, 0, 1, 1, "BROKEN"),
        )
        for critical, data_starved, starved_crit, crit_count, expected in cases:
            with self.subTest(critical=critical, crit_count=crit_count):
                script = "\n".join(
                    [
                        f"CRITICAL={critical}",
                        f"DATA_STARVED={data_starved}",
                        f"STARVED_CRIT={starved_crit}",
                        f"CRIT_COUNT={crit_count}",
                        block,
                        'print -r -- "$RITUAL_TERMINAL_STATUS"',
                    ]
                )
                completed = subprocess.run(
                    [zsh, "-c", script], capture_output=True, text=True, timeout=30
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout.strip(), expected)

    def test_guarded_closes_step_precedes_features_and_fails_soft(self):
        source = _source()
        closes_step = (
            '"$UV" run python -c "from data.recent_topup import '
            "refresh_closes_guarded; import json;"
        )
        features_step = '"$UV" run python -c "from options_researcher.features import build_all;'
        self.assertIn(closes_step, source)
        self.assertIn(features_step, source)
        self.assertLess(source.index(closes_step), source.index(features_step))
        closes_end = source.index("\n\n", source.index(closes_step))
        self.assertNotIn("crit ", source[source.index(closes_step) : closes_end])

    def test_durability_allow_list_is_tier_scoped(self):
        source = _source()
        durability = source[source.index("# Step 8 — DURABILITY") :]
        full_branch = durability.index('if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then')
        git_add = durability.index("git add --")
        self.assertLess(full_branch, git_add)

        for path in (
            "ledger/h7_forward",
            "ledger/h7_forward_schwab",
            "reports/h7_receipts",
            "reports/h7_data_gate",
            "reports/h6_forward",
            "reports/h8_forward",
        ):
            with self.subTest(path=path):
                self.assertIn(path, durability)
                self.assertGreater(durability.index(path), full_branch)
                self.assertLess(durability.index(path), git_add)

        # Data-tier paths are staged unconditionally, ahead of the branch.
        # reports/h5 and reports/h10 belong here (brief 17 review 2026-08-19):
        # the Schwab preclose lane runs OUTSIDE the H7 data-gate fence, so it
        # produces H10b/H5 evidence on data-tier days. Staging them only inside
        # the FULL_AUTHORITY_RC branch meant a registered forward window's
        # evidence was written and then never committed on exactly those days.
        # reports/schwab_chains belongs here for the same reason (2026-08-25):
        # the 15:45 capture wrapper has no commit step of its own, so the
        # ritual is the receipts' only automatic durability path and it must
        # stage them on data-tier days too.
        for path in (
            "reports/ritual",
            "reports/intraday_capture",
            "reports/live_probe",
            "reports/cache_runs",
            "reports/h5",
            "reports/h10",
            "reports/schwab_chains",
            "ledger/facts.log",
        ):
            with self.subTest(path=path):
                self.assertIn(path, durability)
                self.assertLess(durability.index(path), full_branch)

        # ...and they must NOT be re-listed inside the full-tier branch: a
        # duplicate would hide a future accidental removal from the data tier.
        full_branch_body = durability[full_branch:git_add]
        for path in ("reports/h5", "reports/h10", "reports/schwab_chains"):
            with self.subTest(path=path, where="full-tier branch"):
                self.assertNotIn(path, full_branch_body)

        # The commit message must not describe data-phase artifacts as H7
        # evidence (caution C6).
        self.assertIn("data(ritual): daily ritual data-phase artifacts ${RUN_DATE}", durability)
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
            return "\n".join(line for line in block.split("\n") if not line.strip().startswith("#"))

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
        # Brief 17 WP-F: H5 and H10b left this fence, so the paused-lane line
        # must name only the lanes still behind it. A stale "H5/H6/H8/H10"
        # line would tell the operator two running lanes were paused.
        self.assertIn('note "H6/H8 lanes: PAUSED', region_b_else)
        self.assertNotIn("H5", region_b_else)
        self.assertNotIn("H10", region_b_else)
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

    def test_final_exit_agrees_with_the_terminal_status_carve_out(self):
        """The last line the operator reads must not contradict the receipt.

        Before 2026-09-02 the terminal-status computation and the notification
        title both had the OK_STARVED carve-out, but the FINAL echo/exit
        checked raw `CRITICAL` alone -- so a chain-starved day published an
        OK_STARVED receipt and a [DATA-STARVED] notification while printing
        "RITUAL STATUS: BROKEN" and exiting 1. The LaunchAgent's exit code and
        the operator's last log line both said broken on an expected day.
        """
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        source = _source()
        start = source.index('if [ "$CRITICAL" -eq 1 ]; then', source.index("/usr/bin/osascript"))
        block = source[start:]

        cases = (
            # CRITICAL, DATA_STARVED, STARVED_CRIT, CRIT_COUNT, rc, text
            (0, 0, 0, 0, 0, "RITUAL STATUS: OK"),
            (0, 1, 1, 1, 0, "RITUAL STATUS: OK"),
            (1, 1, 1, 1, 0, "RITUAL STATUS: OK_STARVED (chain-starved; see receipt)"),
            (1, 1, 1, 2, 1, "RITUAL STATUS: BROKEN (see CRITICAL lines above)"),
            (1, 1, 0, 1, 1, "RITUAL STATUS: BROKEN (see CRITICAL lines above)"),
            (1, 0, 1, 1, 1, "RITUAL STATUS: BROKEN (see CRITICAL lines above)"),
        )
        for critical, starved, starved_crit, count, rc, text in cases:
            with self.subTest(critical=critical, count=count):
                script = "\n".join(
                    [
                        f"CRITICAL={critical}",
                        f"DATA_STARVED={starved}",
                        f"STARVED_CRIT={starved_crit}",
                        f"CRIT_COUNT={count}",
                        block,
                    ]
                )
                completed = subprocess.run(
                    [zsh, "-c", script], capture_output=True, text=True, timeout=30
                )
                self.assertEqual(completed.stdout.strip(), text, completed.stderr)
                self.assertEqual(completed.returncode, rc)

    def test_final_status_reuses_the_exact_carve_out_condition(self):
        """Static twin of the behavioral test: the three deciders must all use
        the SAME predicate, so a future edit to one is visibly a divergence."""
        source = _source()
        condition = (
            'if [ "$DATA_STARVED" -eq 1 ] && [ "$STARVED_CRIT" -eq 1 ] '
            '&& [ "$CRIT_COUNT" -eq 1 ]; then'
        )
        # terminal receipt status, notification title, final echo/exit
        self.assertEqual(source.count(condition), 3)
        final = source[source.index("/usr/bin/osascript") :]
        self.assertIn(condition, final)
        self.assertIn("RITUAL STATUS: OK_STARVED (chain-starved; see receipt)", final)
        self.assertIn("RITUAL STATUS: BROKEN (see CRITICAL lines above)", final)

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


class CacheEdgeZshExecutionTests(unittest.TestCase):
    """Execute the cache-edge starvation block under the shell that runs it.

    The 2026-08-14 production runs silently skipped starvation detection:
    ``[ "$CHAIN_EDGE" \\< "$AS_OF" ]`` is a bash-ism that zsh's POSIX ``[``
    rejects with "condition expected: <" (exit 2), and with no ``set -e`` the
    script continued with DATA_STARVED=0. Static text assertions cannot catch
    runtime shell semantics — this test runs the real block under zsh.
    """

    def _run_block(self, chain_file: str, as_of: str) -> str:
        import shutil as _shutil
        import subprocess as _sp
        import tempfile as _tf

        zsh = _shutil.which("zsh")
        if zsh is None:  # pragma: no cover - macOS always has zsh
            self.skipTest("zsh is required")
        source = Path("tools/daily_ritual.sh").read_text()
        start = source.index('CHAIN_EDGE="$(ls .cache/chains')
        end = source.index("\nfi", source.index("STARVED", start)) + len("\nfi")
        block = source[start:end]
        tmp = Path(_tf.mkdtemp())
        self.addCleanup(_shutil.rmtree, tmp, True)
        (tmp / ".cache" / "chains").mkdir(parents=True)
        if chain_file:
            (tmp / ".cache" / "chains" / chain_file).write_bytes(b"")
        script = "\n".join(
            [
                "set -u",
                'note() { print -r -- "$1"; }',
                f"AS_OF={as_of}",
                "DATA_STARVED=0",
                block,
                'print -r -- "DATA_STARVED=$DATA_STARVED"',
            ]
        )
        completed = _sp.run(
            [zsh, "-c", script], cwd=tmp, capture_output=True, text=True, timeout=30
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertNotIn("condition expected", completed.stderr)
        return completed.stdout

    def test_stale_edge_sets_starved_under_zsh(self):
        out = self._run_block("VST_2026-07-27.parquet", "2026-08-13")
        self.assertIn("DATA_STARVED=1", out)
        self.assertIn("chain-dependent lanes are STARVED", out)

    def test_current_edge_is_not_starved_under_zsh(self):
        out = self._run_block("VST_2026-08-13.parquet", "2026-08-13")
        self.assertIn("DATA_STARVED=0", out)
        self.assertNotIn("STARVED:", out)


class SchwabPrecloseLaneTests(unittest.TestCase):
    """Brief 17 WP-F: the H10b + H5-observer lane, statically and under zsh.

    The lane exists because ledger seq 28 clause 1 and seq 29 clause 2 record
    the owner-confirmed D-1=F1 override for these two lanes only: the verified
    Schwab 15:45 ET preclose capture is a qualifying exact-session source for
    them, so they leave the H7 data-gate fence while H6/H8 stay behind it.
    Everything the amendments make load-bearing is asserted here -- the lane's
    fail-closed gate, the absence of a ThetaData fallback, the retirement of
    the trigger prose (seq 29 clause 1), and the namespaced observation store.
    """

    # ---- static structure ---------------------------------------------------
    def _lane(self, source: str) -> str:
        start, end = _region(source, "Schwab preclose lane")
        return source[start:end]

    def _lane_code(self, source: str) -> str:
        """Lane text with comment-only lines removed (executable text only)."""
        return "\n".join(
            line for line in self._lane(source).split("\n") if not line.strip().startswith("#")
        )

    def test_lane_sits_outside_both_full_tier_fences(self):
        source = _source()
        region_a = _region(source, "full-tier region A")
        region_b = _region(source, "full-tier region B")
        lane = _region(source, "Schwab preclose lane")
        self.assertLess(region_b[1], lane[0])
        for module in SCHWAB_LANE_SURFACES:
            with self.subTest(module=module):
                offset = _module_site_index(source, module)
                self.assertTrue(lane[0] < offset < lane[1])
                self.assertFalse(region_a[0] < offset < region_a[1])
                self.assertFalse(region_b[0] < offset < region_b[1])
        # H6/H8 did NOT move: they stay inside the fenced region B.
        for module in ("options_researcher.h6_watch", "options_researcher.h8_watch"):
            with self.subTest(module=module):
                offset = _module_site_index(source, module)
                self.assertTrue(region_b[0] < offset < region_b[1])

    def test_lane_is_gated_on_the_shared_verified_view(self):
        source = _source()
        lane = self._lane(source)
        code = self._lane_code(source)
        # The lane's first executable statement is the fail-closed default.
        self.assertEqual(code.strip().split("\n")[0], 'SCHWAB_LANE="UNVERIFIED"')
        self.assertIn('if [ "$SCHWAB_LANE" = "VERIFIED" ]; then', lane)
        # The gate reads the same verified-view boundary h10_watch and
        # entry_watch load through -- not a second, drifting loader.
        self.assertIn("from options_researcher.schwab_chain_view import verified_sessions", lane)
        # Fail-closed default: SCHWAB_LANE is UNVERIFIED before the probe runs,
        # so a missing AS_OF or an unreadable view skips rather than proceeds.
        self.assertLess(code.index('SCHWAB_LANE="UNVERIFIED"'), code.index("verified_sessions"))
        self.assertLess(
            code.index("verified_sessions"),
            code.index('if [ "$SCHWAB_LANE" = "VERIFIED" ]; then'),
        )

    def test_lane_has_no_thetadata_fallback(self):
        """No executable statement in the lane can reach the frozen cache."""
        code = self._lane_code(_source())
        for forbidden in (".cache/chains", "thetadata", "CHAIN_EDGE", "DATA_STARVED"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, code)
        # The one place ThetaData may appear is the skip line, saying it is NOT
        # substituted -- an honest operator message, not a code path.
        self.assertIn("the frozen ThetaData cache is NOT substituted", code)

    def test_trigger_prose_is_retired_everywhere_in_the_ritual(self):
        source = _source()
        for retired in (
            "H5 ENTRY TRIGGER FIRE",
            "no trigger fired",
            "evaluate per H5 CORE rules",
            'grep -q "FIRE"',
            "h5 entry watch",
        ):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, source)
        lane = self._lane(source)
        self.assertIn("observational / non-verdict-bearing", lane)
        self.assertIn("trigger retired per ledger seq 29", lane)

    def test_h10_observe_targets_the_namespaced_store_only(self):
        from options_researcher import h10_observe

        source = _source()
        # The ritual passes no store override, so the module default decides.
        self.assertIn(
            '"$UV" run python -m options_researcher.h10_observe --as-of "$RUN_DATE" &&',
            source,
        )
        # No executable statement anywhere names the legacy store.
        self.assertNotIn(
            "reports/h10/observations.jsonl",
            "\n".join(line for _number, line in _code_lines(source)),
        )
        import inspect

        default = inspect.signature(h10_observe.main).parameters["observations_path"].default
        self.assertEqual(default, h10_observe.H10B_OBSERVATIONS_PATH)
        self.assertEqual(
            Path(h10_observe.H10B_OBSERVATIONS_PATH),
            Path("reports/h10/h10b_observations.jsonl"),
        )
        self.assertNotEqual(
            Path(h10_observe.H10B_OBSERVATIONS_PATH),
            Path(h10_observe.LEGACY_OBSERVATIONS_PATH),
        )

    # ---- behavior under the shell that actually runs it ---------------------
    def _run_lane(self, **env: str) -> tuple[str, str]:
        """Execute the real lane block under zsh with a stub `uv`.

        Static text cannot show which commands actually run, with which
        `--as-of`, or whether a refusal becomes a CRITICAL. The stub records
        every invocation and returns the exit codes the caller chooses.
        """
        import os as _os
        import shutil as _shutil
        import subprocess as _sp
        import tempfile as _tf

        zsh = _shutil.which("zsh")
        if zsh is None:  # pragma: no cover - macOS always has zsh
            self.skipTest("zsh is required")
        lane = self._lane(_source())
        tmp = Path(_tf.mkdtemp())
        self.addCleanup(_shutil.rmtree, tmp, True)
        calls = tmp / "calls.txt"
        stub = tmp / "uv-stub"
        stub.write_text(
            "#!/bin/zsh\n"
            'case "$*" in\n'
            '  *verified_sessions*) print -r -- "$STUB_VERIFIED"; exit 0 ;;\n'
            "  *'import options_researcher.h10_watch'*) exit ${STUB_H10_IMPORT_RC:-0} ;;\n"
            '  *entry_watch*) print -r -- "entry_watch $*" >> "$CALLS"; '
            "exit ${STUB_EW_RC:-0} ;;\n"
            '  *h10_watch*) print -r -- "h10_watch $*" >> "$CALLS"; '
            "exit ${STUB_H10W_RC:-0} ;;\n"
            '  *h10_observe*) print -r -- "h10_observe $*" >> "$CALLS"; '
            "exit ${STUB_H10O_RC:-0} ;;\n"
            '  *) print -r -- "UNEXPECTED $*" >> "$CALLS"; exit 0 ;;\n'
            "esac\n"
        )
        stub.chmod(0o755)
        script = "\n".join(
            [
                "set -u",
                'note() { print -r -- "NOTE: $1"; }',
                "CRITICAL=0",
                'crit() { CRITICAL=1; note "CRITICAL: $1"; }',
                f'UV="{stub}"',
                "AS_OF=2026-08-20",
                "RUN_DATE=2026-08-21",
                lane,
                'print -r -- "CRITICAL=$CRITICAL"',
            ]
        )
        environment = {**_os.environ, "CALLS": str(calls), "STUB_VERIFIED": "VERIFIED"}
        environment.update(env)
        completed = _sp.run(
            [zsh, "-c", script],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=60,
            env=environment,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        recorded = calls.read_text() if calls.exists() else ""
        return completed.stdout, recorded

    def test_unverified_session_skips_both_lanes_visibly(self):
        out, calls = self._run_lane(STUB_VERIFIED="UNVERIFIED")
        self.assertIn("H10b + H5 observe lanes: SKIPPED", out)
        self.assertIn("no verified Schwab 15:45 preclose capture", out)
        self.assertIn("CRITICAL=0", out)
        self.assertEqual(calls, "")

    def test_unreadable_verified_view_also_skips(self):
        """An empty/garbled probe answer must skip, never proceed."""
        out, calls = self._run_lane(STUB_VERIFIED="")
        self.assertIn("H10b + H5 observe lanes: SKIPPED", out)
        self.assertEqual(calls, "")

    def test_verified_session_runs_both_lanes_on_the_run_date(self):
        out, calls = self._run_lane()
        self.assertIn("entry_watch --as-of 2026-08-21", calls)
        self.assertIn("h10_watch --as-of 2026-08-21", calls)
        self.assertIn("h10_observe --as-of 2026-08-21", calls)
        # The evaluation session is resolved by the modules themselves; passing
        # AS_OF would evaluate the session BEFORE the evaluation session.
        self.assertNotIn("--as-of 2026-08-20", calls)
        self.assertIn("observational / non-verdict-bearing", out)
        self.assertNotIn("FIRE", out)
        self.assertIn("CRITICAL=0", out)

    def test_pre_floor_refusals_are_noted_not_critical(self):
        out, calls = self._run_lane(STUB_EW_RC="2", STUB_H10W_RC="2")
        self.assertIn("h5 observe: REFUSED", out)
        self.assertIn("H5_RESUME_FLOOR_SESSION", out)
        self.assertIn("h10b watch: REFUSED", out)
        self.assertIn("H10B_RESUME_FLOOR_SESSION", out)
        # No watcher receipt exists, so nothing may be appended.
        self.assertIn("h10_observe: SKIPPED", out)
        self.assertNotIn("h10_observe --as-of", calls)
        self.assertIn("CRITICAL=0", out)

    def test_h5_data_gap_is_visible_and_not_critical(self):
        out, _calls = self._run_lane(STUB_EW_RC="1")
        self.assertIn("h5 observe: DATA GAP", out)
        self.assertIn("CRITICAL=0", out)

    def test_unexpected_exit_codes_stay_critical(self):
        out, _calls = self._run_lane(STUB_EW_RC="3", STUB_H10W_RC="4")
        self.assertIn("CRITICAL: h5 observe: NONZERO EXIT", out)
        self.assertIn("CRITICAL: h10_watch: NONZERO EXIT", out)
        self.assertIn("CRITICAL=1", out)

    def test_missing_h10_module_is_critical(self):
        out, calls = self._run_lane(STUB_H10_IMPORT_RC="1")
        self.assertIn("CRITICAL: h10_watch: module unavailable", out)
        self.assertNotIn("h10_watch --as-of", calls)
