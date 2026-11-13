# Brief 42 — independent adversarial review (round 1)

**Target:** `docs/superpowers/plans/2026-09-15-42-verdict-bar-ledger-binding-codex-brief.md` (DRAFT)
**Reviewer:** independent Claude session, read-only except this file
**Ref:** branch `claude/audit-2026-09-15`, `git rev-parse --short HEAD` = `f228894` (the same commit the brief claims)
**Stance:** adversarial. Nothing below is a confirmation that the brief works.

**Verdict: FAIL.** Reason in the verdict line at the end.

---

## 0. Citation re-verification summary

Every `file:line` in the brief was re-read at `f228894`. **Code citations are almost
all correct.** The failures are concentrated in the **ledger `seq` citations**, which
is the worst possible place for them, because WP-A and WP-C tell Codex to bind code to
those exact seq numbers.

Verified correct (spot list, not exhaustive): `h6_watch.py:719`, `:806`, `:813`, `:826`,
`:832`; `h6_watch.py:164` (`H6Score`), `:792` (`score_book`), `:898` + `:913-914`
(`h6_config_snapshot` surface); `config.py:349,350,383,384,625,629,630`;
`tests/test_h6_watch.py:493` and body ending `:513-514`;
`tests/test_ritual_switch_on_hash_containment.py:357` + docstring `:358-366`;
`tests/test_h10_config.py:29,46`; `h10_watch.py:35-37`, `:541`; `entry_watch.py:223`;
`h7_forward_scoring.py:343, 350-355, 367-373, 374, 92, 108-109, 126`;
`h7_scoring_identity.py:190-208`; `tests/test_h7_forward_scoring.py:326`;
`h8_watch.py:365,586,614,853` and `grep -c score h8_watch.py` → `0`;
`H10_MIN_LOSSES_FOR_VERDICT` grep hits exactly the four the brief lists; the three
`record_hash` values for seq 6 / 11 / 16 match the file byte-for-byte.

Wrong or misleading citations are findings **5, 6, 7, 8, 9** below.

---

## 1. BLOCKER — The record-hash pin does not seal anything; it compares a self-reported field to a constant

**Brief text (WP-A.1c):** "verifies the selected record's `record_hash` equals a pinned
constant (the three hashes in the table). A mismatch is a **typed refusal** … **This is
what makes the pin meaningful: the registration text cannot change under the code
without the code noticing.**"

**Evidence.** `record_hash` is a *field stored inside the record itself*
(`research/ledger.py:162` `_record_hash(record_without_hash)` computes it; `read_all`
at `research/ledger.py:141` returns raw dicts and does **not** recompute it; chain
verification lives in `research/ledger.py:549` `verify()` and
`:347` `_verify_semantic_records`). Reading `rec["record_hash"]` and comparing it to a
pinned string proves only that the *hash field* was not changed. Edit the `reason`
prose of seq 6 and leave `record_hash` alone and the pin passes, silently. That is the
exact failure mode the brief says the pin prevents.

The brief's own OUT list even concedes the file is a hash chain "written only through
their typed APIs" — but WP-A.1 reaches around that API and reads the field directly.

**Concrete change.** WP-A.1c must require **recomputation**, not field equality:
call `research.ledger.verify(base_dir=...)` (chain integrity) **and** recompute the
record's hash over its body (the private `research.ledger._record_hash`, or a new
public wrapper) and compare *that* to the pinned constant. Refuse on either failure.
State plainly in the brief that a bare `rec["record_hash"] == PIN` check is
insufficient and is not an acceptable simplification.

---

## 2. BLOCKER — WP-A is a constant-vs-constant check, not a ledger binding, and the brief describes it as the opposite

**Brief text (WP-A.4):** "**Config becomes the thing that is checked, not the thing that
is trusted.** The lookup compares the registered value against the corresponding
`config.py` constant and **refuses** on disagreement."
**And (WP-A.2):** "Because the record states them in prose, the module carries them as
named constants adjacent to the pinned hash."

