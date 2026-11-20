# Brief 42 — independent adversarial review (round 2)

**Target:** `docs/superpowers/plans/2026-09-15-42-verdict-bar-ledger-binding-codex-brief.md`, **rev 2**
**Round 1:** `reports/2026-09-15-audit/I-brief-42-adversarial-review.md` (FAIL — 3 blockers, 8 MUST-FIX, 3 SHOULD-FIX, 1 NOTE)
**Reviewer:** independent Claude session, read-only except this file
**Ref:** worktree `.tmp/worktrees/audit-0915`, branch `claude/audit-2026-09-15`, `git rev-parse --short HEAD` = `f228894` — the same commit rev 2 claims
**Stance:** adversarial. Nothing below is a confirmation that the brief works.

**Verdict: PASS WITH FIXES.** Reason in the verdict line at the end.

---

## 0. What I executed, not just read

- Ran all six WP-A.3 anchors and the WP-A.4 word-form case myself against
  `ledger/experiments.jsonl`, building each f-string from the live `config.py`
  value. **All six PASS; the word-form case FAILS.** Exactly as rev 2 claims
  (table in §2).
- Read `research/ledger.py:549-565` line by line to test the claim that
  `verify()` recomputes. **It does** (§2).
- Re-derived every ledger `seq` claim from the file with `json.loads` per line.
- Re-read every `file:line` rev 2 changed or added.
- Checked the ops checkout at `/Users/carsynstephenson/options-validator-ops`
  directly, which answers the brief's own open question 4 (finding N14).
- Confirmed PR #175 state with `gh pr view 175 --json`.

---

## 1. Disposition of the 15 round-1 findings

| # | Round-1 finding | Sev (r1) | Disposition | Evidence |
|---|---|---|---|---|
| 1 | Record-hash pin seals nothing | BLOCKER | **CLOSED** | Field-comparison mechanism deleted. WP-A.1 now calls `research.ledger.verify()`, which recomputes `_record_hash` over the body at `research/ledger.py:557-559`, checks `prev_hash` at `:555-556`, runs `_verify_semantic_records` at `:561`, and requires HEAD to match the tip at `:562-563`. Verified by reading. Residual: the `anchored` parameter is unspecified → N8 |
| 2 | WP-A bound nothing; transcribed constants | BLOCKER | **CLOSED (mechanism); framing OPEN** | No numeric constant survives: Scope OUT "No second home for any verdict number", Acceptance 8 greps for it. Six anchors verified PASS. But the **title still says "Bind … to the registered ledger record"** → N7 |
| 3 | Refusal vs "follows registration" contradiction | BLOCKER | **PARTIAL** | WP-A.5 fixes one fail-closed semantics and binds it on all WPs ✔; WP-D.1's "whichever the WP-A design produces" deleted ✔; WP-E rows 1–2 rewritten as refusals ✔. But WP-E Group 1 now carries a happy-path row that cannot fail on revert, against Acceptance 3 → N1 |
| 4 | No blast radius | MUST-FIX | **CLOSED** | New section (a)–(d). `h6_watch.py:1027` `score_book(book).to_dict()` inside `build_snapshot` ✔; `tools/daily_ritual.sh:448-449` with `\|\| crit "h6_watch: NONZERO EXIT"` ✔. Item (b) can be upgraded from "Codex confirms" to Repo-verified → N14 |
| 5 | seq 28 mislabelled "A2-v1" | MUST-FIX | **CLOSED** | seq 28 `hypothesis_id: "H10b"`, `reason` begins `H10B_AMENDMENT_V1_1 2026-08-16/17`; seq 29 `hypothesis_id: null`, `H5_AMENDMENT_V1`; seq 30 `H10B_H5_AMENDMENT_CORRECTION_V1`. "A2-v1" deleted |
| 6 | WP-C.2 pointed at a non-existent seq 30 clause 5 | MUST-FIX | **CLOSED** | Corrected to seq 28 cl. 5 / seq 29 cl. 5. Verified: seq 28 carries "5. **Implementation gate + hard no-backfill floor** … `H10B_RESUME_FLOOR_SESSION` = the LATER of …"; seq 29 carries "Identical mechanism to H10B clause 5 (`H5_RESUME_FLOOR_SESSION`, refusal + test)"; seq 30 has no clause 5 and no `RESUME_FLOOR` token. Matches `config.py:628`'s own comment |
| 7 | seq 22 mislabelled; "none changes a bar" false | MUST-FIX | **CLOSED** | Every quoted fragment is verbatim in seq 22's `reason`, and rev 2 names its own prior claim as false |
| 8 | `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` unbound; shared helper | MUST-FIX | **PARTIAL** | The named constant is now defect 3, WP-B.1.2/B.1.3 handle the shared-helper trap, and the existing `H6_KILL_V2_TRIAL_INTENT_HASH` precedent is cited ✔. But the enumeration is **still not exhaustive** — `h6_watch.py:748` is a fourth live-config verdict read → N3 |
| 9 | Three citation defects | SHOULD-FIX | **CLOSED** | `h7_forward_scoring.py:356` `registered_window`, `:357` `frozen`, `:358` `stage_bar`, `:359` `scorer_bar` ✔; `tests/test_h7_forward_scoring.py:39` `ScoringCase`, `setUp` `:40-43`, synthetic append `:44-57` ✔; `_synthetic_base` correctly re-described as a production `ActivationBoundaryError` guard defined `:44-54` refusing `REAL_FORWARD_STORE` ✔; "typed reader" withdrawn — WP-A.1 says outright "untyped `list[dict]` — it is *not* a typed reader" ✔ (`research/ledger.py:141`) |
| 10 | Three WP-E tests cannot fail on revert | MUST-FIX | **PARTIAL** | Group 1 / Group 2 split ✔, Acceptance 3 narrowed with Group 2 explicitly exempt ✔, all three named offenders moved to Group 2 ✔. But two Group 1 rows reimport the same defect → N1, N2 |
| 11 | D-1 unenforceable; D-1b invented an entry point | MUST-FIX | **CLOSED** | Acceptance 10 is mechanically checkable (`git diff --name-only` contains no `options_researcher/h8_watch.py`, no `tests/test_h8_*`); D-1b is documentation-only, "No new function, no refusal entry point, no test module"; Group 2's `test_h8_bar_anchors_present_in_seq11` is explicitly un-gated. Residual wording conflict → N12 |
| 12 | Executor typing frozen numbers | MUST-FIX | **CLOSED** | Prose anchor removes the transcription entirely. `CLAUDE.md:53` ("The owner types every frozen number, new registration, and verdict ratification") and `.cursorrules` ("Every number in strategy logic comes from `config.py`. No magic numbers") are both satisfied — `config.py` stays the single source and no one types a number. Acceptance-8 grep is under-scoped → N11 |
| 13 | Resume floors are derivations | SHOULD-FIX | **PARTIAL** | Demoted to tripwires up front ✔ and the derivation is quoted correctly ✔. But the stated *reason* — "no literal `2026-08-19` exists in any record" — is **false**, and it forecloses a real binding → N4 |
| 14 | No hand-off ref | SHOULD-FIX | **CLOSED** | New "Hand-off and ordering" section. Independently verified: `gh pr view 175` → `{"number":175,"state":"OPEN","isDraft":true,"headRefName":"claude/audit-2026-09-15"}`; the brief file is untracked on that branch (`git status --porcelain` → `?? docs/superpowers/plans/2026-09-15-42-…`); ordering, revision-string confirmation, fresh worktree, and the branch-push rule are all stated |
| 15 | What rev 1 got right | NOTE | **CLOSED** | "What H10b actually is", the H8 section, the OUT list, and the revert principle all carried forward intact |

