# Brief 42 — independent adversarial review (round 4, SCOPED confirmation)

**Target:** `docs/superpowers/plans/2026-09-15-42-verdict-bar-ledger-binding-codex-brief.md`, **rev 4**
**Round 3 receipt:** `reports/2026-09-15-audit/N-brief-42-adversarial-review-round3.md`
(PASS WITH FIXES — N16/N17 MUST-FIX, N18/N19 SHOULD-FIX, N20–N23 NOTE, four rulings)
**Reviewer:** independent Claude session, read-only except this file
**Ref:** worktree `.tmp/worktrees/audit-0915`
**Stance:** adversarial. Nothing below is a confirmation that the brief works.

**Verdict: PASS WITH FIXES** (1 MUST-FIX — a one-word edit; 3 SHOULD-FIX; 4 NOTE.
No work package is redesigned, no anchor changes, no ruling reopened.)

---

## 0. What I executed, not just read

- Re-ran all **eight** WP-A.3 anchors by building each f-string from the live
  `config.py` value and testing substring membership in that record's `reason`:
  **8/8 PASS**. The WP-A.4 seq-22 word form **FAILS** as claimed. seq 16's
  distractor confirmed (`MIN_LOSSES_FOR_VERDICT=10` present, `verdict gates at
  >=10 losses` absent).
- Enumerated every `config.` read in `validate_book` (`h6_watch.py:467-606`) by
  line: **15 distinct lines, 17 occurrences**.
- Verified `score_book` def `:792`, `validate_book(book)` `:796`,
  `_hard_kill_versions` `:802`, `REJECT` `:803-825`, sample bar `:826`,
  `validate_book:581-586` raise, `:582`/`:585`, sizing reads `:384`/`:387`,
  `h6_config_snapshot` `:898`/`:908`/`:913`/`:914`.
- Verified `tests/test_ledger_diagnostics.py:230-231`, `tests/test_h10_config.py`
  `_load_registration` / `:46` / `:50-51`, `config.py:344/349/350/354/355/383/384/625/628/629/630`.
- Timed `research.ledger.verify("ledger")` under `uv run --offline`: **1.3 ms
  cold, 0.6 ms warm**, 80,705-byte chain, 32 records (relevant to open question 2).
- Read `tools/daily_ritual.sh:67-71`, `:85`, `:448-449` to check where a refusal
  message actually lands (relevant to open question 1).
- Checked `BRIEF-NUMBER-REGISTRY.md` row 42 and `.agents/skills/codex-brief-writing/SKILL.md`.

---

## 1. Disposition — N16–N23 and the four rulings

