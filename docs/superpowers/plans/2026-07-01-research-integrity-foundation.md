# Research Integrity Foundation (Phase 1A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the code-enforced research-integrity substrate (append-only hash-chained ledger, pre-registration + write-once OOS gate with enforced `IN_SAMPLE_END` and a global look budget, monotonic intent-to-select counter, one canonical frozen cost-model hash) and replace the IID bootstrap in `metrics.py` with a dependence-aware (weekly-cohort block bootstrap + stationary cross-check, widest-CI envelope) one — so run #1 records an honest result.

**Architecture:** A new `research/` package holds focused, independently testable modules (`hashing`, `ledger`, `windows`, `experiments`, `cli`, `facts`); `metrics.py` gets the bootstrap replacement; `config.py` gets the frozen knobs; `harness/run_backtest.py` gets a thin OOS-reveal seam that still stops at `NotImplementedError` for the (unwired) ThetaData fetch. Everything is exercised against synthetic trades — no network, no ThetaData, no Lumibot.

**Tech Stack:** Python 3.12 via `uv`; numpy; stdlib `unittest` (NOT pytest); git.

---

## Context an implementing engineer needs

- **Run everything through `uv`:** `uv run python ...` and `uv run python -m unittest ...`. Never bare `python`.
- **Tests are stdlib `unittest`.** Discover with `uv run python -m unittest discover -s tests`; run one with `uv run python -m unittest tests.test_x.Class.test_method -v`.
- **The spec is the source of truth:** `docs/superpowers/specs/2026-07-01-research-integrity-foundation-design.md` in the current worktree. Check `git status` before assuming it has been committed.
- **`ASSUMED_CREDIT_FRAC` lives in `analysis/feasibility.py:25`, not `config.py`** — that's exactly why the frozen cost model is one explicit snapshot object, not a line/string search.
- **The current scoreboard contract is `{pnl, capital_at_risk}`** ([metrics.py:26-53](../../../metrics.py#L26-L53)); Phase 1A tightens it to also require `entry_date` and `symbol`, raising on absence (no silent IID fallback).
- **Ledger tests must never write to the repo's real `ledger/` dir.** Every test passes a `base_dir` pointing at a `tempfile.TemporaryDirectory()`.
- **Do NOT wire ThetaData or Lumibot.** The Phase-0 stubs stay stubs; `harness/run_backtest.run()` keeps raising `NotImplementedError`.
- **Do not commit unless the user explicitly asks.** The `git add` / `git commit`
  blocks below are commit checkpoints for an approved committing run; otherwise
  implement and verify without writing git history.

## File map

- Modify: `config.py` — add `OOS_LOOK_BUDGET`, `BOOTSTRAP_BLOCK_EXPONENT`, `BOOTSTRAP_BLOCK_CONSTANTS`, `COHORT_GRANULARITY`, `FILL_MODEL_ID`.
- Create: `research/__init__.py` — empty package marker.
- Create: `research/hashing.py` — canonical JSON + SHA-256 helpers; `cost_model_snapshot()`/`cost_model_hash()`/`config_hash()`/`source_hash()`/`data_window_hash()`.
- Create: `research/ledger.py` — append-only hash-chained JSONL store + `HEAD` pointer + `verify([anchored])` + `current_trial_count()`.
- Create: `research/windows.py` — pure IS/OOS split at `IN_SAMPLE_END`.
- Create: `research/experiments.py` — `register()`, `log_trial_intent()`, `reveal_oos()`.
- Create: `research/cli.py` — hook-able subcommands `register` / `reveal-oos` / `trial-log` / `verify`.
- Create: `research/facts.py` — append-only descriptive facts log (non-verdict-feeding).
- Modify: `metrics.py` — require `entry_date`/`symbol`; replace `_expectancy_ci` with the cohort/stationary envelope; add explicit `iid_expectancy_ci` helper; cohort-count verdict guard; update `_demo`.
- Modify: `harness/run_backtest.py` — add `reveal_out_of_sample()` seam delegating to `research.experiments.reveal_oos`.
- Create: `ledger/README.md`, `ledger/.gitkeep` — the committed research-record location.
- Modify: `tests/test_core.py` — update `ScoreboardTests` for the new required fields.
- Create: `tests/test_research_integrity.py` — hashing/ledger/windows/experiments/cli/facts/seam.
- Create: `tests/test_bootstrap.py` — cohorts/block-lengths/resamplers/envelope/dependence/contract.

---

## Task 1: Config — frozen integrity knobs (TDD)

**Files:**
- Modify: `config.py` (append a new section at end)
- Test: `tests/test_research_integrity.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_research_integrity.py`:

```python
import unittest

import config


class ConfigKnobTests(unittest.TestCase):
    def test_oos_look_budget_is_three(self):
        self.assertEqual(config.OOS_LOOK_BUDGET, 3)

    def test_block_exponent_is_one_third(self):
        self.assertAlmostEqual(config.BOOTSTRAP_BLOCK_EXPONENT, 1.0 / 3.0)

    def test_block_constants_are_the_frozen_envelope(self):
        self.assertEqual(list(config.BOOTSTRAP_BLOCK_CONSTANTS), [0.5, 1, 2, 4])

    def test_cohort_granularity_is_week(self):
        self.assertEqual(config.COHORT_GRANULARITY, "week")

    def test_fill_model_id_is_versioned_string(self):
        self.assertEqual(config.FILL_MODEL_ID, "conservative_mid_minus_haircut_v1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.ConfigKnobTests -v`
Expected: FAIL — `AttributeError: module 'config' has no attribute 'OOS_LOOK_BUDGET'`.

- [ ] **Step 3: Add the constants to `config.py`**

Append to the end of `config.py`:

```python

# ---------------------------------------------------------------------------
# RESEARCH INTEGRITY (Phase 1A) -- frozen, verdict-affecting knobs
# ---------------------------------------------------------------------------
# These are hashed into the cost-model snapshot (research/hashing.py) and
# FROZEN before any out-of-sample reveal. Changing one starts a NEW
# pre-registered hypothesis; it must never be quietly retuned toward a PASS.
OOS_LOOK_BUDGET          = 3      # global cap on distinct hypotheses that may reveal OOS
BOOTSTRAP_BLOCK_EXPONENT = 1 / 3  # n^(1/3) blocking rate (Politis-White / Lahiri)
BOOTSTRAP_BLOCK_CONSTANTS = [0.5, 1, 2, 4]  # mean block = round(c * n_cohorts**exp)
COHORT_GRANULARITY       = "week"  # cross-sectional cohort key = ISO week of entry_date
FILL_MODEL_ID            = "conservative_mid_minus_haircut_v1"  # bump if fill logic changes
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.ConfigKnobTests -v`
Expected: PASS (5 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add config.py tests/test_research_integrity.py
git commit -m "feat(config): add frozen Phase-1A integrity knobs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `research/hashing.py` — one canonical hashable surface (TDD)

**Files:**
- Create: `research/__init__.py`, `research/hashing.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py`:

```python
import math
import pathlib
import tempfile

from analysis import feasibility
from research import hashing


class HashingTests(unittest.TestCase):
    def test_canonical_json_is_sorted_and_compact(self):
        self.assertEqual(hashing.canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_canonical_json_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            hashing.canonical_json({"bad": math.nan})

    def test_cost_model_snapshot_includes_scattered_credit_frac(self):
        snap = hashing.cost_model_snapshot()
        # ASSUMED_CREDIT_FRAC lives in feasibility.py, not config -- must be captured.
        self.assertEqual(snap["ASSUMED_CREDIT_FRAC"], feasibility.ASSUMED_CREDIT_FRAC)
        for key in ("SLIPPAGE_HAIRCUT", "MAX_SPREAD_PCT", "MIN_OPEN_INTEREST",
                    "FILL_MODEL_ID", "BOOTSTRAP_BLOCK_CONSTANTS", "COHORT_GRANULARITY",
                    "OOS_LOOK_BUDGET"):
            self.assertIn(key, snap)

    def test_cost_model_hash_is_deterministic(self):
        self.assertEqual(hashing.cost_model_hash(), hashing.cost_model_hash())

    def test_cost_model_hash_changes_when_a_frozen_param_changes(self):
        before = hashing.cost_model_hash()
        original = config.SLIPPAGE_HAIRCUT
        try:
            config.SLIPPAGE_HAIRCUT = original + 0.01
            self.assertNotEqual(hashing.cost_model_hash(), before)
        finally:
            config.SLIPPAGE_HAIRCUT = original

    def test_data_window_hash_is_stable_for_equal_windows(self):
        w = {"start": "2018-01-01", "end": "2022-12-31", "universe": ["SPY"]}
        self.assertEqual(hashing.data_window_hash(w), hashing.data_window_hash(dict(w)))

    def test_source_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "a.py").write_text("X = 1\n")
            self.assertEqual(
                hashing.source_hash(paths=("a.py",), root=tmp),
                hashing.source_hash(paths=("a.py",), root=tmp),
            )

    def test_source_snapshot_default_root_includes_config(self):
        self.assertIn("config.py", hashing.source_snapshot())

    def test_source_snapshot_default_root_includes_dependency_lock_surface(self):
        snap = hashing.source_snapshot()
        self.assertIn("pyproject.toml", snap)
        self.assertIn("uv.lock", snap)

    def test_source_hash_changes_when_source_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp, "a.py")
            path.write_text("X = 1\n")
            before = hashing.source_hash(paths=("a.py",), root=tmp)
            path.write_text("X = 2\n")
            self.assertNotEqual(hashing.source_hash(paths=("a.py",), root=tmp), before)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.HashingTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research'`.

- [ ] **Step 3: Create the package marker**

Create `research/__init__.py` (empty file):

```python
```

- [ ] **Step 4: Create `research/hashing.py`**

```python
"""
research/hashing.py -- deterministic hashing surfaces for the ledger.

The frozen cost/fill params are scattered across files (ASSUMED_CREDIT_FRAC is
in analysis/feasibility.py, the rest in config.py), so we hash ONE explicit
snapshot object -- never a line/string search that could silently miss a param.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import config
from analysis import feasibility

SOURCE_HASH_PATHS = (
    "pyproject.toml",
    "uv.lock",
    "config.py",
    "metrics.py",
    "analysis",
    "data",
    "harness",
    "research",
    "strategies",
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def canonical_json(obj) -> str:
    """Stable serialization: sorted keys, compact, ASCII."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cost_model_snapshot() -> dict:
    """The single frozen, verdict-affecting surface. Hashed into cost_model_hash."""
    return {
        "SLIPPAGE_HAIRCUT": config.SLIPPAGE_HAIRCUT,
        "MAX_SPREAD_PCT": config.MAX_SPREAD_PCT,
        "MIN_OPEN_INTEREST": config.MIN_OPEN_INTEREST,
        "HALF_SPREAD_COST": config.HALF_SPREAD_COST,
        "COMMISSION_PER_CONTRACT": config.COMMISSION_PER_CONTRACT,
        "ASSUMED_CREDIT_FRAC": feasibility.ASSUMED_CREDIT_FRAC,
        "FILL_MODEL_ID": config.FILL_MODEL_ID,
        "BOOTSTRAP_BLOCK_EXPONENT": config.BOOTSTRAP_BLOCK_EXPONENT,
        "BOOTSTRAP_BLOCK_CONSTANTS": list(config.BOOTSTRAP_BLOCK_CONSTANTS),
        "COHORT_GRANULARITY": config.COHORT_GRANULARITY,
        "OOS_LOOK_BUDGET": config.OOS_LOOK_BUDGET,
    }


def cost_model_hash() -> str:
    return sha256_hex(canonical_json(cost_model_snapshot()))


def config_hash() -> str:
    """Provenance hash of ALL uppercase config constants (a superset of the snapshot)."""
    vals = {k: getattr(config, k) for k in dir(config)
            if k.isupper() and not k.startswith("_")}
    return sha256_hex(canonical_json(vals))


def source_snapshot(paths=SOURCE_HASH_PATHS, root=None) -> dict:
    """Hash the verdict/backtest source surface, excluding ledgers and outputs.

    This is intentionally separate from `git rev-parse HEAD`: ledger anchoring
    commits should not invalidate a pre-registration, while source/config changes
    that affect the hypothesis must.
    """
    root_path = Path(root) if root is not None else REPO_ROOT
    out = {}
    for item in paths:
        path = root_path / item
        if path.is_dir():
            files = sorted(
                p for p in path.rglob("*.py")
                if "__pycache__" not in p.parts
            )
        elif path.is_file():
            files = [path]
        else:
            continue
        for file_path in files:
            rel = file_path.relative_to(root_path).as_posix()
            out[rel] = sha256_file(file_path)
    return out


def source_hash(paths=SOURCE_HASH_PATHS, root=None) -> str:
    return sha256_hex(canonical_json(source_snapshot(paths=paths, root=root)))


def data_window_hash(window: dict) -> str:
    """Hash of the data-window identity. Once ThetaData is wired this also folds in
    a content digest of the cached chains; in Phase 1A it hashes the identity dict."""
    return sha256_hex(canonical_json(window))
```

- [ ] **Step 5: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.HashingTests -v`
Expected: PASS (10 tests OK).

- [ ] **Step 6: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/__init__.py research/hashing.py tests/test_research_integrity.py
git commit -m "feat(research): canonical cost-model snapshot + hashes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `research/ledger.py` — append-only hash chain + HEAD + verify (TDD)

**Files:**
- Create: `research/ledger.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `import tempfile`,
`from pathlib import Path`, and `from research import ledger` at the top of the
file with the other imports):

```python
class LedgerChainTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_chains_and_verifies(self):
        ledger.append({"entry_type": "trial_intent", "reason": "first"}, self.base)
        ledger.append({"entry_type": "trial_intent", "reason": "second"}, self.base)
        ledger.verify(self.base)  # must not raise
        records = ledger.read_all(self.base)
        self.assertEqual([r["seq"] for r in records], [0, 1])
        self.assertEqual(records[1]["prev_hash"], records[0]["record_hash"])

    def test_head_matches_tip(self):
        h = ledger.append({"entry_type": "trial_intent", "reason": "x"}, self.base)
        self.assertEqual(ledger.tip(self.base), h)

    def test_verify_detects_a_tampered_record(self):
        ledger.append({"entry_type": "trial_intent", "reason": "keep"}, self.base)
        ledger.append({"entry_type": "trial_intent", "reason": "keep2"}, self.base)
        jsonl = Path(self.base) / "experiments.jsonl"
        lines = jsonl.read_text().splitlines()
        lines[0] = lines[0].replace("keep", "HACKED")
        jsonl.write_text("\n".join(lines) + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)

    def test_verify_wraps_invalid_json_as_ledger_error(self):
        ledger.append({"entry_type": "trial_intent", "reason": "keep"}, self.base)
        (Path(self.base) / "experiments.jsonl").write_text("{not json}\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)

    def test_verify_detects_head_mismatch(self):
        ledger.append({"entry_type": "trial_intent", "reason": "x"}, self.base)
        (Path(self.base) / "HEAD").write_text("0" * 64 + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)

    def test_trial_counter_counts_runs_and_intents_only(self):
        ledger.append({"entry_type": "trial_intent", "reason": "a"}, self.base)
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        ledger.append({"entry_type": "oos_reveal", "hypothesis_id": "H1"}, self.base)
        self.assertEqual(ledger.current_trial_count(self.base), 2)

    def test_append_rejects_reserved_chain_fields(self):
        for key in ("seq", "prev_hash", "record_hash"):
            with self.subTest(key=key):
                with self.assertRaises(ledger.LedgerError):
                    ledger.append({"entry_type": "trial_intent", key: "bad"}, self.base)

    def test_append_refuses_to_build_on_broken_chain(self):
        ledger.append({"entry_type": "trial_intent", "reason": "keep"}, self.base)
        (Path(self.base) / "HEAD").write_text("0" * 64 + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.append({"entry_type": "trial_intent", "reason": "next"}, self.base)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.LedgerChainTests -v`
Expected: FAIL — `AttributeError: module 'research.ledger' has no attribute 'append'` (or import error).

- [ ] **Step 3: Create `research/ledger.py`**

```python
"""
research/ledger.py -- append-only, hash-chained JSONL experiment ledger.

The chain IS the tamper-evidence: each record commits to the previous one.
A second tracked file, HEAD, holds the current tip so it is diffable in git.
"""
from __future__ import annotations
from pathlib import Path

from research.hashing import canonical_json, sha256_hex

GENESIS_PREV = "0" * 64
TRIAL_TYPES = {"run", "trial_intent"}
RESERVED_KEYS = {"seq", "prev_hash", "record_hash"}
REPO_ROOT = Path(__file__).resolve().parents[1]


class LedgerError(Exception):
    pass


def _paths(base_dir):
    base = Path(base_dir)
    return base / "experiments.jsonl", base / "HEAD"


def read_all(base_dir="ledger") -> list[dict]:
    jsonl, _ = _paths(base_dir)
    if not jsonl.exists():
        return []
    import json
    records = []
    for lineno, line in enumerate(jsonl.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"invalid JSON at ledger line {lineno}: {exc}") from exc
    return records


def tip(base_dir="ledger") -> str:
    _, head = _paths(base_dir)
    return head.read_text().strip() if head.exists() else GENESIS_PREV


def _record_hash(record_without_hash: dict) -> str:
    return sha256_hex(canonical_json(record_without_hash))


def append(body: dict, base_dir="ledger") -> str:
    reserved = RESERVED_KEYS & body.keys()
    if reserved:
        raise LedgerError(f"ledger body uses reserved field(s): {sorted(reserved)}")
    verify(base_dir)
    jsonl, head = _paths(base_dir)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    records = read_all(base_dir)
    prev = tip(base_dir)
    record = dict(body)
    record["seq"] = len(records)
    record["prev_hash"] = prev
    record["record_hash"] = _record_hash(record)  # record has no record_hash key yet
    with jsonl.open("a") as f:
        f.write(canonical_json(record) + "\n")
    head.write_text(record["record_hash"] + "\n")
    return record["record_hash"]


def verify(base_dir="ledger", anchored=False, git_clean_tracked=None) -> None:
    records = read_all(base_dir)
    prev = GENESIS_PREV
    for i, rec in enumerate(records):
        if rec.get("seq") != i:
            raise LedgerError(f"seq mismatch at index {i}: {rec.get('seq')}")
        if rec.get("prev_hash") != prev:
            raise LedgerError(f"prev_hash break at seq {i}")
        body = {k: v for k, v in rec.items() if k != "record_hash"}
        if rec.get("record_hash") != _record_hash(body):
            raise LedgerError(f"record_hash mismatch at seq {i}")
        prev = rec["record_hash"]
    if tip(base_dir) != prev:
        raise LedgerError("HEAD does not match chain tip")
    if anchored:
        _require_committed_clean(base_dir, git_clean_tracked)


def current_trial_count(base_dir="ledger") -> int:
    return sum(1 for r in read_all(base_dir) if r.get("entry_type") in TRIAL_TYPES)


def _require_committed_clean(base_dir, git_clean_tracked=None) -> None:
    jsonl, head = _paths(base_dir)
    checker = git_clean_tracked or _git_clean_tracked_default
    if not checker([str(jsonl), str(head)]):
        raise LedgerError(
            "ledger not committed / working tree dirty -- commit ledger before OOS reveal")


def _git_clean_tracked_default(paths) -> bool:
    """True iff every path is git-tracked and has no uncommitted changes."""
    import subprocess
    for p in paths:
        tracked = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", p],
            capture_output=True, text=True)
        if tracked.returncode != 0:
            return False
        status = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", p],
            capture_output=True, text=True)
        if status.stdout.strip():
            return False
    return True
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.LedgerChainTests -v`
Expected: PASS (8 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/ledger.py tests/test_research_integrity.py
git commit -m "feat(research): append-only hash-chained ledger with HEAD + verify

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Ledger anchoring — `verify(anchored=True)` (TDD, real temp git repo)

**Files:**
- Modify: `research/ledger.py` (already implemented in Task 3; this task tests the real git path)
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `import subprocess` and `import os` at the top with the other imports):

```python
class LedgerAnchoringTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(["git", "-C", self.repo, "config", "user.email", "t@t.t"], check=True)
        subprocess.run(["git", "-C", self.repo, "config", "user.name", "t"], check=True)
        self.base = os.path.join(self.repo, "ledger")

    def tearDown(self):
        self._tmp.cleanup()

    def _clean_tracked(self, paths):
        # Same semantics as the default, but scoped to the temp repo via git -C.
        for p in paths:
            rel = os.path.relpath(p, self.repo)
            t = subprocess.run(["git", "-C", self.repo, "ls-files", "--error-unmatch", rel],
                               capture_output=True, text=True)
            if t.returncode != 0:
                return False
            s = subprocess.run(["git", "-C", self.repo, "status", "--porcelain", "--", rel],
                               capture_output=True, text=True)
            if s.stdout.strip():
                return False
        return True

    def test_anchored_verify_fails_when_uncommitted(self):
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base, anchored=True, git_clean_tracked=self._clean_tracked)

    def test_anchored_verify_passes_when_committed_clean(self):
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        subprocess.run(["git", "-C", self.repo, "add", "ledger"], check=True)
        subprocess.run(["git", "-C", self.repo, "commit", "-q", "-m", "anchor"], check=True)
        ledger.verify(self.base, anchored=True, git_clean_tracked=self._clean_tracked)  # no raise

    def test_default_clean_checker_is_repo_root_scoped(self):
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        subprocess.run(["git", "-C", self.repo, "add", "ledger"], check=True)
        subprocess.run(["git", "-C", self.repo, "commit", "-q", "-m", "anchor"], check=True)

        old_root = ledger.REPO_ROOT
        old_cwd = os.getcwd()
        try:
            ledger.REPO_ROOT = Path(self.repo)
            os.chdir(Path(self.repo).parent)
            ledger.verify(self.base, anchored=True)  # no injected checker
        finally:
            os.chdir(old_cwd)
            ledger.REPO_ROOT = old_root
```

- [ ] **Step 2: Run it and confirm it fails, then passes**

Run: `uv run python -m unittest tests.test_research_integrity.LedgerAnchoringTests -v`
Expected: PASS — the anchoring logic already exists from Task 3, so all 3 tests
pass immediately. (If `verify` did not accept `git_clean_tracked`, this would
error; confirm the signature added in Task 3 is present.)

- [ ] **Step 3: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add tests/test_research_integrity.py
git commit -m "test(research): anchored verify requires committed clean ledger

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `research/windows.py` — enforce the IS/OOS split (TDD)

**Files:**
- Create: `research/windows.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `from research import windows`):

```python
class WindowTests(unittest.TestCase):
    def test_split_partitions_at_in_sample_end(self):
        dates = ["2021-06-01", "2022-12-31", "2023-01-01", "2024-05-05"]
        is_idx, oos_idx = windows.split_is_oos(dates, "2022-12-31")
        self.assertEqual(is_idx, [0, 1])   # <= 2022-12-31 is in-sample
        self.assertEqual(oos_idx, [2, 3])  # strictly after is out-of-sample

    def test_assert_oos_only_raises_on_in_sample_leak(self):
        with self.assertRaises(ValueError):
            windows.assert_oos_only(["2023-02-01", "2022-11-01"], "2022-12-31")

    def test_assert_oos_only_accepts_pure_oos(self):
        windows.assert_oos_only(["2023-02-01", "2024-01-01"], "2022-12-31")  # no raise

    def test_assert_within_window_accepts_registered_range(self):
        windows.assert_within_window(
            ["2023-01-01", "2024-12-31"],
            {"start": "2023-01-01", "end": "2024-12-31"},
        )

    def test_assert_within_window_rejects_before_start(self):
        with self.assertRaises(ValueError):
            windows.assert_within_window(
                ["2022-12-31", "2023-01-02"],
                {"start": "2023-01-01", "end": "2024-12-31"},
            )

    def test_assert_within_window_rejects_after_end(self):
        with self.assertRaises(ValueError):
            windows.assert_within_window(
                ["2024-12-31", "2025-01-01"],
                {"start": "2023-01-01", "end": "2024-12-31"},
            )

    def test_assert_within_window_rejects_invalid_date_type(self):
        with self.assertRaises(ValueError):
            windows.assert_within_window(
                [123],
                {"start": "2023-01-01", "end": "2024-12-31"},
            )

    def test_split_rejects_invalid_date_type(self):
        with self.assertRaises(ValueError):
            windows.split_is_oos([object()], "2022-12-31")
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.WindowTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.windows'`.

- [ ] **Step 3: Create `research/windows.py`**

```python
"""
research/windows.py -- the in-sample / out-of-sample boundary at IN_SAMPLE_END.

Keyed on ENTRY date: a trade belongs to the window in which the decision was
made. Keying on exit date would reintroduce look-ahead.
"""
from __future__ import annotations
from datetime import date


def _as_date(x):
    if isinstance(x, date):
        return x
    if isinstance(x, str):
        try:
            return date.fromisoformat(x)
        except ValueError as exc:
            raise ValueError(f"invalid ISO date: {x!r}") from exc
    raise ValueError(f"expected ISO date string or date object, got {type(x).__name__}")


def split_is_oos(entry_dates, in_sample_end):
    """Return (is_indices, oos_indices). In-sample = entry <= IN_SAMPLE_END."""
    end = _as_date(in_sample_end)
    is_idx = [i for i, d in enumerate(entry_dates) if _as_date(d) <= end]
    oos_idx = [i for i, d in enumerate(entry_dates) if _as_date(d) > end]
    return is_idx, oos_idx


def assert_oos_only(entry_dates, in_sample_end) -> None:
    """Raise if any trade is dated on/before IN_SAMPLE_END (a leak into OOS)."""
    end = _as_date(in_sample_end)
    leaked = [d for d in entry_dates if _as_date(d) <= end]
    if leaked:
        raise ValueError(
            f"OOS evaluation contains {len(leaked)} in-sample-dated trade(s): {leaked[:3]}")


def assert_within_window(entry_dates, window) -> None:
    """Raise if any entry date falls outside the registered [start, end] window."""
    start = _as_date(window["start"])
    end = _as_date(window["end"])
    outside = [d for d in entry_dates if not (start <= _as_date(d) <= end)]
    if outside:
        raise ValueError(
            f"evaluation contains {len(outside)} trade(s) outside registered "
            f"window {start.isoformat()}..{end.isoformat()}: {outside[:3]}")
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.WindowTests -v`
Expected: PASS (8 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/windows.py tests/test_research_integrity.py
git commit -m "feat(research): enforce IS/OOS split at IN_SAMPLE_END

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `research/experiments.py` — register + trial counter (TDD)

**Files:**
- Create: `research/experiments.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `from research import experiments`):

```python
def _window():
    return {"start": "2018-01-01", "end": "2024-12-31",
            "is_window": {"start": "2018-01-01", "end": "2022-12-31"},
            "oos_window": {"start": "2023-01-01", "end": "2024-12-31"},
            "universe": ["SPY"]}


class RegisterCounterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True  # simulate a committed-clean source surface

    def tearDown(self):
        self._tmp.cleanup()

    def test_register_writes_run_record_with_null_oos(self):
        experiments.register("H1", "expectancy CI lower bound > 0",
                             is_result={"verdict": "NO EDGE"},
                             data_window=_window(), risk_basis="economic_max_loss",
                             base_dir=self.base, code_sha="deadbeef",
                             source_clean_tracked=self.clean)
        rec = ledger.read_all(self.base)[-1]
        self.assertEqual(rec["entry_type"], "run")
        self.assertEqual(rec["hypothesis_id"], "H1")
        self.assertIsNone(rec["oos_result"])
        self.assertIsNone(rec["deflated_sharpe"])  # Phase-1B stub
        self.assertIsNone(rec["pbo"])              # Phase-1B stub
        self.assertEqual(rec["source_hash"], hashing.source_hash())

    def test_counter_increments_on_register_and_trial_log_only(self):
        experiments.log_trial_intent("eyeballed a 25-delta", base_dir=self.base)
        experiments.register("H1", "t", is_result={}, data_window=_window(),
                             risk_basis="economic_max_loss", base_dir=self.base,
                             code_sha="deadbeef",
                             source_clean_tracked=self.clean)
        self.assertEqual(experiments.current_trial_count(self.base), 2)

    def test_counter_is_monotonic_and_non_resettable(self):
        experiments.log_trial_intent("a", base_dir=self.base)
        experiments.log_trial_intent("b", base_dir=self.base)
        # No API decrements it, and any tamper is caught by verify():
        ledger.verify(self.base)
        self.assertEqual(experiments.current_trial_count(self.base), 2)

    def test_register_rejects_duplicate_hypothesis_id(self):
        experiments.register("H1", "t", is_result={}, data_window=_window(),
                             risk_basis="economic_max_loss", base_dir=self.base,
                             code_sha="deadbeef",
                             source_clean_tracked=self.clean)
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("H1", "t2", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef",
                                 source_clean_tracked=self.clean)

    def test_register_rejects_dirty_source_surface(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hdirty", "t", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef",
                                 source_clean_tracked=lambda paths: False)

    def test_register_rejects_unknown_risk_basis(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hbad", "t", is_result={}, data_window=_window(),
                                 risk_basis="typo", base_dir=self.base,
                                 code_sha="deadbeef",
                                 source_clean_tracked=self.clean)

    def test_register_rejects_empty_identity_or_threshold(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("", "t", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef",
                                 source_clean_tracked=self.clean)
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("H1", "", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef",
                                 source_clean_tracked=self.clean)

    def test_register_rejects_malformed_data_window(self):
        bad = dict(_window())
        del bad["oos_window"]
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hbadwindow", "t", is_result={}, data_window=bad,
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef",
                                 source_clean_tracked=self.clean)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.RegisterCounterTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.experiments'`.

- [ ] **Step 3: Create `research/experiments.py`**

```python
"""
research/experiments.py -- pre-registration, trial counting, and the OOS gate.

register()        -> write a run record (IS result), oos_result null; +1 trial.
log_trial_intent()-> record an intent-to-select that was not a full run; +1 trial.
reveal_oos()      -> the ONLY path that populates an out-of-sample result (Task 7).
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import config
from research import hashing, ledger, windows


class OOSGateError(Exception):
    pass


VALID_RISK_BASES = {"capital_at_risk", "economic_max_loss"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _code_sha():
    import subprocess
    out = subprocess.run(
        ["git", "-C", str(hashing.REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return out.stdout.strip() or "unknown"


def _require_non_empty_text(value, field_name) -> None:
    if not isinstance(value, str) or not value.strip():
        raise OOSGateError(f"{field_name} must be a non-empty string")


def _require_window(data_window, key) -> dict:
    if not isinstance(data_window, dict) or not isinstance(data_window.get(key), dict):
        raise OOSGateError(f"data_window.{key} must contain start/end")
    window = data_window[key]
    try:
        windows.assert_within_window([window["start"], window["end"]], window)
    except (KeyError, TypeError, ValueError) as exc:
        raise OOSGateError(f"data_window.{key} must contain valid start/end") from exc
    return dict(window)


def _source_paths():
    import subprocess
    tracked = subprocess.run(
        ["git", "-C", str(hashing.REPO_ROOT), "ls-files", *hashing.SOURCE_HASH_PATHS],
        capture_output=True, text=True)
    paths = set(hashing.source_snapshot().keys())
    explicit_files = {
        p for p in hashing.SOURCE_HASH_PATHS
        if "." in p.rsplit("/", 1)[-1]
    }
    dir_prefixes = [
        f"{p.rstrip('/')}/" for p in hashing.SOURCE_HASH_PATHS
        if p not in explicit_files
    ]
    if tracked.returncode == 0:
        for p in tracked.stdout.splitlines():
            if not p:
                continue
            if p in explicit_files:
                paths.add(p)
            elif (
                p.endswith(".py")
                and "__pycache__" not in p.split("/")
                and any(p.startswith(prefix) for prefix in dir_prefixes)
            ):
                paths.add(p)
    return sorted(paths)


def _source_clean_tracked_default(paths) -> bool:
    import subprocess
    for p in paths:
        tracked = subprocess.run(
            ["git", "-C", str(hashing.REPO_ROOT), "ls-files", "--error-unmatch", p],
            capture_output=True, text=True)
        if tracked.returncode != 0:
            return False
        status = subprocess.run(
            ["git", "-C", str(hashing.REPO_ROOT), "status", "--porcelain", "--", p],
            capture_output=True, text=True)
        if status.stdout.strip():
            return False
    return True


def _require_source_clean(source_clean_tracked=None) -> None:
    checker = source_clean_tracked or _source_clean_tracked_default
    if not checker(_source_paths()):
        raise OOSGateError("source hash surface is not committed clean")


def current_trial_count(base_dir="ledger") -> int:
    return ledger.current_trial_count(base_dir)


def register(hypothesis_id, decision_threshold, is_result, *, data_window,
             risk_basis, notes="", run_id=None, code_sha=None,
             source_clean_tracked=None, base_dir="ledger") -> str:
    _require_non_empty_text(hypothesis_id, "hypothesis_id")
    _require_non_empty_text(decision_threshold, "decision_threshold")
    if risk_basis not in VALID_RISK_BASES:
        raise OOSGateError(f"unknown risk_basis {risk_basis!r}")
    is_window = _require_window(data_window, "is_window")
    oos_window = _require_window(data_window, "oos_window")
    _require_source_clean(source_clean_tracked)
    if any(r.get("entry_type") == "run" and r.get("hypothesis_id") == hypothesis_id
           for r in ledger.read_all(base_dir)):
        raise OOSGateError(f"hypothesis_id {hypothesis_id!r} is already registered")
    body = {
        "entry_type": "run",
        "timestamp": _now(),
        "run_id": run_id or uuid.uuid4().hex,
        "hypothesis_id": hypothesis_id,
        "decision_threshold": decision_threshold,
        "code_sha": code_sha or _code_sha(),
        "config_hash": hashing.config_hash(),
        "cost_model_hash": hashing.cost_model_hash(),
        "source_hash": hashing.source_hash(),
        "data_window_hash": hashing.data_window_hash(data_window),
        "risk_basis": risk_basis,
        "is_window": is_window,
        "is_result": is_result,
        "oos_window": oos_window,
        "oos_result": None,
        "deflated_sharpe": None,  # Phase-1B stub -- never computed in 1A
        "pbo": None,              # Phase-1B stub -- never computed in 1A
        "notes": notes,
    }
    body["trial_count"] = current_trial_count(base_dir) + 1
    return ledger.append(body, base_dir)


def log_trial_intent(reason, *, hypothesis_id=None, base_dir="ledger") -> str:
    body = {
        "entry_type": "trial_intent",
        "timestamp": _now(),
        "reason": reason,
        "hypothesis_id": hypothesis_id,
    }
    body["trial_count"] = current_trial_count(base_dir) + 1
    return ledger.append(body, base_dir)
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.RegisterCounterTests -v`
Expected: PASS (8 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/experiments.py tests/test_research_integrity.py
git commit -m "feat(research): pre-registration + monotonic trial counter

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: `research/experiments.py` — the write-once OOS gate (TDD)

**Files:**
- Modify: `research/experiments.py` (add `reveal_oos`)
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py`:

```python
def _oos_trades(n=1):
    # All strictly after IN_SAMPLE_END, so the partition assertion passes.
    return [{"pnl": 1.0, "capital_at_risk": 100.0,
             "entry_date": "2023-06-01", "symbol": "SPY"} for _ in range(n)]


class OOSGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True  # simulate committed-clean source/ledger files

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, hyp="H1"):
        experiments.register(hyp, "expectancy CI lower bound > 0", is_result={},
                             data_window=_window(), risk_basis="economic_max_loss",
                             base_dir=self.base, code_sha="deadbeef",
                             source_clean_tracked=self.clean)

    def test_reveal_refused_without_registration(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_on_cost_model_drift(self):
        self._register()
        original = config.SLIPPAGE_HAIRCUT
        try:
            config.SLIPPAGE_HAIRCUT = original + 0.05  # drift after freeze/register
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                       scoreboard_fn=lambda t: {"verdict": "x"},
                                       git_clean_tracked=self.clean)
        finally:
            config.SLIPPAGE_HAIRCUT = original

    def test_reveal_refused_on_config_drift(self):
        self._register()
        original = config.A_SPREAD_WIDTH
        try:
            config.A_SPREAD_WIDTH = original + 1
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                       scoreboard_fn=lambda t: {"verdict": "x"},
                                       git_clean_tracked=self.clean)
        finally:
            config.A_SPREAD_WIDTH = original

    def test_reveal_refused_on_source_drift(self):
        self._register()
        original = hashing.source_hash
        try:
            hashing.source_hash = lambda: "different"
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                       scoreboard_fn=lambda t: {"verdict": "x"},
                                       git_clean_tracked=self.clean)
        finally:
            hashing.source_hash = original

    def test_reveal_is_write_once(self):
        self._register()
        experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                               scoreboard_fn=lambda t: {"verdict": "x"},
                               git_clean_tracked=self.clean)
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_when_budget_exhausted(self):
        for i in range(config.OOS_LOOK_BUDGET):
            self._register(f"H{i}")
            experiments.reveal_oos(f"H{i}", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)
        self._register("Hlast")
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("Hlast", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_on_in_sample_leak(self):
        self._register()
        leaky = lambda: [{"pnl": 1.0, "capital_at_risk": 100.0,
                          "entry_date": "2021-01-01", "symbol": "SPY"}]
        with self.assertRaises(ValueError):
            experiments.reveal_oos("H1", run_fn=leaky, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_outside_registered_oos_window(self):
        self._register()
        wrong_window = lambda: [{"pnl": 1.0, "capital_at_risk": 100.0,
                                 "entry_date": "2025-01-01", "symbol": "SPY"}]
        with self.assertRaises(ValueError):
            experiments.reveal_oos("H1", run_fn=wrong_window, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_when_ledger_dirty(self):
        self._register()
        with self.assertRaises(ledger.LedgerError):
            experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=lambda paths: False)

    def test_reveal_happy_path_writes_oos_reveal_record(self):
        self._register()
        out = experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                     scoreboard_fn=lambda t: {"verdict": "PASS"},
                                     git_clean_tracked=self.clean)
        self.assertEqual(out["verdict"], "PASS")
        rec = ledger.read_all(self.base)[-1]
        self.assertEqual(rec["entry_type"], "oos_reveal")
        self.assertEqual(rec["hypothesis_id"], "H1")
        ledger.verify(self.base)  # chain still intact
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.OOSGateTests -v`
Expected: FAIL — `AttributeError: module 'research.experiments' has no attribute 'reveal_oos'`.

- [ ] **Step 3: Add `reveal_oos` to `research/experiments.py`**

Append to `research/experiments.py`:

```python
def reveal_oos(hypothesis_id, run_fn, *, scoreboard_fn=None, base_dir="ledger",
               git_clean_tracked=None):
    """Write-once OOS reveal. Refuses unless a matching registration exists, the
    registered config/source/cost surfaces are unchanged, the global look budget
    is not spent, no prior reveal exists for this hypothesis, and the ledger is
    committed+clean. Only then does it run the (injected) backtest, assert the
    OOS partition, and append the oos_reveal record."""
    records = ledger.read_all(base_dir)
    runs = [r for r in records
            if r.get("entry_type") == "run" and r.get("hypothesis_id") == hypothesis_id]
    if not runs:
        raise OOSGateError(f"no registered hypothesis {hypothesis_id!r} to reveal")
    run = runs[-1]

    if run["config_hash"] != hashing.config_hash():
        raise OOSGateError("registered config params drifted since registration")
    if run["cost_model_hash"] != hashing.cost_model_hash():
        raise OOSGateError("frozen cost-model params drifted since registration")
    if run["source_hash"] != hashing.source_hash():
        raise OOSGateError("registered source code drifted since registration")

    reveals = [r for r in records if r.get("entry_type") == "oos_reveal"]
    if any(r.get("hypothesis_id") == hypothesis_id for r in reveals):
        raise OOSGateError(f"OOS already revealed for {hypothesis_id!r} (write-once)")

    revealed_hyps = {r.get("hypothesis_id") for r in reveals}
    if len(revealed_hyps) >= config.OOS_LOOK_BUDGET:
        raise OOSGateError(
            f"global OOS look budget exhausted ({config.OOS_LOOK_BUDGET})")

    # The pre-registration must be immutable in git BEFORE we peek at the holdout.
    ledger.verify(base_dir, anchored=True, git_clean_tracked=git_clean_tracked)

    oos_trades = run_fn()
    entry_dates = [t["entry_date"] for t in oos_trades]
    windows.assert_oos_only(entry_dates, config.IN_SAMPLE_END)
    windows.assert_within_window(entry_dates, run["oos_window"])

    if scoreboard_fn is None:
        from metrics import scoreboard as scoreboard_fn  # local import avoids cycle
    oos_result = scoreboard_fn(oos_trades)

    body = {
        "entry_type": "oos_reveal",
        "timestamp": _now(),
        "run_id": run["run_id"],
        "hypothesis_id": hypothesis_id,
        "oos_result": oos_result,
        "budget_used": len(revealed_hyps) + 1,
        "budget_total": config.OOS_LOOK_BUDGET,
    }
    body["trial_count"] = current_trial_count(base_dir)  # reveal adds no new trial
    ledger.append(body, base_dir)
    return oos_result
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.OOSGateTests -v`
Expected: PASS (10 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/experiments.py tests/test_research_integrity.py
git commit -m "feat(research): write-once OOS gate (prereg, drift, budget, anchor, partition)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: `research/cli.py` — hook-able seams (TDD)

**Files:**
- Create: `research/cli.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `from research import cli`):