**Tally: 10 CLOSED, 4 PARTIAL, 0 fully OPEN, 1 (finding 2) closed on mechanism with the framing defect re-raised as N7.**

---

## 2. Attacking the new mechanism (WP-A prose anchor)

The round-2 brief asked for four specific attacks. Results:

### 2a. The six anchors — run, not trusted

Built each f-string from the live `config.py` value and tested substring
membership in that record's `reason`:

| Bound value | seq | Anchor built from config | Result |
|---|---|---|---|
| `H6_MIN_COMPLETED_POSITIONS` = 8 | 6 | `"after 8 completed positions"` | **PASS** |
| `H6_HARD_KILL_FULL_LOSS_MONTHS` = 3 | 6 | `"hard kill regardless: 3 consecutive calendar months"` | **PASS** |
| `H8_MIN_COMPLETED_POSITIONS` = 8 | 11 | `"after 8 completed positions"` | **PASS** |
| `H8_HARD_KILL_FULL_LOSS_MONTHS` = 3 | 11 | `"hard kill regardless: 3 consecutive calendar months"` | **PASS** |
| `H10_MIN_LOSSES_FOR_VERDICT` = 7 | 16 | `"verdict gates at >=7 losses"` | **PASS** |
| `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` = `"2026-08-03"` | 22 | `"on or after 2026-08-03"` | **PASS** |
| WP-A.4 word form | 22 | `"3 consecutive full-loss calendar entry cohorts"` | **FAIL** (record says "Three") |

Rev 2's status column is accurate on all seven. The record selection is also
sound: seq 6, 11, 16 and 22 each resolve to exactly one record, with
`entry_type == "trial_intent"` and `hypothesis_id` `"H6"`, `"H8"`, `"H10b"`,
`"H6"` respectively — matching WP-A.2's assertions.

