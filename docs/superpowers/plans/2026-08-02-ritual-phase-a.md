# Daily Ritual Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the already-audited v2 cache reader offline and make the daily ritual refuse all stateful work while its provider/source/H7 authority is paused.

**Architecture:** Preserve and repair the v2 audit's source-hash contract by porting its nine listed source files, the two runtime dependencies exposed by focused tests, and the focused audit report; do not merge the branch wholesale. Add a pure, read-only ritual-authority module that the shell script calls before creating logs or reaching any receipt, ledger, paper-book, Git, backup, or provider surface.

**Tech Stack:** Python 3.12, pandas/pyarrow, unittest, zsh, Git.

## Global Constraints

- ThetaData acquisition remains disabled with no override.
- V1 cache bytes and the isolated v2 bytes remain unchanged.
- V2 is offline analysis support only; no H6/H7/H8 rebuild, verdict, or activation.
- H7 remains paused; `h7-forward-15-v1` remains immutable.
- Do not run the full `tools/daily_ritual.sh run` path, deploy, push, load
  LaunchAgent, or touch paper books/ledgers. Read-only `status` validation is
  allowed.
- Preserve the root checkout's `wiki/log.md` and the ops checkout's untracked July 28 capture.
- Produce separate local commits for v2 support and ritual hardening.

---

### Task 1: Receipt-bound offline v2 reader

**Files:**
- Create: `data/cache_schema.py`
- Create: `data/v2_partition_quarantine.json`
- Modify: `data/atomic_io.py`
- Create: `tools/thetadata_v2_audit.py`
- Create: `tools/thetadata_v2_backfill.py`
- Modify: `data/thetadata_adapter.py`
- Modify: `data/recent_topup.py`
- Modify: `options_researcher/h7_data_gate.py`
- Modify: `options_researcher/h7_synthetic_proof.py`
- Modify: `options_researcher/h9_census.py`
- Modify: `tools/thetadata_exit_audit.py`
- Create/modify focused tests under `tests/test_cache_schema_v2.py`, `tests/test_thetadata_v2_audit.py`, `tests/test_thetadata_v2_backfill.py`, `tests/test_h7_data_gate.py`, and `tests/test_thetadata_exit_audit.py`
- Create: `reports/thetadata_v2/2026-08-02-od1-full-audit.md`

**Interfaces:**
- Consumes: `.cache/chains_v2/od1-2026-08-01/_meta/full_audit.json` and exact partition bytes.
- Produces: `load_cached_chain(..., verdict_bearing: bool = False,
  verdict_consumer: str | None = None)` plus
  `validate_v2_audit_receipt(...)`; neither function fetches or writes. The
  current receipt authorizes only the audited H7 geometry; H9 remains blocked
  pending its own scope-specific audit.

- [x] **Step 1: Add a failing reader-contract test**

```python
def test_loader_exposes_explicit_verdict_bearing_gate(self):
    self.assertIn(
        "verdict_bearing",
        inspect.signature(thetadata_adapter.load_cached_chain).parameters,
    )
```

- [x] **Step 2: Run the test and confirm RED**

Run: `/Users/carsynstephenson/options-validator/.venv/bin/python -m unittest discover -s tests -p test_cache_schema_v2.py`

Expected: assertion failure because `verdict_bearing` is absent.

- [x] **Step 3: Port the exact audit-bound source set and focused tests**

```python
# Reader behavior after the port:
chain = validate_chain_schema(pd.read_parquet(cached))
metadata = chain_schema_metadata(chain.columns)
if verdict_bearing and metadata.schema_version < CHAIN_SCHEMA_VERSION_V2:
    raise CacheSchemaVersionError("v1 partitions are display-only")
if verdict_bearing:
    validate_v2_audit_receipt(
        cached.parent,
        cached,
        symbol=symbol,
        session=date,
        consumer_scope="H7",
    )
return chain
```

The original nine receipt-bound files and two omitted runtime dependencies must match the audited runtime before the real smoke check; the audit identity is extended to bind those dependencies. Unrelated future-ticker files are excluded.

- [x] **Step 4: Run focused tests and real read-only receipt validation**