```python
import json


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_trial_log_then_verify_returns_zero(self):
        self.assertEqual(cli.main(["trial-log", "--reason", "swept width",
                                   "--ledger", self.base]), 0)
        self.assertEqual(cli.main(["verify", "--ledger", self.base]), 0)

    def test_verify_returns_nonzero_on_tamper(self):
        cli.main(["trial-log", "--reason", "x", "--ledger", self.base])
        jsonl = Path(self.base) / "experiments.jsonl"
        jsonl.write_text(jsonl.read_text().replace("x", "HACK"))
        self.assertNotEqual(cli.main(["verify", "--ledger", self.base]), 0)

    def test_register_subcommand_is_a_distinct_seam(self):
        calls = {}
        original = experiments.register
        try:
            def fake_register(hypothesis_id, decision_threshold, is_result, *,
                              data_window, risk_basis, notes="", base_dir="ledger"):
                calls.update({
                    "hypothesis_id": hypothesis_id,
                    "decision_threshold": decision_threshold,
                    "is_result": is_result,
                    "data_window": data_window,
                    "risk_basis": risk_basis,
                    "notes": notes,
                    "base_dir": base_dir,
                })
                return "hash"
            experiments.register = fake_register
            rc = cli.main([
                "register",
                "--hypothesis-id", "H1",
                "--decision-threshold", "ci_lo>0",
                "--is-result-json", json.dumps({"verdict": "NO EDGE"}),
                "--data-window-json", json.dumps(_window()),
                "--risk-basis", "economic_max_loss",
                "--notes", "synthetic",
                "--ledger", self.base,
            ])
        finally:
            experiments.register = original
        self.assertEqual(rc, 0)
        self.assertEqual(calls["hypothesis_id"], "H1")
        self.assertEqual(calls["base_dir"], self.base)

    def test_reveal_oos_subcommand_is_a_distinct_gate(self):
        # With no registration, the integrity gate refuses before any data path.
        self.assertNotEqual(cli.main(["reveal-oos", "--hypothesis-id", "H1",
                                      "--ledger", self.base]), 0)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.CliTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.cli'`.

