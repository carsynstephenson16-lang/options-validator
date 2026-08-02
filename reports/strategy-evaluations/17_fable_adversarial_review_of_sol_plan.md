# 17 — Adversarial review of the canonical Sol plan (`PROJECT_STATE.md`)

**Reviewer:** Fable High, adversarial senior reviewer.
**Date:** 2026-07-31. **Checkout:** `/Users/carsynstephenson/options-validator`,
branch `sfix`, HEAD `217a4c5`.
**Subject:** `PROJECT_STATE.md` (Sol High, audit date 2026-07-31), reviewed
against current repository evidence.
**Boundary:** read-only except this file. No subagents. No provider call, no
code/test/config/cache/ledger/facts/book/one-run write, no Git write, no edit to
Sol's plan. Commands re-run were read-only: `git log/status`, file reads,
`research.cli verify`, `h7_event_ledger verify`, `tools/cache_manifest.py verify`.

**The prior Fable handoff is not defended here.** Where Sol corrected it, the
correction is confirmed from current evidence and adopted.

---

## 1. Overall verdict

**ACCEPT WITH CONDITIONS — three critical corrections required before the queue
is executed.**

Sol's plan is substantially better than the Fable handoff it replaces. Its
governance posture, fail-closed defaults, surface taxonomy (V/F/B/C/R/P),
one-task-per-session boundaries, and ThetaData offline/online distinction are
correct and evidence-backed. I independently reproduced its ledger, manifest,
and seq-21 claims.

It is **not** safe as written on three points: one factual claim marked verified
is false (CI test discovery), one item is misclassified as a code defect when
the code faithfully implements a registered hypothesis (H6 hard kill), and the
audit missed two shipped provider-exit tools, which makes three queue tasks
partly duplicative and leaves a stale in-code cutoff date uncorrected. The
execution ordering also places the only deadline-bearing lane fifth.

---

## 2. Critical corrections

### C1 — `VERIFIED` test-discovery claim is false. Classification: **CORRECT**

**Sol's claim** (`PROJECT_STATE.md:105`):
> `Discovery audit | 2,236 tests; 144/144 test*.py modules | No top-level pytest
> tests or TestCase test methods omitted by CI's unittest command.`

**Roadmap item:** §3.2 evidence baseline; canonical-plan requirement "14.
Test-discovery and CI findings".

**Evidence:**
- `git ls-files tools/repo_rag/tests` → **11 tracked test modules**; all 11
  contain `unittest`.
- `.github/workflows/ci.yml:39` → `uv run python -m unittest discover -s tests`.
- `PROJECT_STATE.md` contains **zero** occurrences of `repo_rag`
  (`grep -c` = 0).

**Consequence:** 11 tracked unittest modules are collected by neither CI nor the
"current full offline baseline" of 2,236 tests. The baseline overstates the
repo's tested surface, `tools/repo_rag/` can rot silently, and any later agent
citing "2,236/2,236 passed" as full coverage is citing an incomplete number.
This is exactly the class of gap the prompt asked Sol to report and it is
reported inverted.

**Replacement wording for `PROJECT_STATE.md:105` and a new §3.4:**
> `Discovery audit | 2,236 tests; 144/144 test*.py modules under tests/ |
> INCOMPLETE: 11 tracked unittest modules under tools/repo_rag/tests/ are not
> collected by CI's -s tests discovery root and are not in the 2,236 baseline.`
>
> **§3.4 Test-discovery and CI findings.** (a) `tools/repo_rag/tests/` (11
> tracked unittest modules) is outside CI's discovery root; its current
> pass/fail state is unknown. (b) Push CI (`ci.yml:4-8`) targets only `main` and
> the obsolete `phase-1a-research-integrity`; `sfix` receives CI only through a
> pull request. (c) CI does not run `ruff format --check` (261-file pre-existing
> drift). Remedy for (a) and (b) is queued as Q1b.