### 2b. Does `verify()` really recompute? — **Yes.**

`research/ledger.py:549-563`:

```
552    for i, rec in enumerate(records):
553        if rec.get("seq") != i:
554            raise LedgerError(f"seq mismatch at index {i}: {rec.get('seq')}")
555        if rec.get("prev_hash") != prev:
556            raise LedgerError(f"prev_hash break at seq {i}")
557        body = {k: v for k, v in rec.items() if k != "record_hash"}
558        if rec.get("record_hash") != _record_hash(body):
559            raise LedgerError(f"record_hash mismatch at seq {i}")
560        prev = rec["record_hash"]
561    _verify_semantic_records(records)
562    if tip(base_dir) != prev:
563        raise LedgerError("HEAD does not match chain tip")
```

`:557` strips `record_hash` and `:558` recomputes over the remaining body via
`_record_hash` (`:162` → `sha256_hex(canonical_json(...))`). This is a genuine
recomputation, not a field read. Rev 2's claim at WP-A.1 is correct and its
line citations `:557-559`, `:555-556`, `:561`, `:562-563` are all exact.

### 2c. Could a coordinated edit to `config.py` **and** the ledger prose pass? — **No, not a partial one.**

Edit seq 6's `reason` to say "after 5 completed positions" and set
`config.H6_MIN_COMPLETED_POSITIONS = 5`:

1. seq 6's stored `record_hash` no longer matches the recomputed body →
   refusal at `:558`.
2. Recompute and rewrite seq 6's `record_hash` to cover that → seq 7's
   `prev_hash` no longer matches → refusal at `:555`.
3. Rewrite the whole chain seq 6→31 **and** `ledger/HEAD` → `verify()` passes.

So the honest statement is: `verify()` makes prose tampering **tamper-evident
against any partial edit**, and a full 26-record chain rewrite plus a HEAD
rewrite is required to defeat it. That is a real and adequate seal for this
threat model, and it is further backstopped by the `block_ledger_edits` hook
(`.claude/rules/ledger.md`) and by git history. The one gap is that the brief
never specifies `verify()`'s `anchored` flag, which is precisely the parameter
that would also catch a working-tree rewrite (`:564-565` →
`_require_committed_clean`). See N8.

### 2d. Is the substring anchor spoofable by another record? — **No.**

`verify()` at `:553-554` requires `rec["seq"] == index`, so duplicate or
skipped seq values are structurally impossible once `verify()` has passed:
there is exactly one record per seq and no other record can shadow it. A newly
appended record containing the same sentence lands at a new seq and is never
consulted. WP-A.2's `entry_type` / `hypothesis_id` assertions are belt-and-
braces on top of that. Round-1 finding 2's attack (b) is fully answered.

Confirmed there is no *within*-record spoof either: seq 16 contains the
distractor `"MIN_LOSSES_FOR_VERDICT=10"`, but
`"verdict gates at >=10 losses"` is not in the text, so a config edit to 10
still refuses.

### 2e. Is refusing on ANY disagreement operationally safe? — **Yes, and the brief says so; one consequence is mis-described.**

Blast radius (a) is correct and verified: `h6_watch.py:1027` is inside
`build_snapshot`, and `tools/daily_ritual.sh:448-449` wraps the watcher in
`|| crit`. A refusal therefore takes the daily ritual to `crit` and stops the
H6 receipt. Fail-closed is the right posture for a scorer that cannot prove its
bar. The blast radius is bounded: H6 only, and the ops checkout does carry the
ledger (N14).

The consequence rev 2 mis-describes is what happens on a *legitimate* owner
amendment — see N10.

---

## 3. Ruling on the brief's open question 1

> **"Is 'config proposes, registration vetoes' an acceptable framing of the binding?"**

**Ruling: the mechanism is sound and worth building, but it is a refusal guard,
not a binding, and the brief must be retitled to say so.**

Reasoning, stated as plainly as I can:

1. **What "binding" means in this repo is already settled by H7.** At
   `h7_forward_scoring.py:357-359, 374`, the number the scorer uses is *lifted
   out of* the sealed record: `min_losses_for_verdict = stage_bar`, where
   `stage_bar = frozen["stage456_parameters"]["MIN_LOSSES_FOR_VERDICT"]`.
   Delete `config.MIN_LOSSES_FOR_VERDICT` from the file and H7 still scores
   correctly. That is a binding: the record is the source.
2. **Under WP-A the record is never the source.** The number still comes from
   `config.py`. The record contributes exactly one bit — accept or refuse.
   Delete the anchor check and the scorer keeps working, at whatever value
   `config.py` currently holds. A mechanism that supplies zero bits of the
   value is not what "bound to the registered ledger record" means to anyone
   who has read the H7 code.