- [ ] **Step 3: Create `research/cli.py`**

```python
"""
research/cli.py -- the integrity seams as distinct subcommands.

Distinct subcommands so a future PreToolUse hook can gate them individually
(allow an in-sample run, block an OOS reveal or a ledger rewrite). No hook is
built in Phase 1A -- these are the seams it would attach to.

Usage: uv run python -m research.cli <verify|trial-log|register|reveal-oos> ...
"""
from __future__ import annotations
import argparse
import json
import sys

from research import experiments, ledger


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="research.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_ledger(p):
        p.add_argument("--ledger", default="ledger", help="ledger base dir")
        return p

    p_verify = sub.add_parser("verify")
    add_ledger(p_verify)
    p_verify.add_argument("--anchored", action="store_true")

    p_trial = sub.add_parser("trial-log")
    add_ledger(p_trial)
    p_trial.add_argument("--reason", required=True)

    p_register = sub.add_parser("register")
    add_ledger(p_register)
    p_register.add_argument("--hypothesis-id", required=True)
    p_register.add_argument("--decision-threshold", required=True)
    p_register.add_argument("--is-result-json", required=True)
    p_register.add_argument("--data-window-json", required=True)
    p_register.add_argument("--risk-basis", required=True)
    p_register.add_argument("--notes", default="")

    p_reveal = sub.add_parser("reveal-oos")
    add_ledger(p_reveal)
    p_reveal.add_argument("--hypothesis-id", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "verify":
        try:
            ledger.verify(args.ledger, anchored=args.anchored)
        except ledger.LedgerError as exc:
            print(f"INTEGRITY FAIL: {exc}", file=sys.stderr)
            return 1
        print("ledger OK")
        return 0

    if args.cmd == "trial-log":
        experiments.log_trial_intent(args.reason, base_dir=args.ledger)
        print(f"trial logged; count = {experiments.current_trial_count(args.ledger)}")
        return 0

    if args.cmd == "register":
        try:
            experiments.register(
                args.hypothesis_id,
                args.decision_threshold,
                json.loads(args.is_result_json),
                data_window=json.loads(args.data_window_json),
                risk_basis=args.risk_basis,
                notes=args.notes,
                base_dir=args.ledger,
            )
        except (ValueError, experiments.OOSGateError) as exc:
            print(f"REGISTER REFUSED: {exc}", file=sys.stderr)
            return 1
        print("hypothesis registered")
        return 0

    if args.cmd == "reveal-oos":
        def _unwired_oos_run():
            raise NotImplementedError(
                "Phase 0: wire the OOS ThetaData backtest before reveal-oos can run")
        try:
            experiments.reveal_oos(
                args.hypothesis_id, run_fn=_unwired_oos_run, base_dir=args.ledger)
        except experiments.OOSGateError as exc:
            print(f"OOS GATE REFUSED: {exc}", file=sys.stderr)
            return 1
        except NotImplementedError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("OOS revealed")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.CliTests -v`
