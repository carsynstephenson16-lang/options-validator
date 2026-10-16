# Codex brief 42 — Refuse H6/H8/H10b verdicts when `config.py` disagrees with the registered ledger record

**Date:** 2026-09-15
**Author:** Claude (orchestrating session, audit `claude/audit-2026-09-15` worktree `.tmp/worktrees/audit-0915`)
**Executor:** Codex (Sol, high reasoning)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Review history:** rounds 1–4, receipts I, K, N, O; round 4 verdict PASS WITH
FIXES, all applied in rev 5; final confirmation pending owner hand-off.
**Revision:** **rev 5** (2026-09-15) — round-4 scoped confirmation **PASS WITH
FIXES** (1 MUST-FIX, 3 SHOULD-FIX, 4 NOTE; no redesign, no anchor change, no
ruling reopened), receipt
`reports/2026-09-15-audit/O-brief-42-adversarial-review-round4.md`. Rev 5 moves
the hand-off gate to **rev 5 (or later)** because rev 3 halts itself on
Acceptance 14 (O1); fixes the WP-B.1.6→1.7 cross-reference left stale by rev 4's
own renumbering (O2); corrects "seven anchors" to **eight** (O3); corrects
WP-D.1's delivery-surface claim — the `crit` summary line carries only the fixed
literal `"h6_watch: NONZERO EXIT"`, while the refusal text lands in the **ritual
log** — and bounds the message to one line with an asserted field list (O4); and
applies O5–O8. Round-4 rulings: keep the remediation sentence in the refusal
message (corrected reason); close the lookup-cost question outright —
`verify()` measured at **1.3 ms cold / 0.6 ms warm**, paid once per process.
Rev 4 changelog, retained: split the H6 read list into **verdict-determining**
and **invariant-validating** (N16); required the WP-A lookup at the **top of
`score_book`, before `validate_book` at `:796`** (N17); removed WP-B.1.3's
mid-package stop-and-report (N18, ruling 1); named the owner as the only recorder
of a ruling (N19); applied N20–N23; rulings **(1)** v2 month count stays unbound
and tripwired, **(2)** WP-C.2 keeps **UTC**, **(3)** amendment-will-`crit`
warning in the refusal message, **(4)** WP-C **kept**. Earlier receipt:
`reports/2026-09-15-audit/N-brief-42-adversarial-review-round3.md` (round 3,
PASS WITH FIXES, N16–N23), which closed all fifteen round-2 findings against the
code. Prior receipts:
`reports/2026-09-15-audit/K-brief-42-adversarial-review-round2.md` (round 2,
PASS WITH FIXES, N1–N15) and
`reports/2026-09-15-audit/I-brief-42-adversarial-review.md` (round 1, FAIL —
3 blockers). Revs 1–3 are superseded in full. **Status stays DRAFT** until the
final confirmation review passes.
**Provenance:** every constraint below is **Repo-verified against branch
`claude/audit-2026-09-15` @ `f228894`** (`git rev-parse --short HEAD`, run in
the audit worktree 2026-09-15) unless it carries a different label. Labels used:
**Repo-verified**, **Inference**, **Assumption**.

*Header note (N15): the **Revision** field is inserted between Status and
Provenance. All five fields required by `.agents/skills/codex-brief-writing/SKILL.md`
are present in the required relative order; the insertion is cosmetic and was
reviewed as such. The filename slug (`-verdict-bar-ledger-binding-`) is
**unchanged on purpose** — the registry row and PR text reference it, and
renaming a reserved file is forbidden by this brief's own Explicitly-forbidden
list. Only the human-readable title changed.*

This brief closes findings **#2** and **#3** of section 4 ("Integrity findings
— owner decisions") in
`reports/2026-09-15-audit-edge-verdict-and-loose-ends.md`, whose underlying
evidence is memo `reports/2026-09-15-audit/A-evidence-audit.md` §5 items 2 and 3.
Cite those finding IDs verbatim ("audit 2026-09-15 §4 finding 2" / "finding 3")
in the PR body so the same findings are closed, not a reinterpretation.

---

## Why this exists (plain language)

A hypothesis is registered in the ledger with a rule for when it is allowed to
say "this failed" — for H6, "after 8 completed positions" plus a hard kill of
"3 consecutive calendar months each realizing the full monthly cap as losses".
The ledger entry is append-only and hash-chained. But the code that decides the
verdict does not consult it. It reads today's value out of `config.py`. Change
that file and the verdict changes with it, silently, with no record that the
bar moved.

That is not hypothetical. A test in the repo *depends* on the bar being
movable: `tests/test_h6_watch.py:493`, named
`test_hard_kill_uses_registered_configured_month_count`, patches the hard-kill
month count down to 2 and asserts the kill fires. Its name says "registered";
what it proves is the opposite — that config, not the registration, is in
charge.

### What this brief delivers, stated honestly before the work packages

*(Promoted from WP-A.5 per round-2 finding N7 and the reviewer's §3 ruling, so
the honest statement is read before the work, not 300 lines after it.)*

**This is a refusal guard, not H7-grade sourcing.** The difference matters and
the title now says so:

- **H7 is a binding.** At `h7_forward_scoring.py:357-359, 374` the number the
  scorer uses is lifted *out of* the sealed record —
  `min_losses_for_verdict = stage_bar`. Delete `config.MIN_LOSSES_FOR_VERDICT`
  from the file and H7 still scores correctly. The record is the source.
- **This is not that.** Under WP-A the number still comes from `config.py`. The
  registration record contributes exactly one bit: **accept or refuse**. Delete
  the anchor check and the scorer keeps working at whatever `config.py` holds.
- **Why it is still worth building.** It closes the reported defect. Today a
  lone `config.py` edit silently moves the verdict; afterwards it refuses. It is
  the strongest thing available without a ledger amendment, and an amendment is
  correctly OUT of scope (the H6/H8/H10b records have no structured bar field —
  see "The structural problem" below).
- **Do not describe this as "reading the bar from the ledger"** in the PR body,
  the commit message, or any status readout. The accurate phrase is: *config
  proposes, the registration vetoes.*

### Lanes in scope

- **H6** — **four** live-config reads on the verdict path (sample bar,
  hard-kill month count, v2 effective date, and the monthly cap that defines
  what a "full-loss month" *is*).
- **H8** — a registered hypothesis with a written verdict rule and **no scorer
  at all**. Nothing can adjudicate it. Whether to build one is an **owner
  decision this brief cannot make** (OWNER DECISION D-1).
- **H10b** — checked for the same defect. The finding is *different from what
  the audit summary implies*; read "What H10b actually is" before planning WP-C.

---

## Verified facts (the ground this brief stands on)

All `file:line` references are at `f228894`. Rounds 1 and 2 independently
re-verified every code citation; rev 3 carries forward only what survived.

### The H6 defect — four **verdict-determining** live-config reads

*(Rev 3 added read 4; round-2 finding N3. Rev 2 asserted "the three live-config
verdict reads" as exhaustive, which was false — the same mistake rev 1 made with
"two". Rev 4 does not repeat the exhaustiveness claim: the four below are the
verdict-determining reads on the `score_book` path found by inspection, and
Acceptance 14 requires Codex to re-derive the list rather than trust it.)*

**Two classes of `config.` read, and only one is in scope (N16).** `score_book`
reaches many more `config.` reads than the four below, and conflating them would
halt the job on the first grep. The distinction is:

- **Verdict-determining** — a value whose change moves the `verdict`,
  `hard_kill`, or `reason` fields of the returned `H6Score`. **These four are in
  scope.**
- **Invariant-validating** — reads inside `validate_book` (def `h6_watch.py:467`,
  running to `:606`; called from `score_book:796`), which raise `ValueError` on a
  book violating a registered invariant and **cannot select a verdict**.
  `validate_book` contains `config.` reads on **15 distinct lines (17
  occurrences — `:481` and `:504` each carry two)** *(Repo-verified count at
  `f228894`; O5)*, including `H6_MONTHLY_PREMIUM_AT_RISK` at `:582` and `:585`,
  `H6_MAX_ASK_DOLLARS` `:478`, `H6_MAX_CONTRACTS_PER_NAME` `:480`/`:481`/`:492`/`:494`,
  `H6_NAMES` `:490`, `H6_DTE_BAND` `:504`/`:506`, `H6_TAKE_PROFIT_PCT`
  `:553`/`:569`, `H6_CLOSE_AT_DTE` `:561`, `H6_MAX_CONCURRENT` `:595`/`:598`,
  and `COMMISSION_PER_CONTRACT` `:481`. **All of these are OUT of scope.**

Note that `H6_MONTHLY_PREMIUM_AT_RISK` appears in *both* classes: at `:748` it
is verdict-determining (read 4 below) and at `:582`/`:585` it is
invariant-validating. Bind the former; leave the latter alone. This dual role is
also why the lookup must run before `validate_book` — see WP-B.1.5 (N17).