3. **That does not make it worthless.** It closes the actual reported defect:
   today a lone `config.py` edit silently moves the verdict; after WP-A it
   refuses. Verified as real by the six anchors above. It is the strongest
   thing available without an amendment, and an amendment is correctly OUT.
4. **The brief already knows this — in the body.** WP-A.5's "Not claimed"
   bullet is exemplary: *"H7's value comes out of the record; here the value
   comes out of `config.py` and the record vetoes it. Say so plainly in the PR
   body; do not describe it as 'reading the bar from the ledger'."* That is the
   correct sentence. The problem is that it lives 300 lines below a **title
   that says the opposite**, and titles are what get quoted into PR bodies,
   status readouts, and the registry.

So: not a retitle-or-abandon dilemma. The work is right; the label is wrong.
Fix as N7.

---

## 4. Findings

### N1 — MUST-FIX. WP-E Group 1 contains a test that cannot fail on revert, making Acceptance 3 unsatisfiable

**Text at issue.** WP-E Group 1 header: *"**Each MUST fail if the production
binding is reverted.**"* Group 1 final row:
`test_h6_scoring_unchanged_when_config_and_registration_agree` — *"the happy
path at the real values still produces today's verdicts — guards against a
binding that refuses everything"*. Acceptance 3: *"**Every** WP-E Group 1
(binding proof) test fails when the production binding is reverted."*

**Evidence.** By construction that test asserts today's behaviour at today's
values. Revert the binding and the values still agree, so the test still
passes. It is a no-regression guard — a valuable one — but it is definitionally
incapable of failing on revert. This is round-1 finding 10's defect, moved into
the group that was created to fix round-1 finding 10.

**Concrete change.** Move it out of Group 1. Either into Group 2, or (better,
since it is not a tripwire either) create a third labelled group —
"Group 3 — no-regression guards, exempt from Acceptance 3" — and list it there.
Acceptance 3's "Every" then becomes true.

### N2 — MUST-FIX. Group 1's refusal-message test has unspecified scope and may also be revert-proof

**Text at issue.** Group 1 row 4:
`test_refusal_message_names_config_value_registration_text_and_seq` — *"the
refusal is diagnosable, not a bare raise"*.

**Evidence.** Round-1 finding 10's third bullet killed
`test_registration_record_hash_pin_refuses_on_mismatch` precisely because it
"exercises only the new module against a fixture. It cannot fail on a revert of
`h6_watch.py`, because it never calls `h6_watch`." Rev 2's row 4 has the same
shape and the brief does not say which surface it calls. Acceptance 3 demands a
revert demo against *"a deliberately reverted `h6_watch.py` read"* — a test
written against `registered_bars` alone would not fail it.

**Concrete change.** State that this test must go through `score_book` with a
disagreeing config and assert on the raised exception's message, not call the
lookup module directly. Otherwise move it to the exempt group.

### N3 — MUST-FIX. There is a **fourth** unbound live-config verdict read on the H6 hard-kill path, and Scope IN.1 makes a false exhaustive claim

**Text at issue.** Scope IN.1: *"`options_researcher/h6_watch.py` — **the
three** live-config verdict reads at `:710`, `:719`, `:826`"*. Section title:
*"The H6 defect — three live-config verdict reads, not two"*.

**Evidence.** `options_researcher/h6_watch.py:748`, inside `_hard_kill_v1`
(def `:731`):

```
748        if pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK
```

That constant (`config.py:344` = `2_000`) **defines what "a full-loss month"
means** for hard-kill v1 — it is the threshold the streak counter consumes via
`_has_consecutive_months` (`:750`), which `_hard_kill_versions` (`:779`) feeds
into `score_book`'s `REJECT` branch (`:802-803`). It is also interpolated into
the REJECT reason at `:808`. Setting it to `1` would make almost any losing
month a "full loss" and manufacture a `REJECT`; setting it to `10_000` would
make the v1 hard kill unreachable. This is exactly the defect class of round-1
finding 8, which rev 2 accepted.

It is *registered* and it **is anchorable** — I verified:

| Bound value | seq | Anchor from config | Result |
|---|---|---|---|
| `H6_MONTHLY_PREMIUM_AT_RISK` = 2000 | 6 | `f"USD {v:,} per calendar month"` → `"USD 2,000 per calendar month"` | **PASS** |
| same (H8 shared cap) | 11 | `f"USD {v} per calendar month"` → `"USD 2000 per calendar month"` | **PASS** |

(seq 6 "Sizing: total premium at risk <= USD 2,000 per calendar month"; seq 11
"combined H6+H8 premium at risk <= USD 2000 per calendar month".)

