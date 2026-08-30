# Adversarial review receipt — monday-ship batch (2026-08-15)

**Reviewer:** independent adversarial reviewer (Opus), read-only session.
**Branch:** `claude/monday-ship-2026-08-15` (commits `22e801d`, `78f0fef` on
`origin/main` @`58701e9`).
**Posture:** attack, not confirm. Everything below is Repo-verified against the
ledger, the chain cache, and the ops logs unless labeled otherwise. Reading of
`ledger/` was grep/sed only; nothing in `ledger/` was written or opened for
write.

**OVERALL VERDICT: FAIL** — two of six artifacts must not proceed as written
(B-1, B-2, B-3). The other four are PASS WITH FIXES. No fabricated number was
found anywhere in the batch; every ledger value I spot-checked reproduces
exactly, and the feasibility count reproduces exactly. The failures are
supersession-hygiene and root-cause-attribution defects, not invention.

---

## Verdict per file

| # | File | Verdict |
|---|---|---|
| 1 | `docs/superpowers/plans/2026-08-15-14-rq2-badge-build-codex-brief.md` | PASS WITH FIXES (blocking: B-5) |
| 2 | `docs/superpowers/plans/2026-08-15-15-composite-grade-firerate-codex-brief.md` | PASS WITH FIXES |
| 3 | `docs/superpowers/plans/2026-08-15-16-a2-outcome-battery-codex-brief.md` | PASS WITH FIXES (blocking: B-4) |
| 4 | `reports/2026-08-15-rq2-a2-amendment-drafts.md` | **FAIL — do not append as written** (B-2, B-3) |
| 5 | `reports/h10/2026-08-15-h10a-closeout.md` | PASS WITH FIXES |
| 6 | Doc edits in `22e801d` | **FAIL — root-cause prose is wrong** (B-1) |

---

## What I verified and what held

**Ledger fidelity — every checked value reproduces.**

- Seq 18 (`RQ2-v1`, OWNER-TYPED VALUE FREEZE 2026-07-23): "ts_slope percentile
  >= 0.75 AND VRP-proxy percentile <= 0.25"; "dist_52w_high <= -0.20 AND
  mom_1m > 0 AND rv21 percentile >= 0.70"; "Twelve-month forward backstop".
  Brief 14's banner and the amendment draft match exactly. ✓
- Seq 25 (`RQ2_AMENDMENT_V1_1` 2026-08-10): K=3 (B1/A1/V1), V1
  membership-only, statistic NOT pinned, min completed cycles = 6
  (LLM-proposed), Holm alpha=0.10 as ONE joint family across K=3. Brief 14 and
  the amendment match. ✓
- Seq 25 refusal clause verbatim: "The RQ2 runner MUST refuse to execute any V1
  comparison until that statistic is pinned by a further pre-result append-only
  amendment, and it may never be chosen after any RQ2 outcome is observed."
  Brief 14 paraphrases it accurately (see F-1 on the "verbatim" label). ✓
- Seq 19 (`A2-v1`): `MIN_ADVERSE_BOTTOM_BUCKET=10` ✓; five CSP arms ✓ (see
  F-6 on compression); LEAPS 21/63/126, tactical 5/10/20 ✓; ±50% cost stress ✓;
  twelve-month backstop ✓; "an empty lane is no data" ✓.
- `ledger/facts.log` `RQ2_A2_PIN_ADDENDUM_V1` (2026-07-23): fixed-horizon CSP
  arm = 10 trading sessions + expiration-settlement completeness clause ✓
  (brief 16 states this correctly); terciles top-third-vs-bottom-third with the
  "(15-name board gives 5 names per bucket)" parenthetical ✓ (amendment Block 2
  quotes it correctly); one-sided Holm sidedness ✓.

**Pre-result truth — both claims hold.**

- No `run` / `retrospective_result` / `result` entry exists for `RQ2-v1` or
  `A2-v1` anywhere in `ledger/experiments.jsonl` (the only result entries are
  H1, H2, RQ1). `RQ2`/`A2` appear in `facts.log` on exactly one line — the pin
  addendum. ✓
- No badge or battery code exists: `grep -rniE
  'ts_slope|ts_pctl|bounce_armed|bounce_flag|a2_runner|rq2_badges|rq2_recorder|corner_flag|MIN_ADVERSE_BOTTOM_BUCKET'`
  over `options_researcher/`, `tools/`, `config.py`, `tests/` returns zero
  hits. ✓ The amendment's pre-result attestation is true.
- `2026-09-01` appears zero times in `ledger/experiments.jsonl` and zero times
  in `ledger/facts.log`. The claim that it was never a ledger value is true; it
  traces to the 2026-07-22 briefs doc line 306 (LLM-proposed delegated table). ✓