| # | Claim | Evidence | Label |
|---|---|---|---|
| 1 | Sample bar read live at scoring time | `h6_watch.py:826` — `if len(completed) < config.H6_MIN_COMPLETED_POSITIONS:` inside `score_book` (def `:792`); message `:832`. Value `config.py:349` `= 8` | Repo-verified |
| 2 | Hard-kill month count read live | `h6_watch.py:719` — `required = config.H6_HARD_KILL_FULL_LOSS_MONTHS` in `_has_consecutive_months` (def `:718`); interpolated `:806`, `:813`. Value `config.py:350` `= 3` | Repo-verified |
| 3 | v2 effective date read live | `h6_watch.py:710` — `effective = date.fromisoformat(config.H6_KILL_V2_EFFECTIVE_ENTRY_DATE)` in `_kill_v2_effective_entry_date` (def `:708`). Value `config.py:354` `= "2026-08-03"` | Repo-verified |
| 4 | **Monthly cap read live — it defines what a "full-loss month" is** | `h6_watch.py:748` — `if pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK` inside `_hard_kill_v1` (def `:731`), feeding the streak set passed to `_has_consecutive_months` at `:750`; interpolated into the REJECT reason at `:808` (`${config.H6_MONTHLY_PREMIUM_AT_RISK:,.0f}`). Value `config.py:344` `= 2_000` | Repo-verified |
| 5 | Reads 3 and 4 are on the verdict path | `_hard_kill_v1` calls read 3 at `:732` and read 4 at `:748`; `_hard_kill_v2` calls read 3 at `:754`; `_hard_kill_versions` (`:779`) runs both; `score_book` calls it at `:802` and branches to `REJECT` at `:803` | Repo-verified |
| 6 | Editing read 3 disables the v2 kill silently | `_hard_kill_v2` skips positions with `entry_date < effective` (`:757-758`); `_hard_kill_v1` skips positions with `entry_date >= effective` (`:735-736`). A far-future date re-routes the whole book to v1 | Inference (direct reading of those branches) |
| 7 | Editing read 4 manufactures or suppresses a REJECT | `1` would make nearly any losing month a "full loss"; `10_000` makes the v1 hard kill unreachable | Inference |
| 8 | Read 3 is **not** in the declared verdict-affecting surface; read 4 **is** | `h6_config_snapshot` docstring `:898`; its name list has `H6_MONTHLY_PREMIUM_AT_RISK` at `:908`, `H6_MIN_COMPLETED_POSITIONS` `:913`, `H6_HARD_KILL_FULL_LOSS_MONTHS` `:914` — and no `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` | Repo-verified |
| 9 | Read 4 is also used on **non-verdict** paths — bind the verdict use, do not break the rest. `:384`/`:387` are entry sizing gates; `:582`/`:585` are `validate_book` invariants (see the two-class note above) | `h6_watch.py:384`, `:387`, `:582`, `:585` | Repo-verified |
| 10 | `_has_consecutive_months` is **shared by v1 and v2** | called at `:750` (`_hard_kill_v1`) and `:777` (`_hard_kill_v2`) | Repo-verified |
| 11 | A test pins the defect by patching a value | `tests/test_h6_watch.py:493`; body ends `:513-514` with `mock.patch.object(config, "H6_HARD_KILL_FULL_LOSS_MONTHS", 2)` then `assertTrue(score_book(rows).hard_kill)` | Repo-verified |
| 12 | The repo-wide config guard does not catch a **value** change | `tests/test_ritual_switch_on_hash_containment.py:357` compares the sorted tuple of uppercase **names** only; docstring `:358-366` says a value change "is NOT caught here" | Repo-verified |

**Consequence of 10 (the trap rev 1 walked into):** binding the shared helper's
count to seq 6 alone would apply a seq-6 value to the v2 rule registered at
seq 22. WP-B.1.3 handles this.

### The H7 pattern (the posture to imitate; H7 itself is read-only here)

| Claim | Evidence | Label |
|---|---|---|
| Entry point `score_forward_window` | `h7_forward_scoring.py:343` | Repo-verified |
| Reads events, requires exactly one `window_registration` | `:350`, `:351-353` | Repo-verified |
| Lifts the bar out of the sealed payload — two recorded copies | `:356` `registered_window`, `:357` `frozen`, `:358` `stage_bar`, `:359` `scorer_bar` | Repo-verified |
| Refuses on disagreement or bad type | `:367-373`, `ScoringValidationError` | Repo-verified |
| The **record's** value is what is used | `:374` `min_losses_for_verdict = stage_bar`; consumed at `:92`/`:108-109` and `:126`/`:424`/`:429` | Repo-verified |
| No-fallback doctrine is explicit | `h7_scoring_identity.py:190-208` — round-1 finding **F3**: an optional argument defaulting to `config.MIN_LOSSES_FOR_VERDICT` "silently reintroduces exactly the contradiction WP-F exists to close"; `None` is a typed refusal | Repo-verified |
| Proven by test | `tests/test_h7_forward_scoring.py:326` `test_frozen_bar_is_the_registered_one_not_config` | Repo-verified |
| H7's tests build a temp-dir fixture over a **different store with a different API** (`ledger.read_events` over `ledger/h7_forward/events.jsonl`) | `tests/test_h7_forward_scoring.py:39` `ScoringCase`, `setUp` `:40-43`, synthetic append `:44-57` | Repo-verified |

**H7's shape cannot be copied literally**, and its *fixture* approach does not
transfer either — see WP-E Fixtures (N6).

### The registration records

Read from `ledger/experiments.jsonl` at `f228894`.

| Record | `seq` | `hypothesis_id` | `record_hash` | Value location |
|---|---|---|---|---|
| H6 registration (v1 bar, v1 kill, monthly cap) | **6** | `"H6"` | `5d813b8f…f3cf` | prose in `reason` |
| H8 registration | **11** | `"H8"` | `1eed4ae6…2005` | prose in `reason` |
| H10b registration | **16** | `"H10b"` | `401629c6…a3be` | prose in `reason` |
| **H6 hard-kill v2** (`H6_KILL_V2`, 2026-08-02) | **22** | `"H6"` | `4c552641…548b04` | prose in `reason` |
| `H10B_AMENDMENT_V1_1` (H10b resume floor, clause 5) | **28** | `"H10b"` | — | clause 5 prose **+ sealed `timestamp`** |
| `H5_AMENDMENT_V1` (H5 resume floor, clause 5) | **29** | `null` | — | clause 5 prose **+ sealed `timestamp`** |
| `H10B_H5_AMENDMENT_CORRECTION_V1` (corrects seq 28 and 29; **no clause 5**) | **30** | `"H10b"` | — | n/a |

**seq 22 is a prospective replacement hard-kill rule**, not a restatement:
"Cohorts are H6-only calendar **entry** months … **Three consecutive full-loss
calendar entry cohorts trigger H6 rejection.** Existing H6 rows retain v1
exit-month and full-cap semantics." It changes when `REJECT` fires and states
the month count a second time, in a second record. *(Repo-verified. Rev 1
mislabelled it and claimed "none of them changes a bar"; both were false.)*

### The structural problem — no structured bar field exists

The H6/H8/H10b/H6-v2 records state their numbers as **free prose inside
`reason`**:

- seq 6: "Sizing: total premium at risk <= **USD 2,000 per calendar month** …
  REJECTS H6: **after 8 completed positions**, bootstrap CI90 upper bound of
  per-trade expectancy < 0; **hard kill regardless: 3 consecutive calendar
  months** each realizing the full monthly cap as losses."
- seq 11: "SIZING: SHARED monthly cap with H6 — combined H6+H8 premium at risk
  <= **USD 2000 per calendar month** … REJECTS H8: **after 8 completed
  positions**, … **hard kill regardless: 3 consecutive calendar months** …"
- seq 16: "**verdict gates at >=7 losses** (owner override of
  MIN_LOSSES_FOR_VERDICT=10, weaker verdict disclosed)".
- seq 22: "effective only for H6 entries **on or after 2026-08-03** … **Three**
  consecutive full-loss calendar entry cohorts trigger H6 rejection."

*(Repo-verified — quoted from those `reason` fields.)*

Adding a structured field would be a ledger amendment, which is **OUT**. WP-A
specifies the guard that is available without one. **Exception, and it is a real
one:** seq 28 and seq 29 *do* carry a sealed typed field relevant to the resume
floors — their `timestamp`. See WP-C.2.

### What H10b actually is (read before planning WP-C)

The audit's instruction "H10b should be checked for the same live-config read"
is correct as an instruction, but the implied finding is **not** what the code
shows. Rounds 1 and 2 both confirmed this section.

| Claim | Evidence | Label |
|---|---|---|
| `H10_MIN_LOSSES_FOR_VERDICT = 7` exists, comment-bound to the record | `config.py:625` — `# ledger/experiments.jsonl seq 15/16` | Repo-verified |
| **No production module reads it** | repo-wide grep → `config.py:625`, `tests/test_ritual_switch_on_hash_containment.py:140`, `tests/test_h10_config.py:29`, `:46` — tests only | Repo-verified |
| `h10_watch.py` has no scorer | no `score`/`verdict` function; banner "alerts + receipts only; never trades; verdict gates on losses" (`:35-37`) | Repo-verified |
| `h10_observe.py` has no scorer | receipt/observation plumbing only | Repo-verified |
| The live-config read that **does** exist on the H10b path is the **resume floor** | `h10_watch.py:541` reading `config.py:629` | Repo-verified |
| Same shape on the H5 observer | `entry_watch.py:223` reading `config.py:630` | Repo-verified |
| Clause 5 defines the floor as a two-term derivation, **one term of which is machine-checkable** | seq 28 clause 5: "the LATER of (i) the first session on/after the implementation landing and (ii) **this amendment's ledger append date**"; seq 29 clause 5: "Identical mechanism to H10B clause 5". `config.py:628` comment: "mechanical floor per seq 28/29 clause 5; append date 2026-08-18 ET" | Repo-verified |
| Term (ii) is present as a **hash-sealed typed field** | seq 28 `"timestamp": "2026-08-19T01:05:33.937513+00:00"`; seq 29 `"timestamp": "2026-08-19T01:05:33.939961+00:00"` | Repo-verified |