Two differences from the v2 date: it *is* already in `h6_config_snapshot`'s
declared surface (`h6_watch.py:908`), and it is read on non-verdict paths too
(`:384`, `:387`, `:582`, `:585` — sizing gates, not adjudication).

**Concrete change.** Add it as defect 4 with the `:748` / `:808` citations, add
the seq-6 anchor to WP-A.3's table, and bind the `_hard_kill_v1` threshold and
the `:808` interpolation to it in WP-B.1. If the owner prefers to keep it out,
say so explicitly with the reason — but "the three live-config verdict reads"
must stop being asserted as exhaustive either way. Round 1's own words apply:
*silence is not an option.*

### N4 — MUST-FIX. "No literal `2026-08-19` exists in any record" is false; the resume floors **are** partially anchorable, and WP-C.2 forbids finding out

**Text at issue.** WP-C.2: *"**They cannot be anchored**: seq 28 clause 5
(H10b) and seq 29 clause 5 (H5 …) define the floor as *the LATER of* two
derived dates, so **no literal `"2026-08-19"` exists in any record**. … **Do
not attempt a derivation check.**"* Repeated in "What H10b actually is".

**Evidence.** The literal is in the ledger, in a **hash-sealed structured
field** — the `timestamp` of both governing records:

- seq 28 — `"timestamp": "2026-08-19T01:05:33.937513+00:00"`
- seq 29 — `"timestamp": "2026-08-19T01:05:33.939961+00:00"`

Seq 28 clause 5 defines the floor as *"the LATER of (i) the first session
on/after the implementation landing and (ii) **this amendment's ledger append
date**"*. The amendment's ledger append date **is** that `timestamp` — and
`config.py:628`'s own comment confirms the correspondence: *"mechanical floor
per seq 28/29 clause 5; **append date 2026-08-18 ET**"* (2026-08-19T01:05 UTC =
2026-08-18 21:05 ET).

So clause 5's second term is machine-checkable from a typed field, and half the
derivation yields a real one-directional binding:

```
config.H10B_RESUME_FLOOR_SESSION >= <append date of seq 28>
config.H5_RESUME_FLOOR_SESSION   >= <append date of seq 29>
```

Both hold today (`"2026-08-19" >= "2026-08-19"` on UTC, `>= "2026-08-18"` on
ET). This is materially stronger than a literal tripwire — it is a check
against a **sealed typed field**, the very thing WP-A says these records do not
have — and it needs no prose parsing, no word forms, and no regex. Term (i)
("first session on/after the implementation landing") genuinely is not
checkable; the brief may state that and bound the check to term (ii).