| # | Sev (r3) | Disposition in rev 4 | Evidence |
|---|---|---|---|
| N16 — Acceptance 14 halts the job | MUST-FIX | **CLOSED** | Two-class split ("verdict-determining" vs "invariant-validating") now appears in the defect section, WP-B.1.7, the forbidden list, and Acceptance 14; the stop-and-report gate fires only on a fifth **verdict-determining** read. Every line the brief names is correct: `:478`, `:480`, `:481` (×2, incl. `COMMISSION_PER_CONTRACT`), `:490`, `:492`, `:494`, `:504` (×2), `:506`, `:553`, `:561`, `:569`, `:582`, `:585`, `:595`, `:598`. Count nit → **O5** |
| N17 — refusal test unreachable | MUST-FIX | **CLOSED** | New **WP-B.1.5** requires the lookup "once at the top of `score_book`, before the `validate_book` call at `:796`", with the reason stated; the Group 1 row additionally requires asserting the exception is **not** `validate_book`'s `"gross premium risk"` `ValueError`. Verified against code: `score_book:792` → `validate_book` `:796`; `:581-586` raises on gross > cap; the sample bar at `:826` sits after the `REJECT` return at `:803-825`, so the deferred-lookup failure mode was real |
| N18 — WP-B.1.3 stop-and-report | SHOULD-FIX | **CLOSED** | Replaced verbatim with the ruling-1 wording: v2 caller left unbound as today, code comment, PR-body record, Group 2 tripwire, "documented gap, NOT a stop-and-report". The "if review rules…" bullet is gone (grep: no remaining stop-and-report inside WP-B.1) |
| N19 — "recorded in this brief" never says who | SHOULD-FIX | **CLOSED** | New forbidden-list bullet "Editing this brief (N19)" names D-1, WP-A.3 and WP-B.1.3 explicitly and assigns recording to the owner or the orchestrating session on `origin/main`, "never by Codex", which "reports and continues with the documented default" |
| N20 — stronger fixture precedent | NOTE | **CLOSED** | WP-E Fixtures now cites both, one per operation. `tests/test_ledger_diagnostics.py:230-231` verified byte-exact: `def test_real_ledger_still_verifies(self): ledger.verify("ledger")` |
| N21 — registry action item stale | NOTE | **CLOSED** (title), **PARTIAL** (status column) | Section retitled "APPLIED, no action outstanding". Row 42's description column does carry the rev-3 title. But its status column reads **"DRAFT (rev 3)"** and does not list this round-4 receipt, so "no edit is outstanding" is now marginally false → **O8** |
| N22 — `verify()` returns `None` | NOTE | **CLOSED** | WP-A.6 now says cache "the **fact that `verify()` succeeded**", with the explicit `if cached_result:` warning |
| N23 — `config.py:628` under-quoted | NOTE | **CLOSED** | Full line quoted. Verified byte-exact, including the "updated at merge by the orchestrating session if the merge lands later" tail |
| Ruling 1 — v2 count unbound | — | **APPLIED** | WP-B.1.3 + "Rulings recorded" §1 |
| Ruling 2 — UTC | — | **APPLIED** | WP-C.2, with the one-day ET difference and the "tighter bound" reasoning recorded. `config.H10B_RESUME_FLOOR_SESSION` / `H5_RESUME_FLOOR_SESSION` both `"2026-08-19"`; seq 28/29 `timestamp` UTC dates both `2026-08-19` → `>=` holds with equality |
| Ruling 3 — remediation in refusal message | — | **APPLIED**, rationale slightly off | WP-D.1 + Acceptance 11. The *where the operator sees it* sentence is inaccurate → **O4** |
| Ruling 4 — keep WP-C | — | **APPLIED** | Kept, rationale recorded |

**Tally: 7 CLOSED, 1 PARTIAL (N21, cosmetic), 0 OPEN. All four rulings applied.**

---

## 2. Re-opening check (rounds 1–3)

No earlier-closed finding was re-opened by a rev-4 edit. Specifically re-checked:
N1 (Group 3 exists; Acceptance 3 exempts Groups 2 **and** 3), N2 (Group 1 header
and the message-test row both require `score_book`), N3 (four reads; Scope IN.1
says four; WP-B.1.4 intact; `:384`/`:387`/`:582`/`:585` fenced in both places),
N4/N13/N14/N15, N5+N22 (WP-A.6 unchanged except the N22 clarification; anchors
still re-evaluated every call; Acceptance 15 intact), N6 (read-only real-ledger
rule intact, no-write rule still absolute), N7 (title and the honest "what this
delivers" statement unchanged), N8 (`anchored=False` with reason), N9 (format
coupling, incl. the `USD 2,000` / `USD 2000` split — both re-verified PASS), N10
(blast radius (e) intact), N11 (Acceptance 8 grep and the governing plain-language
clause intact), N12 ("skipped, not halted" still in D-1, WP-B.2 and Acceptance 10).

**One rev-4 side effect** did break a cross-reference: inserting the ordering item
as WP-B.1.5 renumbered the old 5→6 and 6→7, and one pointer was not updated (**O2**).

---

## 3. Rulings on rev 4's two open questions

### Q1 — Is the refusal message the right home for the remediation sentence? **Yes. Keep it. Fix the stated reason.**

Ruling 3 stands, but its justification is wrong about the mechanics:

- `tools/daily_ritual.sh:449` is `… || crit "h6_watch: NONZERO EXIT"`, and
  `crit()` at `:85` records that **fixed literal** into the summary. The
  exception text is **not** in the crit line.
- The exception text is not lost either: `:71` is `exec > "$LOG" 2>&1`, with
  `LOG="$REPO/.tmp/daily_ritual/${STAMP}.log"` (`:67-70`). The traceback lands in
  the ritual log, i.e. exactly the file an operator opens to triage
  "h6_watch: NONZERO EXIT".

