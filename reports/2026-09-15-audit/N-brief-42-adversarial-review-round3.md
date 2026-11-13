# Brief 42 — independent adversarial review (round 3, SCOPED confirmation)

**Target:** `docs/superpowers/plans/2026-09-15-42-verdict-bar-ledger-binding-codex-brief.md`, **rev 3**
("Refuse H6/H8/H10b verdicts when `config.py` disagrees with the registered ledger record")
**Round 2:** `reports/2026-09-15-audit/K-brief-42-adversarial-review-round2.md` (PASS WITH FIXES — N1–N15)
**Round 1:** `reports/2026-09-15-audit/I-brief-42-adversarial-review.md` (FAIL — 3 blockers)
**Reviewer:** independent Claude session, read-only except this file
**Ref:** worktree `.tmp/worktrees/audit-0915`, branch `claude/audit-2026-09-15`, `git rev-parse --short HEAD` = `f228894` — the commit rev 3 claims
**Stance:** adversarial. Nothing below is a confirmation that the brief works.

**Verdict: PASS WITH FIXES** (2 MUST-FIX, 2 SHOULD-FIX, 4 NOTE; no redesign).

---

## 0. What I executed, not just read

- Re-ran **all eight** WP-A.3 anchors by building each f-string from the live
  `config.py` value and testing substring membership in that record's `reason`.
  **8/8 PASS**, including both new N3 anchors. The WP-A.4 word form **FAILS**
  as claimed ("Three", not "3").
- Re-read `h6_watch.py:467-607`, `:703-866`, `:894-920`, `:1027` line by line
  and traced every `config.` read reachable from `score_book`.
- Dumped seq 6/11/16/22/28/29/30 with `json.loads` — `entry_type`,
  `hypothesis_id`, `timestamp`, `record_hash` prefix.
- Ran `research.ledger.verify("ledger")` and `verify("ledger", anchored=True)`
  under `uv run --offline`. **Both return cleanly.**
- Re-checked the ops checkout at `/Users/carsynstephenson/options-validator-ops`
  independently (N14).
- Confirmed PR #175 with `gh pr view 175 --json`.
- Read `.agents/skills/codex-brief-writing/SKILL.md` against the rev-3 header
  and body order.

---

## 1. Disposition of N1–N15