**Attack.** Trace where the number actually comes from under WP-A as specified:

1. `config.H6_MIN_COMPLETED_POSITIONS = 8` — a Python constant.
2. `registered_bars.H6_SAMPLE_BAR = 8` — a *second* Python constant, hand-transcribed
   by the executor.
3. The record is opened, and a hash field is compared to a string.

**Nothing at any point compares `8` to the registration's prose.** The record supplies
zero bits of the value. The brief's plain-language opening says the defect is that the
code "does not read the ledger. It reads today's value out of `config.py`." After
WP-A, the code **still does not read the bar from the ledger**; it reads it from a
duplicate of `config.py` sitting in a new file. Answering the review question directly:
it is not a tautology in the trivial sense — a *lone* edit to `config.py:349` now
refuses — but it is a **drift detector between two executor-maintained copies**, and
the brief markets it as a registration binding.

**What happens if `config.py` changes:** a lone edit refuses (good). A *coordinated*
edit to both `config.py:349` and the new module's constant follows silently (the
defect, unchanged). Both are ordinary code edits with no ledger gate, no owner typing,
and no hook. Compare H7, where the number is literally `frozen["stage456_parameters"]
["MIN_LOSSES_FOR_VERDICT"]` inside the sealed event payload (`h7_forward_scoring.py:358`)
— there is no second copy to coordinate with.

**Could the pin be satisfied by a wrong record?** Yes, two ways: (a) finding 1 above
(prose edited, hash field untouched); (b) the seq→hash pairing is asserted by the
executor, and `read_all` returns a plain list — if two records ever carry the same
`seq`, or the file is truncated above seq 6, nothing in WP-A cross-checks
`entry_type == "trial_intent"` or `hypothesis_id == "H6"` before trusting the row.

**Safer design, fully inside the brief's OUT list (no ledger write, no amendment, no
frozen-value change).** Derive the check from the record's own text instead of a
transcribed constant:

- Read seq 6 / 11 / 16 via `research.ledger.read_all`, with `verify()` + recomputed
  record hash as the seal (finding 1).
- **Assert the config value against the registration prose by exact substring**, and
  refuse if the substring is absent:
  - H6 seq 6 — require `f"after {config.H6_MIN_COMPLETED_POSITIONS} completed positions"`
    in `reason` (the record reads "REJECTS H6: after 8 completed positions, …") and
    `f"hard kill regardless: {config.H6_HARD_KILL_FULL_LOSS_MONTHS} consecutive calendar months"`.
  - H8 seq 11 — same two clauses, verbatim from that record.
  - H10b seq 16 — require `f"verdict gates at >={config.H10_MIN_LOSSES_FOR_VERDICT} losses"`.