So the operator *does* see the remediation at the moment it matters — one file
open away, with no new docs, which is still strictly better than a merged PR body
or a runbook with no `crit` section (`docs/monday-runbook.md` confirmed: zero
occurrences of "crit"). Prose inside an exception string is unusual for this repo
(`h7_forward_scoring.py:360-373` uses short one-clause messages), so bound it
rather than abandon it. **Recommended wording, added to WP-D.1:**

> The refusal message is a **single line** with a fixed field order: config name
> and live value, the registration text as it appears in the record, the `seq`,
> then one remediation clause — *"if a ledger amendment changed this value, update
> this module's (seq, anchor) table"*. Group 1's
> `test_refusal_message_names_config_value_registration_text_and_seq` asserts on
> those four components individually, never on the whole string, so the wording
> can be improved without breaking the test. The operator reads it in the ritual
> log `.tmp/daily_ritual/<stamp>.log` (`tools/daily_ritual.sh:71` redirects all
> output there); the `crit` summary line itself carries only
> `"h6_watch: NONZERO EXIT"` (`:85`, `:449`).

### Q2 — Does the top-of-`score_book` lookup cost anything? **No. Keep the ordering; drop the worry, record the measurement.**

Measured in this worktree under `uv run --offline`: `research.ledger.verify("ledger")`
takes **1.3 ms** on the first call and **0.6 ms** warm, over an 80,705-byte,
32-record chain. That is the *unmemoised* cost. With WP-A.6's memoisation
(`verify()`-succeeded flag + parsed bodies, keyed on `base_dir`), a process pays
it **once**, and `build_snapshot` (`h6_watch.py:1027`) calls `score_book` once per
ritual run. Every later call costs one dict lookup plus eight substring tests.

There is no trade-off to weigh: the ordering N17 requires is **correctness**, the
cost is sub-millisecond and paid once. **Recommendation:** delete open question 2,
and replace blast-radius (c)'s vague "State in the PR body what a full
`unittest discover` run costs" with the measured figure —

> *(c) Caching.* Per WP-A.6: the `verify()`-succeeded flag and the parsed records
> are memoised per `base_dir`; anchors are re-evaluated every call. Measured cost
> of one `verify()` over the 32-record chain: **~1.3 ms** (round-4 review, offline,
> `f228894`-era chain, 80,705 bytes), paid once per process. The PR body states
> the observed delta on a full `unittest discover` run; a delta above ~1 s is a
> memoisation defect, not an expected cost.

---

## 4. Status line and skill shape — compliant

- **Status:** verbatim `DRAFT — pending independent adversarial review before
  hand-off` (line 6). It must **stay DRAFT** — this receipt is PASS WITH FIXES.
  Flip it only after **O1** lands (and, recommended, O2–O4).
- **Header order:** Date → Author → Executor → Status → *Revision* → Provenance.
  All five skill-required fields present in the required relative order; the
  insertion is disclosed in the header note. ✔
- **Body order:** Why this exists → Scope → Work packages → Acceptance, with the
  usual disclosed insertions. ✔
- **Labels:** Repo-verified / Inference / Assumption carried on every constraint,
  including all rev-4 additions. I found no unlabelled flat factual assertion.
  The count looseness at O5 is imprecision, not a false claim.
- **Prior finding IDs verbatim:** "audit 2026-09-15 §4 finding 2 / finding 3",
  N1–N23, round-1 1–15. ✔
- **Naming/registry:** filename unchanged with the reason recorded; row 42
  reserved to this path; resolving a registry conflict is forbidden. ✔

---

## 5. Authority delegation check — clean

Nothing in rev 4 hands Codex authority `CLAUDE.md:53` reserves to the owner.

- No frozen number is typed by anyone: every anchor is built from the live
  `config.py` value, and Acceptance 8's grep + the governing plain-language
  clause hunt for any copy. ✔
- No ledger write, registration, or amendment; read-only reads only; the
  `block_ledger_edits` hook is pre-declared correct. ✔