**Inference:** H10b's exposure is (a) an *unread* bar constant — a scorer built
later would have nothing forcing it to use the registered 7 — and (b) a
live-config resume floor. Rev 2 claimed the floors "cannot be anchored" because
"no literal `2026-08-19` exists in any record"; **that was false and unlabelled**
(round-2 N4), and it forbade finding the real check. WP-C.2 now specifies it.

### The H8 gap

| Claim | Evidence | Label |
|---|---|---|
| H8 has a registered verdict rule (quoted above) | seq 11 | Repo-verified |
| H8 has **no scorer of any kind** | `grep -c "score" options_researcher/h8_watch.py` → **0**; no `def .*score`/`verdict`/`REJECT`/`hard_kill` hits | Repo-verified |
| Bar constants exist, no production reader | `config.py:383` `= 8`; `:384` `= 3` | Repo-verified |
| H8's monthly cap is **shared with H6** by registration | `h8_watch.py:365`, `:586`, `:614`, `:853` read `config.H6_MONTHLY_PREMIUM_AT_RISK` | Repo-verified |

---

## OWNER DECISION D-1 — H8: build a scorer, or retire pending re-registration

**This brief cannot make this call, and the executor must not either.** Audit
§4 finding 3's disposition is explicitly "Same brief as #2, **or retire H8
pending re-registration (owner call)**."

- **D-1a — Build.** An H8 scorer binding its rule to seq 11 via WP-A, mirroring
  H6's `score_book` shape. Cost: new verdict-bearing code for a lane with 0
  completed positions and, per memo A, no realistic path to 8 completed inside
  a year.
- **D-1b — Documentation-only retirement.** Comments in `config.py` beside
  `:383-384` and a line in the `h8_watch.py` module docstring recording that H8
  has no bound scorer and that any verdict requires a new owner registration.
  **No new function, no refusal entry point, no test module** — rev 1 specified
  a "typed refusal on any H8 adjudication attempt", which would have required
  the executor to invent an entry point, name, signature, and call sites that do
  not exist.

**Ruling status: UNRULED as of rev 3.**

**How a ruling reaches Codex, and what "unruled" means operationally**
*(round-2 finding N12 — rev 2 gave two conflicting instructions):*

- A D-1 ruling reaches Codex **only** as an owner-recorded amendment to this
  brief file on `origin/main`, or as an owner message at dispatch. Codex never
  infers one, and never edits this brief to record one.
- **Unruled means WP-B.2 is SKIPPED, not halted.** Everything else in the brief
  completes, the PR is opened, and its body records "D-1 unruled; WP-B.2 skipped
  with reason". Acceptance 10 checks exactly this. Codex does **not** stop the
  whole job. (Rev 2's "stop and report" wording conflicted with Acceptance 10,
  which presumes a PR exists.)

---

## Scope

### IN

1. `options_researcher/h6_watch.py` — the **four** live-config verdict reads at
   `:710`, `:719`, `:748`, `:826`, and the reason-string interpolations at
   `:806`, `:808`, `:813`, `:832` that must stay consistent with the values
   actually used. *(Rev 3 adds `:748` and `:808`; round-2 N3.)*
2. A new guard module (`options_researcher/registered_bars.py` unless review
   directs otherwise) implementing WP-A.
3. `tests/test_h6_watch.py` — invert `test_hard_kill_uses_registered_configured_month_count`
   (`:493`) per WP-D.
4. `options_researcher/h8_watch.py` and a matching test module — **only under a
   recorded OWNER DECISION D-1 ruling**, per WP-B.2.
5. `tests/test_h10_config.py` — extend the existing prose-anchor pattern, per
   WP-C.1.
6. Resume-floor checks for `config.py:629`, `:630`, per WP-C.2.
7. New tests per WP-E.

### OUT — explicit; the executor may not negotiate these

- **No ledger writes.** Not `ledger/experiments.jsonl`, `ledger/HEAD`,
  `ledger/h7_forward/*`, or `ledger/facts.log`. Per `.claude/rules/ledger.md`
  these are append-only hash chains written only through their typed APIs, and a
  `block_ledger_edits` hook block is correct. If the work seems to *need* a
  ledger write, stop and report. **Read-only reads of the real ledger are
  permitted** (WP-E Fixtures).
- **No registration and no amendment.**
- **No change to any frozen value.** `H6_MIN_COMPLETED_POSITIONS` 8,
  `H6_HARD_KILL_FULL_LOSS_MONTHS` 3, `H6_MONTHLY_PREMIUM_AT_RISK` 2_000,
  `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` `"2026-08-03"`, `H8_MIN_COMPLETED_POSITIONS`
  8, `H8_HARD_KILL_FULL_LOSS_MONTHS` 3, `H10_MIN_LOSSES_FOR_VERDICT` 7,
  `H10B_RESUME_FLOOR_SESSION` / `H5_RESUME_FLOOR_SESSION` `"2026-08-19"`,
  `MIN_LOSSES_FOR_VERDICT` 10.
- **No change to any `config.py` value**, and no addition, removal, or rename of
  any uppercase config name (that changes `config_hash()` and trips
  `tests/test_ritual_switch_on_hash_containment.py:357`). Comment lines may be
  added.
- **No second home for any verdict number.** `.cursorrules` requires "Every
  number in strategy logic comes from `config.py`. No magic numbers";
  `CLAUDE.md:53` reserves typing frozen numbers to the owner. The new module
  must contain **no numeric verdict constants** — only `seq` integers, anchor
  templates, and refusal code (Acceptance 8).
- **No live-order paths**, no activation, no Schwab-lane authority change.
- **No authority flips.** No `data/ritual_authority.py` change, no window
  pause/resume, no "GO" a gate did not already give.
- **No H8 scorer semantics invented by the executor.** See D-1.
- **No verdict emitted, changed, or ratified.**
- **No change to H7's behavior.** `h7_forward_scoring.py` and
  `h7_scoring_identity.py` are read-only references.
- PR opens as a **GitHub draft** and stays one.

---

## Work packages

### WP-A — The refusal guard (prose anchor; everything depends on it)

**Why the mechanism is what it is.** Rev 1 specified a `rec["record_hash"] == PIN`
field comparison plus hand-transcribed numeric constants. Both were wrong:
`research.ledger.read_all` (`research/ledger.py:141`) returns raw
`list[dict]` and **never recomputes** `record_hash`, so a field comparison
catches nothing if the prose is edited and the field left alone; and
transcribed constants would have created a second executor-maintained copy of
five owner-frozen numbers. The in-repo precedent for the correct approach
already existed: `tests/test_h10_config.py:7` `_load_registration(seq)` reads
the ledger by seq and `:50-51` anchor config values in the registration text
with `assertIn`. *(Repo-verified.)*

1. **Read and seal.** Load records via `research.ledger.read_all` — an
   **untyped `list[dict]`; it is *not* a typed reader** — and call
   `research.ledger.verify(base_dir=...)` first. `verify()` **does recompute**
   every record's hash over its body (`research/ledger.py:557-559`), check the
   `prev_hash` chain (`:555-556`), run `_verify_semantic_records` (`:561`, def
   `:347`), and require `HEAD` to match the chain tip (`:562-563`). That
   recomputation — not a stored-field comparison — is what makes the prose
   trustworthy. A `LedgerError` is a refusal, never a fallback.
   **Threat model, stated precisely** (round-2 §2c): a partial edit is caught —
   editing seq 6's prose breaks `:558`; fixing that breaks seq 7's `prev_hash`
   at `:555`. Defeating the guard requires rewriting the whole chain from that
   seq forward **plus** `ledger/HEAD`. That residual is backstopped by the
   `block_ledger_edits` hook and by git history, not by this module.
   **`anchored` parameter (N8):** the real signature is
   `verify(base_dir="ledger", anchored=False, git_clean_tracked=None)`
   (`research/ledger.py:549`); `anchored=True` adds `_require_committed_clean`
   (`:564-565`), the only check that would also catch a working-tree rewrite.
   **Use the default `anchored=False`** in the production lookup, deliberately:
   the daily ritual must not fail because the working tree is dirty. Record that
   reason in the module docstring. Do not leave it to executor default.
2. **Select the record defensively, and know which check is load-bearing.**
   Select by `seq`, using the seq integers as the module's only numeric
   constants. Assert `entry_type == "trial_intent"` and the expected
   `hypothesis_id` (`"H6"` for seq 6 and 22, `"H8"` for seq 11, `"H10b"` for
   seq 16) before trusting a row. **Note (N13): uniqueness is already
   guaranteed by `verify()`**, which requires `rec["seq"] == index`
   (`research/ledger.py:553-554`) — so duplicate or skipped seq values are
   structurally impossible once `verify()` passes, and a later record containing
   the same sentence lands at a new seq and is never consulted. Keep the
   `entry_type`/`hypothesis_id` assertions as cheap belt-and-braces, but state
   in the docstring that `verify()` is the load-bearing check, so a reader does
   not mistake the defensive one for it.