- No new numeric constant is typed by anyone. `config.py` stays the single source of
  the value (satisfying `.cursorrules` "Every number in strategy logic comes from
  `config.py`. No magic numbers."), and the **owner-authored registration text** is what
  ratifies it. A config edit 8→5 now fails because `"after 5 completed positions"` is
  not in the record — the registration, not a duplicate, is doing the refusing.

**This pattern already exists in the repo and the brief does not cite it:**
`tests/test_h10_config.py:7` `_load_registration(seq)` reads
`ledger/experiments.jsonl` by seq, and `:50-51` anchor config values against the
registration text with `assertIn`. WP-C.1 proposes to "strengthen" this very test
without noticing that it is already the better mechanism.

---

## 3. BLOCKER — WP-A.4 (refuse on mismatch) and WP-E's first two named tests are mutually unsatisfiable

**Brief text (WP-E table):**
`test_h6_sample_bar_binds_to_registered_seq6` — "with config patched away from 8, H6's
`INSUFFICIENT_SAMPLE` boundary **follows the registration**";
`test_h6_hard_kill_months_binds_to_registered_seq6` — "with config patched to 2, a
two-month full-loss book does **not** hard-kill".

**Attack.** WP-A.4 says a config/registration disagreement is a **refusal**. Under a
refusal, `score_book` raises; there is no `INSUFFICIENT_SAMPLE` boundary to observe and
no `hard_kill=False` to assert. You cannot simultaneously *follow the registration* and
*refuse*. WP-D.1 then hands the contradiction to the executor to resolve —
"assert the scorer either still requires 3 … or refuses … **whichever the WP-A design
produces**" — which is the brief delegating a semantics decision it elsewhere forbids.

**Concrete change.** Pick one and make the whole brief consistent. Recommended:
**refuse** (it is the honest behaviour and matches H7 at `h7_forward_scoring.py:367-373`).
Then rewrite the two WP-E rows as refusal assertions, delete "whichever the WP-A design
produces" from WP-D.1, and state the chosen semantics once in WP-A.4 as binding on all
downstream WPs.

---

## 4. MUST-FIX — Refusal lands on the daily ritual and the brief never says so

**Brief text:** the entire brief; there is no operational blast-radius section.

**Evidence.** `h6_watch.py:1027` — `"score": score_book(book).to_dict()` inside
`build_snapshot`; `tools/daily_ritual.sh:448-449` runs
`options_researcher.h6_watch --as-of … --write-receipt reports/h6_forward/${AS_OF}.json`
with `|| crit "h6_watch: NONZERO EXIT"`. So a WP-A refusal does not merely fail a test —
it takes the **daily ritual to `crit`** and stops the H6 receipt being written. WP-A also
introduces a **new runtime dependency**: `h6_watch` would now require
`ledger/experiments.jsonl` to be present and chain-intact in the ops checkout on every
scoring run, which it does not today.

**Concrete change.** Add a "Blast radius" subsection stating (a) refusal surfaces as
`crit` in `tools/daily_ritual.sh:449`, and that this is intended fail-closed behaviour;
(b) the new ledger-read dependency on the ops checkout, and what happens if the file is
missing there; (c) whether the lookup is cached per process or re-read per call.

---

## 5. MUST-FIX — Seq 28 is H10b, not "A2-v1", and `H10B_AMENDMENT_V1_1` is seq 28, not the "seq 29/30 pair"

**Brief text (Verified facts → registration records):** "H10b seq 28 (`A2-v1`, **not
H10b** — see the note below) and seq 29 / seq 30 (the **H10B_AMENDMENT_V1_1 pair**,
observation resumption + Schwab data substitution)".

**Evidence** (`ledger/experiments.jsonl` at `f228894`):
- seq 28 — `hypothesis_id: "H10b"`, `reason` begins `H10B_AMENDMENT_V1_1 2026-08-16/17:
  owner-directed pre-result amendment to H10b (seq 16)`.
- seq 29 — `hypothesis_id: null`, `reason` begins `H5_AMENDMENT_V1 … amendment to H5
  (ledger seq 5)`.
- seq 30 — `hypothesis_id: "H10b"`, `reason` begins `H10B_H5_AMENDMENT_CORRECTION_V1
  2026-08-18: append-only factual correction to seq 28 … and seq 29 …`.
- Corroborated by `reports/2026-09-15-audit/A-evidence-audit.md:27`: "**H10b (16,28,30)**".

The brief has the H10b amendment attributed to the wrong records and invents an
"A2-v1" identity for seq 28 that the record does not carry (A2-v1 is a separate lane,
memo A line 69 item 9).

**Concrete change.** Rewrite the amendments-in-force line as: H10b seq 28
(`H10B_AMENDMENT_V1_1`), seq 30 (`H10B_H5_AMENDMENT_CORRECTION_V1`, correcting seq 28
and seq 29); H5 seq 29 (`H5_AMENDMENT_V1`). Delete the "A2-v1" claim.

---

## 6. MUST-FIX — WP-C.2 sends Codex to a clause that does not exist (seq 30 has no clause 5), and contradicts the repo's own comment

**Brief text (WP-C.2):** "Add a value pin test for both, bound to the **seq 29/30
amendment clause-5** mechanical floor."