Expected: PASS (4 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/cli.py tests/test_research_integrity.py
git commit -m "feat(research): integrity CLI seams

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: `research/facts.py` — descriptive facts log (TDD)

**Files:**
- Create: `research/facts.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `from research import facts`):

```python
class FactsLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_facts_append_and_read_are_separate_from_ledger(self):
        facts.append_fact("ThetaData missing EOD marks 2020-03-16", base_dir=self.base)
        facts.append_fact("SPY spread ~2% at 30-delta", base_dir=self.base)
        self.assertEqual(len(facts.read_facts(self.base)), 2)
        # Facts must NOT land in the verdict-bearing ledger:
        self.assertEqual(ledger.read_all(self.base), [])
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.FactsLogTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.facts'`.

- [ ] **Step 3: Create `research/facts.py`**

```python
"""
research/facts.py -- append-only DESCRIPTIVE log (ThetaData gaps, measured
spreads, workflow notes). Deliberately separate from the hypothesis ledger and
explicitly NOT verdict-feeding: the "learn facts, not parameters" channel.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path


def _path(base_dir):
    return Path(base_dir) / "facts.log"


def append_fact(text: str, base_dir="ledger") -> None:
    p = _path(base_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with p.open("a") as f:
        f.write(f"{stamp}\t{text}\n")


def read_facts(base_dir="ledger") -> list[str]:
    p = _path(base_dir)
    if not p.exists():
        return []
    return [line for line in p.read_text().splitlines() if line.strip()]
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.FactsLogTests -v`
Expected: PASS (1 test OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add research/facts.py tests/test_research_integrity.py
git commit -m "feat(research): descriptive facts log (non-verdict-feeding)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: `metrics.py` — require entry_date + symbol (TDD, update existing tests)

**Files:**
- Modify: `metrics.py:26-53` (`_validated_arrays`)
- Modify: `tests/test_core.py` (existing `ScoreboardTests` build trades without the new fields)
- Test: `tests/test_bootstrap.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_bootstrap.py`:

```python
import unittest

from metrics import scoreboard


def _trade(pnl, date="2021-01-04", symbol="SPY", car=100.0):
    return {"pnl": pnl, "capital_at_risk": car, "entry_date": date, "symbol": symbol}


class ContractTests(unittest.TestCase):
    def test_scoreboard_raises_without_entry_date(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 5.0, "capital_at_risk": 100.0, "symbol": "SPY"}])

    def test_scoreboard_raises_without_symbol(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 5.0, "capital_at_risk": 100.0, "entry_date": "2021-01-04"}])

    def test_scoreboard_raises_on_unparseable_entry_date(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, date="not-a-date")])

    def test_scoreboard_raises_on_non_date_entry_type(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, date=123)])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_bootstrap.ContractTests -v`
Expected: FAIL — the current `_validated_arrays` ignores missing `entry_date`/`symbol`, so no `ValueError` is raised.

- [ ] **Step 3: Update `_validated_arrays` in `metrics.py`**

Add near the top of `metrics.py` (after `import config`):

```python
from datetime import date


def _as_date(x):
    if isinstance(x, date):
        return x
    if isinstance(x, str):
        try:
            return date.fromisoformat(x)
        except ValueError as exc:
            raise ValueError(f"invalid ISO date: {x!r}") from exc
    raise ValueError(f"expected ISO date string or date object, got {type(x).__name__}")
```

Replace the body of `_validated_arrays` (currently [metrics.py:26-53](../../../metrics.py#L26-L53)) with:

```python
def _validated_arrays(trades):
    pnls = []
    wins = []
    capital_at_risk = []
    entry_dates = []

    for idx, trade in enumerate(trades):
        missing = {"pnl", "capital_at_risk", "entry_date", "symbol"} - trade.keys()
        if missing:
            raise ValueError(f"trade {idx} missing required field(s): {sorted(missing)}")

        if not trade["symbol"]:
            raise ValueError(f"trade {idx} has empty symbol")
        try:
            entry_date = _as_date(trade["entry_date"])
        except (ValueError, TypeError):
            raise ValueError(
                f"trade {idx} has unparseable entry_date: {trade['entry_date']!r}")

        pnl = float(trade["pnl"])
        car = float(trade["capital_at_risk"])
        if not np.isfinite(pnl):
            raise ValueError(f"trade {idx} has non-finite pnl: {trade['pnl']!r}")
        if not np.isfinite(car) or car <= 0:
            raise ValueError(
                f"trade {idx} has invalid capital_at_risk: {trade['capital_at_risk']!r}")

        pnls.append(pnl)
        wins.append(bool(trade.get("is_win", pnl > 0)))
        capital_at_risk.append(car)
        entry_dates.append(entry_date)

    return (
        np.array(pnls, dtype=float),
        np.array(wins, dtype=bool),
        np.array(capital_at_risk, dtype=float),
        entry_dates,
    )
```

- [ ] **Step 4: Update `scoreboard` to unpack the extra return value**

In `scoreboard` ([metrics.py:77](../../../metrics.py#L77)), change:

```python
    pnls, wins, cap = _validated_arrays(trades)
```

to:

```python
    pnls, wins, cap, entry_dates = _validated_arrays(trades)
```

(The `entry_dates` local is consumed by the bootstrap in Task 13. For now it is unused — that is fine; the existing IID `_expectancy_ci(pnls, ...)` call still works.)

- [ ] **Step 5: Update the existing `ScoreboardTests` in `tests/test_core.py`**

The three trade-building tests in `ScoreboardTests` ([tests/test_core.py:38-57](../../../tests/test_core.py#L38-L57)) must now supply `entry_date` and `symbol`. Replace `test_scoreboard_rejects_zero_capital_at_risk` and `test_loss_count_gate_blocks_thin_short_vol_sample` with:

```python
    def test_scoreboard_rejects_zero_capital_at_risk(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 12.0, "capital_at_risk": 0.0,
                         "entry_date": "2021-01-04", "symbol": "SPY"}])

    def test_loss_count_gate_blocks_thin_short_vol_sample(self):
        trades = [
            {"pnl": 20.0, "capital_at_risk": 100.0, "entry_date": "2021-01-04", "symbol": "SPY"},
            {"pnl": 15.0, "capital_at_risk": 100.0, "entry_date": "2021-01-11", "symbol": "SPY"},
            {"pnl": -70.0, "capital_at_risk": 100.0, "entry_date": "2021-01-19", "symbol": "SPY"},
        ]

        result = scoreboard(trades)

        self.assertEqual(result["n_losses"], 1)
        self.assertIn("INSUFFICIENT SAMPLE", result["verdict"])
```

(`test_scoreboard_requires_capital_at_risk` already expects a `ValueError` and still passes — a `{"pnl": 12.0}` trade is now missing even more required fields.)

- [ ] **Step 6: Run the affected suites and confirm they pass**

Run: `uv run python -m unittest tests.test_bootstrap.ContractTests tests.test_core.ScoreboardTests -v`
Expected: PASS (ContractTests 4 OK; ScoreboardTests 3 OK).

- [ ] **Step 7: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add metrics.py tests/test_bootstrap.py tests/test_core.py
git commit -m "feat(metrics): require entry_date + symbol on the verdict path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: `metrics.py` — weekly cohorts + block-length envelope (TDD)

**Files:**
- Modify: `metrics.py` (add cohort/block helpers)
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bootstrap.py`:

```python
from datetime import date

import config
import metrics


class CohortAndBlockTests(unittest.TestCase):
    def test_same_iso_week_trades_form_one_cohort(self):
        # 2021-01-04 (Mon) and 2021-01-08 (Fri) are the same ISO week.
        dates = ["2021-01-04", "2021-01-08", "2021-01-11"]
        pnls = __import__("numpy").array([1.0, 2.0, 3.0])
        cohorts = metrics._build_week_cohorts(dates, pnls)
        self.assertEqual(len(cohorts), 2)          # week1 {Mon,Fri}, week2 {Mon}
        self.assertEqual(sorted(cohorts[0].tolist()), [1.0, 2.0])

    def test_block_lengths_are_deduped_clamped_and_theory_anchored(self):
        Ls = metrics._block_lengths(64)  # 64**(1/3)=4 -> {2,4,8,16}
        self.assertEqual(Ls, [2, 4, 8, 16])
        for L in Ls:
            self.assertGreaterEqual(L, 2)
            self.assertLessEqual(L, 63)

    def test_block_lengths_empty_below_three_cohorts(self):
        self.assertEqual(metrics._block_lengths(2), [])
        self.assertEqual(metrics._block_lengths(1), [])
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_bootstrap.CohortAndBlockTests -v`
Expected: FAIL — `AttributeError: module 'metrics' has no attribute '_build_week_cohorts'`.

- [ ] **Step 3: Add the helpers to `metrics.py`**

Add after `_as_date` (from Task 10):

```python
def _iso_week_key(d):
    iso = _as_date(d).isocalendar()
    return (iso[0], iso[1])  # (ISO year, ISO week)


def _build_week_cohorts(entry_dates, pnls):
    """Group PnLs into cohorts keyed by ISO week of entry, ordered chronologically.

    Weekly cohorts keep same-week trades across all names as one INDIVISIBLE unit
    (the cross-sectional axis); the block bootstrap over the ordered cohort
    sequence handles the serial axis (Task 12)."""
    order = sorted(range(len(entry_dates)), key=lambda i: _as_date(entry_dates[i]))
    groups = {}
    keys_in_order = []
    for i in order:
        k = _iso_week_key(entry_dates[i])
        if k not in groups:
            groups[k] = []
            keys_in_order.append(k)
        groups[k].append(float(pnls[i]))
    return [np.array(groups[k], dtype=float) for k in keys_in_order]


def _block_lengths(n_cohorts):
    """Frozen, theory-anchored mean block lengths (in cohorts): round(c*n^(1/3)),
    deduped, clamped to 2 <= L <= n_cohorts-1. Empty if n_cohorts < 3 (no valid
    block) -> the caller returns INSUFFICIENT SAMPLE / no verdict."""
    if n_cohorts < 3:
        return []
    lengths = set()
    for c in config.BOOTSTRAP_BLOCK_CONSTANTS:
        L = int(round(c * n_cohorts ** config.BOOTSTRAP_BLOCK_EXPONENT))
        L = max(2, min(L, n_cohorts - 1))
        lengths.add(L)
    return sorted(lengths)
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_bootstrap.CohortAndBlockTests -v`
Expected: PASS (3 tests OK).

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add metrics.py tests/test_bootstrap.py
git commit -m "feat(metrics): weekly cohorts + frozen block-length envelope

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 12: `metrics.py` — resamplers + widest-CI envelope + IID helper (TDD)

**Files:**
- Modify: `metrics.py` (add resamplers, `_dependence_aware_ci`, `iid_expectancy_ci`)
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bootstrap.py`:

```python
import numpy as np


class EnvelopeCiTests(unittest.TestCase):
    def _independent_weekly(self):
        # 60 trades, one per distinct ISO week, mild both-signed PnL, one symbol.
        base = date(2018, 1, 1)
        dates = [(base.toordinal() + i * 7) for i in range(60)]
        dates = [date.fromordinal(o).isoformat() for o in dates]
        rng = np.random.default_rng(0)
        pnls = rng.normal(5.0, 40.0, size=60)
        return dates, pnls

    def test_ci_is_finite_ordered_and_seed_stable_on_independent_data(self):
        dates, pnls = self._independent_weekly()
        lo1, hi1 = metrics._dependence_aware_ci(dates, pnls, n_boot=400, seed=7)
        lo2, hi2 = metrics._dependence_aware_ci(dates, pnls, n_boot=400, seed=7)
        self.assertTrue(np.isfinite(lo1) and np.isfinite(hi1))
        self.assertLess(lo1, float(pnls.mean()))
        self.assertLess(float(pnls.mean()), hi1)
        self.assertEqual((lo1, hi1), (lo2, hi2))  # deterministic under fixed seed

    def test_ci_is_nan_below_three_cohorts(self):
        dates = ["2021-01-04", "2021-01-11"]  # 2 weeks -> no valid block
        lo, hi = metrics._dependence_aware_ci(dates, np.array([1.0, -1.0]), n_boot=50)
        self.assertTrue(np.isnan(lo) and np.isnan(hi))

    def test_iid_helper_exists_and_is_not_used_by_scoreboard(self):
        _, pnls = self._independent_weekly()
        lo, hi = metrics.iid_expectancy_ci(pnls, n_boot=400, seed=1)
        self.assertLess(lo, hi)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_bootstrap.EnvelopeCiTests -v`
Expected: FAIL — `AttributeError: module 'metrics' has no attribute '_dependence_aware_ci'`.

- [ ] **Step 3: Add the resamplers and envelope to `metrics.py`**

Add after `_block_lengths`:

```python
def _resample_block(cohorts, n_target, block_len, rng):
    """Circular block bootstrap over the ordered cohort sequence. Accumulates
    contiguous blocks of whole cohorts (with wraparound) until >= n_target trades,
    then returns the mean PnL per trade of the resample."""
    n = len(cohorts)
    acc = []
    total = 0
    while total < n_target:
        start = int(rng.integers(n))
        for j in range(block_len):
            c = cohorts[(start + j) % n]
            acc.append(c)
            total += len(c)
            if total >= n_target:
                break
    return float(np.concatenate(acc).mean())


def _resample_stationary(cohorts, n_target, block_len, rng):
    """Stationary bootstrap (Politis-Romano): geometric block length with mean
    `block_len` (p = 1/block_len), over the same cohort sequence."""
    n = len(cohorts)
    p = 1.0 / block_len
    acc = []
    total = 0
    idx = int(rng.integers(n))
    while total < n_target:
        c = cohorts[idx]
        acc.append(c)
        total += len(c)
        if rng.random() < p:
            idx = int(rng.integers(n))
        else:
            idx = (idx + 1) % n
    return float(np.concatenate(acc).mean())


def _ci_one(cohorts, n_target, block_len, method, n_boot, rng, lo, hi):
    fn = _resample_block if method == "block" else _resample_stationary
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = fn(cohorts, n_target, block_len, rng)
    return float(np.percentile(means, lo)), float(np.percentile(means, hi))


def _ci_from_cohorts(cohorts, n_target, n_boot, lo, hi, seed):
    """Widest CI across ALL (method, block_len) combinations: min lower bound,
    max upper bound. No configuration can be selected because it flatters."""
    Ls = _block_lengths(len(cohorts))
    if not Ls:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    los, his = [], []
    for method in ("block", "stationary"):
        for L in Ls:
            lo_b, hi_b = _ci_one(cohorts, n_target, L, method, n_boot, rng, lo, hi)
            los.append(lo_b)
            his.append(hi_b)
    return (min(los), max(his))


def _dependence_aware_ci(entry_dates, pnls, n_boot=None, lo=5, hi=95, seed=42):
    """Verdict CI: weekly-cohort block bootstrap + stationary cross-check over a
    shared frozen block-length envelope, reporting the widest CI."""
    n_boot = n_boot or config.BOOTSTRAP_SAMPLES
    cohorts = _build_week_cohorts(entry_dates, pnls)
    return _ci_from_cohorts(cohorts, len(pnls), n_boot, lo, hi, seed)


def iid_expectancy_ci(pnls, n_boot=None, lo=5, hi=95, seed=42):
    """EXPLICIT, opt-in IID resample -- for the demo/illustration ONLY. NEVER
    called by scoreboard(): a silent IID fallback is the integrity hole this
    module exists to close."""
    n_boot = n_boot or config.BOOTSTRAP_SAMPLES
    if len(pnls) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = rng.choice(pnls, size=len(pnls), replace=True).mean()
    return (float(np.percentile(means, lo)), float(np.percentile(means, hi)))
```

- [ ] **Step 4: Leave the old `_expectancy_ci` in place for now**

Do NOT delete the old IID `_expectancy_ci` ([metrics.py:65-73](../../../metrics.py#L65-L73)) yet — `scoreboard` still calls it, so removing it now would break the full suite. It is deleted in Task 13 at the moment `scoreboard` is rewired to the envelope, keeping every commit green.

- [ ] **Step 5: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_bootstrap.EnvelopeCiTests -v`
Expected: PASS (3 tests OK).

- [ ] **Step 6: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add metrics.py tests/test_bootstrap.py
git commit -m "feat(metrics): dependence-aware widest-CI envelope + explicit IID helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 13: `metrics.py` — wire the envelope into scoreboard + cohort guard + demo (TDD)

**Files:**
- Modify: `metrics.py` (`scoreboard` verdict; `_demo`)
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bootstrap.py`:

```python
class VerdictGuardTests(unittest.TestCase):
    def _weeks(self, n_weeks, pnl, symbol="SPY", start=date(2018, 1, 1)):
        out = []
        for w in range(n_weeks):
            d = date.fromordinal(start.toordinal() + w * 7).isoformat()
            out.append(_trade(pnl, date=d, symbol=symbol))
        return out

    def test_insufficient_when_fewer_than_three_cohorts(self):
        # 2 weeks, 20 losses -> passes the loss gate but fails the cohort gate.
        trades = ([_trade(-50.0, date="2021-01-04") for _ in range(10)]
                  + [_trade(-50.0, date="2021-01-11") for _ in range(10)])
        result = scoreboard(trades)
        self.assertIn("INSUFFICIENT SAMPLE", result["verdict"])

    def test_verdict_present_with_enough_cohorts_and_losses(self):
        # 40 weekly winners + 12 weekly losers across many weeks -> a real verdict.
        trades = self._weeks(40, 30.0) + [
            _trade(-60.0, date=date.fromordinal(date(2019, 1, 7).toordinal() + w * 7).isoformat())
            for w in range(12)]
        result = scoreboard(trades)
        self.assertNotIn("INSUFFICIENT SAMPLE", result["verdict"])
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_bootstrap.VerdictGuardTests -v`
Expected: FAIL — `scoreboard` still uses the IID CI path and has no cohort guard,
so the two-cohort all-loss sample returns a `FAIL` verdict instead of
`INSUFFICIENT SAMPLE`.

- [ ] **Step 3: Rewire `scoreboard` in `metrics.py`**

In `scoreboard`, replace the CI call and verdict block. Change:

```python
    expectancy = float(pnls.mean()) if n else 0.0
    ci_lo, ci_hi = _expectancy_ci(pnls, config.BOOTSTRAP_SAMPLES)
```

to:

```python
    expectancy = float(pnls.mean()) if n else 0.0
    cohorts = _build_week_cohorts(entry_dates, pnls)
    n_cohorts = len(cohorts)
    ci_lo, ci_hi = _ci_from_cohorts(cohorts, n, config.BOOTSTRAP_SAMPLES, 5, 95, seed=42)
```

Then replace the verdict block ([metrics.py:91-100](../../../metrics.py#L91-L100)) with:

```python
    # ---- verdict gates on LOSSES and on COHORTS, not trades -----------------
    if n_loss < config.MIN_LOSSES_FOR_VERDICT:
        verdict = (f"INSUFFICIENT SAMPLE ({n_loss} losses; need "
                   f">= {config.MIN_LOSSES_FOR_VERDICT}). Ratios below are NOT reliable.")
    elif n_cohorts < 3:
        verdict = (f"INSUFFICIENT SAMPLE ({n_cohorts} entry-week cohorts; need >= 3 "
                   "to form a dependence-aware CI). No verdict.")
    elif ci_lo > 0:
        verdict = "PASS -- expectancy positive after costs (CI above zero)"
    elif ci_hi < 0:
        verdict = "FAIL -- expectancy negative after costs (CI below zero)"
    else:
        verdict = "NO EDGE -- expectancy indistinguishable from zero after costs"
```

Then delete the now-unreferenced old IID `_expectancy_ci` function ([metrics.py:65-73](../../../metrics.py#L65-L73)) — `scoreboard` no longer calls it, and `iid_expectancy_ci` (Task 12) is the only remaining IID resampler (used by tests/demo only). Removing it in this same task keeps this commit's full suite green.

- [ ] **Step 4: Update `_demo` to build dated, symboled trades**

Replace the trade construction in `_demo` ([metrics.py:150-154](../../../metrics.py#L150-L154)) with:

```python
    rng = np.random.default_rng(7)
    base = date(2020, 1, 6).toordinal()  # Monday
    symbols = config.UNIVERSE
    trades = [{"pnl": float(rng.normal(45, 8)), "capital_at_risk": 350.0,
               "entry_date": date.fromordinal(base + i * 3).isoformat(),
               "symbol": symbols[i % len(symbols)]}
              for i in range(35)]
    trades += [{"pnl": float(rng.normal(-300, 40)), "capital_at_risk": 350.0,
                "entry_date": date.fromordinal(base + 120 + i * 3).isoformat(),
                "symbol": symbols[i % len(symbols)]}
               for i in range(6)]
```

- [ ] **Step 5: Run the bootstrap suite and the demo**

Run: `uv run python -m unittest tests.test_bootstrap.VerdictGuardTests -v`
Expected: PASS (2 tests OK).

Run: `uv run python metrics.py`
Expected: prints the scoreboard demo and ends in a `VERDICT: INSUFFICIENT SAMPLE (6 losses; need >= 10)...` line (the loss gate fires first, as before).

- [ ] **Step 6: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add metrics.py tests/test_bootstrap.py
git commit -m "feat(metrics): dependence-aware verdict + cohort guard + dated demo

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 14: `metrics.py` — the under-coverage demonstration (TDD)

**Files:**
- Test: `tests/test_bootstrap.py`

This is the load-bearing statistical test: on a clustered series the IID CI produces a **false PASS** (excludes zero) while the dependence-aware envelope correctly **includes zero** and is **wider**.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bootstrap.py`:

```python
class UnderCoverageTests(unittest.TestCase):
    def _clustered(self):
        """42 'up' weeks (+10 for all 5 names) then 8 CONTIGUOUS 'down' weeks
        (-30 for all 5 names). Overall mean is mildly positive, but losses cluster
        both serially (contiguous weeks) and cross-sectionally (all names move
        together each week)."""
        dates, pnls, symbols = [], [], ["SPY", "QQQ", "MSFT", "AAPL", "NVDA"]
        start = date(2018, 1, 1).toordinal()
        week = 0
        for _ in range(42):
            for s in symbols:
                dates.append(date.fromordinal(start + week * 7).isoformat()); pnls.append(10.0)
            week += 1
        for _ in range(8):
            for s in symbols:
                dates.append(date.fromordinal(start + week * 7).isoformat()); pnls.append(-30.0)
            week += 1
        return dates, np.array(pnls, dtype=float)

    def test_iid_false_pass_but_dependence_aware_refuses(self):
        dates, pnls = self._clustered()
        iid_lo, iid_hi = metrics.iid_expectancy_ci(pnls, n_boot=2000, seed=42)
        dep_lo, dep_hi = metrics._dependence_aware_ci(dates, pnls, n_boot=2000, seed=42)

        self.assertGreater(iid_lo, 0.0)               # IID: false PASS (CI excludes 0)
        self.assertLessEqual(dep_lo, 0.0)             # dependence-aware: includes 0
        self.assertGreater(dep_hi - dep_lo, iid_hi - iid_lo)  # and is wider
```

- [ ] **Step 2: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_bootstrap.UnderCoverageTests -v`
Expected: PASS. The IID CI clusters tightly above zero (many independent +10s, few -30s); the weekly-cohort envelope sees only ~50 cohorts with 8 contiguous losers, so its widest bound dips below zero. If `dep_lo` is marginally above 0, increase the down-week magnitude to `-35.0` (a stronger, still-honest cluster) — do not weaken the IID side.

- [ ] **Step 3: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add tests/test_bootstrap.py
git commit -m "test(metrics): IID false-PASS is refused by the dependence-aware CI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 15: `harness/run_backtest.py` — the OOS-reveal seam (TDD)

**Files:**
- Modify: `harness/run_backtest.py`
- Test: `tests/test_research_integrity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research_integrity.py` (add `from harness import run_backtest`):

```python
class RunBacktestSeamTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_reveal_seam_gate_runs_before_the_unwired_data_path(self):
        # No registration exists -> the gate must refuse BEFORE reaching the
        # NotImplementedError ThetaData fetch inside the injected run function.
        with self.assertRaises(experiments.OOSGateError):
            run_backtest.reveal_out_of_sample("H1", base_dir=self.base,
                                              git_clean_tracked=lambda paths: True)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run python -m unittest tests.test_research_integrity.RunBacktestSeamTests -v`
Expected: FAIL — `AttributeError: module 'harness.run_backtest' has no attribute 'reveal_out_of_sample'`.

- [ ] **Step 3: Add the seam to `harness/run_backtest.py`**

Append to `harness/run_backtest.py`:

```python
def _oos_backtest_trades():
    """PHASE 0 SEAM: this is where the wired Lumibot/ThetaData OOS backtest will
    produce the post-IN_SAMPLE_END trades. Until then it raises -- but the OOS
    gate (research.experiments.reveal_oos) enforces pre-registration, frozen
    params, look budget, and a committed ledger BEFORE this is ever called."""
    raise NotImplementedError(
        "Phase 0: wire the OOS ThetaData backtest, then this feeds reveal_oos().")


def reveal_out_of_sample(hypothesis_id, *, base_dir="ledger", git_clean_tracked=None):
    """Thin seam: delegate the write-once OOS reveal to the integrity substrate,
    injecting the (still-unwired) backtest as the run function."""
    from research import experiments
    return experiments.reveal_oos(
        hypothesis_id, run_fn=_oos_backtest_trades, base_dir=base_dir,
        git_clean_tracked=git_clean_tracked)
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `uv run python -m unittest tests.test_research_integrity.RunBacktestSeamTests -v`
Expected: PASS (1 test OK). The gate raises `OOSGateError` (no registration) before `_oos_backtest_trades` is called.

- [ ] **Step 5: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add harness/run_backtest.py tests/test_research_integrity.py
git commit -m "feat(harness): OOS-reveal seam delegating to the integrity gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 16: Committed ledger location + full-suite verification

**Files:**
- Create: `ledger/README.md`, `ledger/.gitkeep`

- [ ] **Step 1: Create the committed research-record location**

Create `ledger/.gitkeep` (empty file):

```text
```

Create `ledger/README.md`:

```markdown
# Experiment ledger

Append-only, hash-chained research record written by `research/ledger.py`.

- `experiments.jsonl` — one JSON record per line, each committing to the previous
  via `prev_hash`/`record_hash` (the chain IS the tamper-evidence).
- `HEAD` — the current chain tip, tracked so it is diffable in git.

Do not hand-edit these files: `uv run python -m research.cli verify` (and
`--anchored` before any OOS reveal) will detect tampering, a HEAD mismatch, or an
uncommitted tree. They are created when the first run is registered.
```

- [ ] **Step 2: Confirm `ledger/` is NOT gitignored**

Run: `git check-ignore ledger/README.md; echo "exit=$?"`
Expected: no path printed and `exit=1` (not ignored). `results/*` is ignored, but `ledger/` is a distinct, tracked location.

- [ ] **Step 3: Run the entire test suite**

Run: `uv run python -m unittest discover -s tests -v`
Expected: `OK`. Count: the original 12 (`tests/test_core.py`, with 2 `ScoreboardTests` bodies updated) + the `tests/test_research_integrity.py` classes + the `tests/test_bootstrap.py` classes. No failures, no errors.

- [ ] **Step 4: Confirm the demo and feasibility scripts still run**

Run: `uv run python metrics.py`
Expected: prints the scoreboard, ends in `VERDICT: INSUFFICIENT SAMPLE (6 losses; need >= 10)...`.

Run: `uv run python analysis/feasibility.py`
Expected: prints the feasibility table (unchanged by this phase).

- [ ] **Step 5: Confirm the lockfile is untouched (no new dependencies)**

Run: `uv sync --locked --check`
Expected: `Would make no changes` — Phase 1A adds no runtime dependency (numpy + stdlib only).

- [ ] **Step 6: Optional commit checkpoint (only if the user asked for commits)**

```bash
git add ledger/README.md ledger/.gitkeep
git commit -m "chore(ledger): add committed research-record location + README

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-review notes (author)

- **Spec coverage:** Unit 1 typed trade record → Task 10 (`entry_date`/`symbol` required, raise). Unit 2 ledger + HEAD + anchoring → Tasks 3–4. Unit 3 CLI seams + canonical frozen hash → Tasks 2, 8. Unit 4 RunWindow/OOS gate + look budget + injected run fn → Tasks 5, 7, 15. Unit 5 dependence-aware CI (weekly cohort block + stationary cross-check, shared envelope, widest, `n_cohorts<3` guard) → Tasks 11–14. Unit 6 facts log → Task 9. Risk-basis (#7, ledger side) → `risk_basis` field carried through `register()` (Task 6); the `size_defined_risk` code change stays a tracked prerequisite (out of scope, per spec). DSR/PBO stubbed as `null` → Task 6. Frozen knobs → Task 1. Registered hypothesis drift guard → `config_hash`, `cost_model_hash`, and `source_hash` are stored at registration (Task 6) and rechecked before OOS reveal (Task 7). Registration also refuses dirty, deleted, untracked, or ignored source-hash files before writing the ledger record, so a preregistered hash remains recoverable from git; it also refuses empty hypothesis IDs, empty thresholds, and malformed registered windows.
- **Placeholder scan:** no TODO/TBD; every code step shows complete code; the one tunable (down-week magnitude in Task 14) has an explicit fallback value and a "don't weaken the IID side" rule.
- **Type/name consistency:** `_validated_arrays` returns a 4-tuple (Task 10) consumed identically in Tasks 10 and 13; `_ci_from_cohorts(cohorts, n_target, n_boot, lo, hi, seed)` defined in Task 12 and called with matching args in Tasks 12 and 13; `register(..., source_clean_tracked, base_dir)` defined in Task 6 and called consistently in Tasks 6 and 7; `reveal_oos(hypothesis_id, run_fn, *, scoreboard_fn, base_dir, git_clean_tracked)` defined in Task 7 and called consistently in Tasks 7 and 15; `ledger.verify(base_dir, anchored, git_clean_tracked)` consistent across Tasks 3, 4, 7.
- **TDD + commit checkpoints:** every task is failing-test-first, minimal impl,
  verify, then commit only if the user explicitly asked for task commits. No
  pushes; single branch `phase-1a-research-integrity`.
- **No ThetaData/Lumibot wiring:** `run_backtest.run()` untouched; the new `_oos_backtest_trades` seam raises `NotImplementedError` behind the gate.