3. **Anchor the config value in the registration's own words.** For each guarded
   value, build the expected substring from the **live `config.py` value** and
   refuse unless it appears in that record's `reason`. No number is typed by
   anyone. The **eight** anchors, each **verified to match at `f228894`** by
   constructing the f-string from the current config value and testing
   membership — independently re-run by the round-2, round-3 and round-4
   reviewers, **8/8 PASS** each time. *(O3: rev 4 said "seven" over a table of
   eight — the same countable-claim slip as N3 and N16, in the one section where
   a miscount could let an executor think an anchor is optional.)*

   | Guarded value | `seq` | Required substring (built from config) | Status |
   |---|---|---|---|
   | `H6_MIN_COMPLETED_POSITIONS` | 6 | `f"after {v} completed positions"` → "after 8 completed positions" | Repo-verified PASS |
   | `H6_HARD_KILL_FULL_LOSS_MONTHS` (v1) | 6 | `f"hard kill regardless: {v} consecutive calendar months"` | Repo-verified PASS |
   | **`H6_MONTHLY_PREMIUM_AT_RISK`** | 6 | `f"USD {v:,} per calendar month"` → "USD 2,000 per calendar month" | Repo-verified PASS |
   | `H8_MIN_COMPLETED_POSITIONS` | 11 | `f"after {v} completed positions"` | Repo-verified PASS |
   | `H8_HARD_KILL_FULL_LOSS_MONTHS` | 11 | `f"hard kill regardless: {v} consecutive calendar months"` | Repo-verified PASS |
   | **`H6_MONTHLY_PREMIUM_AT_RISK`** (H8 shared cap) | 11 | `f"USD {v} per calendar month"` → "USD 2000 per calendar month" | Repo-verified PASS |
   | `H10_MIN_LOSSES_FOR_VERDICT` | 16 | `f"verdict gates at >={v} losses"` | Repo-verified PASS |
   | `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` | 22 | `f"on or after {v}"` → "on or after 2026-08-03" | Repo-verified PASS |

   **Anchors are format-coupled; this is a rule, not an accident (N9).** The
   same value `2000` appears as **"USD 2,000"** in seq 6 and **"USD 2000"** in
   seq 11 — so the format spec (`{v}` vs `{v:,}`) is a per-record choice. Each
   anchor template **including its format spec** is fixed in the module as a
   literal keyed on the `(seq, config-name)` pair, verified once at
   brief-writing time. **Adding a new anchor requires re-verifying it against
   the record and recording the PASS in this brief before implementation** — an
   executor may not invent one.
   **No distractor risk on seq 16** (round-2 §2d): the record contains
   `"MIN_LOSSES_FOR_VERDICT=10"`, but `"verdict gates at >=10 losses"` is
   verified absent, so a config edit to 10 still refuses.
4. **The one value that cannot be anchored, stated rather than fudged.** Seq 22
   writes its month count in **words** — "**Three** consecutive full-loss
   calendar entry cohorts trigger H6 rejection" — so
   `f"{config.H6_HARD_KILL_FULL_LOSS_MONTHS} consecutive full-loss calendar entry cohorts"`
   is **verified NOT to match** at `f228894` (re-confirmed by round-2). Do
   **not** invent a word-form map, regex, or fuzzy match. Handle per WP-B.1.3.
5. **Fail-closed, one semantics, binding on every downstream WP.** Every failure
   above — chain verify error, missing seq, wrong `entry_type`/`hypothesis_id`,
   absent anchor substring — raises a **typed refusal**. The scorer **refuses;
   it does not "follow" either side**, and there is no "registration wins" path.
   Same posture as H7 at `h7_forward_scoring.py:367-373`. No WP may specify
   different behavior. What this does and does not achieve is stated in "Why
   this exists" above; do not restate it more strongly anywhere.
6. **Memoisation — cache the records, never the resolved value (N5).** Rev 2's
   "read and verify once per process, memoised" was ambiguous in a way that
   could silently disable the whole guard. The requirement is exact:
   - **Cache only** the **fact that `verify()` succeeded** for this `base_dir`,
     plus the parsed record bodies. *(N22: `verify()` returns `None`
     (`research/ledger.py:549-565`), so "cache the result" would literally mean
     caching `None` — do not write `if cached_result:` and re-verify on every
     call. Cache a boolean or a sentinel.)*
   - **The anchor comparison is re-evaluated on EVERY call**, against the live
     `config` attribute read at call time. Never cache a resolved bar value.
   - Rationale: caching the resolved value reproduces the
     `h7_scoring_identity.py:190-208` F3 defect this brief cites approvingly — a
     convenience that silently reintroduces the contradiction the work exists to
     close. It would also make WP-E's refusal tests order-dependent inside the
     shared `unittest discover` process.
   - Proven by Acceptance 15 and WP-E Group 1's second-call test.

### WP-B — H6 (and, conditionally, H8)

**WP-B.1 — H6 (unconditional).**

1. `h6_watch.py:826` takes its sample bar from the WP-A lookup for **seq 6**.
2. `h6_watch.py:710` takes its date from the WP-A lookup for **seq 22**, the
   record that registers it. Cite in the code comment the existing precedent:
   `config.py:355` `H6_KILL_V2_TRIAL_INTENT_HASH` is **already** a record-hash
   pin to seq 22, consumed at `h6_watch.py:1065` (receipt field
   `hard_kill_v2_trial_intent_record_hash`) and `:1199` (receipt verification
   refusing a wrong registration). *(Repo-verified.)* Do not change, remove, or
   duplicate that pin.
3. **The shared `_has_consecutive_months` month count — the record/rule
   mismatch.** The helper (`:718`) is called by `_hard_kill_v1` (`:750`) and
   `_hard_kill_v2` (`:777`), but v1's count is registered at seq 6 and v2's at
   seq 22. Required treatment:
   - Pass the count in explicitly from each caller rather than reading `config`
     inside the shared helper. **Threading the count touches three signatures,
     not one (O6):** `_hard_kill_versions` (`:779`), `_hard_kill_v1` (`:731`)
     and `_hard_kill_v2` (`:753`), as well as the helper itself (`:718`). There
     is also an unused wrapper `_hard_kill` (`:788-789`,
     `return bool(_hard_kill_versions(book))`) with **no callers anywhere** in
     `options_researcher/` or `tests/` at `f228894` *(Repo-verified by grep)*:
     **keep it compiling, do not delete it** — deleting it is a scope expansion.
   - Bind the **v1** caller to **seq 6** (anchor verified PASS).
   - For the **v2** caller, the count is registered at seq 22 in word form and
     is **not anchorable** (WP-A.4). **Leave it reading `config` exactly as it
     does today — unbound, not bound to the wrong record** — with a code comment
     naming the word-form obstacle and citing Group 2's
     `test_seq22_month_count_is_word_form_not_numeric`. Record in the PR body
     that the v2 hard-kill month count remains unbound and why. Do **not** reuse
     the seq-6 value for it, and do **not** write a word-form parser. Both
     numbers are 3 today, which is precisely why this must not be papered over —
     bound to the wrong record, the code would look correct while being wrong.
     **This is a documented gap, NOT a stop-and-report: the rest of the brief
     completes.** *(Rev 4, ruling 1 / N18. Rev 3 specified a mid-package "stop
     and report" here, which would have halted WP-B.1.4, WP-B.1.5, WP-C, WP-D,
     WP-E and the PR over one caller of one helper — the same defect round-2
     finding N12 closed one package over. The v2 caller being unbound is exactly
     today's behaviour, so nothing regresses.)*
4. **`h6_watch.py:748` — the monthly cap on the v1 hard-kill path (N3).** Bind
   the `pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK` threshold and the `:808`
   reason interpolation to the **seq 6** anchor. **Do not touch the non-verdict
   uses** at `:384`, `:387`, `:582`, `:585` — those are sizing gates, not
   adjudication, and changing them is out of scope. Note this constant is
   already inside `h6_config_snapshot`'s declared surface (`:908`), so no
   receipt-surface change is involved.
5. **Lookup ordering — required, not stylistic (N17).** The WP-A lookup is
   performed **once at the top of `score_book`, before the `validate_book` call
   at `:796`**, and all guarded values are resolved by that single call and
   passed down. The reason: a guarded value that also appears in
   `validate_book`'s invariants (`H6_MONTHLY_PREMIUM_AT_RISK` at `:582`, raising
   `ValueError` at `:583-586`) would otherwise raise **before** the guard could
   refuse — so a test patching the cap to `1` would observe
   `validate_book`'s `"gross premium risk"` `ValueError`, not the typed refusal.
   The same ordering bites the sample bar: if the lookup were deferred to `:826`,
   a hard-killing book returns `REJECT` at `:803` and the sample bar is never
   consulted. *(Repo-verified: `score_book:792` → `validate_book(book)` at
   `:796`; `validate_book` def `:467`.)*
   **`validate_book` has a second caller: `_book_state` (def `:328`, calling
   `validate_book(book)` at `:329`). It is a position-state helper, not a verdict
   path — do NOT add the lookup there (O7).** Adding it for symmetry would widen
   the `crit` blast radius beyond H6 scoring for no integrity gain.
6. The reason strings at `:806`, `:808`, `:813`, `:832` interpolate the **same
   guarded values** that single lookup returned — never a second `config` read.
7. Do not change H6's verdict **semantics**: the CI90 logic (`:840-866`), the
   verdict labels, the `H6Score` shape (`:164`), the v1/v2 split, and
   `h6_config_snapshot` (`:898`) all stay as they are. Adding
   `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` to that surface (`:913-914`) changes a
   receipt payload and is **out of scope** — flag it in the PR body as a
   follow-up. **Do not touch `validate_book` (`:467-606`) at all** — its 15
   `config.` reads are invariant-validating, not verdict-determining (N16).

**WP-B.2 — H8 (CONDITIONAL on a recorded D-1 ruling; skipped if unruled).**