**Evidence.** The floor clauses are **seq 28 clause 5** ("Implementation gate + hard
no-backfill floor … A frozen constant `H10B_RESUME_FLOOR_SESSION` = the LATER of (i)
the first session on/after the implementation landing and (ii) this amendment's ledger
append date") and **seq 29 clause 5** ("Identical mechanism to H10B clause 5
(`H5_RESUME_FLOOR_SESSION`, refusal + test)"). Seq 30 is a correction record about IV
normalization with no clause 5. `config.py:628`'s own in-file comment — which the
brief quotes elsewhere — says "**mechanical floor per seq 28/29 clause 5**". The brief
contradicts the line it cites.

**Concrete change.** `seq 29/30` → `seq 28 clause 5 (H10b) and seq 29 clause 5 (H5)`.

---

## 7. MUST-FIX — Seq 22 is mislabelled, and "none of them changes a bar" is not true

**Brief text:** "H6 seq 22 (2026-08-02, **exit-month/full-cap rule**, prospective only)"
and "Amendments in force … **none of them changes a bar**".

**Evidence.** Seq 22 is `H6_KILL_V2`: "Cohorts are H6-only calendar **entry** months …
aggregate exit proceeds equal zero relative to the actually deployed premium … **Three
consecutive full-loss calendar entry cohorts trigger H6 rejection.** Existing H6 rows
retain **v1 exit-month and full-cap** semantics." The exit-month/full-cap rule is the
*v1* rule that seq 22 preserves for old rows; seq 22 introduces a **different** rule.
It changes when `REJECT` fires — i.e. it changes the hard-kill half of the bar,
prospectively. It also states the month count ("Three consecutive") a **second time, in
a different record**.

**Concrete change.** Relabel seq 22 as the prospective entry-cohort zero-proceeds
hard-kill (v2). Replace "none of them changes a bar" with an accurate statement.

---

## 8. MUST-FIX — The H6 v2 path is a live-config verdict read the brief leaves untouched, inside its own core target

**Brief text (Scope IN.1):** "`options_researcher/h6_watch.py` — the two live-config
reads at `:719` and `:826`".

**Evidence.** There is a **third** verdict-affecting live-config read on the H6 scoring
path: `h6_watch.py:710` — `effective = date.fromisoformat(config.H6_KILL_V2_EFFECTIVE_ENTRY_DATE)`
(`config.py:354` = `"2026-08-03"`), called by both `_hard_kill_v1` (`:732`) and
`_hard_kill_v2` (`:754`), which `_hard_kill_versions` (`:779`) feeds straight into
`score_book`'s `REJECT` branch (call at `:802`, branch at `:803`). Editing that date to `2030-01-01` silently
disables the v2 hard kill and re-enables v1 over the whole book. It is registered in
seq 22, it is **not** in `h6_config_snapshot`'s "explicit verdict-affecting H6
configuration surface" (`h6_watch.py:900-922`), and it is **not** in the brief.

Worse, there is a semantic defect: `_has_consecutive_months` (`:718`) is **shared by v1
and v2**. If WP-B.1 binds `required` to seq 6, the seq-6-derived value is then applied
to the v2 rule registered at **seq 22**. That is a record/rule mismatch the brief
creates rather than fixes.

**Evidence the repo already knows the answer:** `config.py:355`
`H6_KILL_V2_TRIAL_INTENT_HASH = "4c5526…"` is *already* a record-hash pin to seq 22,
consumed at `h6_watch.py:1065` (receipt) and `:1199` (receipt verification). The brief
presents the record-hash pin as a new invention and never cites the existing one.

**Concrete change.** Either (a) add `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` to scope and bind
it to seq 22 (citing the existing `H6_KILL_V2_TRIAL_INTENT_HASH` precedent), and bind
the shared month count to **both** seq 6 and seq 22 (seq 22 says "Three" in words, so
say explicitly whether word-form is in scope or is a stop-and-report); or (b) declare
v2 explicitly OUT with the reason written down. Silence is not an option — the brief
otherwise ships an H6 "bound" scorer with an unbound trigger in it.

---

## 9. SHOULD-FIX — Three smaller citation defects

- **`_synthetic_base` is an activation guard, not test-fixture evidence.** Brief:
  "*(Inference on the fixture approach; **Repo-verified that the H7 tests use a
  synthetic base** — `h7_forward_scoring._synthetic_base`, `h7_forward_scoring.py:345`)*".
  `:345` is a **call site**; the definition is `:44-54`, and it is a *production*
  `ActivationBoundaryError` guard that refuses `REAL_FORWARD_STORE`. It says nothing
  about how the tests build fixtures. Cite `tests/test_h7_forward_scoring.py`'s
  `ScoringCase` setup instead, or drop the Repo-verified label.