### C2 — H6 hard kill matches its registration; it is an amendment, not a defect. Classification: **CORRECT + REORDER**

**Sol's claim** (`PROJECT_STATE.md:21-27`, row P0.7 at `:145`):
> "H6's hard-kill calls a month a full loss only when realized loss reaches the
> entire `$2,000` monthly cap. Three months that each deploy and lose roughly
> `$900` therefore do not trigger it. The code also keys losses by exit month
> and cannot see H8 despite the shared-cap setting."

**Roadmap item:** P0.7 (Sol-added), Q2, cleanup row "Correct | H6 kill".

**Evidence:**
- Registered H6 wording, `ledger/experiments.jsonl` (`H6_REGISTERED
  2026-07-08`): *"hard kill regardless: 3 consecutive calendar months each
  realizing the full monthly cap as losses."*
- `options_researcher/h6_watch.py:707-730`: `pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK`
  with `config.H6_MONTHLY_PREMIUM_AT_RISK = 2_000` (`config.py:339`) and
  `H6_HARD_KILL_FULL_LOSS_MONTHS = 3` (`config.py:345`). This is a literal,
  faithful implementation of the registered sentence.
- `H8_CAP_SHARED_WITH_H6 = True` (`config.py:367-368`) is a **sizing** constraint
  ("combined H6+H8 premium at risk shares H6_MONTHLY_PREMIUM_AT_RISK"). No
  registered H6 text makes H8 an input to the H6 kill rule, so "cannot see H8"
  is not a deviation from registration.
- Current exposure: `data/positions/h6_positions.csv` holds **one** row,
  `H6-0001` NVDA, `exit_date` empty. `_hard_kill` is called on `completed` only,
  so with zero closed positions it cannot fire, and
  `H6_MIN_COMPLETED_POSITIONS` is also unreached.

**Consequence:** Sol's *remedy* (prospective H6 v2, owner-typed, old rows
untouched) is right, but its *framing* is dangerous. Describing a registered
rule as a correctness defect and elevating it to P0 invites an implementing
agent to "fix a bug" inside a live registered hypothesis — the precise failure
`.cursorrules` and `ledger-discipline` exist to prevent. It is a **hypothesis
amendment**, governed by CLAUDE.md's amendment-delegation clause (independent
adversarial review + Fable sign-off + provenance label
"owner-delegated standing 2026-07-25"), and it carries no deadline and no
current adjudication exposure.

**Replacement wording for `PROJECT_STATE.md:21-27`, item 1:**
> 1. H6's hard-kill rule is implemented exactly as registered
>    (`ledger/experiments.jsonl` H6_REGISTERED: "3 consecutive calendar months
>    each realizing the full monthly cap as losses";
>    `options_researcher/h6_watch.py:707-730`). This is **not** an
>    implementation defect. It is a design limitation of the registered rule:
>    three months that each deploy and fully lose ~$900 do not trigger it, and
>    exit-month keying plus H8 exclusion are defensible readings of the
>    registered text, not deviations from it. Changing it is a **prospective H6
>    amendment** under the CLAUDE.md amendment-delegation clause, not a P0 fix.
>    Current exposure is nil: `data/positions/h6_positions.csv` holds one open
>    position and zero completed positions, so the kill rule cannot fire and no
>    H6 adjudication is pending.

**Replacement for the P0.7 row status field (`:145`):**
> **OWNER-GATED AMENDMENT / NOT A P0 BLOCKER.** Renumber to P2.5. Preparation
> (red/green fixtures under a new version flag) stays safe now.

### C3 — Two shipped ThetaData exit tools were never inventoried. Classification: **MERGE + CORRECT**

**Sol's omission:** `PROJECT_STATE.md` contains **zero** occurrences of
`thetadata_exit_audit` or `thetadata_cutoff_preflight` (`grep -c` = 0), yet §9,
Q5, Q6 and Q9 propose building acquisition-inventory, preflight, and cache
coverage capability.