- *If D-1a (build):* an H8 scorer mirroring H6's `score_book` shape, guarded via
  WP-A against seq 11 (all three seq-11 anchors verified PASS), implementing the
  registered rule as written and nothing more. Note the shared-cap coupling
  (`h8_watch.py:365`, `:586`, `:614`, `:853`): H8's hard-kill "full monthly cap"
  clause refers to the H6 cap. State the interpretation in the PR body and flag
  it for review; do not decide it silently.
- *If D-1b:* documentation only, as described under D-1.
- *If unruled:* **skip WP-B.2, complete the rest, record the skip in the PR
  body** (Acceptance 10). Do not pick a branch.

### WP-C — H10b and the resume floors

The scorer half is vacuous (no H10b scorer exists). Do the two real things:

1. **Bar anchors — extend the existing precedent, do not duplicate it.**
   `tests/test_h10_config.py:46` already asserts
   `config.H10_MIN_LOSSES_FOR_VERDICT == 7` and `:50-51` already anchor two
   window-end dates with `assertIn`. Extend that file with the WP-A anchor for
   seq 16's loss bar, plus anchors for `H6_MIN_COMPLETED_POSITIONS` /
   `H6_HARD_KILL_FULL_LOSS_MONTHS` / `H6_MONTHLY_PREMIUM_AT_RISK` (seq 6),
   `H8_MIN_COMPLETED_POSITIONS` / `H8_HARD_KILL_FULL_LOSS_MONTHS` (seq 11), and
   `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` (seq 22). These are **regression
   tripwires**, not guards — they pass at `f228894` with no production change
   (WP-E Group 2).
2. **Resume floors — a real lower-bound check against a sealed typed field
   (N4).** *(Rev 2 asserted, unlabelled, that "no literal `2026-08-19` exists in
   any record" and forbade a derivation check. That was false. The literal is in
   the hash-sealed `timestamp` of both governing records.)*
   - Clause 5 defines the floor as *the LATER of* (i) the first session on/after
     the implementation landing and (ii) **this amendment's ledger append date**.
   - Term (ii) **is** machine-checkable: seq 28 `timestamp`
     `"2026-08-19T01:05:33.937513+00:00"`, seq 29 `timestamp`
     `"2026-08-19T01:05:33.939961+00:00"` — inside the body `verify()`
     recomputes, so this is a check against a sealed typed field, the very thing
     the prose records otherwise lack.
   - **Implement the one-directional binding:**
     `config.H10B_RESUME_FLOOR_SESSION >= <append date of seq 28>` and
     `config.H5_RESUME_FLOOR_SESSION >= <append date of seq 29>`. Both hold
     today.
   - **Timezone convention — UTC, and write it in the module docstring
     (ruling 2).** Use the **UTC date of the `timestamp`** (`"2026-08-19"`),
     giving `"2026-08-19" >= "2026-08-19"` → true. Reasons, recorded so this is
     not relitigated: the UTC date is a **prefix slice of the sealed field
     itself** — zero interpretation — whereas the ET date requires a timezone
     conversion and a DST rule, i.e. a normalisation step, and it would be
     incoherent for this brief to ban prose normalisation and then DST-convert a
     sealed timestamp. UTC is also the strictly **tighter** bound. Note that
     `config.py:628`'s comment reads ET, that the two differ by one calendar day
     (`>= "2026-08-19"` vs `>= "2026-08-18"`), and that the UTC reading is
     deliberately the tighter of the two. Do not leave this implicit; an
     unstated convention is a latent off-by-one.
   - **Quote `config.py:628` in full when citing it (N23)** — the tail is the
     strongest evidence for `>=` rather than `==`: *"mechanical floor per seq
     28/29 clause 5; append date 2026-08-18 ET; **updated at merge by the
     orchestrating session if the merge lands later**"*. That closing clause is
     the owner's own statement that this constant moves **forward and never
     backward**, which is exactly the direction of the lower-bound check.
   - **Term (i) remains uncheckable** — no record states the implementation
     landing session. Disclose that in the docstring and the PR body; the check
     is a lower bound only, not a full derivation.
   - Keep a literal-value tripwire for both constants as an additional Group 2
     test. **Change neither value.**

### WP-D — Invert the value-patching test

`tests/test_h6_watch.py:493` patches `config.H6_HARD_KILL_FULL_LOSS_MONTHS` to 2
and asserts the kill fires. After WP-A/WP-B that patch must no longer move the
verdict.

1. **Invert it to the WP-A.5 semantics, which are fixed and not the executor's
   to choose.** Patch config to 2 and assert `score_book` **raises the typed
   refusal**. Rename to
   `test_hard_kill_month_count_refuses_when_config_disagrees_with_seq6`.

   **Refusal message shape (ruling 3, corrected surface per O4).** The message is
   a **single line** with a fixed field order:
   1. the config name and its live value;
   2. the registration text as it appears in the record;
   3. the `seq`;
   4. one remediation clause — *"if a ledger amendment changed this value, update
      this module's (seq, anchor) table"*.

   Group 1's `test_refusal_message_names_config_value_registration_text_and_seq`
   asserts on **those four components individually, never on the whole string**,
   so the wording can be improved later without breaking the test.

   **Where the operator actually reads it — stated correctly this time.** The
   `crit` summary line carries only the **fixed literal**
   `"h6_watch: NONZERO EXIT"` (`tools/daily_ritual.sh:449` passes that literal;
   `crit()` at `:85` records only it). The exception text is **not** in the crit
   line. It lands in the **ritual log** `.tmp/daily_ritual/<stamp>.log`, because
   `:71` is `exec > "$LOG" 2>&1` with `LOG` set at `:67-70` — i.e. exactly the
   file an operator opens to triage `"h6_watch: NONZERO EXIT"`.
   *(All Repo-verified at `f228894`. Rev 4 claimed the operator "sees the
   remediation in the `crit` output", which was wrong about the delivery
   surface.)*

   Ruling 3 stands on the corrected mechanics: the remediation is one file open
   away from the crit, which still beats a merged PR body or a runbook with no
   `crit` section (`docs/monday-runbook.md`: zero occurrences of "crit").
   Prose inside an exception string is unusual for this repo —
   `h7_forward_scoring.py:360-373` uses short one-clause messages — which is why
   the message is **bounded to one line** rather than left open-ended. The
   Acceptance-11 PR-body requirement is kept as well.
2. Keep the neighbouring three-month test (immediately above `:493`) **passing
   unchanged** — it tests the real registered rule and is not the defect.
3. Do not delete coverage. If a patching test is removed, a stronger test
   replaces it in the same commit.

### WP-E — Tests, in three labelled groups

*(Rev 3 adds Group 3 and rescopes two rows; round-2 findings N1 and N2. Rev 2's
Group 1 contained a happy-path test that is definitionally incapable of failing
on revert, which made Acceptance 3's "Every" false — the same defect round-1
finding 10 created the group to fix.)*

**Group 1 — Refusal proofs. Each MUST fail if the production guard is reverted.**
Every Group 1 test calls **`score_book`** (not the lookup module directly) with a
disagreeing config, so a revert of `h6_watch.py` breaks it.

| Test | Proves |
|---|---|
| `test_h6_sample_bar_refuses_when_config_disagrees_with_seq6` | `H6_MIN_COMPLETED_POSITIONS` patched away from 8 → `score_book` raises; no `INSUFFICIENT_SAMPLE` verdict is produced |
| `test_hard_kill_month_count_refuses_when_config_disagrees_with_seq6` | WP-D.1: config patched to 2 → typed refusal, not a 2-month hard kill |
| `test_kill_v2_effective_date_refuses_when_config_disagrees_with_seq22` | date patched to `"2030-01-01"` → refusal, instead of silently routing the whole book to v1 |
| `test_monthly_cap_refuses_when_config_disagrees_with_seq6` | N3: `H6_MONTHLY_PREMIUM_AT_RISK` patched to `1` → refusal, instead of manufacturing a v1 `REJECT`. **N17: the refusal must be raised before `validate_book` runs** (WP-B.1.5 ordering). Assert on the typed refusal **and** assert explicitly that the raised exception is **not** `validate_book`'s `"gross premium risk"` `ValueError` from `:583-586` — at a patched cap of `1` any book with real entry costs trips that invariant, so a deferred lookup would make this test assert the wrong exception |
| `test_refusal_message_names_config_value_registration_text_and_seq` | **must go through `score_book`** with a disagreeing config and assert on the raised exception's message — not call the lookup module directly (N2). A module-only version cannot fail the Acceptance-3 revert demo |
| `test_second_call_refuses_after_config_patched_between_calls` | N5: call `score_book` once successfully, patch `config`, call again → the second call refuses. Proves the anchor is re-evaluated per call and only the records are memoised |

**Group 2 — Regression tripwires. EXEMPT from Acceptance 3**, labelled
"tripwire, not a guard" in each docstring and in the PR body.

| Test | Proves |
|---|---|
| `test_h10b_loss_bar_anchor_present_in_seq16` | `config.H10_MIN_LOSSES_FOR_VERDICT` still appears in seq 16's text (no H10b scorer exists to guard) |
| `test_h8_bar_anchors_present_in_seq11` | same for seq 11's clauses. An anchor check, **not** an H8 scorer; **not gated on D-1** |
| `test_h6_anchors_present_in_seq6_and_seq22` | the four H6-side anchors still match |
| `test_resume_floor_not_before_amendment_append_date` | WP-C.2's lower bound against seq 28 / seq 29 `timestamp` (H10b and H5) |
| `test_resume_floors_are_value_pinned` | literal change tripwire on `config.py:629-630` |
| `test_seq22_month_count_is_word_form_not_numeric` | pins the WP-A.4 obstacle so a later session cannot quietly "fix" it with a word-form parser |