| # | Sev (r2) | Disposition in rev 3 | Evidence |
|---|---|---|---|
| N1 — happy-path test in Group 1 | MUST-FIX | **CLOSED** | Group 3 created ("No-regression guards. EXEMPT from Acceptance 3"), `test_h6_scoring_unchanged_when_config_and_registration_agree` is its only row, and Acceptance 3 now exempts Groups 2 **and** 3. Acceptance 3's "Every" is true as written |
| N2 — refusal-message test scope | MUST-FIX | **CLOSED** | Group 1 header: "Every Group 1 test calls **`score_book`** (not the lookup module directly)"; the row itself repeats "**must go through `score_book`**". Revert-demo is now satisfiable. (See N17 — one Group 1 row is unreachable for a different reason) |
| N3 — fourth live-config read | MUST-FIX | **CLOSED** | `h6_watch.py:748` `if pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK` inside `_hard_kill_v1` (def `:731`), feeding `_has_consecutive_months` at `:750`; `:808` `${config.H6_MONTHLY_PREMIUM_AT_RISK:,.0f}` — all four verified verbatim. Both new anchors re-verified PASS by me (table §2). Scope IN.1 says four; WP-B.1.4 added; `:384/:387/:582/:585` fenced off in both WP-B.1.4 and the forbidden list; `h6_config_snapshot` name list confirmed to contain `H6_MONTHLY_PREMIUM_AT_RISK` at `:908`. **Acceptance 14, the anti-recurrence device, is itself defective → N16** |
| N4 — "no literal 2026-08-19" false | MUST-FIX | **CLOSED** | Claim deleted. seq 28 `timestamp` `"2026-08-19T01:05:33.937513+00:00"`, seq 29 `"2026-08-19T01:05:33.939961+00:00"` — both confirmed byte-exact. `timestamp` is inside the body `_record_hash` covers (`research/ledger.py:557-559` strips only `record_hash`), so it is genuinely sealed. WP-C.2's `>=` binding holds today (`"2026-08-19" >= "2026-08-19"`); UTC convention stated; term (i) disclosed as uncheckable |
| N5 — memoisation ambiguity | MUST-FIX | **CLOSED** | WP-A.6 is now unambiguous: cache `verify()` result + parsed bodies keyed on `base_dir`; "The anchor comparison is re-evaluated on EVERY call, against the live `config` attribute read at call time. Never cache a resolved bar value." Backed by Group 1's second-call test, Acceptance 15, and a forbidden-list entry. Wording nit → N22 |
| N6 — fixture instruction unimplementable | MUST-FIX | **CLOSED** | Replaced with the read-only real-ledger rule. Independently confirmed implementable: `ledger.verify("ledger")` succeeds offline under `uv run --offline` with the default `anchored=False`; `tests/test_h10_config.py:7-12` `_load_registration(seq)` already opens the real file read-only. Constraints (seq==index, `trial_count`, HEAD) written out and verified at `research/ledger.py:553-554`, `:369-373`, `:562-563`. No-write rule kept absolute; temp-dir retained only for malformed chains. A **stronger** precedent exists and is not cited → N20 |
| N7 — title overclaims | MUST-FIX | **CLOSED** | Title is the reviewer's exact wording. "What this brief delivers, stated honestly before the work packages" sits inside "Why this exists", above Scope. Registry text supplied. Filename deliberately unchanged, with the reason recorded. (Registry row already carries it → N21) |
| N8 — `anchored` unspecified | SHOULD-FIX | **CLOSED** | Signature re-verified: `verify(base_dir="ledger", anchored=False, git_clean_tracked=None)` at `research/ledger.py:549`; `anchored` gates `_require_committed_clean` at `:564-565`. WP-A.1 picks `anchored=False`, states the ritual-must-not-fail-on-dirty-tree reason, and requires it in the module docstring |
| N9 — anchors format-coupled | SHOULD-FIX | **CLOSED** | WP-A.3 states the rule (template **including format spec** fixed per `(seq, config-name)` pair) and requires a recorded PASS before any new anchor; forbidden-list entry mirrors it. The `USD 2,000` / `USD 2000` split is called out by name. Confirmed real: seq 6 uses the comma form, seq 11 does not |
| N10 — amendment consequence mis-described | SHOULD-FIX | **CLOSED** | Sentence deleted; blast radius **(e)** states the `crit`-until-anchor-table-updated behaviour, names seq 22 as the precedent, and Acceptance 11 forces it into the PR body |
| N11 — Acceptance 8 grep | SHOULD-FIX | **CLOSED** | Alternation is `\b(8\|3\|7\|2000\|2_000)\b\|2026-08-03\|2026-08-19`; expected result stated as **no matches** — verified correct, since 6/11/16/22 match none of the alternates. Plain-language condition added and made governing |
| N12 — WP-B.2 vs Acceptance 10 | SHOULD-FIX | **CLOSED** | "Skipped, not halted" appears in the D-1 section, WP-B.2, and Acceptance 10; how a ruling reaches Codex is specified. **The same conflict now exists one package over, at WP-B.1.3 → N18** |
| N13 — duplicate-seq defence redundant | NOTE | **CLOSED** | WP-A.2 states `verify()` is the load-bearing check (`:553-554`) and the `entry_type`/`hypothesis_id` assertions are belt-and-braces, with a docstring requirement |
| N14 — ops checkout carries the ledger | NOTE | **CLOSED** | Re-verified independently: 32 records, max `seq` 31, `HEAD` equals the last `record_hash`, and the full hash sequence is byte-identical to this worktree's. Checkout is at `a3745ab`. Blast radius (b) records all of it plus the lag caveat and the link to (e) |
| N15 — header cosmetic deviation | NOTE | **CLOSED** | Header note records it; §4 below confirms the shape is compliant |

**Tally: 15 CLOSED, 0 PARTIAL, 0 OPEN.** Every round-2 finding is genuinely
closed against the code, not merely acknowledged.