**Evidence:**
- `tools/thetadata_exit_audit.py:1-12` — *"Read-only, content-addressed audit
  for ThetaData subscription exit… audits every selected symbol/session after
  `config.BACKTEST_END` without fetching data, binds the exact chain bytes and
  independent close files, and can write or verify a deterministic receipt."*
  Interface `--scope h7 --as-of YYYY-MM-DD [--write|--verify]`;
  `AUDIT_VERSION = "thetadata-exit-audit/1"`; receipts to
  `reports/thetadata_exit/`.
- `tools/thetadata_cutoff_preflight.py:38-52` — `SCHEMA =
  "thetadata-cutoff-preflight/v1"`, **`DEFAULT_CUTOFF = date(2026, 7, 29)`**,
  frozen 12-symbol `HISTORICAL_CUTOFF_SCOPE`, `SOURCE_PATHS` content-addressing.
- `reports/thetadata_exit/` **does not exist** — no exit receipt has ever been
  written despite the tool being read-only and runnable now.

**Consequence, two parts.** (a) Q5's "enumerate exact missing
sessions/endpoints/calls" and Q9's cache inventory duplicate shipped, tested,
content-addressed tooling; executing them as written spends a session
re-building capability. (b) OD-4's conflict set is **incomplete**. Sol lists two
conflicting dates (`docs/provider-transition.md:106-110`: 07-07 checklist
"ends 2026-07-29" vs PROJECT_STATE 07-23 "confirmed to 2026-11-30"). There is a
**third, in-code** source — `DEFAULT_CUTOFF = 2026-07-29` — which is now in the
past, and which will silently drive any default-argument preflight run. A stale
frozen constant is a fail-*open* path in a plan that claims fail-closed.

**Replacement wording — add to the OD-4 packet Evidence line
(`PROJECT_STATE.md:284`):**
> **Evidence:** conflicting dates at `docs/provider-transition.md:106-110`, plus
> a third in-code source `tools/thetadata_cutoff_preflight.py:DEFAULT_CUTOFF =
> date(2026, 7, 29)`, which is already in the past and will drive any
> default-argument run. Correcting or parameterizing that constant is a code
> change and belongs in Q5/Q7, not the docs-only task.

**Replacement wording — Q5 and Q9 Implementation lines:**
> Q5 Implementation: run the existing read-only tools first —
> `uv run python tools/thetadata_cutoff_preflight.py` (explicit `--cutoff`, never
> the stale default) and `uv run python tools/thetadata_exit_audit.py --scope h7
> --as-of <edge> --write` — and build the decision packet from their receipts.
> Only specify new code where those two tools provably do not cover the
> question. Writing the first `reports/thetadata_exit/` receipt is itself
> cheap, read-only evidence available today.
>
> Q9 Implementation: extend/reuse `thetadata_exit_audit.py`'s coverage and
> content-addressing rather than authoring a parallel inventory tool; keep the
> new work to the network-disabled replay harness and the DATA-GATED flow
> readiness report.

---

## 3. Important corrections

### I1 — The only deadline-bearing lane sits fifth. Classification: **REORDER**

Queue order is Q0 fact → Q1 docs → Q2 H6 kill → Q3 atomicity → Q4 H5 → Q5
provider closeout. But `docs/provider-transition.md` §3 states the v2 backfill
"is only executable while the ThetaData subscription is active… it cannot sit in
the P2 backlog as if it were schedulable later", and §2 concludes "anything that
needs new historical option data either happens before cancel day or never."
By contrast: H6 kill has zero completed positions (C2), and Q3 atomicity gates a
backtest that P0 forbids running anyway.

**Consequence:** the plan spends its first four sessions on items with no
deadline while the one irreversible window may close.

**Replacement:** reorder to **Q0, Q1, Q5, Q1b, Q6/Q7, Q4, Q3, Q8, Q9, Q2(→P2.5),
Q10-Q15.** Add to Q5 Goal: *"Position: first after documentation repair, because
OD-1/OD-2 are the only decisions in this plan that become permanently impossible
at cancellation."*