- **"the existing typed reader in `research/ledger.py`" is not typed, and `:138` is
  private.** `read_all` (`:141`) returns `list[dict]`; `_paths` (`:136-138`) is private.
  Say "`research.ledger.read_all` (untyped `list[dict]`) plus `verify()`" and stop
  calling it typed — the brief's whole framing leans on H7's *typed* read being the
  gold standard, and this is not that.
- **H7 field lines are off by one.** Brief cites `:356-359` for
  `frozen` / `stage_bar` / `scorer_bar`; actual: `:356` is `registered_window`,
  `:357` `frozen`, `:358` `stage_bar`, `:359` `scorer_bar`. Memo A already cites
  `:358-359` correctly.

---

## 10. MUST-FIX — Three of the seven WP-E tests cannot satisfy acceptance criterion 2

**Brief text (Acceptance 2):** "Every test named in WP-E … **fails if the binding is
reverted** … A test that passes both before and after the fix proves nothing."

**Attack.** Check each against today's code:
- `test_h10b_loss_bar_pinned_to_registered_seq16` — `config.H10_MIN_LOSSES_FOR_VERDICT`
  is 7 and seq 16 says 7, so it passes at `f228894` with **no** production change. It
  also near-duplicates `tests/test_h10_config.py:46`. Cannot fail on revert.
- `test_resume_floors_are_value_pinned` — pure literal assertion on `config.py:629-630`.
  Passes before and after. It is a change tripwire, not a binding proof.
- `test_registration_record_hash_pin_refuses_on_mismatch` — exercises only the new
  module against a fixture. It cannot fail on a revert of `h6_watch.py`, because it
  never calls `h6_watch`.

So acceptance 1 ("no test skipped") + acceptance 2 ("every WP-E test fails on revert")
are jointly unsatisfiable as written, and the executor will have to fudge one.

**Concrete change.** Split the WP-E table into **binding proofs** (must fail on revert:
the two H6 rows + the config-override refusal) and **regression tripwires** (explicitly
exempt from acceptance 2, and labelled as tripwires, not bindings, in the PR body).
Narrow acceptance 2 to the binding-proof rows.

---

## 11. MUST-FIX — "Stop and report" on OWNER DECISION D-1 is prose only; nothing enforces it, and WP-E pressures Codex to pick

**Brief text (WP-B.2):** "*If no ruling is recorded:* **stop and report.** Do not pick."
**But (WP-E table):** a `test_h8_*` row is listed unconditionally, "name per D-1 branch".
**And (Acceptance 1):** full suite green, "no test skipped or xfailed".

**Attack.** The Acceptance section — the part the brief itself says "defines done" —
contains **zero** references to D-1. A row exists in the required-tests table for H8
regardless of the ruling. An executor optimizing for a complete acceptance checklist has
every incentive to pick a branch. D-1b compounds this: "a typed refusal on **any H8
adjudication attempt**" requires inventing an entry point that does not exist
(`grep -c score h8_watch.py` → 0) — its name, its signature, and its call sites are all
executor inventions, i.e. exactly the "H8 scorer semantics" the brief forbids.