**Price-source clause (3) genuinely fills a blank.** Seq 18, seq 19, seq 25 and
the pin addendum contain no price-source, closing-print, mid, mark, quote or
snapshot specification for RQ2. The only "close"/"mark" hits are A2 exit-arm
words ("close at 21 DTE", "LEAPS marks are 21, 63, 126 sessions") and the pin's
"expiration settlement". Clause 3 is a fill, not an override. ✓ Not a blocker.

**Clause 5b is not an auto-switch.** "That switch is NOT automatic: it requires
its own future append-only pre-result amendment (or new-window registration if
RQ2-v1 results exist by then)" — explicit, and it correctly handles the
post-result case by escalating to re-registration. ✓

**Feasibility claim reproduces exactly.** I counted standard monthly
expirations spanned by each symbol's cached chain sessions in `.cache/chains`
(31,367 files, main checkout — the worktree's `.cache` is empty, which is
expected):

- CRWV: 2025-04-02 → 2026-07-27, **15** completed cycles.
- USAR: 2025-04-07 → 2026-07-27, **15** completed cycles.
- MSFT: 2018-01-02 → 2026-07-27, **102** completed cycles.
- Exactly 18 symbols resolve as `ATTRACTIVENESS_UNIVERSE`
  (`H7_WATCHLIST` + `H7_CORE_LONG_ONLY` − `HYLN` + NBIS/AMAT/CLSK), and all 18
  clear the 6-cycle floor; the minimum is 15 and it is exactly CRWV and USAR;
  the maximum is 102. The drafts' "18/18 clear the floor (min 15 — CRWV, USAR;
  max 102)" is **correct as stated**, not merely order-of-magnitude correct.
  (Caveat: my count is expirations spanned by the cached date range, an upper
  bound if there are interior gaps; the implementer should recount with the
  anchor-session rule the amendment pins.)

**Repo anchors cited in the briefs all resolve.** `composite_signals.py:552`
`confluence_grade` ✓; `rq1_runner.py:48` `green_fraction` ✓;
`tools/h7_schwab_feasibility.py` `_receipt_hash`/`RECEIPT_KIND`/`STACK_VERSION`
✓; `config.py` composite block ~L804-832 with `COMPOSITE_GRADE_A_MIN_ALIGNED=3`
/ `_B_=2` ✓; `.tmp/composite_cache/` holds exactly 36 files ✓;
`RQ1_RV_ANNUALIZATION_SESSIONS = 252` ✓.

**Banner in `22e801d` is honest.** The four "wrong" values are really in the
briefs doc (lines 291-296: 0.80 / 0.20 / +5% / 0.60) and the ledger really does
say otherwise. Line 306 really does print "Start 2026-09-01". ✓

**OD-3 transcription source checks out.** `git show 74a82a8:PROJECT_STATE.md`
lines 108-110 contain the quoted sentence verbatim modulo line wrapping ✓. The
bar-7 wording "7 as well but i want to watch it fire" is attributed to
`reports/2026-08-14-owner-answers-decision-menu.md`, which exists ✓.

**H10a factual record is right.** `reports/h10/observations.jsonl` has exactly
4 records — 2026-07-23, 07-24, 07-27, 07-28 — every one with `open_positions:0`
and `fired:[]`, across the 11 `H7_WATCHLIST` names ✓. Zero `H10a` lines in
`ledger/facts.log` ✓. Seq 15 confirms window end 2026-10-06, ≥7-loss bar,
premium ≤$600, 30-60 DTE, outcome-informed permanent disclosure ✓. Both quoted
rulings (2026-08-04 "no forward hypothesis can accumulate marks…"; 2026-08-14
D-1=F1) are verbatim-accurate against their source reports ✓.

**Authority smuggling — mostly clean.** No brief grants Codex or any runner
ledger-write, verdict, FIRE, order-path, paper-book, baseline-ranking or
network capability. Brief 14 says "Codex does NOT touch the ledger" and scopes
the amendment check to a read-only grep. Briefs 15 and 16 carry explicit OUT
lists covering ledger, verdict text, network, and the frozen GREEN-fraction
recipe. The one real smuggling risk I found is B-3 below.

**No packet writes the ledger before owner approval.** The H10a closeout is
DRAFT, states that the amendment delegation does not cover verdicts, and puts
owner approval as step 1. ✓

---

## Blockers

**B-1 — `22e801d` misattributes the preclose root cause, and contradicts its
own table.** (`reports/2026-08-12-schwab-auth-diagnosis.md` addendum §2 +
`PROJECT_STATE.md` edit.) Ops logs, read directly:

- `~/options-validator-ops/.tmp/schwab_chain_capture/2026-08-1{0,1,2,3}_1545.log`
  — **all four** contain `schwab_chain_capture wrapper REFUSED: HEAD is not
  aligned with origin/main`. `2026-08-14_1545.log` is the 15/15 success.
  `~/options-validator-ops/reports/schwab_chains/` contains exactly one dated
  directory: `2026-08-14`.