### I2 — CI push-trigger gap is reported but never queued. Classification: **SPLIT**

`PROJECT_STATE.md:113-117` correctly reports that push CI targets `main` and the
obsolete `phase-1a-research-integrity` (verified: `ci.yml:4-8`), but no queue
task or cleanup row fixes it, so `sfix` — the branch all work happens on — has no
push CI.

**Replacement — new task:**
> ### Q1b — Test discovery and CI trigger repair
> **Goal/position:** make CI's collected surface equal the repo's tracked test
> surface before further implementation. **Files:** `.github/workflows/ci.yml`,
> optionally a discovery shim; `tools/repo_rag/tests/`. **Allowed:** CI config and
> a discovery root addition. **Forbidden:** editing repo_rag test assertions to
> force green, mass formatting, any code fix bundled in. **Gate:** none.
> **Implementation:** run `tools/repo_rag/tests` once to record its true state;
> add it to discovery (or document an explicit, tracked exclusion with a reason);
> add `sfix` to the push branch list. **Proof:** CI run on `sfix` showing the new
> total; a recorded pass/fail state for the 11 modules. **One session:** yes.

### I3 — Plan lacks the required numbered test-discovery/CI section. Classification: **SPLIT**

The canonical-plan spec required a section "14. Test-discovery and CI findings".
Sol folded it into one table row of §3.2 — the row that is wrong (C1). Promote
it to §3.4 with the wording in C1.

### I4 — `append_fact` validation claim is over-precise. Classification: **ACCEPT WITH CONDITION**

`PROJECT_STATE.md:144` says the API "accepts arbitrary non-empty fact text".
`research/facts.py:17-29` performs **no** validation at all — it timestamps and
writes any string, empty included, under an `fcntl` lock. Sol's operational
conclusion (hash the approved payload before appending; the operator is the only
real guard) is correct and unchanged; only tighten the wording to "accepts any
string with no validation, no prefix concept, and no hash chain."

### I5 — Q8's gate is soft where it should be hard. Classification: **ACCEPT WITH CONDITION**

Q8 says "P0.8 code **should** land first if the audit claims engine-complete
behavior". Make it binary: *"Q8's receipt must be labelled `engine=pre-atomicity`
unless Q3 has landed; a receipt claiming engine-complete behavior before Q3 is a
stop condition."*

---

## 4. Accepted Sol improvements over the original Fable handoff

Independently re-verified this session; do not re-litigate.

1. **P0.6 — Fable's "confirm the ledger hook accepts the prefix" is void.**
   `research/facts.py` has no prefix concept; `research/cli.py` and
   `research/ledger.py` contain **zero** references to facts, so
   `research.cli verify` does not validate `facts.log`;
   `.agents/hooks/block_ledger_edits.py:43` guards only direct
   Edit/Write/NotebookEdit on protected paths. Sol's correction is confirmed.
2. **P1.3 — Fable's blanket "every watch fails closed" is FALSE.**
   `options_researcher/entry_watch.py:_gather` independently takes
   `closes.iloc[-1]`, `features.index[-1]`, and `sorted(glob)[-1]` with no
   common-session requirement, and `trigger_status` returns
   `"verdict": "FIRE"` whenever `unmet` is empty; staleness appears only as a
   printed note afterwards. Sol's PARTIALLY COMPLETE is correct and Q4 is the
   right remedy.
3. **P1.4 — grep-clean removal of `DATA_PROVIDER` is insufficient.**
   `config.py:90` is one constant, while `data/cache_runner.py:62`,
   `data/recent_topup.py:309,431` and `data/underlying_closes.py:135` reach
   fetch/blind-cache paths independently. Sol's central-disable-then-remove
   ordering is correct.