Run the focused unittest files, then validate `NVDA_2026-07-31.parquet`
against the clean-commit receipt. Receipt `6fd9a3ca...9578` was superseded by
the dependency-closure repair (`c08106ba...c7e3`), the initial consumer-scoped
contract (`689c2b02...b1b6`), the formatter-clean contract
(`1e6951cc...61b3`), the programmatic-authority repair
(`316e415f...7959`), and the isolated scope-closed receipt
(`99d409c3...c68d`). The final combined-`main` receipt is
`865024a8...3123`, bound to source commit `14c59606...0174`.

Expected: focused tests pass; the real partition returns `PASS WITH WARNINGS` and its bound SHA-256.

- [x] **Step 5: Commit**

```bash
git add data/atomic_io.py data/cache_schema.py data/v2_partition_quarantine.json \
  data/thetadata_adapter.py data/recent_topup.py \
  options_researcher/h7_data_gate.py options_researcher/h7_synthetic_proof.py \
  options_researcher/h9_census.py \
  tools/thetadata_exit_audit.py tools/thetadata_v2_audit.py \
  tools/thetadata_v2_backfill.py \
  tests/test_cache_schema_v2.py tests/test_h7_data_gate.py \
  tests/test_thetadata_exit_audit.py tests/test_thetadata_v2_audit.py \
  tests/test_thetadata_v2_backfill.py \
  reports/thetadata_v2/2026-08-02-od1-full-audit.md \
  docs/superpowers/plans/2026-08-02-ritual-phase-a.md
git commit -m "feat(data): integrate audited v2 offline reads"
```

---

### Task 2: Fail-closed ritual authority and status lane

**Files:**
- Create: `data/ritual_authority.py`
- Modify: `tools/daily_ritual.sh`
- Modify: `tests/test_daily_ritual_provenance.py`
- Modify: `tests/test_h7_daily_exit_order.py`
- Modify: `.agents/skills/daily-ritual/SKILL.md`

**Interfaces:**
- Consumes: immutable provider policy and tracked paused-H7/exact-session-source constants.
- Produces: `python -m data.ritual_authority status` (read-only, exit 0) and `require-full` (exit 1 while blocked).

- [x] **Step 1: Add failing policy and shell-order tests**

```python
def test_full_ritual_is_blocked_without_source_and_h7_authority(self):
    readiness = evaluate_full_ritual()
    self.assertFalse(readiness.ready)
    self.assertIn("H7", " ".join(readiness.blockers))

def test_authority_preflight_precedes_every_mutation_surface(self):
    source = RITUAL.read_text()
    preflight = source.index("data.ritual_authority require-full")
    for token in ("mkdir -p", "--status RUNNING", "h7_exit_session", "h10_observe", "git add --", "restic backup"):
        self.assertLess(preflight, source.index(token))
```

- [x] **Step 2: Run focused tests and confirm RED**

Expected: missing module/preflight assertions fail before production edits.

- [x] **Step 3: Implement minimal authority gate and remove acquisition assumptions**

```python
CURRENT = RitualAuthority(
    h7_active=False,
    exact_session_source_active=False,
    provider_acquisition_active=False,
)
```

`tools/daily_ritual.sh status` prints the policy without writes. The default full path calls `require-full` before log creation and exits while blocked. Remove API-key resolution, both duplicate display top-ups, and the non-dry H7 top-up.

- [x] **Step 4: Run shell syntax, focused tests, mutation-token inspection, lint, and types**

Expected: status mode succeeds read-only; require-full refuses; focused tests, Ruff, Pyright, `zsh -n`, and `git diff --check` pass.

- [x] **Step 5: Commit**

```bash
git add data/ritual_authority.py tools/daily_ritual.sh tests/test_daily_ritual_provenance.py tests/test_h7_daily_exit_order.py .agents/skills/daily-ritual/SKILL.md
git commit -m "fix(ritual): fail closed before stateful work"
```

---

## Final verification

- [x] Run the affected test set and repository-standard lint/types.
- [x] Review all Phase A commits and confirm no cache bytes, provider calls,
  ledgers, paper books, ops files, scheduler state, or remote refs changed.
- [x] Leave the branch local and report that full ritual execution remains not
  ready.

Final verification: 2,347 tests passed; repository-wide Ruff lint and Pyright
passed; shell syntax and read-only ritual status passed; independent re-review
reported no remaining Critical or Important findings. Repository-wide Ruff
formatting still reports 250 legacy files, including pre-existing formatting
debt in `h7_watch.py`; that wholesale rewrite is outside Phase A.