- No verdict emitted, changed, or ratified. ✔
- D-1 stays with the owner; unruled means **skip WP-B.2**, not halt. ✔
- Rev 4's new forbidden bullet **tightens** this: Codex may not record any ruling
  in the brief, and reports-and-continues instead. ✔
- PR stays a draft; no merge, deploy, or ops sync. ✔

---

## 6. New findings

### O1 — MUST-FIX. The hand-off gate still accepts **rev 3**, the revision that halts itself

**Text at issue,** Hand-off item 3 (line 733): *"Confirm the **Revision** line
reads **rev 3** (or later) before implementing; an older copy is a stop-and-report."*

**Why it bites.** Round 3 established that rev 3, read faithfully, halts on
Acceptance 14's first grep (N16) and specifies a Group 1 test that cannot assert
the exception it is specified to assert (N17). Rev 4 exists to fix exactly that.
Leaving the gate at "rev 3 (or later)" tells a Codex that finds a rev-3 copy on
`origin/main` — plausible, since the brief is still untracked on PR #175's head
branch — to proceed with the defective revision.

**Concrete change.** One word:

> 3. Implementation base is `origin/main` at hand-off time. Confirm the
>    **Revision** line reads **rev 4** (or later) before implementing; an older
>    copy is a stop-and-report — revs 1–3 are superseded in full, and rev 3 in
>    particular halts on Acceptance 14 (round-3 finding N16).

### O2 — SHOULD-FIX. Stale WP-B.1 cross-reference after the rev-4 renumbering

Inserting the ordering item as WP-B.1.5 pushed "reason strings" to 6 and "do not
change H6's semantics" to 7. The forbidden list (line 849) still points the
`h6_config_snapshot` follow-up at **WP-B.1.6**; it now lives in **WP-B.1.7**.
(The rev-4 disposition table already says WP-B.1.7, so the two disagree.)

**Concrete change.** In the forbidden list, replace `(WP-B.1.6)` with
`(WP-B.1.7)`.

### O3 — SHOULD-FIX. WP-A.3 says "seven anchors"; the table has eight

Line 389 reads *"The seven anchors, each verified to match at `f228894`…"*. The
table beneath it has **eight** rows, and round 3 reported 8/8 PASS. I re-ran all
eight independently: **8/8 PASS**. This is the same class of countable-claim
error as N3 ("three" reads) and N16 (rev 1 "two", rev 2 "three"), in the one
section where a miscount could let an executor think an anchor is optional.

**Concrete change.** "The **eight** anchors, each **verified to match at
`f228894`**…".

### O4 — SHOULD-FIX. WP-D.1's ruling-3 rationale mis-states where the operator sees the message

**Text at issue:** *"The operator sees the remediation in the `crit` output, at
the moment it matters."*

**Evidence.** `tools/daily_ritual.sh:449` passes the fixed literal
`"h6_watch: NONZERO EXIT"` to `crit`, and `crit()` (`:85`) records only that into
the summary. The exception text reaches the **ritual log**
(`.tmp/daily_ritual/<stamp>.log`) via the `exec > "$LOG" 2>&1` redirect at `:71`.

The ruling survives — see §3 Q1 — but a rationale that is factually wrong about
the delivery surface will mislead the next reader, and it is the kind of
unverified mechanism claim rounds 1–3 kept catching.

**Concrete change.** Apply the §3 Q1 wording, which states the correct surface
and bounds the message to one line with an asserted field list.

### O5 — NOTE. "15 `config.` reads" in `validate_book` is 15 *lines*, 17 *occurrences*

Enumerated at `f228894`: 15 distinct lines, but `:481` carries two
(`COMMISSION_PER_CONTRACT` and `H6_MAX_CONTRACTS_PER_NAME`) and `:504` carries two
(`H6_DTE_BAND` twice) — 17 occurrences. Acceptance 14's parenthetical "about
nineteen reads" reachable from `score_book` is likewise loose (17 in
`validate_book` + 4 verdict-determining = 21 occurrences, or 19 lines). Nothing
downstream depends on the number, but this brief's history is miscounts.

**Concrete change.** In the two-class note: "`validate_book` contains `config.`
reads on **15 distinct lines** (17 occurrences — `:481` and `:504` each carry
two)". In Acceptance 14's parenthetical: "which is roughly twenty reads".