4. **Ledger and manifest baseline reproduced now:** `research.cli verify` →
   `ledger OK`; `h7_event_ledger verify` → `VALID records=1
   head=a1ea228c2abb`; `tools/cache_manifest.py verify` → `verify: 33
   problem(s)`, all `EXTRA` (Jul 24/27), no missing/mismatch. Seq 21
   `record_hash=a540a074…` present with `A_ENTRY_CREDIT_TOLERANCE=0.01` and the
   terminal exception text.
5. **P0.3 cap mechanism is genuinely implemented as registered.**
   `strategies/put_credit_spread.py:318-334` freezes the day-D legs, cancels on
   `execution_credit < signal_credit - A_ENTRY_CREDIT_TOLERANCE`
   (`config.py:244`), and resizes downward only via
   `min(pending.contracts, fill_contracts)`. I additionally checked the
   accounting path Sol did not: `_submit_spread` stores the day-D credit as
   `model_credit` only, while `entry_credit` is derived from realized
   `entry_fills` (`_ready_to_manage`), so the day-D credit never contaminates
   P&L, max loss, or the exit `captured` ratio. Sol's "VERIFIED COMPLETE WITH
   RESIDUAL RISK" stands, and the residual risk is correctly located in
   reproducibility of report 16, not in the mechanism.
6. **Structural judgments accepted:** split P2.2 rather than merging the stale
   `codex/cache-schema-v2` branch; no broad archive/delete sweep; classify
   branches before deleting; keep the options-flow lane visibly DATA-GATED
   rather than deleting it; preserve the `ov` bundle rather than deduplicating
   it away.

---

## 5. Missing work

1. `tools/repo_rag/tests` — 11 tracked modules outside CI, state unknown (C1).
2. CI push trigger excludes `sfix` (I2).
3. `tools/thetadata_cutoff_preflight.py:DEFAULT_CUTOFF` is a stale frozen date
   with no owning task (C3).
4. No task writes the first `reports/thetadata_exit/` receipt, although the tool
   is read-only, runnable today, and is the cheapest provider-exit evidence
   available before the cancellation date is known (C3).
5. No task records the H6 kill rule's **current non-exposure** (one open
   position, zero completed) in the plan, which is the fact that de-escalates
   P0.7 (C2).

---

## 6. Unsafe or poorly ordered work

- **Unsafe framing:** P0.7 as stated invites an agent to modify a live
  registered hypothesis under a "correctness" label (C2). This is the single
  highest-risk sentence in the plan.
- **Poorly ordered:** provider closeout fifth behind four deadline-free tasks
  (I1).
- **Poorly ordered:** Q1 is docs-only but the stale cutoff constant it should
  logically catch is code, so the defect falls between Q1 and Q5 with no owner
  (C3/I2).
- **Soft gate:** Q8 receipt labelling versus Q3 (I5).
- Everything else in §13 "Exact stop conditions" is correct and should be kept
  verbatim, including the data-authority stop on the 33 extras.

---

## 7. ThetaData continuity verdict

**ACCEPT.** Sol's core distinction is correct and repository-grounded:
cancellation ends **new acquisition** and must not disable **immutable cached
reads**. Confirmed at `docs/provider-transition.md` §2 — existing chain reads are
local and `UNCHANGED`; new historical collection `STOPS at cancel`; the cache
freezes at edge 2026-07-27 — and §5's four owner decisions. §8.3's frozen-data
contract (v1 bytes immutable, versioned lineage, as-of visible in output, no
silent fallback, no synthetic fill, cached reads survive cancellation,
network-disabled replay test) is sound and should be adopted as written.

Two conditions: (a) reuse `thetadata_exit_audit.py` for the read-only half of
§8.4 and Q9 rather than authoring parallel tooling (C3); (b) the "no new calls"
posture must not depend on the stale `DEFAULT_CUTOFF` constant.

Unverifiable here: the provider account's actual state. The repo's own dates
conflict three ways and that remains an owner fact.

---

## 8. Exact plan edits