---

## 2. Re-verification of rev 3's four new claims

### 2a. The fourth read and its two anchors — **both confirmed**

```
748        if pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK
```

inside `_hard_kill_v1` (def `:731`), result passed to `_has_consecutive_months`
at `:750`; `_hard_kill_versions` (`:779`) runs it; `score_book` (`:792`) calls
that at `:802` and returns `REJECT` at `:803-825` with `:808` interpolating the
same constant. All exact.

| Guarded value | seq | Anchor built from live config | Result |
|---|---|---|---|
| `H6_MIN_COMPLETED_POSITIONS`=8 | 6 | `"after 8 completed positions"` | **PASS** |
| `H6_HARD_KILL_FULL_LOSS_MONTHS`=3 | 6 | `"hard kill regardless: 3 consecutive calendar months"` | **PASS** |
| `H6_MONTHLY_PREMIUM_AT_RISK`=2000 | 6 | `f"USD {v:,} per calendar month"` → `"USD 2,000 per calendar month"` | **PASS** |
| `H8_MIN_COMPLETED_POSITIONS`=8 | 11 | `"after 8 completed positions"` | **PASS** |
| `H8_HARD_KILL_FULL_LOSS_MONTHS`=3 | 11 | `"hard kill regardless: 3 consecutive calendar months"` | **PASS** |
| `H6_MONTHLY_PREMIUM_AT_RISK`=2000 | 11 | `f"USD {v} per calendar month"` → `"USD 2000 per calendar month"` | **PASS** |
| `H10_MIN_LOSSES_FOR_VERDICT`=7 | 16 | `"verdict gates at >=7 losses"` | **PASS** |
| `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` | 22 | `"on or after 2026-08-03"` | **PASS** |
| WP-A.4 word form | 22 | `"3 consecutive full-loss calendar entry cohorts"` | **FAIL** (record says "Three") |

seq 16's distractor re-confirmed: `"MIN_LOSSES_FOR_VERDICT=10"` is present,
`"verdict gates at >=10 losses"` is absent, so a config edit to 10 still refuses.

### 2b. seq 28/29 timestamps and the resume-floor comparison — **confirmed, and the brief under-quotes its own evidence**

Both timestamps are exact. `config.H10B_RESUME_FLOOR_SESSION` and
`config.H5_RESUME_FLOOR_SESSION` are both `"2026-08-19"` (`config.py:629-630`),
so the UTC-date lower bound holds with equality and the ET reading holds
strictly. seq 30 (`H10B_H5_AMENDMENT_CORRECTION_V1`, `timestamp`
`2026-08-19T01:17:20`) carries no clause 5, as rev 3 states.

One omission: `config.py:628`'s comment does not stop where the brief quotes it.
The full line is *"mechanical floor per seq 28/29 clause 5; append date
2026-08-18 ET; **updated at merge by the orchestrating session if the merge
lands later**"*. That tail is evidence **for** rev 3's choice — it says the
constant moves forward, never backward, which is exactly the `>=` direction.
See N23.

### 2c. WP-A.6 memoisation and its test — **sound, one wording nit**

The rule as written cannot produce the catastrophic reading N5 identified. The
second-call test is the right proof and it is in Group 1, so it participates in
the Acceptance-3 revert demo. Nit at N22: `verify()` returns `None`
(`research/ledger.py:549-565`), so "cache the `verify()` result" is literally
caching `None`; what is meant is "cache the fact that verification succeeded".

### 2d. The N6 read-only-real-ledger approach — **works, and there is a better precedent**

- `ledger.verify("ledger")` with default `anchored=False` runs clean offline in
  this worktree. (`anchored=True` also passes here, but WP-A.1's reasoning for
  the default is still correct and should stand.)
- `tests/test_h10_config.py:7-12` already opens `ledger/experiments.jsonl`
  read-only — the cited precedent is real.
- **Stronger, uncited precedent:** `tests/test_ledger_diagnostics.py:230-231`,
  `def test_real_ledger_still_verifies(self): ledger.verify("ledger")` — an
  existing test that calls `verify()` **on the real ledger** offline. That is the
  precedent for the exact operation WP-A adds, not merely for opening the file.
  See N20.