### O6 — NOTE. WP-B.1.3's "pass the count in from each caller" implies a signature change the brief does not name

`_has_consecutive_months` (`:718`) is reached only through `_hard_kill_v1`
(`:750`) and `_hard_kill_v2` (`:777`), which are reached only through
`_hard_kill_versions` (`:779`), called from `score_book:802`. Threading the v1
count from `score_book` therefore changes **three** signatures, not one. There is
also a wrapper `_hard_kill` at `:788-789` (`return bool(_hard_kill_versions(book))`)
with **no callers anywhere** in `options_researcher/` or `tests/` — grep at
`f228894` returns none. Worth one sentence so the executor neither stalls on it
nor deletes it as "dead code" (deleting it is a scope expansion).

**Concrete change.** Add to WP-B.1.3: *"Threading the count touches
`_hard_kill_versions` (`:779`), `_hard_kill_v1` (`:731`) and `_hard_kill_v2`
(`:753`) as well as the helper. The unused wrapper `_hard_kill` (`:788-789`) has
no callers at `f228894`: keep it compiling, do not delete it."*

### O7 — NOTE. `score_book` is not `validate_book`'s only caller

`_book_state` (`h6_watch.py:328-329`) also calls `validate_book(book)`. It is a
position-state helper, not a verdict path, so it is correctly out of scope — but
WP-B.1.5 says only "at the top of `score_book`", and an executor optimising for
symmetry could add the lookup there too, widening the `crit` blast radius beyond
H6 scoring.

**Concrete change.** Add to WP-B.1.5: *"`validate_book` has a second caller,
`_book_state` (`:329`). It is not a verdict path — do **not** add the lookup
there."*

### O8 — NOTE. Registry row 42's status column still reads "DRAFT (rev 3)"

The description column does carry the rev-3 title, so the brief's "APPLIED, no
action outstanding" is right about the part that matters. But the status column
says `DRAFT (rev 3)` and lists receipts I/K/N only. The orchestrating session (not
Codex — per the rev-4 forbidden bullet) should refresh it to rev 4 and add this
receipt when the fixes land. Flagged so the "no action outstanding" heading is not
read as covering the status column too.

---

## 7. Verdict

**PASS WITH FIXES** — one MUST-FIX that is a single word, three SHOULD-FIX wording
repairs, four NOTEs. No work package is redesigned, no anchor changes, no ruling is
reopened, and nothing in rev 4 delegates owner authority to Codex.

Both round-3 MUST-FIXes are genuinely closed against the code. The two-class read
split is correct line by line: `validate_book` really does hold the reads the old
Acceptance 14 would have tripped on, including the two `H6_MONTHLY_PREMIUM_AT_RISK`
reads at `:582`/`:585` the brief separately forbids touching, and the gate now
fires only on a fifth **verdict-determining** read. The ordering requirement is
right for the reason given: `score_book:796` calls `validate_book` first, `:581-586`
raises on a patched cap of `1`, and the sample bar at `:826` sits behind the
`REJECT` return at `:803-825` — so a deferred lookup really would have made two
Group 1 tests assert the wrong exception. I re-ran all eight anchors rather than
reading them: 8/8 PASS, seq-22 word form FAIL as claimed. The N20 precedent,
the full `config.py:628` quote, and the `verify()`-returns-`None` correction are
all exact.

The one thing that would bite on day one is not in a work package: hand-off item 3
still accepts "rev 3 (or later)" — the revision round 3 proved halts itself. Fix
that word. The other three are hygiene: a cross-reference left stale by rev 4's own
renumbering, a "seven anchors" over a table of eight, and a ruling rationale that
puts the refusal message in the `crit` summary line when it actually lands in the
ritual log.

On the open questions: keep the remediation sentence in the refusal message, but
make it one line with an asserted field list and state the ritual log as its real
surface; and close question 2 outright — `verify()` costs 1.3 ms cold, 0.6 ms warm,
paid once per process under WP-A.6's memoisation, so the top-of-function lookup has
no cost worth trading correctness for.

Apply **O1** (and, recommended, O2–O4), keep the Status line at DRAFT until they
land, and this is **ready for hand-off pending owner decision D-1 and the PR #175
merge**.