**Concrete change.** Delete "no literal `2026-08-19` exists in any record" and
"Do not attempt a derivation check". Replace with: the append-date half of
clause 5 is bindable as a lower bound against seq 28 / seq 29 `timestamp`;
specify the timezone convention explicitly (UTC date of the timestamp, or the
ET date per `config.py:628`'s comment — pick one and write it down); the
implementation-landing half remains uncheckable and is disclosed. Keep the
literal tripwire as an additional Group 2 test if desired. Note the claim-
discipline angle: this is an unlabelled flat assertion inside a work package
that a five-line script disproves.

### N5 — MUST-FIX. WP-A.6's memoisation is ambiguous in a way that can silently disable the entire binding

**Text at issue.** WP-A.6: *"**Caching.** Read and verify **once per process**,
memoised, so a scoring run does not re-verify the chain per call."*

**Evidence.** Two readings, with opposite consequences:

- *Memoise the verified record set only, re-evaluate anchors per call against
  the live `config` value.* Correct. Every WP-E Group 1 test's
  `mock.patch.object(config, …)` is observed and refuses.
- *Memoise the resolved bar value.* Catastrophic. After the first successful
  lookup in a process, later `config` patches are invisible — Group 1's three
  refusal tests would not refuse (outcome depending on test execution order
  within the shared `unittest discover` process), and in production a config
  change taking effect after the first scoring call in a long-lived process
  would go unchecked. This is the same failure shape as the
  `h7_scoring_identity.py:190-208` F3 defect the brief itself cites approvingly
  — a convenience that "silently reintroduces exactly the contradiction" the
  work exists to close.

The brief gives the executor no way to tell which is meant, and Acceptance does
not disambiguate.

**Concrete change.** Rewrite WP-A.6 as: cache **only** the `verify()` result
and the parsed record bodies, keyed on `base_dir`; the anchor comparison is
re-evaluated on **every** call against the live `config` attribute; add an
Acceptance condition that a second `score_book` call in the same process, with
`config` patched between the two calls, refuses on the second.

### N6 — MUST-FIX. The WP-E fixture instruction is not implementable as specified, and the cited precedent does not transfer

**Text at issue.** WP-E Fixtures: *"Every refusal test builds a **fixture ledger
in a `tempfile.TemporaryDirectory()`** and points the lookup's `base_dir` at it
— the shape `tests/test_h7_forward_scoring.py:39-57` (`ScoringCase.setUp`)
uses. **No test may read, write, or mutate the real `ledger/experiments.jsonl`**,
except the Group 2 anchor tests."*

**Evidence.**

1. `verify()` requires `rec["seq"] == index` (`research/ledger.py:553-554`). A
   fixture whose lookup targets **seq 22** must therefore contain **23**
   chain-valid records; seq 16 needs 17; seq 6 needs 7.
2. Each must survive `_verify_semantic_records` (`:347`), which enforces
   `entry_type in VALID_ENTRY_TYPES`, `_reject_unknown_fields`, and a running
   `trial_count` that must match exactly (`:370-374`), plus per-type required
   fields (`_require_timestamp`, `_require_canonical_text`, …).
3. `HEAD` must equal the chain tip (`:562-563`).
4. The cited precedent is a **different store with a different API**: H7 uses
   `ledger.read_events` over `ledger/h7_forward/events.jsonl` and
   `ScoringCase.setUp` appends **one** synthetic `window_registration`. None of
   the seq-equals-index or `trial_count` machinery applies there.

Meanwhile the simplest correct Group 1 test does not need a fixture at all: the
refusal comes from the **patched config value**, not from a fabricated record,
so patching `config` and reading the real ledger read-only (exactly as
`tests/test_h10_config.py:7` `_load_registration` already does) produces the
refusal with no fixture. The brief's blanket prohibition forecloses that.

**Concrete change.** Either (a) permit Group 1 refusal tests to read the real
`ledger/experiments.jsonl` **read-only**, with the existing
`tests/test_h10_config.py:7` reader named as the precedent and the no-write rule
kept absolute; or (b) if fixtures are required, specify a helper that builds the
chain through `research.ledger.append` (`research/ledger.py:516`) and state the
seq-equals-index and `trial_count` constraints up front so the executor does not
burn a round trip discovering them.

### N7 — MUST-FIX. The title and the registry row overclaim; rename per the §3 ruling

**Text at issue.** Title: *"Codex brief 42 — **Bind** H6/H8/H10b verdict bars
and hard-kill triggers **to the registered ledger record**"*. Registry row 42:
*"Bind H6/H8/H10b verdict bars, hard-kill counts and resume floors to the
registered ledger record"*. Opening summary: *"Three lanes are in scope"* under
the same framing.

**Evidence.** §3 above. WP-A.5's own "Not claimed" bullet contradicts the title.
`.cursorrules` Claim discipline forbids exactly this gap between headline and
mechanism, and it was round-1 blocker 2's substance.

**Concrete change.** Retitle to something the mechanism delivers, e.g.
*"Refuse H6/H8/H10b verdicts when `config.py` disagrees with the registered
ledger record"*. Update `docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md` row 42
to match (description only; the reservation and number are unchanged). Promote
WP-A.5's "Not claimed" bullet into the "Why this exists" section so the honest
statement is read before the work packages, not after them. Note the filename
slug (`-verdict-bar-ledger-binding-`) may stay as-is — renaming a reserved file
is forbidden by the brief's own Explicitly-forbidden list.

### N8 — SHOULD-FIX. `verify()`'s `anchored` parameter is unspecified

**Text at issue.** WP-A.1: *"call `research.ledger.verify(base_dir=...)`
first."*

**Evidence.** The real signature is
`verify(base_dir="ledger", anchored=False, git_clean_tracked=None)`
(`research/ledger.py:549`). With `anchored=True`, `:564-565` calls
`_require_committed_clean`, which is the only check that would catch a
working-tree rewrite of the whole chain (§2c step 3). With the default it is
omitted. Fixtures under `tempfile` cannot satisfy `anchored=True`; the
production path arguably should.

**Concrete change.** State the choice and the reason. Suggested: production
lookup uses the default (`anchored=False`) because the ritual must not depend on
git state, and the working-tree threat is covered by the `block_ledger_edits`
hook plus git history — but say that, rather than leaving a security-relevant
parameter to executor default.

### N9 — SHOULD-FIX. The anchors are format-coupled and the brief never says so

**Evidence.** The same value `2000` appears as **"USD 2,000"** in seq 6 and
**"USD 2000"** in seq 11 (both verified in N3). So the f-string format spec
(`{v}` vs `{v:,}` vs `{v:,.0f}`) is a per-record choice the executor must get
right, and it sits uncomfortably beside the Explicitly-forbidden line
*"Parsing, interpreting, or normalising registration prose beyond exact
substring membership"*. The six WP-A.3 anchors happen to be plain `{v}`, so
nothing breaks today — but N3's new anchor is the first one that needs a format
spec, and a future maintainer has no rule to follow.

**Concrete change.** Add one sentence to WP-A.3: each anchor template, including
its format spec, is fixed in the module as a literal per `(seq, config-name)`
pair, verified once at brief-writing time; adding a new anchor requires
re-verifying it against the record and recording the PASS in the brief.

### N10 — SHOULD-FIX. WP-A.5 mis-describes what a legitimate future amendment does

**Text at issue.** WP-A.5, "Does not bind": *"It also does not prevent an
owner-authorized future amendment from changing the rule — that is correct
behavior, not a gap."*

**Evidence.** The actual behaviour is the opposite of what that sentence
suggests to a reader. Because the anchors are pinned to fixed seq numbers, an
owner amendment that changes a bar — appended at a *new* seq, with `config.py`
updated to the new value — makes the **old** seq's anchor fail, and by WP-A.5
the scorer refuses. Via blast radius (a), the daily ritual goes to `crit` on the
next run and stays there until a code change lands. This is not hypothetical:
seq 22 is exactly such an amendment, and its word form already broke one anchor
(WP-A.4).

That fail-closed outcome is arguably correct. But it is an operational trap the
owner must be told about before the first amendment, not after the first `crit`.

**Concrete change.** Replace the sentence with: an owner-authorized amendment
that changes a bound value will cause a refusal — and a ritual `crit` — until
the module's `(seq, anchor)` table is updated in a follow-up change. Add that to
Blast radius as item (e), and add a line to the PR body requirement.

### N11 — SHOULD-FIX. Acceptance 8's grep is under-scoped

**Text at issue.** Acceptance 8: *"Demonstrate with
`grep -nE '\b(8|3|7)\b|2026-08-03' options_researcher/registered_bars.py`
returning only `seq` integers."*

**Evidence.** It misses `2000` / `2_000` (needed once N3's anchor is added),
misses spelled-out numbers ("three"), misses `"2026-08-19"` (relevant under
N4), and hard-codes today's values so it silently stops testing anything if a
value ever changes. Also note it cannot actually return "only `seq` integers" —
the seq values are 6, 11, 16, 22 and none of them match `\b(8|3|7)\b`, so a
clean module returns **nothing**. The stated expected output is wrong.

**Concrete change.** Extend the alternation to
`\b(8|3|7|2000|2_000)\b|2026-08-03|2026-08-19`, state that the expected result
is **no matches**, and add a plain-language condition: a reviewer reading the
module finds no copy of any verdict number.

### N12 — SHOULD-FIX. WP-B.2 and Acceptance 10 prescribe two different executor behaviours for an unruled D-1

**Text at issue.** WP-B.2: *"If no ruling is recorded: **stop and report.** Do
not pick."* Acceptance 10: *"…the PR body states 'D-1 unruled; WP-B.2 skipped
with reason'. Codex **stops and reports** rather than choosing a branch."*

**Evidence.** "Stop and report" in this repo's convention halts the work
(cf. `reports/2026-09-09-brief-41-codex-stop-report.md`). But Acceptance 10
assumes a PR exists with a body — i.e. that Codex skipped WP-B.2 and completed
everything else. Those are different instructions. Additionally, nothing says
**who** records a D-1 ruling or **where**: the brief is read from `origin/main`
and Codex may not edit it (and per `CLAUDE.md:53` the H8 disposition is an owner
call), so the ruling has to arrive some other way that the brief never names.

**Concrete change.** Say plainly: an unruled D-1 means WP-B.2 is **skipped, not
halted** — the rest of the brief completes and the PR body records the skip
(this is what Acceptance 10 checks). Add: a D-1 ruling reaches Codex only as an
owner-recorded amendment to this brief file on `origin/main`, or an owner
message at dispatch; Codex never infers one.

### N13 — NOTE. WP-A.2's duplicate-seq defence is redundant, and saying so strengthens the brief

`verify()` at `:553-554` already guarantees one record per seq with
seq == index, so *"Refuse on a duplicate or missing seq rather than taking the
first match"* can never fire after a successful `verify()`. Keep the code — it
is cheap and correct — but state that the uniqueness guarantee comes from
`verify()`, so a reader does not mistake the defensive check for the load-
bearing one. This is the full answer to round-1 finding 2's attack (b) and it
should be recorded.

### N14 — NOTE. Open question 4 is answered: the ops checkout carries the ledger, chain-intact

Checked directly at `/Users/carsynstephenson/options-validator-ops`:

- `ledger/experiments.jsonl` present, 32 records, max `seq` 31
- `ledger/HEAD` present and equal to the last record's `record_hash`
- the full `record_hash` sequence is **byte-identical** to the audit worktree's

So WP-A's new runtime read is satisfied there today, and blast radius (b) can be
upgraded from "Codex must confirm" to **Repo-verified 2026-09-15**. One caveat
worth writing down: the ops checkout is at `a3745ab`, behind `f228894`, so its
`ledger/` can lag `main` — and `verify()` proves *internal consistency*, never
*freshness*. Harmless for seq 6/11/16/22, which are frozen, but it interacts
with N10: after an amendment, ops could hold a ledger that disagrees with a
newly-synced `config.py`.

### N15 — NOTE. Guardrails: clean, with one cosmetic header deviation

- `.agents/skills/codex-brief-writing/SKILL.md` requires the header *"in order:
  **Date**; **Author**; **Executor**; **Status**; **Provenance**"*. Rev 2 inserts
  **Revision** between Status and Provenance. The five required fields are all
  present in the required relative order; the insertion is not forbidden.
  Cosmetic only — flagging so a later reviewer does not re-raise it.
- Status line is verbatim the required string: *"DRAFT — pending independent
  adversarial review before hand-off"*. ✔
- Body order (Why this exists → Scope → Work packages → Acceptance) is preserved
  with insertions between. ✔ Claim-discipline labels (Repo-verified / Inference /
  Assumption) are used throughout, with the exceptions called out in N4. ✔
  Prior finding IDs cited verbatim. ✔
- `docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md` row 42 is reserved to this
  file with the correct path and provenance; no conflict; the brief correctly
  forbids resolving one. ✔ (Description needs the N7 rename.)
- `.claude/rules/ledger.md`: the OUT list's reading remains accurate — all four
  chained paths plus `facts.log` forbidden, `block_ledger_edits` block treated as
  correct. ✔
- `CLAUDE.md:53` division of labor: satisfied. No frozen number is typed by the
  executor; no registration, amendment, or verdict is created. ✔
- `.cursorrules`: "Every number in strategy logic comes from `config.py`" ✔;
  draft-PR authority hold ✔ (Acceptance 13 + Explicitly forbidden); validator-only
  / no-look-ahead / conservative-fills untouched ✔. Claim discipline is the one
  place rev 2 still trips — N4 and N7.
- Hand-off ordering relative to PR #175: **correct**. PR #175 is OPEN, draft,
  head `claude/audit-2026-09-15`; the brief is untracked on that branch; rev 2
  requires Codex to read from `origin/main` only after #175 merges (or an
  owner-named SHA), to confirm the Revision line, and to work in a fresh
  worktree. This is the lesson from brief 41's stop-report, correctly applied.
  Brief 42 does not touch `tools/daily_ritual.sh`, so blast radius (d)'s
  "sequencing only, no registry collision" is right.

---

## 5. Verdict

**PASS WITH FIXES.**

The three round-1 blockers are substantively dead. I attacked the replacement
mechanism rather than reading it: `verify()` really does recompute every
record's hash over its body (`research/ledger.py:557-559`), so the prose it
authorises is genuinely sealed against any partial edit; all six WP-A.3 anchors
pass when built from the live config values and the seq-22 word form fails
exactly as the brief says; the anchor is not spoofable by another record because
`verify()` pins seq to list index; and refusing on disagreement is operationally
bounded — H6 only, fail-closed into a `crit` the brief now documents, on an ops
checkout that I confirmed carries the chain intact. Every ledger `seq` citation
that was wrong in rev 1 is now right, the hand-off ordering against PR #175 is
correct, and the executor no longer types a frozen number anywhere.

It is not a clean pass. Seven MUST-FIX items remain, and three of them matter.
The brief's scope claim "the three live-config verdict reads" is still not
exhaustive — `h6_watch.py:748` reads `H6_MONTHLY_PREMIUM_AT_RISK` to decide what
a full-loss month *is*, which is the same defect class as the v2 date that round
1 caught, and it is anchorable in seq 6. WP-C.2 asserts, unlabelled, that "no
literal `2026-08-19` exists in any record" and forbids looking; the literal is
sitting in seq 28's and seq 29's hash-sealed `timestamp` field, and a real
lower-bound binding against a typed field — the thing the brief says these
records do not offer — is available and forbidden by the text. And WP-A.6's
one-word ambiguity about *what* is memoised is the difference between a binding
that checks every call and one that checks once per process, with WP-E's own
refusal tests as the collateral.

None of that is a redesign. The mechanism survived the attack; the writing
around it has not caught up in three places. Fix N1–N7, apply the §3 retitle so
the headline stops promising H7-grade sourcing the design does not deliver, and
this is ready to hand off.