- `.tmp/intraday_capture/`: 08-10 and 08-11 show `OAuthError … invalid_grant`;
  08-12, 08-13, 08-14 show 15/15 OK. The per-row table in the addendum is
  therefore **accurate** — it correctly marks Mon 08-10 preclose as "wrapper
  REFUSED (alignment)".

The prose beneath the table is not:

1. "the expired refresh token broke BOTH lanes on 08-10 and 08-11 only" — false
   for the preclose lane. On 08-10 and 08-11 the preclose lane refused at the
   alignment guard and never reached auth. Had the token been valid, those
   captures would still have failed. This sentence contradicts the table three
   lines above it.
2. "the preclose chain lane ALSO refused on 08-11 → 08-13 **after auth was
   already fixed**" — the refusals span **08-10 → 08-13**, and "after auth was
   already fixed" (reauth 08-12 ~00:56 ET) is true only of 08-12 and 08-13.
   The cited evidence glob `2026-08-1{1,2,3}_1545.log` omits the 08-10 log,
   which carries the same refusal.
3. Consequence line and the `PROJECT_STATE.md` edit both scope the ops-sync
   attribution to "08-11→08-13" and then say "only 08-10/08-11 trace to the
   expired token". Read in a sentence about missing PRECLOSE captures, that is
   wrong in the most consequential direction: **no** missing preclose capture
   traces to the token; all four trace to the alignment guard.

This is a truth-repair commit whose headline is a root-cause split, and the
split it publishes is off by one day and mixes the two lanes. Fix: change the
range to 08-10→08-13 throughout, restrict the auth-caused breakage claim to the
intraday lane, cite the 08-10 log, and correct the `PROJECT_STATE.md` sentence
so it cannot be read as "the 08-10/08-11 preclose gaps were Schwab's fault".