**Concrete change.** (a) Add to Acceptance: "If D-1 is unruled, `git diff --name-only`
contains **no** `options_researcher/h8_watch.py` and no `tests/test_h8_*`, and the PR
body states D-1 is unruled." (b) Mark the WP-E H8 row **CONDITIONAL — omit entirely if
unruled**. (c) For D-1b, name the exact function and call site the refusal goes in, or
convert D-1b to a documentation-only disposition.

---

## 12. MUST-FIX — WP-A.2 has the executor typing a frozen number, against CLAUDE.md and `.cursorrules`

**Brief text (WP-A.2):** "the module carries them as named constants … They are: H6
sample bar 8, H6 hard-kill months 3, H8 sample bar 8, H8 hard-kill months 3, H10b loss
bar 7. **These are not new numbers** — every one already equals the current `config.py`
value … so this introduces no frozen-number change."

**Guardrails hit.**
- `CLAUDE.md:53` (Division of labor): "**The owner types every frozen number**, new
  registration, and verdict ratification." The 2026-07-25 delegation amendment
  (`CLAUDE.md:54-58`) covers *amendments to already-registered specs* — it does **not**
  cover typing frozen numbers.
- `.cursorrules` (Engineering rules): "**Every number in strategy logic comes from
  `config.py`. No magic numbers.**" WP-A.2 creates a second home for five verdict
  numbers outside `config.py`.
- `.cursorrules` (Claim discipline / Vocabulary discipline): "Config becomes the thing
  that is **checked, not the thing that is trusted**" and "This is what makes the pin
  meaningful" are unlabelled assertions that findings 1 and 2 show to be false.

The brief's own open question 1 anticipates this. **Answer: not acceptable.** And the
fix is not "get owner sign-off on the transcription" — it is to delete the
transcription, per the prose-anchor design in finding 2, which removes the second copy
entirely and therefore needs no owner typing at all.

**Concrete change.** Replace WP-A.2 with the prose-anchor mechanism. Delete the
"owner-ratifiable transcription" framing. Downgrade the WP-A.4 sentence to something
defensible, e.g. "a lone `config.py` edit that disagrees with the registration text is
refused".

Other guardrails checked and **not** violated: `.claude/rules/ledger.md` (the OUT list
correctly forbids all writes under `ledger/` including `facts.log`, and correctly treats
a `block_ledger_edits` block as correct); `.cursorrules` draft-PR authority hold
(acceptance 9 + Explicitly forbidden are correct); no-look-ahead / conservative-fills /
validator-only (untouched); brief-number registry (42 is properly reserved in
`docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md`, the brief correctly forbids resolving
a conflict). `.agents/skills/codex-brief-writing/SKILL.md` header shape is satisfied.

---

## 13. SHOULD-FIX — H5's resume floor is in scope but the H5 amendment is never cited correctly

**Brief text (WP-C.2):** pins `H5_RESUME_FLOOR_SESSION` (`config.py:630`, read at
`entry_watch.py:223`) — both Repo-verified correct.

**Gap.** The governing record is **seq 29** (`H5_AMENDMENT_V1`, clause 5), and its text
defines the floor as *derived* ("the LATER of (i) the first session on/after the
implementation landing and (ii) this amendment's ledger append date" — seq 28 clause 5,
which seq 29 adopts by reference). **A derived value cannot be pinned to a record**;
there is no literal `"2026-08-19"` in the registration to anchor against. So WP-C.2's
"bound to the … clause-5 mechanical floor" is not implementable as stated, and what
will actually get written is a literal assertion (finding 10). The brief's "stop and
report rather than choosing a reading" catches this, but only after the executor has
burned a round trip discovering it.

**Concrete change.** Say it up front: the resume floors are **tripwires, not
bindings**, because clause 5 states a derivation rather than a value. Also note that
seq 29 binds its target by seq because `hypothesis_id` is `null` — that is the precedent
the brief means to cite in WP-A.1b, and the brief attributes it to **seq 30** (wrong;
see finding 5).

---

## 14. SHOULD-FIX — No hand-off ref, despite the repo's own documented stop-report on exactly this