**Group 3 — No-regression guards. EXEMPT from Acceptance 3.**

| Test | Proves |
|---|---|
| `test_h6_scoring_unchanged_when_config_and_registration_agree` | the happy path at the real values still produces today's verdicts — guards against a guard that refuses everything. *(Moved out of Group 1 per N1: it asserts today's behaviour at today's values, so it cannot fail on revert. Valuable, but not a refusal proof.)* |

**Fixtures — read-only real ledger, not a fabricated chain (N6).** *(Rev 2
instructed the executor to build a `tempfile` fixture ledger and banned reading
the real one. That was not implementable and its cited precedent did not
transfer.)*

- **Why fixtures are the wrong tool here:** `verify()` requires
  `rec["seq"] == index` (`research/ledger.py:553-554`), so a fixture targeting
  seq 22 needs **23** chain-valid records; seq 16 needs 17; seq 6 needs 7. Each
  must survive `_verify_semantic_records` (`:347`) — valid `entry_type`,
  `_reject_unknown_fields`, an exactly-matching running `trial_count`
  (`:369-373`), and per-type required fields — and `HEAD` must equal the tip
  (`:562-563`). The H7 precedent does not transfer: it is a **different store
  with a different API** (`ledger.read_events` over
  `ledger/h7_forward/events.jsonl`), and `ScoringCase.setUp` appends one
  synthetic event with none of that machinery.
- **The rule:** Group 1 refusal tests **read the real
  `ledger/experiments.jsonl` READ-ONLY** and produce the refusal by patching
  `config` — the refusal comes from the patched value, not from a fabricated
  record, so no fixture is needed at all. Groups 2 and 3 read it read-only too.
  **Two named precedents, one for each operation (N20):**
  - `tests/test_h10_config.py:7-12` `_load_registration(seq)` — the precedent for
    the **read-only file open** of `ledger/experiments.jsonl`.
  - `tests/test_ledger_diagnostics.py:230-231` —
    `def test_real_ledger_still_verifies(self): ledger.verify("ledger")`, an
    existing standing-suite test that calls **`verify()` against the real chain,
    offline**. That is the precedent for the operation WP-A actually introduces,
    and it pre-answers whether the new tests can pass offline: round-3 review ran
    `ledger.verify("ledger")` and `verify("ledger", anchored=True)` under
    `uv run --offline` and both returned cleanly.
- **The no-write rule stays absolute.** No test may write, append to, mutate, or
  create a ledger under `ledger/`. A test that needs a *malformed* chain (e.g.
  to exercise the `LedgerError` path) builds it in a `tempfile.TemporaryDirectory()`
  and points `base_dir` at it — that is a temp directory, not the real ledger,
  and is the only fixture case in scope.
- All tests run **offline**.

---

## Blast radius (read before implementing)

- **(a) A refusal reaches the daily ritual as `crit`.** `h6_watch.py:1027` calls
  `score_book(book).to_dict()` inside `build_snapshot`; `tools/daily_ritual.sh:448-449`
  wraps the watcher in `|| crit "h6_watch: NONZERO EXIT"`. *(Repo-verified.)* So
  a config/registration disagreement stops the H6 receipt and takes the ritual to
  `crit`. **Intended fail-closed behavior** — a scorer that cannot prove its bar
  must not emit a verdict. Say so in the PR body so the first `crit` is not
  misdiagnosed. Blast radius is bounded to H6.
- **(b) New runtime dependency on the ops checkout — satisfied today
  (Repo-verified, upgraded from "Codex must confirm" per N14).** `h6_watch` does
  not read `ledger/experiments.jsonl` at scoring time today; after WP-A it does,
  on every scoring run, including in the ops checkout. Checked directly at
  `/Users/carsynstephenson/options-validator-ops` on 2026-09-15:
  `ledger/experiments.jsonl` present with 32 records, max `seq` 31;
  `ledger/HEAD` present and equal to the last record's `record_hash`; the full
  `record_hash` sequence **byte-identical** to the audit worktree's. **Caveat:**
  that checkout is at `a3745ab`, behind `f228894`, so its `ledger/` can lag
  `main` — and `verify()` proves *internal consistency*, never *freshness*.
  Harmless for seq 6/11/16/22, which are frozen, but it compounds (e). Still
  specify and test the missing-file and failed-`verify()` cases: both are
  refusals (`crit`), never a silent skip or a `config` fallback.
- **(c) Caching — measured, not guessed.** Per WP-A.6: the
  `verify()`-succeeded flag and the parsed records are memoised per `base_dir`;
  anchors are re-evaluated every call. Measured cost of one
  `research.ledger.verify("ledger")` over the 32-record, 80,705-byte chain:
  **~1.3 ms cold, ~0.6 ms warm** *(round-4 review, `uv run --offline`,
  `f228894`-era chain — Run-verified)*, paid **once per process** under
  memoisation; `build_snapshot` (`h6_watch.py:1027`) calls `score_book` once per
  ritual run, and every later call costs one dict lookup plus eight substring
  tests. The PR body states the observed delta on a full `unittest discover`
  run; **a delta above ~1 s is a memoisation defect, not an expected cost** —
  treat it as a bug in WP-A.6's caching, not a reason to move the lookup.
- **(d) No collision with brief 41.** Brief 41 renumbers
  `PYTHON_DASH_C_CLASSIFICATION` / `MUTATION_VERB_SITES`
  (`tests/test_daily_ritual_provenance.py:98,138`), which key on
  `tools/daily_ritual.sh`. **Brief 42 does not modify `tools/daily_ritual.sh`** —
  sequencing only, no registry collision.
- **(e) A legitimate owner amendment will cause a refusal and a ritual `crit`
  until a follow-up code change lands (N10).** *(Rev 2 said the guard "does not
  prevent an owner-authorized future amendment from changing the rule — that is
  correct behavior, not a gap", which suggests the opposite of what happens.)*
  Because anchors are pinned to fixed seq numbers, an amendment that changes a
  guarded value — appended at a **new** seq, with `config.py` updated to match —
  makes the **old** seq's anchor fail, and by WP-A.5 the scorer refuses. Via (a)
  the ritual goes to `crit` on the next run and stays there until the module's
  `(seq, anchor)` table is updated. This is not hypothetical: **seq 22 is
  exactly such an amendment, and its word form already broke one anchor**
  (WP-A.4). The fail-closed outcome is arguably correct, but the owner must be
  told before the first amendment, not after the first `crit`. **This must appear
  in the PR body** (Acceptance 11).

---

## Hand-off and ordering

*(Brief 41's first Codex dispatch stopped for exactly this reason — receipt
`reports/2026-09-09-brief-41-codex-stop-report.md`.)*

1. This brief file is currently **untracked on `claude/audit-2026-09-15`, the
   head branch of open draft PR #175** (`gh pr view 175`: number 175, state
   OPEN, isDraft true, headRefName `claude/audit-2026-09-15`).
   *(Repo-verified 2026-09-15, re-confirmed by round-2 review.)*
2. **Codex reads this brief from `origin/main` only after PR #175 merges**, or
   from an owner-named pinned SHA. Never from PR #175's head branch. Audit §4
   finding 6 sets the same ordering ("Land this PR first").
