# Ledger `retrospective_result` + H10a/H10b Registration Path — Implementation Plan (Track B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a trial-counting `retrospective_result` record type to the hash-chained ledger (`research/ledger.py`), a dry-run-first publisher for the QM attempt-#2 record, and dry-run-first registration bodies for H10a/H10b + the rank-quality prereg — with **zero production ledger writes**; every real append is owner-gated behind an explicit `--execute`.

**Architecture:** `research/ledger.py` gains one new entry type validated exactly like the six existing ones (strict allowed-keys, semantic checks, chain re-verify on append). H10a/H10b reuse the **existing `trial_intent`** type — no new code — because a registration is precisely what `trial_intent` is, and each append increments the chain's trial count (two records = two attempts, computed from the chain, never prose). Publishing tools default to dry-run: they print the canonical record and exit; `--execute` performs the append.

**Tech Stack:** Python 3.12, `uv`, `unittest` (offline, temp-dir ledgers only), `ruff`, `pyright`.

**API facts this plan is built on (Repo-verified, read 2026-07-18):**
- `research/ledger.py:18` `TRIAL_TYPES = {"run", "trial_intent"}` — members increment `trial_count`; `research/ledger.py:139-145` `_expected_trial_count`.
- `:34` `TRIAL_INTENT_KEYS = CHAIN_KEYS | {"timestamp", "reason", "hypothesis_id"}`; validated at `:284-287` (tz-aware timestamp, trimmed non-empty reason, optional hypothesis_id).
- `:201-205` `_reject_unknown_fields` — every type has an exact allowed-key set in `ALLOWED_KEYS_BY_TYPE` (`:94-101`).
- `:406-436` `append(body, base_dir="ledger")` — rejects reserved keys, runs full `verify()` first, fills `trial_count`, stamps `seq`/`prev_hash`/`record_hash`, re-runs semantic verification on the would-be chain, then writes and moves `HEAD`.
- `:439-455` `verify(base_dir, anchored=False)` — full chain + semantic verification; `anchored` additionally requires the ledger files git-committed-clean.
- All tests can (and MUST) target a temp `base_dir`; the real `ledger/` is never touched by tests.

---

## File Structure

- Modify: `research/ledger.py` — add `retrospective_result` (constants + semantic branch).
- Create: `tests/test_retrospective_result.py` — temp-dir ledger tests for the new type.
- Create: `tools/publish_qm_retrospective.py` — dry-run-first QM attempt-#2 publisher.
- Create: `tools/register_h10.py` — dry-run-first H10a/H10b + rank-quality `trial_intent` bodies.
- Test: `tests/test_h10_registration_tool.py` — dry-run behavior + body validation against a temp ledger.

---

## Task 1: `retrospective_result` schema + semantic validation