---

## 3. Rulings on rev 3's four open questions

### Q1 — WP-B.1.3: is stop-and-report on the v2 month count still right? **No. Replace it.**

The diagnosis is right and the remedy is wrong. Rev 3 spent finding N12 teaching
itself that "stop and report" halts the whole job while "skip" completes it —
and then left a mid-package `stop and report` at WP-B.1.3 that halts everything
downstream (WP-B.1.4, WP-B.1.5, WP-C, WP-D, WP-E, the PR) over one caller of one
helper whose registered value is not machine-anchorable. That is the N12 defect
reappearing one package later.

**Ruling: leave the v2 caller exactly as it is today, unbound, documented, and
tripwired.** It is no worse than today (it is today), it does not paper over
anything, and it does not cost a round trip. Concretely: pass the count in
explicitly from both callers per WP-B.1.3's first bullet; the **v1** caller takes
it from the seq-6 anchor; the **v2** caller reads `config` directly with a code
comment naming the word-form obstacle and pointing at
`test_seq22_month_count_is_word_form_not_numeric` (already specified in Group 2);
the PR body states that the v2 hard-kill count remains unbound and why. The trap
rev 1 walked into — silently applying a seq-6 value to a seq-22 rule — stays
closed, because the v2 caller is bound to nothing at all rather than to the wrong
record. See N18 for the wording.

### Q2 — WP-C.2 timezone convention: **keep UTC. Do not switch to ET.**

The UTC date is a prefix slice of the sealed field itself — zero interpretation.
The ET date requires a timezone conversion and a DST rule, which is a
normalisation step, and the brief's own forbidden list bans "Parsing,
interpreting, or normalising registration prose beyond exact substring
membership". It would be incoherent to ban prose normalisation and then
DST-convert a sealed timestamp. UTC is also the strictly stronger bound
(`>= 2026-08-19` vs `>= 2026-08-18`). Add one clause noting the `config.py:628`
comment reads ET, that the two differ by one calendar day, and that the UTC
reading is deliberately the tighter of the two.

### Q3 — Blast radius (e): owner-facing runbook note, or PR body only? **Neither, as posed. Put it in the refusal message.**

`docs/monday-runbook.md` contains no `crit` triage section at all (checked —
zero occurrences of "crit" in 122 lines), so a note bolted there would not be
read by the person who hits the `crit`, and adding it expands the file set for
no operational gain. A PR body alone is worse: nobody reads a merged PR body at
8am.

**Ruling: require the refusal message itself to carry the remediation
sentence.** WP-D.1 already requires the message to name the config value, the
registration text, and the seq. Add: *"and a remediation clause stating that if a
ledger amendment changed this value, the module's `(seq, anchor)` table must be
updated"*. The operator sees it in the `crit` output, at the moment it matters,
with no new files. Keep the Acceptance-11 PR-body requirement as well.

### Q4 — Is WP-C scope creep? **No. Keep it.**

Both halves are **test-only**: WP-C.1 extends an existing file
(`tests/test_h10_config.py`) with `assertIn` anchors in the pattern already at
`:50-51`, and WP-C.2 adds two comparisons against sealed timestamps. Neither
touches production code, so blast radius (a) — the `crit` path — cannot reach
them; a WP-C failure fails the suite, it does not stop the ritual. The marginal
cost is small and the marginal value is real (N4 turned WP-C.2 from a literal
tripwire into a check against a sealed typed field, which nothing else in this
brief has). Splitting it into a follow-up brief would cost a whole registry slot
and hand-off cycle for two test methods.

---

## 4. Brief-writing skill compliance

Checked against `.agents/skills/codex-brief-writing/SKILL.md`:

- **Header order** — required: Date; Author; Executor; Status; Provenance. Rev 3
  has Date → Author → Executor → Status → **Revision** → Provenance. All five
  required fields present in the required relative order; the insertion is not
  forbidden and is disclosed in the header note. ✔