**B-2 — Amendment Block 1 clause (1) silently supersedes an owner-typed pin.**
`RQ2_A2_PIN_ADDENDUM_V1` clause (iv) defines Badge B's applicable event window
and states "earnings provenance via h7_earnings with **UNKNOWN refusing**, per
seq 18". Seq 25 explicitly kept all four pins in force across K=3. Draft clause
(1) converts UNKNOWN-refuses into UNKNOWN-is-a-visible-tag and drops the gate
the window definition served — but the draft's UNCHANGED paragraph covers only
"every other term of seq 18 and seq 25" and never names the pin addendum. Seq
25 itself set the correct precedent by naming its one supersession ("except its
parenthetical 'K unchanged'"). An append-only record that changes an
owner-typed pin without naming it is exactly the drift this ledger exists to
prevent. Fix before append: name `RQ2_A2_PIN_ADDENDUM_V1` clause (iv)
explicitly, state that its UNKNOWN-refusal is superseded for B1's *firing*, and
state whether its event-window definition survives as the definition of
`earnings_tag = "event-priced"` (it should — otherwise `earnings_tag` has no
frozen meaning).

Second half of B-2: the owner wording being relied on — "i dont want that to
fire if theres confirmed earnings i want that fired daily and studied" — reads
literally as the *opposite* of the change being made (seq 18's gate *requires*
confirmed earnings coverage before B1 may display; the owner's first clause
says don't fire *if* there are confirmed earnings). The second clause supports
ungating, and I think ungating is the right reading, but the draft reverses an
owner-typed registration term on wording that admits two readings and does not
say so. Record the ambiguity in the amendment text and flag it for owner
confirmation rather than resolving it silently.

**B-3 — Amendment Block 1 clause (5c) is a badge acquiring board-ordering
influence inside the same block that swears it never will.** 5c pins V1's
tiebreak form ("V1 enters the lexicographic tiebreak within equal
GREEN-fraction as its RAW statistic value"), while the UNCHANGED paragraph
reasserts "never reordering the frozen GREEN-fraction baseline". The "if
promoted" conditional is doing all the work and it is doing it in one clause of
a subordinate. The ledger currently contains no RQ2 tiebreak concept at all
(zero `tiebreak` hits in `experiments.jsonl`; the two in `facts.log` are H7c);
this would be its first appearance. Fix before append: add an explicit sentence
that 5c defines only the FORM a tiebreak would take, confers no promotion
authority and no ordering change of any kind, and that adopting it requires a
separate owner-typed decision plus the applicable registration gate.

**B-4 — Brief 16 runs the A2 historical pass on an outcome-selected universe
with no required disclosure, and its bucket rule is undefined historically.**
Today's 18-name board applied retroactively to 2018 is universe look-ahead:
CRWV's cache starts 2025-04-02, USAR 2025-04-07, NBIS 2024-10-30, TEM
2024-07-01, AMAT/CLSK 2025-01-02. These names are on the board *because of what
they became*. The brief mandates a no-look-ahead invariance test on time series
but says nothing about selection. Separately, "terciles of 6" is meaningless
for cohort dates when fewer than 18 names have data — and the amendment's Block
2 states both "terciles" and "top 6 versus bottom 6" as if they were the same
rule. Fix: (a) require every A2 historical output to carry a permanent
disclosure that the universe is the 2026-08 board applied retroactively and
name inclusion is outcome-informed (the H10a precedent for permanent
outcome-informed disclosures applies directly); (b) state that terciles is the
rule and 6/6 is the current-board instantiation, and that each historical
cohort takes terciles of the names with data at that cohort's formation date,
with per-cohort counts printed.

**B-5 — Brief 14's `PENDING_AMENDMENT` mode is fail-open with a label, on the
one lane that is verdict-bearing.** "compute and write everything, but stamp
every output `amendment_pending: true`" is not fail-closed; it is fail-open
plus a sticker. The risk is concrete: if the recorder runs Monday 2026-08-17
before `RQ2_AMENDMENT_V1_2` is appended, and the amendment lands 08-18 saying
"the window opens 2026-08-17", that first row was computed under un-amended
rules and gets retroactively counted into the only verdict-bearing path RQ2
has. Fix: state that sessions recorded while the amendment is absent are
permanently excluded from the scored window (diagnostic-only, and marked so
irreversibly in the output), or define the window start as the first session on
or after the amendment's append timestamp.

---

## Fixes (non-blocking)

- **F-1** Brief 14 calls its paraphrase of the refusal clause a "seq 25 verbatim
  requirement". It is a faithful paraphrase, not verbatim. Either quote seq 25
  or drop "verbatim".
- **F-2** Brief 14's binding-definitions section says V1's "scoring statistic is
  NOT pinned" and WP-C hard-wires an unconditional V1-refusal test — but the
  same batch's amendment pins it. If `RQ2_AMENDMENT_V1_2` appends first, brief
  14 is stale on hand-off and its refusal test will need rewriting immediately.
  Gate the refusal on the pin's presence, the same way WP-B gates on
  `amendment_pending`.
- **F-3** Brief 14 inherits "252 trailing / min 60" from the 2026-07-22 briefs
  doc (line 71). The repo's own convention is `features.PCT_MIN_OBS = 126`, and
  the composite lane uses `COMPOSITE_PCTL_MIN_OBS = 126`. RQ2's badges would
  fire on half the history every other lane requires. Justify or align; do not
  inherit it silently just because it is already written down.
- **F-4** Brief 14 WP-D wires a new module into the daily preclose flow. Even as
  a read-only consumer this changes what runs at 15:45 in the ops checkout.
  Specify that a failure in `rq2_recorder` can never affect the capture lane's
  exit status, and say explicitly whether an ops-checkout sync is required
  before Monday.
- **F-5** Amendment clause (3) says forward badge computation uses the Schwab
  captures, but A1's inputs (`dist_52w_high`, `mom_1m`, `rv21`) come from
  `data/underlying_closes.py`, as brief 14 itself states. Say "options-derived
  marks" rather than implying a single source for everything.
- **F-6** Brief 16 compresses seq 19's breach-defensive arm ("breach followed by
  hold to 21 DTE then mechanical close") to bare "breach-defensive". Under a
  "Binding definitions / Repo-verified" heading, the mechanics must be spelled
  out or Codex will invent them.
- **F-7** Brief 16 provenance-labels `MIN_ADVERSE_BOTTOM_BUCKET = 10` as
  "owner-forwarded 2026-07-23". Seq 19 is headed "OWNER-TYPED VALUE FREEZE".
  Use "owner-typed 2026-07-23 (ledger seq 19)".
- **F-8** Brief 16's OUT list forbids "verdict, promotion, or rejection text
  anywhere in output" while WP-C requires `INSUFFICIENT_SAMPLE` labeling —
  which is a verdict term in this repo. Pick one; if the label stays, say
  explicitly that it is a sample-adequacy annotation on an exploratory pass and
  is not the registered verdict.
- **F-9** Amendment clause 5a pins far more than seq 25 enumerated. Seq 25's
  pin scope was "which of the two V1 lines ranks, its direction, and how
  insufficient-history names are handled"; 5a additionally fixes cycle geometry
  (monthly E_k → E_k+1), the entry-anchor convention, the aggregator (median),
  the annualization, and a 24-cycle cap. Pinning more pre-result is
  conservative and I do not object to it — but say so, rather than presenting
  it as if seq 25 asked for it.
- **F-10** The 24-cycle cap is LLM-proposed inside a verdict-bearing statistic
  and would discard 78 of MSFT's 102 cycles. Seq 25 handled its own
  LLM-proposed value (6) by stating it is not owner-typed and remains subject to
  re-confirmation and owner veto. Give the cap the same treatment, or drop it.
- **F-11** Amendment clause 5a weakens seq 25's unconditional "earnings-window
  cycles reported separately from clean cycles" to "stays binding where coverage
  exists". Add: where coverage is absent the split renders UNKNOWN, fail-visible
  — never silently omitted.
- **F-12** The amendment's recording provenance pre-names this receipt before
  the review existed. Record the actual verdict (this receipt returns FAIL on
  the amendment as written), not merely the path.
- **F-13** H10a closeout: the 2026-07-24 record has all 11 names `skipped: DATA`
  — that session observed nothing. "Every day: 0 fires … across all 11 eligible
  names" and the verdict's "4 observation receipts" over "the only sessions with
  live data" are technically defensible but soften the truth: there were three
  usable sessions and one data-blocked one. Say so; it strengthens the
  STARVED finding rather than weakening it.
- **F-14** H10a verdict text says "the data pipeline ended 5 sessions into the
  window". The record supports 4 receipts (3 usable). Either show the session
  count derivation or use the receipt count.
- **F-15** H10a closeout step 2 ("Append via `research/ledger.py` typed API")
  does not say who appends. Verdict ratifications are owner-typed; state that
  the owner performs or explicitly authorizes the append.
- **F-16** H10a closeout blends two distinct registered disclosures — the
  outcome-informed *selection* disclosure and the weaker-verdict disclosure from
  the ≥7-loss override — into one sentence. Keep them separate.
- **F-17** Auth addendum labels the 7-day refresh-token lifetime
  "Official-source" while deliberately withholding the source URL. The repo's
  fetcher rule requires retaining source URL and capture time. Record a capture
  timestamp and a defanged or receipt-stored URL; otherwise label it
  "Official-source text via third-party mirror, URL withheld" so the reader can
  price the claim. The schwab-py corroboration is a secondary source and should
  be labeled as such.
- **F-18** Brief 15 calls `.tmp/composite_cache/`'s 36 files "Repo-verified" at
  a commit. `.tmp/` is gitignored local state; it verified true on the main
  checkout today (36 files) but is empty in this worktree. Label it
  "locally verified 2026-08-15 on the main checkout", not Repo-verified at a SHA.
- **F-19** The OD-3 slot transcription fills a `[OWNER TYPES … HERE]` placeholder
  with agent-written text. It is labeled a transcription and cites `74a82a8`
  verbatim, which is the right way to do it — but consider prefixing the block
  "TRANSCRIBED, NOT OWNER-TYPED" so a future skim cannot mistake it.

---

## Bottom line

Nothing in this batch is invented and nothing smuggles an order path, a network
call, or a ledger write. The ledger arithmetic is clean and the feasibility
count is exactly right — I tried to break it and could not. What fails is
supersession hygiene: an amendment that changes an owner-typed pin without
naming it (B-2), a tiebreak clause that opens a door the same block says is
locked (B-3), and a truth-repair commit whose root-cause prose is off by a day
and contradicts its own evidence table (B-1). All three are text-level fixes;
none requires re-doing work. Fix B-1 through B-5, apply F-1 through F-19 as
judgment allows, and this batch is appendable and hand-off-ready.

---

# Round 2 — confirmation review (2026-08-15)

**Reviewer:** independent adversarial reviewer (Opus), read-only session except
for this section. **Target:** `155418b` on `claude/monday-ship-2026-08-15`,
which claims B-1..B-5 and F-1..F-19 closed. **Method:** each blocker re-attacked
against the revised text on its original terms, then five F-fixes spot-checked,
then a hunt for defects the fixes themselves introduced. `ledger/` was read via
grep/sed/`json` only; nothing under `ledger/` was written or opened for write.

**OVERALL ROUND-2 VERDICT: PASS WITH FIXES.** Four of five blockers are dead.
B-1 is dead in the text it named and **alive in one adjacent sentence the fix
did not reach**. Two new residuals (N-1, N-2) and one partially-closed fix
(F-12) must be settled before the amendment is appended, because an
append-only entry cannot be corrected afterwards except by another amendment.

## Blocker re-attack

**B-1 — STILL ALIVE (narrow residual; the named prose is dead).**

The specifically-named prose is now correct and matches the evidence exactly.
Re-read directly, not via the diff:

- `~/options-validator-ops/.tmp/schwab_chain_capture/2026-08-1{0,1,2,3}_1545.log`
  — all four carry `schwab_chain_capture wrapper REFUSED: HEAD is not aligned
  with origin/main` and nothing else. `2026-08-14_1545.log` is `15/15 ... OK`.
- `.tmp/intraday_capture/` 08-10 and 08-11 → `OAuthError ... invalid_grant` on
  all five slots each day; 08-12, 08-13, 08-14 → `15/15 OK` on all five slots.
- `~/options-validator-ops/reports/schwab_chains/` contains exactly one dated
  directory, `2026-08-14`. Same in this worktree. There is exactly **one**
  preclose capture for the whole week.
- The addendum's new claim "The wrapper refuses BEFORE attempting auth" is
  Repo-verified: `tools/schwab_chain_capture.sh` runs the branch check, fetch,
  and alignment gate at lines 34-104 and only reaches
  `uv run python -m options_researcher.schwab_chain_capture` at line 119.

So "all four days 08-10 → 08-13", "intraday quote lane only, on 08-10 and
08-11", and "every missing preclose chain capture ... none to Schwab
availability" are all correct. The per-row table is unchanged and still
accurate. That part of B-1 is **CONFIRMED DEAD**.

What survives is four lines above the corrected sentence, in the same
parenthetical, untouched by `155418b` — `PROJECT_STATE.md:86-87`:

> "the token was re-authorized 2026-08-12 ~00:56 ET and **both capture lanes
> verified 15/15 on 08-12→08-14**"

The preclose lane did not verify 15/15 on 08-12 or on 08-13 — it refused on
both, as the very next sentence of the same parenthetical now says ("all four
were the wrapper's own ... alignment guard refusing"). The paragraph therefore
still contradicts itself, and it does so in the direction that overstates the
evidence: a reader takes away three preclose captures for 08-12..08-14 when
exactly one exists. This is the identical conflation B-1 was raised about,
one sentence over. Fix: "the intraday quote lane verified 15/15 on 08-12→08-14
and the preclose chain lane on 08-14 (its first clean run since the alignment
guard cleared)".

Secondary instance, softer because a correcting table follows immediately:
`reports/2026-08-12-schwab-auth-diagnosis.md:84` "Both capture lanes then
verified working:". Tighten to "Both capture lanes were then exercised, with
different results:" so the header does not have to be walked back by its own
table.

**B-2 — CONFIRMED DEAD (mechanically), with a new residual N-1.**

Clause (1) now carries an explicit `NAMED SUPERSESSION` naming
`RQ2_A2_PIN_ADDENDUM_V1` clause (iv), stating that the UNKNOWN-refusal is
superseded **only** for B1's firing, that the applicable-event-window
definition **survives unchanged as the frozen definition of
`earnings_tag = "event-priced"`**, and that the h7_earnings provenance rule
survives. That is precisely what B-2 demanded, including the part about
`earnings_tag` otherwise having no frozen meaning.

Quote fidelity re-checked against `ledger/facts.log` line 17984. Pin clause
(iv) reads: *"Badge B applicable event window: a confirmed earnings report date
strictly inside the near leg's remaining life, evaluation date < report date <
near-leg expiration date (the 15-45 DTE leg); a report dated on the expiration
date itself is excluded as conservatively unspanned; earnings provenance via
h7_earnings with UNKNOWN refusing, per seq 18."* The amendment's split of that
single sentence into a surviving window definition, a surviving provenance
rule, and a superseded UNKNOWN-refusal is an accurate and precise partial
supersession. Block 2's quote of the tercile pin ("top third versus bottom
third (15-name board gives 5 names per bucket)") is verbatim-accurate. Seq 25's
naming precedent it invokes is real: *"except its parenthetical 'K unchanged',
which this amendment supersedes."* Seq 18's gate wording it removes is real:
*"earnings-GATED, meaning confirmed report coverage inside the applicable event
window is required before the badge can display."*

The second half of B-2 (the ambiguous owner wording) is answered — but by a
route that raises **N-1**, below.

**B-3 — CONFIRMED DEAD.**

5c now carries a `NO-AUTHORITY CLAUSE`: *"5c defines only the FORM a tiebreak
would take IF a promotion ever occurs; it confers no promotion authority,
changes no ordering of any board or output today or at any time before a
promotion, and adopting the tiebreak in practice requires a separate
owner-typed promotion decision passing the registered promotion rule plus every
applicable registration gate. This is the first tiebreak concept in this ledger
for RQ2 and it is form-only."* Every element B-3 asked for is present,
including the acknowledgement that it is the first such concept. It also scopes
itself to V1 and disclaims B1/A1. Nothing else in the block re-opens the door;
the UNCHANGED paragraph still carries "never reordering the frozen
GREEN-fraction baseline", and the two clauses no longer contradict.

**B-4 — CONFIRMED DEAD.**

Both halves landed, and they landed identically in brief 16 and in amendment
Block 2, which is what makes it real rather than decorative:

(a) *"MANDATORY PERMANENT DISCLOSURE on every historical output: the universe
is the 2026-08 board applied retroactively; name inclusion is outcome-informed
(names are on this board because of what they became), which biases the
historical pass in unknowable directions — a second reason it is
exploratory-only."* The brief also names the concrete cache starts
(CRWV/USAR 2025-04, NBIS 2024-10, TEM 2024-07, AMAT/CLSK 2025-01) so an
implementer cannot mistake the scale of the problem.

(b) *"TERCILES IS THE RULE; 'top 6 vs bottom 6' is only its instantiation on
the current 18-name board"*, plus per-cohort terciles of the names with cached
data at that cohort's formation date, with per-cohort counts printed. The
amendment's Block 2 now says the same in the same words, so the ledger text and
the build spec cannot drift.

**B-5 — CONFIRMED DEAD, with a new residual N-2.**

`PENDING_AMENDMENT` fail-open is gone and replaced with a genuine quarantine:
*"the recorder REFUSES to write to the official output tree entirely. It may
write diagnostics ONLY under `reports/rq2/dryrun/<date>/`, and any session
recorded there is permanently excluded from the scored window — the future
scorer must hard-refuse to read anything under `dryrun/` (enforce with a test).
The scored window's first admissible session is the LATER of the registered
open date (2026-08-17) and the first session on/after the amendment's append
timestamp. No pre-amendment row can ever be retroactively counted."* B-5 asked
for either of two remedies; the revision implements both, and adds a test
obligation on the scorer side, which is the half that actually binds. Brief 16
adopts the same pattern for A2 (`reports/a2/dryrun/`).

## Spot-checks — five F-fixes, verified against primary sources

- **F-3 (min-obs) — CLOSED, and the repo backs it.** Brief 14 now pins
  252-session lookback with min-obs **126**, citing `features.PCT_MIN_OBS` and
  `COMPOSITE_PCTL_MIN_OBS`. Both verified: `options_researcher/features.py:25`
  `PCT_MIN_OBS = 126` (enforced at line 77) and `config.py:820`
  `COMPOSITE_PCTL_MIN_OBS = 126`. The change is labeled LLM-proposed
  2026-08-15-by-alignment rather than smuggled in as owner-typed, and names
  below min-obs render UNAVAILABLE fail-visible.
- **F-6 (breach-defensive) — CLOSED, wording is faithful.** Seq 19 reads
  *"breach-defensive with breach followed by hold to 21 DTE then mechanical
  close"*; brief 16 now spells out *"after a strike breach the position is HELD
  to 21 DTE and then mechanically closed, per seq 19's own wording, not any
  other defensive scheme."* No invention.
- **F-7 (provenance label) — CLOSED.** Seq 19's `reason` opens
  *"OWNER-TYPED VALUE FREEZE 2026-07-23 for A2-v1..."* and contains
  `MIN_ADVERSE_BOTTOM_BUCKET=10`; brief 16 now labels it "owner-typed
  2026-07-23 (ledger seq 19)".
- **F-10 (24-cycle cap) — CLOSED, mirrors the seq-25 precedent exactly.** Seq
  25 handles its own LLM value as *"the value 6 is LLM-proposed under the
  owner's 2026-07-24 delegation, is NOT owner-typed, and remains subject to
  that briefs doc's own re-confirmation rule and to owner veto by further
  append-only amendment."* Clause 5a now says the cap *"is LLM-proposed
  2026-08-15, not owner-typed ... subject to re-confirmation and owner veto by
  further pre-result amendment."* Same treatment, and the rationale (histories
  spanning 15 to 102 cycles) is stated rather than assumed.
- **F-11 (clean-vs-earnings split) — CLOSED.** Seq 25's line-1 definition
  carries *"earnings-window cycles reported separately from clean cycles"*
  unconditionally. Clause 5a now adds *"where coverage exists it renders; where
  coverage is absent it renders UNKNOWN, fail-visible — never silently
  omitted"* — the exact remedy F-11 asked for. Its accompanying decision (all
  completed cycles enter the RANKING) is a fill, not a supersession: seq 25
  imposed a reporting split, never a ranking exclusion, and the reason is
  recorded on the record ("excluding by coverage would make data coverage a
  hidden signal").

Also confirmed closed in passing, at lower depth: F-1 ("faithful paraphrase"
replaces the false "verbatim" label), F-2 (V1 refusal now gated on the pin's
presence, both branches test-enforced), F-4 (hard isolation of `rq2_recorder`
from the capture lane's exit status, plus an explicit ops-sync-before-Monday
note), F-5 ("OPTIONS-DERIVED marks" with underlying inputs routed to
`data/underlying_closes.py`), F-8 (`INSUFFICIENT_SAMPLE` carved out as a named
sample-adequacy annotation, not a verdict), F-9 (the extra pinning is now
disclosed as the amendment's own choice, not a seq-25 requirement), F-13/F-14
(3 usable sessions stated plainly; the unsupported "5 sessions" claim removed),
F-15 (the owner performs or explicitly authorizes the append; the 2026-07-25
delegation is stated not to cover verdicts), F-16 (STARVED, outcome-informed
SELECTION, and the >=7-loss weaker-verdict disclosure now listed as three
separate records), F-17 ("Official-source text via third-party mirror (URL
withheld)" with a 2026-08-15 ~16:20 ET capture time, and schwab-py demoted to
"Secondary source"), F-18 ("locally verified 2026-08-15 on the main checkout"
replaces "Repo-verified", with a note that the tool must rebuild the cache when
absent), F-19 ("TRANSCRIBED, NOT OWNER-TYPED" prefix added).

## New defects introduced or left open by the fixes

**N-1 — the 2026-08-15 owner rulings exist nowhere but inside the document
that relies on them.** `grep` across every tracked `.md` finds the strings
"i dont want that to fire if theres confirmed earnings", "start rq2 today",
"a2 bucket size fix", "do both and split each decesion 50% weight" and
"do 100% the other one untill you can pull all company earnings" in exactly one
file: `reports/2026-08-15-rq2-a2-amendment-drafts.md` itself. The repo's own
precedent is the opposite — the 2026-08-14 rulings live in
`reports/2026-08-14-owner-answers-decision-menu.md` and
`reports/2026-08-14-switch-on-owner-decisions.md`, and round 1 of this review
verified H10a's owner quotes *against those source reports*. The B-2 fix makes
this sharper, not softer: it now asserts a specific process — *"the ambiguity
was put to the owner in-session as an explicit three-option question (fire
daily on every name / fire only when NO earnings near / keep both versions) and
the owner selected 'Fire daily on every name'"* — and that three-option
exchange has zero corroboration on disk either. I have no evidence the exchange
did not happen; I have no evidence outside the draft that it did. An
append-only entry that supersedes an owner-instructed pin on the strength of
owner authority should cite that authority from somewhere other than itself.
Fix before append: write the 2026-08-15 owner rulings into a dated
`reports/2026-08-15-owner-*.md` on the 08-14 pattern (or cite the session
transcript path), and have the amendment's clause (1) cite it. Cheap now,
impossible after the append.

**N-2 — the B-5 fix creates a brief-vs-ledger drift on the window start.**
Brief 14 line 64 now says the first admissible session is *"the LATER of the
registered open date (2026-08-17) and the first session on/after the
amendment's append timestamp"*. Amendment clause (2) still says flatly *"The
RQ2-v1 forward window opens 2026-08-17 (first scored session) and its
twelve-month backstop ... therefore ends 2027-08-17."* If the append happens
this weekend the two agree and nothing bites. If it slips past Monday — the
exact scenario B-5 was raised about — the immutable ledger text says the window
opened on a session the build spec forbids scoring. Fix: add one sentence to
clause (2) — if the amendment is appended after 2026-08-17, the first scored
session is the first session on or after the append and the backstop end date
does not move (a shorter window, the conservative direction).

**F-12 residual — partially closed.** The recording provenance now honestly
records round 1 as FAIL and makes the append conditional on a confirmation-round
PASS, which is a real improvement. But the string that would be appended still
reads "round 2 verdict recorded in the receipt" without naming it. Before
append, replace it with the actual round-2 verdict and the residuals' status,
so the ledger entry states what review it survived rather than pointing at a
file.

**N-3 (minor, disclosed already — no action required).** Seq 25 defines V1
line 1 as VRP history *"at the card's DTE bucket"*; clause 5a fixes cycle
geometry to standard monthly `E_k → E_k+1` for every card. Read as a narrowing
of "the card's DTE bucket" this would be a supersession; read as choosing one
tenor convention inside the 15-45 DTE near leg it is a fill. The clause's own
SCOPE DISCLOSURE already tells the reader this pinning is the amendment's
choice and not a seq-25 requirement, which is the honesty round 1 asked for
under F-9, so I am not treating it as a defect — only noting that a reader
should not mistake it for something seq 25 specified.

## Is the amendment safe to append?

**Not yet — but it is three text edits away, none of which requires re-doing
work.** On the merits the document now clears the bar the 2026-07-25
owner-delegated standing sets: it is pre-result (re-verified — no `run`,
`retrospective_result`, or `result` entry for RQ2-v1 or A2-v1 exists, and no
badge or battery code exists in the repo), it names its supersessions in the
seq-25 style, it labels its LLM-proposed values as such, it grants no promotion
or ordering authority, and it has now survived independent adversarial review
across two rounds. What is missing is the authority citation (N-1), the
window-start consistency sentence (N-2), and a provenance line that states this
round's verdict (F-12 residual).

Recommended order: fix `PROJECT_STATE.md:86-87` (B-1 residual, unrelated to the
append but it is the canonical status doc and it is wrong today), then N-1,
N-2, and the F-12 residual, then append both blocks via the `research/ledger.py`
typed API under "owner-delegated standing 2026-07-25". The H10a closeout
remains owner-gated and is correctly marked so — it is not covered by the
amendment delegation and must not ride along with this append.

**Round-2 status table**

| Blocker | Round-2 status |
|---|---|
| B-1 | STILL ALIVE — named prose CONFIRMED DEAD; `PROJECT_STATE.md:86-87` still claims both lanes verified 15/15 on 08-12→08-14 |
| B-2 | CONFIRMED DEAD (see N-1 on the authority citation) |
| B-3 | CONFIRMED DEAD |
| B-4 | CONFIRMED DEAD |
| B-5 | CONFIRMED DEAD (see N-2 on clause (2) consistency) |