**Files:**
- Modify: `research/ledger.py`
- Test: `tests/test_retrospective_result.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_retrospective_result.py
"""retrospective_result: a trial-counting chained record for publishing a
result whose inputs already exist (no new run). Tests use a TEMP ledger dir --
never the real ledger/."""
import tempfile
import unittest
from pathlib import Path

from research.ledger import (
    RETROSPECTIVE_REQUIRED_LABELS,
    LedgerError,
    append,
    current_trial_count,
    verify,
)

SHA = "a" * 64
GITSHA = "b" * 40


def rr_body(**over):
    body = {
        "entry_type": "retrospective_result",
        "timestamp": "2026-07-18T12:00:00+00:00",
        "subject": "QM base-rates study attempt publication",
        "hypothesis_id": None,
        "report_sha256": SHA,
        "context_sha256": SHA,
        "prereg_ref_sha256": SHA,
        "source_commit": GITSHA,
        "labels": list(RETROSPECTIVE_REQUIRED_LABELS),
        "result": {"parabolic_5d_excess": 0.0268},
    }
    body.update(over)
    return body


class TestRetrospectiveResult(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_appends_and_verifies(self):
        append(rr_body(), base_dir=self.base)
        verify(base_dir=self.base)  # must not raise

    def test_increments_trial_count(self):
        self.assertEqual(current_trial_count(self.base), 0)
        append(rr_body(), base_dir=self.base)
        self.assertEqual(current_trial_count(self.base), 1)
        append({"entry_type": "trial_intent",
                "timestamp": "2026-07-18T12:01:00+00:00",
                "reason": "H10a registration", "hypothesis_id": "H10a"},
               base_dir=self.base)
        self.assertEqual(current_trial_count(self.base), 2)

    def test_missing_required_label_rejected(self):
        labels = [x for x in RETROSPECTIVE_REQUIRED_LABELS if x != "no-verdict"]
        with self.assertRaises(LedgerError):
            append(rr_body(labels=labels), base_dir=self.base)

    def test_unknown_field_rejected(self):
        with self.assertRaises(LedgerError):
            append(rr_body(verdict="PASS"), base_dir=self.base)

    def test_bad_report_sha_rejected(self):
        with self.assertRaises(LedgerError):
            append(rr_body(report_sha256="deadbeef"), base_dir=self.base)

    def test_result_must_be_dict(self):
        with self.assertRaises(LedgerError):
            append(rr_body(result="looked fine"), base_dir=self.base)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest discover -s tests -p "test_retrospective_result.py" -v`
Expected: FAIL / ImportError (`RETROSPECTIVE_REQUIRED_LABELS` not defined).

- [ ] **Step 3: Implement in `research/ledger.py`** — four edits:

Edit A (`:18`, replace the TRIAL_TYPES line):
```python
TRIAL_TYPES = {"run", "trial_intent", "retrospective_result"}
```

Edit B (after `TRIAL_INTENT_KEYS`, `:34`):
```python
# retrospective_result (BS-arc spec 2026-07-17 sec.9): a TRIAL-COUNTING record
# publishing a result whose inputs already exist (no new run). A post-result
# trial_intent would be semantically false ("intent" implies pre-result).
# The attempt number IS this record's chain-computed trial_count -- never
# restated in prose (owner correction 2026-07-18). Labels are mandatory
# honesty markers; result is the summary readings being published.
RETROSPECTIVE_REQUIRED_LABELS = (
    "outcome-selected",
    "self-deceiving",
    "descriptive-only",
    "no-verdict",
    "cannot-promote",
)
RETROSPECTIVE_RESULT_KEYS = CHAIN_KEYS | {
    "timestamp",
    "subject",
    "hypothesis_id",
    "report_sha256",
    "context_sha256",
    "prereg_ref_sha256",
    "source_commit",
    "labels",
    "result",
}
```

Edit C (`ALLOWED_KEYS_BY_TYPE`, `:94-101`, add one entry):
```python
    "retrospective_result": RETROSPECTIVE_RESULT_KEYS,
```

Edit D (in `_verify_semantic_records`, add a branch after the `trial_intent` branch at `:284-287`):
```python
        elif entry_type == "retrospective_result":
            _require_timestamp(rec, "timestamp", i)
            _require_canonical_text(rec, "subject", i)
            _require_optional_canonical_text(rec, "hypothesis_id", i)
            _require_sha256_hex(rec, "report_sha256", i)
            _require_sha256_hex(rec, "context_sha256", i)
            _require_sha256_hex(rec, "prereg_ref_sha256", i)
            _require_git_sha(rec, "source_commit", i)
            labels = rec.get("labels")
            if (not isinstance(labels, list) or not labels
                    or not all(isinstance(x, str) and x and x == x.strip()
                               for x in labels)):
                raise LedgerError(
                    f"labels must be a non-empty list of trimmed strings at seq {i}")
            missing = [x for x in RETROSPECTIVE_REQUIRED_LABELS if x not in labels]
            if missing:
                raise LedgerError(
                    f"retrospective_result missing required label(s) at seq {i}: "
                    f"{missing}")
            _require_dict(rec, "result", i)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -p "test_retrospective_result.py" -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Regression — the REAL chain still verifies** (new type must not disturb existing records)

Run: `uv run python -m research.cli verify`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add research/ledger.py tests/test_retrospective_result.py
git commit -m "feat(ledger): trial-counting retrospective_result record type"
```