- **Status line** — verbatim `DRAFT — pending independent adversarial review
  before hand-off`. ✔ It must **stay** DRAFT: this receipt is a PASS WITH FIXES,
  and the skill says the Status line stays DRAFT until the review passes. Flip it
  only after the two MUST-FIX edits land.
- **Body order** — Why this exists → Scope → Work packages → Acceptance,
  preserved with insertions between (Lanes, Verified facts, D-1, Blast radius,
  Hand-off). ✔
- **Labels on every constraint** — Repo-verified / Inference / Assumption used
  throughout, including on both new N3 rows and both new N4 rows. I found no
  unlabelled flat factual assertion of the N4 class in rev 3. The one
  under-quotation (N23) is an omission, not a false claim. ✔
- **Prior finding IDs cited verbatim** — "audit 2026-09-15 §4 finding 2 /
  finding 3", N1–N15, round-1 1–15. ✔
- **Naming and registry** — filename unchanged with the reason recorded;
  registry row 42 reserved to this path; the brief correctly forbids resolving a
  registry conflict. ✔ (N21)
- **Closest example** — the brief exceeds the cited example's rigour; no issue.

## 5. Authority delegation check — clean, with one wording gap

Nothing in rev 3 hands Codex authority that `CLAUDE.md:53` ("the owner types
every frozen number, new registration, and verdict ratification") reserves:

- No frozen number is typed by anyone — the anchor is built from the live
  `config.py` value, and Acceptance 8 greps for any copy. ✔
- No registration, no amendment, no ledger write; `.claude/rules/ledger.md`
  honoured; a `block_ledger_edits` block is pre-declared correct. ✔
- No verdict emitted, changed, or ratified. ✔
- D-1 stays with the owner, arrives only as an owner-recorded amendment on
  `origin/main` or an owner message at dispatch, and Codex "never infers one, and
  never edits this brief to record one". ✔
- PR stays a draft; no merge, deploy, or ops sync. ✔

**Gap (N19):** the "Codex never edits this brief" sentence is scoped to D-1 only,
but two other places say a ruling "must be recorded in this brief before
implementation" (WP-B.1.3's v2-count fallback, WP-A.3's new-anchor rule) without
naming who records it. A literal executor could read those as its own job.

---

## 6. New findings

### N16 — MUST-FIX. Acceptance 14 contradicts WP-B.1.4 and will halt the job as written

**Text at issue.** Acceptance 14: *"Codex greps `options_researcher/h6_watch.py`
for every `config.` read **reachable from `score_book`** and reports the list in
the PR body. If it finds a fifth, **stop and report**."*

**Evidence.** `score_book` (`:792`) calls `validate_book` at `:796`.
`validate_book` is defined at `:467` and runs to `:606`, and it contains roughly
fifteen further `config.` reads — including **`config.H6_MONTHLY_PREMIUM_AT_RISK`
at `:582` and `:585`**, the exact lines WP-B.1.4 and the forbidden list order
Codex not to touch, plus `H6_MAX_ASK_DOLLARS` `:478`, `H6_MAX_CONTRACTS_PER_NAME`
`:480/:481/:492/:494`, `H6_NAMES` `:490`, `H6_DTE_BAND` `:504/:506`,
`H6_TAKE_PROFIT_PCT` `:553/:569`, `H6_CLOSE_AT_DTE` `:561`, `H6_MAX_CONCURRENT`
`:595/:598`, `COMMISSION_PER_CONTRACT` `:481`. A faithful executor finds a fifth
on the first grep and stops — the brief halts itself.

**Concrete change.** Replace Acceptance 14's condition with:

> 14. **The four-read list is re-derived, not trusted.** Codex greps
>     `options_researcher/h6_watch.py` for every `config.` read reachable from
>     `score_book` and reports the full list in the PR body, split into two
>     columns: **verdict-determining** (a value whose change moves the
>     `verdict`, `hard_kill`, or `reason` fields of the returned `H6Score`) and
>     **invariant-validating** (reads inside `validate_book`, `:467-606`, which
>     raise `ValueError` on a book that violates a registered invariant and
>     cannot select a verdict). Only the first column is in scope; it is
>     expected to be exactly the four reads at `:710`, `:719`, `:748`, `:826`.
>     If a **fifth verdict-determining** read is found, **stop and report** — do
>     not silently extend scope. *(Rev 1 said "two", rev 2 said "three"; both
>     were wrong. `validate_book`'s reads, including
>     `H6_MONTHLY_PREMIUM_AT_RISK` at `:582`/`:585`, are invariant-validating and
>     are explicitly out of scope per WP-B.1.4.)*

### N17 — MUST-FIX. One Group 1 refusal test cannot reach the guard, because `validate_book` raises first

**Text at issue.** WP-E Group 1:
`test_monthly_cap_refuses_when_config_disagrees_with_seq6` — *"`H6_MONTHLY_PREMIUM_AT_RISK`
patched to `1` → refusal"*. WP-B.1.5: *"One lookup per scoring call, passed
down"* — with no statement of **where in `score_book` the lookup happens**.

**Evidence.** `score_book:796` calls `validate_book` **before** anything else.
`validate_book:581-586`:

```
581    for key, gross in monthly.items():
582        if gross > config.H6_MONTHLY_PREMIUM_AT_RISK:
583            raise ValueError(
584                f"book {key[0]:04d}-{key[1]:02d} gross premium risk "
585                f"${gross:,.2f} exceeds ${config.H6_MONTHLY_PREMIUM_AT_RISK:,.2f}"
586            )
```

Any book with real entry costs blows this at a patched cap of `1`. The existing
neighbouring test at `tests/test_h6_watch.py:493-514` builds four positions at
`entry_cost=1000.0`, two per month — gross 2000 per month, which passes at the
real cap and raises instantly at `1`. So the test as specified would observe a
plain `ValueError` from `validate_book`, not the typed refusal, and asserting on
the refusal's message would fail. The same ordering question bites
`test_h6_sample_bar_refuses_when_config_disagrees_with_seq6`: if the lookup is
deferred to `:826`, a hard-killing book returns `REJECT` at `:803` and the sample
bar is never consulted.

**Concrete change.** Two sentences. Add to **WP-B.1.5**:

> The WP-A lookup is performed **once at the top of `score_book`, before the
> `validate_book` call at `:796`**, and all four guarded values are resolved by
> that single call and passed down. This ordering is required, not stylistic: a
> guarded value that also appears in `validate_book`'s invariants
> (`H6_MONTHLY_PREMIUM_AT_RISK` at `:582`) would otherwise raise a `ValueError`
> before the guard could refuse, and a hard-killing book would return `REJECT`
> at `:803` before the sample bar at `:826` is read.

And add to the `test_monthly_cap_refuses_when_config_disagrees_with_seq6` row:

> the refusal must be raised before `validate_book` runs (WP-B.1.5 ordering);
> assert on the typed refusal, and assert explicitly that the raised exception is
> **not** `validate_book`'s `"gross premium risk"` `ValueError`.

### N18 — SHOULD-FIX. WP-B.1.3's "stop and report" re-imports the N12 defect

Per §3 Q1. **Concrete change.** Replace WP-B.1.3's third bullet with:

> - For the **v2** caller, the count is registered at seq 22 in word form and is
>   **not anchorable** (WP-A.4). Leave it reading `config` exactly as it does
>   today — **unbound, not bound to the wrong record** — with a code comment
>   naming the word-form obstacle and citing Group 2's
>   `test_seq22_month_count_is_word_form_not_numeric`. Record in the PR body that
>   the v2 hard-kill month count remains unbound and why. Do **not** reuse the
>   seq-6 value for it, and do **not** write a word-form parser. Both numbers are
>   3 today, which is precisely why this must not be papered over. This is a
>   documented gap, **not** a stop-and-report: the rest of the brief completes.

and delete the following "If review or the owner rules that the v2 count may
inherit the seq-6 anchor…" bullet, which N19 also touches.

### N19 — SHOULD-FIX. "Recorded in this brief" never says who, outside D-1

**Concrete change.** Add one bullet to the Explicitly-forbidden list:

> - **Editing this brief.** Any ruling this brief says "must be recorded in this
>   brief before implementation" (D-1, WP-A.3's new anchors, WP-B.1.3) is
>   recorded by the owner or the orchestrating session on `origin/main`, never by
>   Codex. If Codex believes a ruling is needed, it reports and continues with the
>   documented default.

### N20 — NOTE. A stronger N6 precedent exists and should be named

`tests/test_ledger_diagnostics.py:230-231` already calls
`ledger.verify("ledger")` against the real chain, offline, in the standing
suite. Add it beside `tests/test_h10_config.py:7` in WP-E Fixtures: the first is
the precedent for the **file read**, the second for the **`verify()` call**,
which is the operation WP-A actually introduces. It also pre-answers the
Acceptance-1 question of whether the new tests can pass offline.

### N21 — NOTE. The registry-row action item is already done

`docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md` row 42 already carries the new
description (a superset of the brief's proposed text — it adds the D-1 clause and
this receipt's filename) and the file shows as modified in this worktree. The
brief's "Registry row update required" section is therefore stale as an action
item. Either mark it "applied 2026-09-15, see row 42" or drop it. Harmless
either way; flagged so a later reader does not make the edit twice.

### N22 — NOTE. `verify()` returns `None`

`research/ledger.py:549-565` returns nothing. WP-A.6's "Cache only the
`verify()` result and the parsed record bodies" is literally an instruction to
cache `None`. Say "cache the **fact that `verify()` succeeded** for this
`base_dir`, plus the parsed record bodies" so an executor does not write
`if cached_result:` and re-verify on every call.

### N23 — NOTE. WP-C.2 under-quotes its best piece of evidence

`config.py:628` in full: *"mechanical floor per seq 28/29 clause 5; append date
2026-08-18 ET; **updated at merge by the orchestrating session if the merge lands
later**"*. The brief quotes only up to "ET". The tail is the owner's own
statement that this constant moves forward and never backward — which is
precisely why a `>=` lower bound (rather than `==`) is the correct check. Quote
the whole line in WP-C.2.

---

## 7. Verdict

**PASS WITH FIXES.**

All fifteen round-2 findings are closed against the code, not merely
acknowledged. I re-ran the anchors rather than reading them: eight of eight pass
when built from the live `config.py` values, including both anchors rev 3 added
for the fourth read, and the seq-22 word form fails exactly as claimed. The
fourth read at `h6_watch.py:748` is real and is cited correctly down to the
`:808` interpolation. The seq 28/29 timestamps are byte-exact and sit inside the
body `verify()` re-hashes, so WP-C.2's lower bound is a genuine check against a
sealed typed field. `verify()` runs clean offline with `anchored=False`, and an
existing test already does exactly that against the real chain — so the N6
replacement is implementable, which its predecessor was not. WP-A.6 can no
longer be read the catastrophic way. The ops checkout still carries a
byte-identical chain. The header, body order, labelling, and authority split all
comply with the brief-writing skill, and nothing in rev 3 hands Codex a frozen
number, a registration, an amendment, a verdict, or the D-1 call.

Two things would bite on day one, and neither is a design problem. Acceptance 14
tells Codex to grep every `config.` read reachable from `score_book` and stop if
it finds a fifth — but `score_book` calls `validate_book` at `:796`, which holds
about fifteen more, including the two `H6_MONTHLY_PREMIUM_AT_RISK` reads the
brief separately forbids touching. Read faithfully, the brief halts itself on the
first grep. And `test_monthly_cap_refuses_when_config_disagrees_with_seq6`
patches the cap to `1`, which makes `validate_book:582` raise a plain
`ValueError` before any guard runs — so the test cannot assert the refusal it is
specified to assert, unless the brief says the lookup happens at the top of
`score_book`. Both are closed by the exact wording in N16 and N17; no work
package is redesigned and no anchor changes.

On the open questions: keep UTC; keep WP-C; drop WP-B.1.3's stop-and-report in
favour of a documented unbound v2 caller; and put the amendment-will-crit warning
in the refusal message rather than a runbook with no `crit` section.

Apply N16 and N17 (and, recommended, N18–N19), keep the Status line at DRAFT
until they land, and this is ready for hand-off pending the owner's D-1 call.