3. Implementation base is `origin/main` at hand-off time. Confirm the
   **Revision** line reads **rev 5** (or later) before implementing; an older
   copy is a stop-and-report — revs 1–4 are superseded in full, and **rev 3 in
   particular halts on Acceptance 14's first grep** (round-3 finding N16) while
   specifying a Group 1 test that cannot assert the exception it is specified to
   assert (N17). *(O1: rev 4's gate said "rev 3 (or later)", which would have
   told a Codex finding a rev-3 copy on `origin/main` to proceed with the
   defective revision — plausible while this brief is still untracked on PR
   #175's head branch.)*
4. Work happens on a fresh branch in a fresh `.tmp/worktrees/` worktree —
   **never in the audit worktree `.tmp/worktrees/audit-0915`**.
5. Push the working branch before ending any session that created commits
   (standing branch-hygiene rule).

---

## Acceptance / verification

Exit codes define done. Run from the implementation worktree root, offline.

```bash
uv sync --frozen
uv run python -m unittest discover -s tests          # full suite, OFFLINE (~10 min); exit code is the verdict
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

Fast loop (named modules, per CLAUDE.md):

```bash
PYTHONPATH=tests uv run python -m unittest test_h6_watch test_h10_config test_ritual_switch_on_hash_containment test_h7_forward_scoring
```

Conditions:

1. `uv run python -m unittest discover -s tests` exits **0**. No test is skipped
   or xfailed to accommodate this change, **except** the conditional H8 work
   governed by condition 10.
2. `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`
   are clean.
3. **Every WP-E Group 1 test fails when the production guard is reverted.**
   Demonstrate in the PR body with the output of running Group 1 against a
   deliberately reverted `h6_watch.py` read. **Groups 2 and 3 are exempt** and
   must be labelled tripwires / no-regression guards in the PR body — they pass
   at `f228894` by design. *(This condition is now true as written; rev 2's
   version was unsatisfiable.)*
4. `tests/test_h7_forward_scoring.py` passes **unchanged**.
5. `tests/test_ritual_switch_on_hash_containment.py:357` passes **without
   editing `FROZEN_CONFIG_UPPERCASE_NAMES`**. A failure means a config name was
   added, removed, or renamed — out of scope; stop and report.
6. `git diff config.py` shows **no value change** (added comment lines at most).
7. `git diff --name-only` contains **no path under `ledger/`**.
8. **No numeric verdict constant appears in the new module.** Demonstrate with
   `grep -nE '\b(8|3|7|2000|2_000)\b|2026-08-03|2026-08-19' options_researcher/registered_bars.py`
   — **the expected result is NO MATCHES** (the seq values 6, 11, 16, 22 do not
   match the alternation). *(Rev 2's grep was under-scoped and its stated
   expected output was wrong; N11.)* Plain-language condition, which governs if
   the grep and it ever disagree: **a reviewer reading the module finds no copy
   of any verdict number**, in digits or words.
9. The WP-A.4 obstacle is **not** worked around: no word-form number map, regex
   over registration prose, or fuzzy anchor match anywhere in the diff.
10. **OWNER DECISION D-1 enforcement.** If D-1 is **unruled** at hand-off,
    `git diff --name-only` contains **no** `options_researcher/h8_watch.py` and
    **no** `tests/test_h8_*`, and the PR body states "D-1 unruled; WP-B.2
    skipped with reason". WP-B.2 is **skipped, not halted** — the rest of the
    brief completes. (Group 2's `test_h8_bar_anchors_present_in_seq11` lives in
    `tests/test_h10_config.py`-style anchor tests and is **not** gated on D-1.)
11. Blast-radius items (a), (c), and **(e)** are each addressed explicitly in
    the PR body. Item (b)'s ops-checkout status is already Repo-verified here;
    re-confirm only that the missing-file and failed-`verify()` paths refuse.
12. Independent adversarial review receipt before merge.
13. PR is a **draft**, and stays one.
14. **The four-read list is re-derived, not trusted.** Codex greps
    `options_researcher/h6_watch.py` for every `config.` read reachable from
    `score_book` and reports the **full** list in the PR body, **split into two
    columns**:
    - **verdict-determining** — a value whose change moves the `verdict`,
      `hard_kill`, or `reason` fields of the returned `H6Score`;
    - **invariant-validating** — reads inside `validate_book` (`:467-606`),
      which raise `ValueError` on a book that violates a registered invariant
      and cannot select a verdict.

    **Only the first column is in scope**, and it is expected to be exactly the
    four reads at `:710`, `:719`, `:748`, `:826`. If a **fifth
    verdict-determining** read is found, **stop and report** — do not silently
    extend scope. *(Rev 4 / N16. Rev 3's version gated on "every `config.` read
    reachable from `score_book`", which is roughly twenty reads — `validate_book`
    alone holds 15 lines / 17 occurrences, including the
    `H6_MONTHLY_PREMIUM_AT_RISK` reads at `:582`
    and `:585` that this brief separately forbids touching. Read faithfully, rev
    3 halted itself on the first grep. Rev 1 said "two", rev 2 said "three"; both
    were wrong, which is why the re-derivation requirement stays.)*
15. **Memoisation is proven, not asserted.** WP-E Group 1's
    `test_second_call_refuses_after_config_patched_between_calls` passes, and
    the PR body states what is cached (`verify()` result + parsed records, keyed
    on `base_dir`) and what is not (any resolved value).

---

## Explicitly forbidden

- Marking the PR ready, merging, deploying, or syncing the ops checkout.
- Any **write** under `ledger/`, including `facts.log`. (Read-only reads are
  permitted and are the specified test approach.)
- Registering or amending any hypothesis.
- Changing any frozen value, or any `config.py` value.
- Creating any numeric copy of a verdict bar, hard-kill count, monthly cap, or
  effective date outside `config.py`.
- Caching a resolved guarded value across calls (WP-A.6).
- Parsing, interpreting, or normalising registration prose beyond exact
  substring membership (no word-form maps, no regex, no fuzzy matching).
- Adding an anchor not verified and recorded in WP-A.3.
- Choosing the H8 disposition (OWNER DECISION D-1), or creating an H8 refusal
  entry point that does not exist today.
- Emitting, changing, or ratifying a verdict for any hypothesis.
- Touching the non-verdict `H6_MONTHLY_PREMIUM_AT_RISK` reads at
  `h6_watch.py:384`, `:387` (entry sizing) or `:582`, `:585` (`validate_book`
  invariants), or any other read inside `validate_book` (`:467-606`).
- **Editing this brief (N19).** Any ruling this brief says "must be recorded in
  this brief before implementation" — D-1, WP-A.3's new anchors, WP-B.1.3 — is
  recorded by **the owner, by amendment to this brief on `origin/main` or by
  message at dispatch**, or by the orchestrating session on `origin/main`. Never
  by Codex. If Codex believes a ruling is needed, it **reports and continues
  with the documented default**.
- Adding `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` to `h6_config_snapshot`'s surface
  (WP-B.1.7) — flag as follow-up only.
- **Renaming this file.** The registry row and PR text reference the filename.
- Implementing from PR #175's head branch, or in the audit worktree.
- Resolving a brief-number registry conflict, renaming, staging, or deleting any
  concurrent draft in `docs/superpowers/plans/`.
- Deleting a worktree, branch, or directory without first running
  `uv run python tools/irreplaceable_data_guard.py verify`.

---

## Registry row — description APPLIED; status column needs a refresh

*(N21, refined by O8.)* `docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md` row 42
**already carries the correct title** in its description column (a superset of
the text rev 3 proposed — it adds the D-1 clause and the review-receipt
filenames). That part needs no edit, and this section is retained so a later
reader does not make it twice. The reservation, the number, and the filename are
unchanged.

**Outstanding (O8):** the row's **status column still reads `DRAFT (rev 3)`** and
lists receipts I/K/N only. It should be refreshed to **rev 5** with receipt O
added. This is work for **the owner or the orchestrating session on
`origin/main` — never Codex** (see the "Editing this brief" forbidden bullet,
which covers the registry row by the same logic).

---

## Rulings recorded (round 3)

Rev 3's four open questions were ruled on by the round-3 review
(`reports/2026-09-15-audit/N-brief-42-adversarial-review-round3.md` §3). They are
closed; do not reopen without new evidence.

1. **v2 month count — do NOT stop and report.** Leave the v2 caller unbound
   exactly as today, documented in code and PR body, tripwired by Group 2's
   `test_seq22_month_count_is_word_form_not_numeric`. Applied at WP-B.1.3.
   Rationale: a mid-package halt over one caller would stop everything
   downstream, which is round-2 finding N12 reappearing; and unbound is
   today's behaviour, so nothing regresses, while binding to seq 6 would be
   binding to the wrong record.
2. **WP-C.2 timezone — keep UTC.** Applied at WP-C.2, with the reasoning and the
   one-day ET difference recorded there.
3. **Blast radius (e) warning — put it in the refusal message**, and keep the
   PR-body requirement. Applied at WP-D.1 and Acceptance 11. `docs/monday-runbook.md`
   has no `crit` triage section, so a runbook note would not be read by the
   person who hits the `crit`.
4. **WP-C — keep it.** Both halves are test-only (WP-C.1 extends
   `tests/test_h10_config.py`; WP-C.2 adds two comparisons against sealed
   timestamps), so neither touches production code and a WP-C failure fails the
   suite without stopping the ritual. Splitting it out would cost a registry slot
   and a hand-off cycle for two test methods.

---

## Open questions — both closed in round 4

1. **Is the refusal message the right home for the remediation sentence?**
   **Ruled: yes, keep it**, with the corrected reason. The exception text lands
   in the **ritual log** (`.tmp/daily_ritual/<stamp>.log`, via
   `tools/daily_ritual.sh:71`), not the `crit` summary line — which carries only
   the fixed literal `"h6_watch: NONZERO EXIT"` (`:85`, `:449`). That is one file
   open from the crit, still better than a merged PR body or a runbook with no
   `crit` section. The message is bounded to one line with a fixed field order,
   and the test asserts the four components individually (WP-D.1).
2. **Does WP-B.1.5's "lookup at the top of `score_book`" have a cost?**
   **Closed outright: no.** Measured at **1.3 ms cold / 0.6 ms warm**, paid once
   per process under WP-A.6's memoisation — see blast radius (c). There is no
   trade-off to weigh: the ordering is a correctness requirement (N17) and the
   cost is sub-millisecond.

**No open questions remain.** The only outstanding input is OWNER DECISION D-1,
which gates WP-B.2 alone (skipped, not halted, if unruled).

---

## Review disposition

### Round 4 (rev 4 → rev 5)

Round 4 was a scoped confirmation: **PASS WITH FIXES**, 7 of the 8 round-3 items
CLOSED and 1 PARTIAL (N21, cosmetic), all four rulings applied, no earlier
finding re-opened, no work package redesigned, no anchor changed. The reviewer
re-ran all eight anchors (**8/8 PASS**), enumerated `validate_book`'s reads line
by line, timed `verify()`, and traced where a refusal message actually lands.

| Finding | Sev | Disposition in rev 5 |
|---|---|---|
| O1 — hand-off gate still accepted **rev 3**, the revision that halts itself | MUST-FIX | Hand-off item 3 now requires **rev 5 (or later)**, with the reason (rev 3 halts on Acceptance 14 per N16; its Group 1 test cannot assert its specified exception per N17) |
| O2 — stale `WP-B.1.6` pointer after rev 4's renumbering | SHOULD-FIX | Forbidden-list pointer corrected to **WP-B.1.7**, matching the rev-4 disposition table |
| O3 — "seven anchors" over a table of eight | SHOULD-FIX | Corrected to **eight**, noting 8/8 PASS across rounds 2, 3 and 4 |
| O4 — WP-D.1's ruling-3 rationale mis-stated the delivery surface | SHOULD-FIX | Corrected: the `crit` line carries only the fixed literal `"h6_watch: NONZERO EXIT"` (`daily_ritual.sh:85`, `:449`); the refusal text reaches the **ritual log** via `exec > "$LOG" 2>&1` (`:71`, `LOG` at `:67-70`). Message bounded to **one line with a fixed four-field order**; the test asserts the four components **individually, never the whole string** |
| O5 — "15 reads" is 15 lines / 17 occurrences | NOTE | Both figures stated in the two-class note (`:481` and `:504` each carry two); Acceptance 14's parenthetical relaxed to "roughly twenty" |
| O6 — threading the count touches three signatures; callerless wrapper | NOTE | WP-B.1.3 names `_hard_kill_versions` (`:779`), `_hard_kill_v1` (`:731`), `_hard_kill_v2` (`:753`) plus the helper, and instructs keeping the unused `_hard_kill` (`:788-789`) compiling rather than deleting it |
| O7 — `score_book` is not `validate_book`'s only caller | NOTE | WP-B.1.5 now states `_book_state` (`:328`/`:329`) is not a verdict path and must **not** receive the lookup |
| O8 — registry row 42's status column reads "DRAFT (rev 3)" | NOTE | Registry section retitled and split: description APPLIED, **status column refresh outstanding** for the owner/orchestrating session, never Codex |
| Q1 ruling — keep prose in the refusal message | — | Applied at WP-D.1 with the corrected surface; open-questions section records it closed |
| Q2 ruling — close the cost question | — | Question deleted; blast radius (c) now carries the measured **1.3 ms cold / 0.6 ms warm** figure and a **">~1 s = memoisation defect"** tripwire |

### Round 3 (rev 3 → rev 4)

Round 3 was a scoped confirmation: it closed **all fifteen** round-2 findings
against the code (15 CLOSED, 0 PARTIAL, 0 OPEN), re-ran all eight WP-A.3 anchors
(8/8 PASS) and the WP-A.4 word-form case (FAIL, as claimed), and confirmed the
skill-compliance, authority-split, and ops-checkout facts independently.

| Finding | Sev | Disposition in rev 4 |
|---|---|---|
| N16 — Acceptance 14 would halt the job: `validate_book` (`:467-606`) holds 15 more `config.` reads, including the `:582`/`:585` ones the brief forbids touching | MUST-FIX | Read list split into **verdict-determining** vs **invariant-validating** in the defect section, WP-B.1.7, the forbidden list, and Acceptance 14; the stop-and-report gate now fires only on a fifth **verdict-determining** read |
| N17 — `test_monthly_cap_refuses_…` unreachable: `validate_book:582` raises `ValueError` first | MUST-FIX | New **WP-B.1.5** requires the lookup at the top of `score_book`, **before** the `validate_book` call at `:796`, with the reason; the test row requires asserting the exception is **not** the `"gross premium risk"` `ValueError` |
| N18 — WP-B.1.3's mid-package stop-and-report re-imports the N12 defect | SHOULD-FIX | Replaced per ruling 1: v2 caller left unbound as today, documented in code and PR body, tripwired by the Group 2 word-form test; the "if review rules…" bullet deleted |
| N19 — "recorded in this brief" never says who, outside D-1 | SHOULD-FIX | New forbidden-list bullet: rulings are recorded by **the owner** (amendment on `origin/main` or message at dispatch) or the orchestrating session, never by Codex, which reports and continues with the documented default |
| N20 — a stronger N6 precedent exists | NOTE | `tests/test_ledger_diagnostics.py:230-231` (`verify()` on the real chain, offline) cited beside `tests/test_h10_config.py:7-12`, one precedent per operation |
| N21 — registry action item is stale | NOTE | Section retitled "APPLIED, no action outstanding" |
| N22 — `verify()` returns `None` | NOTE | WP-A.6 now says cache the **fact that `verify()` succeeded** plus the parsed bodies, with an explicit warning against `if cached_result:` |
| N23 — WP-C.2 under-quotes `config.py:628` | NOTE | Full line quoted, with its "updated at merge … if the merge lands later" tail identified as the evidence for `>=` over `==` |
| Ruling 1 — v2 month count | — | Applied at WP-B.1.3; recorded in "Rulings recorded" |
| Ruling 2 — UTC | — | Applied at WP-C.2 with reasoning and the one-day ET difference |
| Ruling 3 — remediation in the refusal message | — | Applied at WP-D.1; Acceptance 11 PR-body requirement kept |
| Ruling 4 — keep WP-C | — | Kept; rationale recorded |

### Round 2 (rev 2 → rev 3)

| Finding | Sev | Disposition in rev 3 |
|---|---|---|
| N1 — happy-path test in Group 1 breaks Acceptance 3 | MUST-FIX | New **Group 3** (no-regression guards, exempt); Acceptance 3's "Every" is now true |
| N2 — refusal-message test scope unspecified | MUST-FIX | Group 1 header requires **every** row to call `score_book`; the row says so explicitly |
| N3 — fourth live-config read `H6_MONTHLY_PREMIUM_AT_RISK` | MUST-FIX | Added as read 4 (`:748`, `:808`); two anchors added to WP-A.3 (both verified PASS); Scope IN.1 corrected to four; WP-B.1.4 added; non-verdict uses fenced off; Acceptance 14 stops the exhaustiveness claim recurring |
| N4 — "no literal 2026-08-19 exists" false; forbade a real binding | MUST-FIX | Claim deleted; WP-C.2 now binds `>=` against seq 28 / seq 29 sealed `timestamp`, with an explicit UTC convention and term-(i) disclosure |
| N5 — memoisation ambiguity could disable the guard | MUST-FIX | WP-A.6 rewritten: cache `verify()` + parsed records only, anchors re-evaluated per call; Group 1 second-call test; Acceptance 15; forbidden-list entry |
| N6 — fixture instruction unimplementable | MUST-FIX | Replaced with read-only real-ledger reads (precedent `tests/test_h10_config.py:7`), with the seq-index / `trial_count` / HEAD constraints written out as the reason; no-write rule kept absolute; temp-dir fixtures retained only for malformed-chain cases |
| N7 — title overclaims | MUST-FIX | Retitled to the reviewer's wording; "What this brief delivers" promoted into "Why this exists"; registry row text supplied; filename deliberately unchanged |
| N8 — `verify()`'s `anchored` unspecified | SHOULD-FIX | WP-A.1 specifies `anchored=False` with the reason and a docstring requirement |
| N9 — anchors are format-coupled | SHOULD-FIX | WP-A.3 rule: template **including format spec** fixed per `(seq, config-name)`; new anchors require re-verification recorded in the brief |
| N10 — amendment consequence mis-described | SHOULD-FIX | Sentence deleted; blast radius **(e)** added; Acceptance 11 requires it in the PR body |
| N11 — Acceptance 8 grep under-scoped, wrong expected output | SHOULD-FIX | Alternation extended; expected result stated as **no matches**; plain-language condition added and made governing |
| N12 — WP-B.2 vs Acceptance 10 conflict | SHOULD-FIX | "Skipped, not halted" stated in both places; how a ruling reaches Codex specified |
| N13 — duplicate-seq defence is redundant | NOTE | WP-A.2 states `verify()` is load-bearing and the assertions are belt-and-braces |
| N14 — ops checkout carries the ledger | NOTE | Blast radius (b) upgraded to Repo-verified with the `a3745ab` lag caveat, linked to (e) |
| N15 — header cosmetic deviation | NOTE | Recorded in the header note; no change made |

### Round 1 (rev 1 → rev 2), carried for the record

| Finding | Sev | Disposition |
|---|---|---|
| 1 — record-hash pin seals nothing | BLOCKER | CLOSED — mechanism replaced by `verify()` + prose anchor |
| 2 — WP-A bound nothing; transcribed constants | BLOCKER | CLOSED on mechanism; framing defect re-raised and closed as N7 |
| 3 — refusal vs "follows registration" contradiction | BLOCKER | CLOSED — single fail-closed semantics in WP-A.5 |
| 4 — no blast radius | MUST-FIX | CLOSED — section added, extended in rev 3 |
| 5 — seq 28 mislabelled "A2-v1" | MUST-FIX | CLOSED |
| 6 — WP-C.2 pointed at non-existent seq 30 clause 5 | MUST-FIX | CLOSED |
| 7 — seq 22 mislabelled; "none changes a bar" false | MUST-FIX | CLOSED |
| 8 — `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` unbound | MUST-FIX | CLOSED in rev 2; enumeration completed in rev 3 (N3) |
| 9 — three citation defects | SHOULD-FIX | CLOSED |
| 10 — three WP-E tests cannot fail on revert | MUST-FIX | CLOSED in rev 3 (N1, N2) |
| 11 — D-1 unenforceable; D-1b invented an entry point | MUST-FIX | CLOSED; wording conflict closed as N12 |
| 12 — executor typing frozen numbers | MUST-FIX | CLOSED |
| 13 — resume floors are derivations | SHOULD-FIX | CLOSED in rev 3 (N4) |
| 14 — no hand-off ref | SHOULD-FIX | CLOSED |
| 15 — what rev 1 got right | NOTE | Carried forward |