---

## Task 2: QM attempt-#2 publisher (dry-run first)

**Files:**
- Create: `tools/publish_qm_retrospective.py`
- Test: covered by Task 1's schema tests + a `--help`/dry-run smoke check below

- [ ] **Step 1: Write the tool**

```python
# tools/publish_qm_retrospective.py
"""Publish the QM base-rates attempt-#2 retrospective_result -- WITHOUT
re-running the study (one-run-per-vintage contract is spent).

DRY-RUN BY DEFAULT: prints the canonical record and exits. --execute performs
the real chained append; owner go required (spec 2026-07-17 sec.9)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from research.ledger import RETROSPECTIVE_REQUIRED_LABELS, append

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "reports" / "2026-07-14-qm-base-rates.md"
CONTEXT = REPO / "reports" / "attractiveness_context" / "2026-07-15.json"
FACTS = REPO / "ledger" / "facts.log"
PREREG_MARKER = "QM_STUDY_PREREG"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prereg_line_sha(path: Path, marker: str) -> str:
    lines = [ln for ln in path.read_text().splitlines() if marker in ln]
    if len(lines) != 1:
        sys.exit(f"expected exactly one {marker} line in facts.log, found {len(lines)}")
    return hashlib.sha256(lines[0].encode()).hexdigest()


def _first_commit(path: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), "log", "--diff-filter=A", "--format=%H", "--", str(path)],
        capture_output=True, text=True, check=True).stdout.strip().splitlines()
    if not out:
        sys.exit(f"no commit found adding {path}")
    return out[-1]  # oldest = the commit that added the file


def build_record() -> dict:
    return {
        "entry_type": "retrospective_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": ("QM base-rates study (2026-07-14) attempt-#2 publication: "
                    "already-computed readings, no rerun"),
        "hypothesis_id": None,
        "report_sha256": _sha256_file(REPORT),
        "context_sha256": _sha256_file(CONTEXT),
        "prereg_ref_sha256": _prereg_line_sha(FACTS, PREREG_MARKER),
        "source_commit": _first_commit(REPORT),
        "labels": list(RETROSPECTIVE_REQUIRED_LABELS),
        "result": {
            "breakout_deduped_fires": 11,
            "breakout_reading": "descriptive only (10-19 band), no H8 decision possible",
            "parabolic_deduped_fires": 35,
            "parabolic_excess_5d": 0.0268,
            "parabolic_excess_10d": 0.0070,
            "parabolic_excess_20d": 0.0147,
            "parabolic_fade_reading": "REJECTED (median excess >= 0)",
            "h8_decision": "NO H8 arc for either setup",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true",
                    help="perform the real chained append (owner go required)")
    args = ap.parse_args()
    record = build_record()
    print(json.dumps(record, indent=2, sort_keys=True))
    if not args.execute:
        print("\nDRY RUN -- nothing appended. Re-run with --execute after owner go.")
        return
    record_hash = append(record)
    print(f"\nAPPENDED. record_hash={record_hash}")
    print("Commit ledger/experiments.jsonl + ledger/HEAD now.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run smoke test (no write)**

Run: `uv run python tools/publish_qm_retrospective.py`
Expected: prints the record with real SHAs; ends with `DRY RUN -- nothing appended.`
Then: `uv run python -m research.cli verify` → exit 0 (chain untouched).

The `result` numbers above are transcribed from ledger fact `QM_STUDY_RESULT
2026-07-14` (facts.log:12013). **Verify each against the actual fact line before
first dry-run; fix any transcription drift in the tool, not the fact.**

- [ ] **Step 3: Commit**

```bash
git add tools/publish_qm_retrospective.py
git commit -m "feat(ledger): dry-run-first QM attempt-#2 retrospective publisher"
```

---

## Task 3: H10a/H10b + rank-quality registration bodies (dry-run first)

**Files:**
- Create: `tools/register_h10.py`
- Test: `tests/test_h10_registration_tool.py`

The three registrations are **existing-type `trial_intent` appends** — no new
ledger code. Each `reason` string carries the full owner-locked frozen text
(source: `docs/superpowers/specs/2026-07-18-h10-rank-quality-parameter-proposals.md`,
LOCKED 2026-07-18). H10a and H10b are separate records → separate attempts.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_h10_registration_tool.py
import tempfile
import unittest
from pathlib import Path

from research.ledger import append, current_trial_count, verify
from tools.register_h10 import REGISTRATIONS


class TestH10Registrations(unittest.TestCase):
    def test_three_bodies_valid_and_count_three_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for body in REGISTRATIONS:
                append(dict(body), base_dir=base)
            verify(base_dir=base)
            self.assertEqual(current_trial_count(base), 3)

    def test_h10_lanes_are_separate_records(self):
        ids = [b["hypothesis_id"] for b in REGISTRATIONS]
        self.assertIn("H10a", ids)
        self.assertIn("H10b", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_owner_locked_values_present_in_reason(self):
        text = " ".join(b["reason"] for b in REGISTRATIONS)
        for needle in ("0.40-0.60", "30-60 DTE", ">=7 losses", "$2,000/month",
                       "2026-10-06", "2027-01-06"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m unittest discover -s tests -p "test_h10_registration_tool.py" -v`