Apply in this order. All are edits to `PROJECT_STATE.md` except where noted.

1. **`:105`** — replace the discovery-audit row with the C1 wording.
2. **New §3.4** — insert "Test-discovery and CI findings" per C1.
3. **`:21-27` item 1** — replace with the C2 wording.
4. **`:145` (P0.7 row)** — status becomes "OWNER-GATED AMENDMENT / NOT A P0
   BLOCKER"; renumber P0.7 → P2.5; update §10 dependency graph to move
   `P0.7 H6 new-version decision + build` out of the P0 cluster into the
   post-provider cluster.
5. **`:284` (OD-4 Evidence)** — add the third in-code date source per C3.
6. **`:314` (H6-KILL packet)** — retitle "H6-KILL — prospective amendment
   (not a defect)" and prepend: *"The current code implements the registered
   rule faithfully; this packet asks the owner to change a registered design,
   under the CLAUDE.md amendment-delegation clause with provenance label
   `owner-delegated standing 2026-07-25`."*
7. **§12 queue** — reorder to Q0, Q1, Q5, Q1b, Q6/Q7, Q4, Q3, Q8, Q9, Q2, Q10-Q15;
   insert Q1b verbatim from I2; amend Q5 and Q9 Implementation lines per C3;
   amend Q5 Goal per I1; amend Q8 gate per I5.
8. **`:144`** — "accepts arbitrary non-empty fact text" → "accepts any string
   with no validation, no prefix concept, and no hash chain".
9. **§11 cleanup table** — change the "Correct | H6 kill and Strategy A
   atomicity" row to two rows, separating "Register (amendment) | H6 kill" from
   "Correct | Strategy A atomicity"; add a row "Add test | repo_rag discovery +
   `sfix` push CI".

No other section requires change. §2, §6, §7 (other packets), §8.3, §13 and §14
are accepted as written.

---

## 9. Residual uncertainty

- I did **not** re-run the full suite; Sol's 2,236/2,236 figure is accepted as
  reported for the `tests/` root only. The pass/fail state of
  `tools/repo_rag/tests` is **unknown**.
- I did not re-audit P0.2 (ratio/drawdown) or P0.4 (terminal exit) test content;
  Sol's evidence is accepted and its cited files exist.
- Provider account status, entitlement, and true cancellation date are external
  owner facts; three conflicting repository sources exist and none is
  authoritative.
- No value-level audit of the 79.5M cached chain rows was performed by either
  session; structural metadata cannot prove quote, Greek, OI, split, or contract
  completeness.
- Whether `tools/thetadata_exit_audit.py`/`_cutoff_preflight.py` are fully
  current against `sfix` was checked only at interface level, not by running
  them.
- Whether the 33 manifest extras have complete acquisition facts was not
  re-derived; Sol's `facts.log:19324,19329` citation is accepted as covering 18
  of 33.

---

## 10. Self-audit

- Reviewed every P0, P1, P2 and P3 row of Sol's matrix; disagreements are
  limited to the items above, each with file/line or command evidence.
- Focus areas from the review brief covered: P0 cap enforceability (§4.5),
  entry/execution-date semantics (seq 21 verified verbatim), correction-fact
  governance (§4.1, I4), ledger verification (§4.4, re-run), provider
  disablement (§4.3, C3), cache as-of refusal (§4.2), ThetaData offline
  continuity (§7), H1/H2/H9/live-book paths (C2 — H6 book inspected read-only),
  v1 cache and one-run protection (accepted, unchanged), test discovery and CI
  (C1, I2), and every `VERIFIED COMPLETE` claim (one falsified: C1; one
  reclassified: C2; the rest confirmed).
- No new roadmap was produced. Sol's plan was not modified.
- No subagents. No code, test, cache, config, facts, ledger, book, one-run, or
  Git write. No provider or network call. The only write is this file.
- Every factual statement above cites a file, line, ledger record, or command
  result observed in this session; everything else is labelled uncertain in §9.