**Gap.** The brief has no launch-prompt / hand-off section and never says which git ref
Codex reads it from. This matters concretely: the brief file is **untracked on
`claude/audit-2026-09-15`, which is the head branch of open draft PR #175**
(`gh pr view 175` — 33 files, all audit/ops docs). Brief 41's launch prompt
(`docs/superpowers/plans/2026-09-09-41-launchagent-loaded-check-codex-brief.md:127`)
exists in its current form *because* Codex's first dispatch stopped when the brief was
not on `main` before #165 merged (receipt `reports/2026-09-09-brief-41-codex-stop-report.md`).
Brief 42 repeats the setup without the lesson.

Ordering, verified: audit §4 finding 6 says "**Land this PR first**; then Codex rebases
brief 41 and recomputes `PYTHON_DASH_C_CLASSIFICATION` / `MUTATION_VERB_SITES`". Those
two registries live in `tests/test_daily_ritual_provenance.py:98,138` and key on
`tools/daily_ritual.sh`, which brief 42 does **not** touch — so there is **no direct
registry collision** between briefs 41 and 42. The dependency is sequencing only:
#175 lands → brief 42 reaches `main` → Codex dispatches from `main`.

**Concrete change.** Add a hand-off section stating: implementation base is
`origin/main`; Codex reads the brief from `origin/main` only after PR #175 merges, else
from an owner-named pinned SHA; the revision string is confirmed before implementing;
work happens on a fresh branch in `.tmp/worktrees/`, not in the audit worktree.

---

## 15. NOTE — Things the brief gets right, recorded so a rewrite does not lose them

- The "What H10b actually is" section is the strongest part of the brief: it correctly
  refuses the audit summary's implied finding, and every claim in that table verified.
  Closed open question 4 (seq 16 carries "verdict gates at >=7 losses" independently) is
  Repo-verified and correct.
- The H8 section is correct: `grep -c score h8_watch.py` → 0, the shared-cap coupling at
  `h8_watch.py:365,586,614,853` is real, and refusing to make the D-1 call is right.
- The OUT list is unusually good and the `.claude/rules/ledger.md` reading is accurate.
- Acceptance 2's *principle* ("a test that passes both before and after the fix proves
  nothing") is the correct standard — it is the brief's own WP-E table that fails it.

---

## Verdict

**FAIL.**

Three blockers, and they are load-bearing rather than cosmetic. (1) The record-hash pin
as specified compares a self-reported field to a string and does not detect the prose
edit it claims to detect. (2) With the pin hollow and the values hand-transcribed into a
new module, WP-A binds nothing to the ledger — it adds a second executor-maintained copy
of five owner-frozen numbers and calls the drift check between the copies a
registration binding, which `.cursorrules` ("every number comes from `config.py`") and
`CLAUDE.md:53` ("the owner types every frozen number") both forbid. (3) WP-A.4's refusal
semantics and WP-E's first two named tests cannot both be satisfied, and WP-D.1 hands
that contradiction to the executor to resolve.

On top of those, the ledger `seq` citations — the one class of citation this brief must
get right, because WP-A and WP-C tell Codex to bind code to specific seq numbers — are
wrong in three places (seq 28 called "A2-v1"; `H10B_AMENDMENT_V1_1` attributed to
"seq 29/30"; WP-C.2 pointing at a clause 5 that seq 30 does not have, contradicting
`config.py:628`'s own comment). And the brief's core target, H6, still contains an
unbound verdict-affecting config read it never mentions
(`H6_KILL_V2_EFFECTIVE_ENTRY_DATE`, `h6_watch.py:710`), whose registered rule (seq 22)
shares `_has_consecutive_months` with the value WP-B.1 would bind to seq 6.

The finding the brief is chasing is real and well-evidenced. The mechanism proposed for
it is not, and it is described in language stronger than what it delivers. A rewrite
around the prose-anchor design in finding 2 — which needs no ledger write, no amendment,
no frozen-value change, and no executor-typed number, and for which
`tests/test_h10_config.py:7,50-51` is the in-repo precedent — would be a genuine binding
and is materially simpler than what is specified today.