Expected: FAIL / ImportError (`tools.register_h10` not found).

- [ ] **Step 3: Write the tool** (reason strings must carry the LOCKED values verbatim)

```python
# tools/register_h10.py
"""H10a/H10b + rank-quality chained registrations. DRY-RUN BY DEFAULT.

Owner-locked values (2026-07-18, spec sec.15 LOCKED block): delta 0.40-0.60,
DTE 30-60, verdict gate >=7 losses (H10 override of repo default 10, weaker
verdict disclosed), own $2,000/month premium cap (not shared with H6+H8),
windows H10a 2026-10-06 / H10b 2027-01-06. Signal selection is OUTCOME-INFORMED
and permanently disclosed; only observations after registration count."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from research.ledger import append

_COMMON = (
    "structure=defined-risk single long call, premium<=$600 (MAX_LOSS_PER_TRADE); "
    "contract=delta 0.40-0.60 within +/-10 pct of spot; 30-60 DTE; "
    "universe=H7_WATCHLIST names passing H7 admission at entry "
    "(>=5 NTM monthly contracts, spread<=5 pct, OI>=100), re-measured at entry; "
    "fills=mid-or-worse + SLIPPAGE_HAIRCUT + COMMISSION_PER_CONTRACT both legs; "
    "sizing=1 contract; concurrency=own cap $2,000/month premium at risk "
    "(NOT shared with H6+H8); earnings=skip entry if a known report lands inside "
    "the option life, source-health UNHEALTHY = per-name entry ban; "
    "exit priority=(1) +100 pct target (2) time-exit 20 trading sessions "
    "(3) 21 DTE; receipts=forward paper book only, no order path; "
    "verdict gates at >=7 losses (owner override of MIN_LOSSES_FOR_VERDICT=10, "
    "weaker verdict disclosed); reject=90 pct bootstrap CI upper<=0 on after-cost "
    "expectancy/trade; further-testing=CI lower>0; "
    "signal selection is outcome-informed (QM study 2026-07-14) and permanently "
    "disclosed; only observations recorded after this registration count."
)

REGISTRATIONS = [
    {
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H10a",
        "reason": ("H10a REGISTRATION -- QM parabolic long-continuation, forward "
                   "paper only, window ends 2026-10-06. " + _COMMON),
    },
    {
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H10b",
        "reason": ("H10b REGISTRATION -- QM breakout continuation, forward paper "
                   "only, window ends 2027-01-06 (low fire rate disclosed: 11 "
                   "historical fires; may stay INSUFFICIENT_SAMPLE). " + _COMMON),
    },
    {
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "RQ1",
        "reason": ("RANK-QUALITY DESCRIPTIVE PREREG -- no-verdict study: Spearman "
                   "rho between attractiveness GREEN-fraction and forward "
                   "21-trading-day realized vol (and separately forward IV "
                   "change); |rho|>=0.30 flagged notable, DESCRIPTIVE ONLY; "
                   "synthetic and lookahead-contaminated rows excluded; big 4 are "
                   "outcome-selected so no rho is ever edge without a fresh "
                   "forward preregistration."),
    },
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true",
                    help="perform the real chained appends (owner go required)")
    args = ap.parse_args()
    for body in REGISTRATIONS:
        print(json.dumps(body, indent=2, sort_keys=True))
    if not args.execute:
        print("\nDRY RUN -- nothing appended. Re-run with --execute after owner go.")
        return
    for body in REGISTRATIONS:
        record_hash = append(dict(body))
        print(f"APPENDED {body['hypothesis_id']}: {record_hash}")
    print("Commit ledger/experiments.jsonl + ledger/HEAD now; then update README "
          "scope status (four -> six live hypotheses) in the same commit.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest discover -s tests -p "test_h10_registration_tool.py" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Dry-run smoke + real-chain untouched**

Run: `uv run python tools/register_h10.py` → three bodies + `DRY RUN`.
Run: `uv run python -m research.cli verify` → exit 0.

- [ ] **Step 6: Commit**

```bash
git add tools/register_h10.py tests/test_h10_registration_tool.py
git commit -m "feat(ledger): dry-run-first H10a/H10b + rank-quality registration bodies"
```

---

## Task 4: full-suite green + lint gate

- [ ] **Step 1:** `uv run python -m unittest discover -s tests` → exit 0.
- [ ] **Step 2:** `uv run ruff check . && uv run pyright` → clean.
- [ ] **Step 3:** commit any fixes: `git commit -am "chore(ledger): track-B green"`.

---

## Owner-gated finale (NOT agent-executable; listed so it is never skipped)

1. Owner reviews both dry-run outputs (exact records, exact SHAs).
2. Owner says "register now" → run both tools with `--execute`.
3. Commit `ledger/experiments.jsonl` + `ledger/HEAD`; run
   `uv run python -m research.cli verify` again (exit 0).
4. Update README "Scope status" four → six live hypotheses **in the same
   commit** (spec §16) — only after both H10 records verify.
5. The QM cumulative attempt count is thereafter **computed from the chain**
   (`current_trial_count` + per-hypothesis queries), never asserted in prose.

Out of scope for Track B (later arcs): the H10 watcher/receipt lane, config
wiring of H10 caps, the earnings-path staleness fix (§8), the term-structure
column (§6), and the equity-research earnings cross-check (path still needed
from owner).

---

## Self-Review (done)

- **Spec coverage:** §9 (retrospective_result: defined, tested, trial-counting,
  publishes by hash without qm_study) → Tasks 1–2. §13 (two separate H10
  records, two attempts, README only after verify) → Task 3 + finale. §15
  LOCKED values verbatim in the reason strings, tested by needle-assertions.
  §2 (outcome-informed disclosure) → in both H10 reasons.
- **Placeholder scan:** none; every step has complete code/commands.
- **Type consistency:** `RETROSPECTIVE_REQUIRED_LABELS` tuple defined in Edit B,
  imported by test and publisher; `append`/`verify`/`current_trial_count`
  signatures match `research/ledger.py` as read (base_dir param).
- **Integrity check:** no test or dry-run touches the real `ledger/`; the only
  production-write path is `--execute`, which sits behind the owner-gated
  finale. `append()` itself re-verifies the whole chain first (`:410`), so even
  a mistaken `--execute` cannot corrupt an existing valid chain — it can only
  append a valid record or refuse.
