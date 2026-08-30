# DRAFT — NOT A REGISTRATION

**This document registers nothing.** No ledger file has been touched, no
fact has been appended, and no frozen number is entered here except where
explicitly marked "owner-typed" and already recorded elsewhere. This is a
drafting exercise so the owner can review the shape of a registration before
any guarded door is used. Writing to `ledger/h7_forward_schwab/` remains an
owner action through the typed API, per `CLAUDE.md` ("Claude writes code
directly only for docs, briefs, and trivial mechanical fixes — not strategy
or ledger code") and the hard-enforcement ledger-write hook.

**Vocabulary discipline applies throughout:** nothing below claims an edge is
"proven," "confirmed," or "found." Where a result exists it is described as
"survived this test," "not yet rejected," "rejected," or "consistent with
zero edge" per `.cursorrules`.

---

## 0. Blocking preconditions — current status

> **Re-verified 2026-08-15 ~10:00 ET (scheduled weekend-cleanup session).**
> This table was first written at 00:38 ET, before PR #46 merged. Rows 1 and
> 2 have since cleared and are corrected below; rows 3–5 remain open, and row
> 3's reason is now understood to be *structural*, not a missing step. The
> original 00:38 wording is preserved in git history (`d3e0a66`).

> **Refreshed again 2026-08-29** against `origin/main` @ `4790cba`. Rows 3 and
> 4 have since cleared and are corrected below. **Two rows are new and the
> table was renumbered:** row 5 (fresh feasibility receipt at current config)
> is a precondition that the 2026-08-15 draft listed only in §4's prose and
> never tracked here, so the former row 5 "Owner final go" is now **row 6**;
> row 7 (quote-age commitment) is **not a gate** at all. Every status below was
> re-verified by a command run on 2026-08-29; the command is named in the row's
> Evidence cell, and the full log is §8a.

> **Updated 2026-08-29 evening (owner-directed).** Row 5's open question — rerun
> or waive the config drift — was answered by the owner: **re-measure**. The
> rerun ran, every packet-cited figure re-measured identical, and **row 5 now
> reads MET**. Row 6 (owner final go) is the only precondition still open.
> Evidence: `reports/h7_forward_schwab/2026-08-29-variant-menu-rerun-current-config.md`,
> PR #132. §8a's F8 note is superseded accordingly (and its "five constants"
> drift count corrected to nine).

Registration of the bar-7 window **cannot happen** until all six preconditions
(rows 1–6) clear. **Five of six have cleared** as of the 2026-08-29 evening
update — with two clearances that must not be read as clean passes: row 2
cleared (its earlier provenance gap was closed 2026-08-29 by the committed §7a transcription, PR #133), and row 4
cleared by owner override rather than by the observed three-session streak.
Row 5 cleared on its own terms, by re-measurement rather than by waiver.
**Row 6 — owner final go — is the only precondition still open.** Row 7 is an
obligation, not a precondition, and is excluded from the count.

| # | Precondition | Status found | Evidence |
|---|---|---|---|
| 1 | **Disposition B merged to main** | **MET (2026-08-15 02:11 ET).** Merged via **PR #46** (`fd6af2f`), from `claude/drill-disposition-b-final` — which carries `54e9a00` (disposition B) plus `4a33520` (D-6a alignment check), `2cf883a` (receipt-hash coverage test) and `60a999c` (review-blocker fixes). `git merge-base --is-ancestor 54e9a00 origin/main` now succeeds. The seven typed `H7_INPUT_BINDING_INVALIDATION` facts are present on `main` in `ledger/facts.log`, one per July receipt (2026-07-17/20/21/22/23/24/27) — count verified = 7. The unrelated WIP commit `c02558f` on the *older* `claude/drill-disposition-b` branch was correctly **not** merged. **Re-verified 2026-08-29:** still an ancestor of `origin/main` @ `4790cba` (exit 0). | `git merge-base --is-ancestor 54e9a00 origin/main` (exit 0), `git show origin/main:ledger/facts.log \| grep -c`, `gh pr view 46` |
| 2 | **Independent adversarial review of disposition B, PASS or PASS WITH FIXES resolved** | **MET.** Review ran and was resolved: PASS WITH FIXES with 5 blockers (two novel mutation survivors; a detection-only bypass via `git branch -f`), all fixes applied in `60a999c`, **reviewer re-verified with its own repros and upgraded to PASS**. Mutation battery 9/9 plus reviewer-added M14–M16 red. Suite reported **2944 OK, exit 0**; ruff + pyright clean. **Provenance gap CLOSED (2026-08-29 late):** §7a's recommended transcription is now a committed file — `reports/h7_forward_schwab/2026-08-15-drill-disposition-b-review-receipt.md`, landed on `origin/main` via PR #133 (`3155fab`), naming blockers B1–B5 + C2, reviewer mutations M14–M16, and the PASS upgrade, transcribed from the PR #46 body and the `60a999c` commit message. Row 2 is now MET on the same committed-receipt terms as the 2026-08-12/13 sibling reviews. | `gh pr view 46 --json body`, `git merge-base --is-ancestor 60a999c origin/main` (exit 0), `git ls-tree -r --name-only origin/main -- docs/superpowers/reviews/`, `git grep -il 'disposition b' origin/main -- '*.md'` |
| 3 | **Drill re-run GREEN post-merge** | **MET (2026-08-20; verified 2026-08-29).** The structural blocker described on 2026-08-15 resolved exactly as predicted. A fresh backup was taken for a later completed session and restored: `reports/h7_receipts/backup/2026-08-19.json` (snapshot `0774b5c8…`, created `2026-08-20T14:16:34Z`) and its drill `reports/h7_receipts/backup_restore/2026-08-20.json` — `receipt_type "backup_restore"`, `completed_session "2026-08-19"`, `verified_at_utc "2026-08-20T14:18:21Z"`, `verification.manifest "OK"`, `verification.problems` empty (length 0), `verification.notes` 105 entries, `verification.ok true`, across 25 receipts / 7 data gates on scope `h7-forward-15-v1`. That matches this row's own 2026-08-15 prediction (`manifest OK`, `problems 0`, `notes 105`, `ok True`) field for field. Both receipts are on `origin/main`. This supersedes `reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`, whose red result was never disposition B failing. | `git show origin/main:reports/h7_receipts/backup_restore/2026-08-20.json`; `git show origin/main:reports/h7_receipts/backup/2026-08-19.json` |
| 4 | **S1 — three consecutive verifying trading sessions** (§7 of `docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md`, ratified via owner decision D-4/menu item 3, sub-fork **3a**) | **CLEARED BY OWNER OVERRIDE — not by the observed streak (2026-08-23; verified 2026-08-29).** Three separate things happened; keeping them apart matters. **(i) 3a landed.** `invocation_source` is present on `origin/main` in `options_researcher/schwab_chain_capture.py`, `data/ritual_authority.py`, `tools/job_health_digest.py` and four test modules; introduced by `ef69c94` (2026-08-15 13:10 ET), merged via PR #50 (`9e3e304`, 2026-08-15). **(ii) Recomputed arithmetic (see §1).** 3a landed on a Saturday, which is not an XNYS session, so the three-session projection is unchanged from the 2026-08-15 estimate: Mon 2026-08-17 → Wed **2026-08-19**. **(iii) The streak itself never completed.** The first tracked preclose receipt carrying the field is `reports/schwab_chains/2026-08-19/preclose.json` (`invocation_source: "launchd"`), then 2026-08-20; **2026-08-21 has no tracked preclose receipt**, so the run stopped at 2 of 3. The owner then **overruled the streak bar in-session 2026-08-23**, recorded on main in `data/ritual_authority.py` beside `exact_session_source_active=True` (commit `2e7eb3e`): *"S1's 3-session streak bar is overruled … Evidence at flip time: clean launchd receipts 08-19 and 08-20 (streak 2 of 3); the 08-21 gap was a network outage, not a source defect."* **Not re-run for this refresh:** spec §7 condition 1 (executing `tools/schwab_chain_manifest.verify_session` across a span) and condition 5 (capturing `launchctl list` verbatim). This row is therefore cleared **by owner disposition**, not by the honesty bar being satisfied as written. **The override is now optional, though.** Four consecutive tracked preclose receipts carrying `invocation_source: "launchd"` exist for 2026-08-24 / 25 / 26 / 27, so conditions 1 and 5 could be satisfied on that span for the cost of one `verify_session` run plus one `launchctl list` capture — the owner can retire the override and clear this row on its own terms rather than rely on a waiver. | `git grep -l invocation_source origin/main -- '*.py'`; `git log -S invocation_source origin/main -- '*.py'`; `git show origin/main:data/ritual_authority.py`; `git ls-tree -r --name-only origin/main -- reports/schwab_chains/` |
| 5 | **Fresh feasibility receipt at current config** (named as a remaining precondition by §4's registration-mechanics note; never tracked in this table before 2026-08-29) | **MET (2026-08-29 evening) — by re-measurement, not by waiver.** The owner's call on the open question below was to re-run rather than waive. The full menu (all 18 variants, both panels) plus the `V9_LANE_A_OR_COHORT9` follow-up combination were re-measured at `main` @ `86e8ba6`, `baseline_config_hash` **`b86b3188…`**, into a fresh receipt set at `reports/h7_forward_schwab/variant-receipts/rerun-2026-08-29-current-config/` (written via the menu tool's own `--outdir` flag; no existing receipt deleted, edited, moved or overwritten, and no immutability guard bypassed). **Every figure this packet cites re-measured identical:** V0 and V14 at 4.00 unconstrained / 3 occupancy-constrained; V9 at 104 with 10 (42-session) and 16 (21-session); V9 × cohort-9 at 80 unconstrained with 7 (42) and 11 (21); the per-symbol counts (PLTR 38 on the 9-name subset vs 37 on the 15-name panel, MSFT 12, NOW 28, VST 2); the baseline waterfall; and the whole deep arming census. All 38 receipts compared field by field gave **zero substantive differences** — only `code_sha`, `baseline_config_hash` and the derived `receipt_hash` moved, with every `variant_identity_hash` unchanged. Window and universe verified unchanged (2026-04-16 → 2026-07-27, 1,050 name-days; earnings input hashes identical; the chain cache has gained no session for any scope name since 2026-07-27). **§3's conclusion is unaffected: the 14-entry shortfall is confirmed, not narrowed.** *(One correction this rerun produced: the earlier "five constants" drift count was an undercount — it is nine, all display-lane / chain-consistency / lane-resume, none of them an H7 entry-stack or fill-realism constant. See §8a, F8.)* | Rerun PR **#132**, **MERGED to `origin/main` 2026-08-29 evening (`babaa6d`)** — all cited receipt paths resolve on main; report `reports/h7_forward_schwab/2026-08-29-variant-menu-rerun-current-config.md`; receipts `.../variant-receipts/rerun-2026-08-29-current-config/comparable_70_common/{V0_BASELINE,V14_REGISTERED_COHORT_9,V9_LANE_A_OR,V9_LANE_A_OR_COHORT9}.json`, each carrying `baseline_config_hash b86b3188…` and `code_sha 86e8ba6` |
| 6 | **Owner final go** — registration through the guarded door, plus the still-blank OD-3 namespace line from `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` ("`OD-3 2026-__-__: future H7 paper observations MUST USE NEW NAMESPACE h7-forward-schwab-v1`" — currently `[NOT TYPED / NOT AUTHORIZED]`), and (separately, see §4) explicit confirmation of which entry-rule variant is being frozen | **NOT MET (re-verified 2026-08-29).** Owner has typed the loss bar (7) and the drill disposition (B) in `reports/2026-08-14-owner-answers-decision-menu.md`. Of this row's three sub-items, **one is answered and two are not.** (a) **Entry-rule variant — ANSWERED 2026-08-15:** ruling 10 of `reports/2026-08-15-owner-rulings.md` records *"Start it, shortfall in writing"* — configuration **V0**, the current registered rule unchanged, loss bar 7, with the explicit starvation pre-acceptance. That selection is transcribed in §4 and is not re-asked anywhere in this packet. (b) **OD-3 namespace line — STILL BLANK:** on `origin/main`, `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` still carries the un-typed template `OD-3 2026-__-__: …`. (c) **Final go — NOT GIVEN:** nothing has been registered through a guarded door, and §6 is unsigned. | `git show origin/main:reports/2026-08-15-owner-rulings.md` (ruling 10); `git show origin/main:reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` |
| 7 | **Quote-age gate commitment recorded in registration text** (not a registration blocker — a forward obligation created BY registering) | **Not a gate on this registration.** A descriptive daily quote-age sidecar report is **implemented, adversarially reviewed (APPROVE + one fix round), and MERGED to `origin/main`**: brief 32 rev 4 landed as `options_researcher/schwab_quote_age_report.py` via PR #131 (merged 2026-08-29, main @ `86e8ba6`). The `"display_only": true` / `"verdict_eligible": false` pair, the absence of a threshold, and the no-GO/NO_GO-effect rule are emitted and test-enforced on main; the sidecar runs from the next chain capture. Owner ruled 2026-08-28 ("Report now, gate later"): the BLOCKING gate + owner-typed threshold are a binding requirement of the H7 Schwab registration **arc**, triggered by the registration event itself — explicitly NOT satisfied by merging PR #71's caller of `h7_schwab_data_gate.evaluate()` (brief 32 round-3 finding F2). The registration `reason` text must record this commitment and cite the evidence: worst SELECTABLE quote age 0.61–10.38 min across 7 timestamped sessions (10-min block ⇒ 1/7 NO_GO; 15/20-min ⇒ 0/7; n=7, Reviewer-measured 2026-08-28, not owner-typed). | `docs/superpowers/plans/2026-08-28-32-schwab-quote-age-gate-codex-brief.md` ("Recorded for the H7 registration arc"); `reports/2026-08-28-deferred-closeout-rulings.md` ruling 1 + correction addendum. **Both documents landed on `origin/main` via PR #124 (merged 2026-08-29, `316b54f`).** |

Evidence status (updated 2026-08-29 evening): **PR #102 is MERGED** (squash,
main @ `7ddc2ef`) — the packet-integrity prerequisite recorded in earlier
revisions of this caveat is satisfied. All 38 variant receipts, the
`2026-08-14-entry-redesign-variant-menu.md` menu document, and
`V14_REGISTERED_COHORT_9.json` (the receipt cited inside §4's owner-ratified
pre-accept block for the figure of 3) now resolve on `origin/main`. Verified:
`git cat-file -e origin/main:reports/h7_forward_schwab/variant-receipts/comparable_70_common/V9_LANE_A_OR_COHORT9.json`
exits 0. Nothing in §4 is edited here.

Reconciliation note (2026-08-29): this branch previously carried the stale
2026-08-15 00:38 ET draft of this packet, which never saw the 2026-08-15
~10:00 ET re-verification or the 2026-08-16 §4 update that recorded the
owner's V0 ruling. That draft is preserved in history (`d3e0a66`, refreshed at
`766f1f9`). Two separate repairs followed on 2026-08-29: the file **content**
was adopted from `origin/main`'s copy and re-refreshed on top of it, and then
the branch **history** was merged with `origin/main` to resolve the add/add
divergence that had made PR #101 read as a whole-file addition. After both, the
PR diff is this refresh alone — never a reversion of the recorded ruling.

**Until rows 1–6 all read MET, this document is inert. Row 7 is not a registration gate; it records the obligation the registration event itself creates.**

---

## 1. S1 — earliest completion date, shown worked

Owner ruling text (`reports/2026-08-14-owner-answers-decision-menu.md`,
ruling 2) already states the answer verbatim: *"S1's three clean sessions
(earliest ≈ 2026-08-19)."* Shown here so the arithmetic is checkable rather
than taken on faith:

- 3a (the `invocation_source` field) was scheduled to land batched with "the
  current §11 regime-1 landing window" — per the ruling, "tonight" relative
  to the 2026-08-14 ~23:00 ET session. **It did not land** (§0 row 4:
  `grep -rln invocation_source` over `origin/main` returns nothing).
- S1 condition 1 (§7 of the rev-2.1 spec) requires **three consecutive
  scheduled XNYS trading sessions**, each with a verified preclose capture
  receipt carrying the new field, before the honesty bar is met.
- The next three XNYS trading sessions after Friday 2026-08-14 are **Monday
  2026-08-17, Tuesday 2026-08-18, Wednesday 2026-08-19** — no US market
  holiday falls in that span (Labor Day is 2026-09-07).

**Corrected arithmetic (re-verified 2026-08-15).** The binding deadline is
not "when 3a lands" but **whether 3a is landed and synced into the ops
checkout before a given session's 15:45 ET pre-close capture**, because only
that capture writes the receipt that carries the field.

| If 3a lands and ops syncs before… | First qualifying session | S1 completes (3rd session) |
|---|---|---|
| Mon 2026-08-17 15:45 ET | Mon 2026-08-17 | **Wed 2026-08-19** (matches the owner's recorded estimate) |
| Tue 2026-08-18 15:45 ET | Tue 2026-08-18 | Thu 2026-08-20 |
| Wed 2026-08-19 15:45 ET | Wed 2026-08-19 | Fri 2026-08-21 |
| later | that session | +2 trading sessions |

So **2026-08-19 remains reachable**, but it is no longer the default — it now
depends on 3a being written, reviewed, merged, and ops-synced across a
weekend. This is a schedule observation, not a recommendation to rush it:
S1 exists to prove capture provenance is honest, and a hurried 3a that has
to be re-landed would reset the count anyway.

**What actually happened (recorded 2026-08-29).** The two bullets above that
say 3a "did not land" describe 2026-08-15 and are superseded — 3a landed later
that same Saturday (`ef69c94`, 13:10 ET; PR #50 `9e3e304`). Saturday is not an
XNYS session, so the projection above did not move: Mon 2026-08-17 remained
the first qualifying session and Wed 2026-08-19 the projected completion. The
observed outcome was different from the projection: the first tracked preclose
receipt carrying `invocation_source` is 2026-08-19, not 2026-08-17; 2026-08-20
followed; **2026-08-21 has no tracked preclose receipt**, so the streak stopped
at 2 of 3. The owner overruled the streak bar on 2026-08-23 (§0 row 4). Three
consecutive tracked preclose receipts carrying the field do exist later
(2026-08-24 / 25 / 26 / 27 — four, not three), but spec §7 condition 1 requires running
`tools/schwab_chain_manifest.verify_session` over the span, which has **not**
been done, and condition 5's `launchctl list` capture is likewise not on
record. This packet therefore does not claim the S1 bar was met on its own
terms.

---

## 2. What this proposes to register

**Design option (c) — lower the loss bar.** Owner wording, in-session
2026-08-14: *"2.c lets use 7 as well but i want to watch it fire i want all
these different pathways to be running while i monitor."*
(`reports/2026-08-14-owner-answers-decision-menu.md`, ruling 2.)

| Field | Value | Provenance |
|---|---|---|
| `min_losses_for_verdict` | **7** (overrides the frozen `MIN_LOSSES_FOR_VERDICT = 10` / the existing window's `scorer.min_losses_for_verdict: 10`) | **Owner-typed in-session 2026-08-14** |
| Feasibility bar (2026-07-24 gate) | **2 × 7 = 14** expected entries | Menu arithmetic rule, applied to the owner-typed bar |
| Window length | 70 XNYS decision sessions | **Inherited-registered** — matches the existing (paused) `h7-forward-15-v1` window identity (`ledger/h7_forward/events.jsonl` seq 0, `window.decision_session_count: 70`) |
| Cohort | 9 names: AMD, AMZN, CEG, ET, MSFT, NOW, PLTR, TEM, VST (AVGO/CRWV/IREN/NVDA/SMCI/USAR excluded EARNINGS-UNKNOWN) | **Inherited-registered** — `ledger/h7_forward/events.jsonl` seq 0, `universe.included`/`universe.excluded` |
| Entry-rule variant | **V0 — the current registered rule, unchanged.** Selected by the owner in-session 2026-08-15 ("Start it, shortfall in writing"); the higher-firing V9 OR-rule was offered and not taken. Transcribed in §4; §2a below records why V9 is still priced in this packet as the rejected alternative. | **Owner-selected 2026-08-15** — `reports/2026-08-15-owner-rulings.md` ruling 10 |
| All other frozen parameters (fills, costs, liquidity gates, structures/exits, `H7_MONTHLY_AT_RISK=$6,000`, `H7_MAX_OPEN_PER_UNDERLYING=1`, `H7_CLOSE_AT_DTE=30`, `H7_DELTA_TOLERANCE=0.07`, earnings-ban/grace windows, bootstrap config) | Unchanged | **Inherited-registered** — `ledger/h7_forward/events.jsonl` seq 0, `frozen.stage456_parameters`; original design doc `docs/superpowers/specs/2026-07-09-h7-swing-options-design.md` + amendments v1.1–v1.7 |
| Namespace | Proposed `h7-forward-schwab-v1` (per the still-blank OD-3 line) | **Owner-typed, not yet entered** — `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` |

### 2a. Why "V9" appears here at all

> **Resolved 2026-08-15 — the owner chose V0, not V9** (ruling 10,
> `reports/2026-08-15-owner-rulings.md`; transcribed in §4). This subsection is
> kept as the record of *why the question was open* and of what V9 would have
> meant. Nothing here re-opens the choice.

The task that produced this draft named `V9_LANE_A_OR` as the design to
price. That is **not the same thing as an owner ratification of V9.** The
owner's own ruling record types only the loss bar. The variant menu itself
is explicit that it recommends nothing: *"You decide. This document ranks
nothing and recommends no variant. The owner picks, and types the frozen
numbers at registration."* (`reports/h7_forward_schwab/2026-08-14-entry-redesign-variant-menu.md`.)

So: **this draft prices V9 as a candidate because it was asked to, not
because it has been chosen.** Before any registration, the owner needs to
separately confirm (a) whether the entry rule changes at all, and if so (b)
which of the 18 measured variants — most plausibly V9, the only "high-drift"
candidate that clears the *old* 20-entry bar unconstrained — is being frozen.
The variant's own identity is hash-bound in its receipt
(`variant_identity_hash: 9e523154a8ea7566a48fd1f18b3a35f31ebd2291fd5e1df266812136cd0537d3`,
`reports/h7_forward_schwab/variant-receipts/comparable_70_common/V9_LANE_A_OR.json`)
so that whichever variant is chosen, the registration can cite it exactly.

V9's rule change, quoted from the menu: *"Arm on a deep fall **or** a
20-day-high reclaim, instead of requiring both."* Flagged by the menu itself
as **high drift** — a different hypothesis from the registered "beaten-down
name stabilizing" story, not a threshold tweak.

---

## 3. Feasibility arithmetic — quoted honestly

Per `docs/superpowers/2026-07-24-registration-feasibility-gate.md`: bar =
2 × loss bar = **2 × 7 = 14** expected entries over the declared window, on
the declared universe.

**Corrected 2026-08-29 (F6).** The 2026-08-14 menu computed V9 only on the
full 15-name `official_scope_15` universe, so this section originally said no
receipt existed for V9 × the registered 9-name cohort with the position limit
applied, and offered an Inference of ≈7–8 instead. **That receipt now exists**
— `reports/h7_forward_schwab/variant-receipts/comparable_70_common/V9_LANE_A_OR_COHORT9.json`
plus its write-up `reports/h7_forward_schwab/2026-08-15-v9-cohort9-occupancy-followup.md`
— and it measures **7** occupancy-constrained entries (42-session lockout) or
**11** (21-session alternate). **Provenance: receipt on `origin/main` — PR #102
(`wt/brief09-variant-menu-0814`) merged 2026-08-29, `7ddc2ef`.**
The measured 7 sits inside the prior ≈7–8 Inference band: better-evidenced,
same conclusion, still short of the 14-entry bar. The numbers below are laid
out so the gap between "what the menu measured" and "what this registration
would actually run against" stays visible rather than papered over.

### 3a. Menu-computed numbers (exact, receipt-bound — every receipt below is on `origin/main`; PR #102 merged 2026-08-29, `7ddc2ef`)

| Configuration | Universe | Unconstrained entries / window | 95% CI | Occupancy-constrained (42-session hold, matches `H7_CLOSE_AT_DTE=30`) | Source |
|---|---|---|---|---|---|
| V0 (current registered rule) | 15 names | 4.00 | [1.09, 10.21] | 3 | `variant-receipts/comparable_70_common/V0_BASELINE.json` |
| **V14 — current registered rule, restricted to the 9-name registered cohort** | **9 names (exact registered cohort)** | **4.00** | **[1.09, 10.19]** | **3** | `variant-receipts/comparable_70_common/V14_REGISTERED_COHORT_9.json` |
| V9 (OR-armed lane a) | 15 names (`official_scope_15`) | 104.00 | [85.73, 124.67] | 10 (21-session hold: 16) | `variant-receipts/comparable_70_common/V9_LANE_A_OR.json` |

V14 is the number that actually matches this draft's proposed universe (the
9-name registered cohort) **if the entry rule does not change**: **3
occupancy-constrained entries against a 14-entry bar.** That is a shortfall,
not a near-miss.

### 3b. V9 on the 9-name cohort — superseded Derivation, then the measured receipt

**The table immediately below is the superseded 2026-08-14 arithmetic**, kept
so the correction is auditable. It is **not** a tool run: it is arithmetic on
the V9 receipt's own published `entries_per_symbol` field
(`variant-receipts/comparable_70_common/V9_LANE_A_OR.json`), restricted to
the 9 cohort names. The measured replacement follows it.

| Symbol | V9 entries (of 104, unconstrained, 15-name panel) |
|---|---|
| AMD | 0 |
| AMZN | 0 |
| CEG | 0 |
| ET | 0 |
| MSFT | 12 |
| NOW | 28 |
| PLTR | 37 |
| TEM | 0 |
| VST | 2 |
| **Cohort-9 subtotal** | **79** |

The 2026-08-14 reasoning was that the menu's 104 → 10 deflation had been
computed once, on all 15 names together, and could not be validly re-scaled by
a simple ratio, because which names compete for calendar-time under the
one-open-position-per-name cap changes when 6 of the 15 names are removed. The
ratio bound (10/104 ≈ 9.6% applied to 79) gave **≈7–8** as an
order-of-magnitude check only — an Inference, not a receipt.

**Measured replacement (F6, recorded 2026-08-29).** The combination was
subsequently run through the unmodified `tools/h7_entry_variant_menu.py`
pipeline as a new variant, `V9_LANE_A_OR_COHORT9`:

| Metric (V9 arming rule × registered 9-name cohort, 70-session panel 2026-04-16 → 2026-07-27) | Value |
|---|---|
| Entries, unconstrained (flat-book assumption) | **80** / 630 symbol-days |
| Expected entries per 70-session window, unconstrained | 80.00, 95% CI [64.25, 97.99] |
| **Occupancy-constrained, 42-session lockout (primary schedule assumption)** | **7** |
| Occupancy-constrained, 21-session lockout (generous alternate) | 11 |
| Names contributing | 4 of 9 — MSFT 12, NOW 28, PLTR 38, VST 2; AMD/AMZN/CEG/ET/TEM = 0 |
| Top-symbol concentration | PLTR 38/80 = 47.5% |

**Provenance: Tool-computed, receipt-bound —
`variant-receipts/comparable_70_common/V9_LANE_A_OR_COHORT9.json`
(`receipt_hash 5b0fb191…`, `variant_identity_hash 6e47a2cb…`,
`code_sha ccd161f`), write-up
`reports/h7_forward_schwab/2026-08-15-v9-cohort9-occupancy-followup.md`. Both
live on PR #102 (`wt/brief09-variant-menu-0814`) and are NOT yet on
`origin/main`.** The measured 7 falls inside the earlier ≈7–8 Inference band —
the estimate was a reasonable approximation on this axis, and replacing it with
a receipt does not change the conclusion: 7 < 14, and 11 < 14 even under the
generous alternate.

Two readings to avoid. First, the receipt's own `clears_bar_ci_lower_ge_bar:
true` and `point_estimate_ge_bar: true` fields are computed against the
**unconstrained 80-entry count** and the tool's coded **20**-entry bar (2× the
*currently registered* 10-loss rule) — they say nothing about the 14-entry bar
this packet is measured against, and nothing about the occupancy-constrained
figures. Second, both occupancy figures are **upper bounds**: neither nets the
monthly risk sleeve across the lockout, and both assume the book starts flat
every session, which no live window can reproduce.

**Per-symbol note (F9).** PLTR shows **38** entries on the strict 9-name subset
against **37** on the 15-name panel. That is arithmetically consistent, not a
discrepancy: removing AVGO/CRWV/SMCI — which sort ahead of PLTR in the board
resolver's tie-break — frees same-session sleeve capacity that PLTR then takes.
The same mechanism explains why the measured unconstrained cohort-9 total is
**80** rather than the 79 obtained by summing the 15-name panel's per-symbol
counts.

The arithmetic ceiling in the menu (§5 of the menu doc) puts an upper bound
on *any* rule for the 9-name cohort at a 70-session window regardless of
entry logic: 70 ÷ 42 sessions-per-position × 9 names ≈ **15**. So even a
maximally permissive redesign on the registered cohort cannot structurally
clear much past 15 entries in 70 sessions — only marginally above the
14-entry bar (the menu doc's own wording is "the ceiling (~15, plus ~3)"), but the *measured* V9-on-cohort-9 figure (**7**, receipt on
`origin/main` via PR #102) sits far below that ceiling, meaning firing frequency,
not the schedule, is what would need to close the gap.

### 3c. Conclusion against the 14-entry bar

| Configuration | Best available number | Clears 14? |
|---|---|---|
| V0/current rule, 9-name cohort, occupancy-constrained | 3 (menu-computed) | **No** |
| V9, 15-name universe, occupancy-constrained | 10 (menu-computed) | **No** |
| **V9, 9-name cohort, occupancy-constrained (42-session lockout)** | **7** (measured; receipt on `origin/main` via PR #102) | **No** |
| V9, 9-name cohort, occupancy-constrained (21-session alternate) | 11 (measured; same receipt) | **No** |

**Every configuration this packet can price fails the 14-entry pass
condition.** This is not close to a rounding-error miss (3, 7, 10 or 11 vs.
14) — the shortfall persists even for the most permissive high-drift
variant measured, and worsens once that variant is properly restricted to
the smaller registered cohort. The selected configuration is V0, whose
receipt-bound figure is **3**. Replacing the former ≈7–8 Inference with the
measured 7 (F6) narrows the uncertainty without moving the conclusion.

---

## 4. Required disclosure — explicit starvation-risk pre-acceptance (2026-07-24 gate, step 4(b))

The gate's rule: *"the registration is REFUSED as written [...] or (b)
registers anyway with an explicit starvation-risk pre-acceptance clause in
the registration text, quoting the computed base rate and expected-entry
count (the H10 precedent). Silence is not an option."*

**H10 precedent wording, quoted exactly** (`ledger/experiments.jsonl` seq
16, H10b registration): *"H10b REGISTRATION [...] (low fire rate disclosed:
11 historical fires; may stay INSUFFICIENT_SAMPLE) [...] verdict gates at
>=7 losses (owner override of MIN_LOSSES_FOR_VERDICT=10, weaker verdict
disclosed)."*

**Filled-in pre-accept block for this registration (OWNER-SELECTED
2026-08-15, in-session — variant and disposition chosen; see
`reports/2026-08-15-owner-rulings.md` §pm addendum for the exact exchange):**

> **Starvation-risk pre-acceptance (H10 precedent).** This registration's
> configuration is **V0 — the current rule, unchanged** (owner-selected
> 2026-08-15: "Start it, shortfall in writing"; the measured menu offered
> the higher-firing V9 OR-rule and the owner did not take it — the OR-rule
> is honestly a different hypothesis) on the 9-name registered cohort over
> a 70-session window, measured at **3 expected entries (receipt-bound,
> `V14_REGISTERED_COHORT_9.json`) against a 14-entry bar (2× the
> owner-typed 7-loss verdict rule)**. The registration proceeds accepting
> that the window may end **INSUFFICIENT_SAMPLE**, the same outcome already
> recorded for H9 (4 losses vs. a 10-loss bar) and for H10a (closed
> 2026-08-15, STARVED). Multiple-testing disclosure: this figure comes from
> a menu of **18+1 measured entry-rule variants**
> (`reports/h7_forward_schwab/2026-08-14-entry-redesign-variant-menu.md` +
> the 2026-08-15 V9×cohort-9 follow-up receipt); the baseline was chosen,
> so no highest-firing-candidate search bias attaches to this
> configuration, and the menu remains disclosed as a search that found no
> qualifying alternative.
>
> **Owner disposition 2026-08-15: ACCEPT** (selected in-session from the
> explicit three-way question: accept-shortfall / record-longer-first /
> longer-window; recorded same-day in
> `reports/2026-08-15-owner-rulings.md`).

Registration-mechanics note: this selection resolves §6's variant choice
and starvation disclosure. The registration EVENT itself still executes
only after the remaining preconditions complete (S1 three unattended
sessions Mon–Wed 08-17→08-19, fresh backup drill ≥ Mon 08-17, fresh
feasibility receipt at current config, OD-3 namespace line), through the
guarded door, with the owner's §6 sign-off — per steps 5–9 below.
*(Status 2026-08-29 evening: of the four named here, three have cleared —
S1 by owner override, the backup drill on 2026-08-20, and the fresh
feasibility receipt by the 2026-08-29 rerun. The OD-3 namespace line is still
blank. See §0 rows 3–6.)*

---

## 5. Every number, labeled by provenance

| Number | Value | Provenance |
|---|---|---|
| Loss bar | 7 | **Owner-typed in-session 2026-08-14** |
| Feasibility bar | 14 (= 2×7) | Menu arithmetic rule (`docs/superpowers/2026-07-24-registration-feasibility-gate.md`), applied to the owner-typed number |
| Window length | 70 sessions | **Inherited-registered** (`ledger/h7_forward/events.jsonl` seq 0) |
| Cohort (9 names) | AMD/AMZN/CEG/ET/MSFT/NOW/PLTR/TEM/VST | **Inherited-registered** (same event, `universe.included`) |
| V0/cohort-9 occupancy-constrained entries | 3 | **Menu-computed** (`V14_REGISTERED_COHORT_9.json`); **receipt on `origin/main` (PR #102 merged 2026-08-29, `7ddc2ef`).** This is the figure §4's owner-ratified block cites |
| V9/15-name occupancy-constrained entries | 10 | **Menu-computed** (`V9_LANE_A_OR.json`); **receipt on `origin/main` (PR #102 merged 2026-08-29, `7ddc2ef`)** |
| V0/15-name occupancy-constrained entries | 3 | **Menu-computed** (`V0_BASELINE.json`); **receipt on `origin/main` (PR #102 merged 2026-08-29, `7ddc2ef`)** |
| V9/cohort-9 unconstrained entries — superseded derivation | 79 | **Derived (superseded)** — arithmetic on the 15-name panel's per-symbol data; the measured cohort-9 run gives 80 (see F9 note in §3b) |
| V9/cohort-9 unconstrained entries | 80 | **Tool-computed** — `V9_LANE_A_OR_COHORT9.json`; **receipt on `origin/main` (PR #102 merged)** |
| V9/cohort-9 occupancy-constrained entries (42-session lockout) | **7** | **Tool-computed** — `V9_LANE_A_OR_COHORT9.json` (`occupancy_constrained_entries["42"]`); **receipt on `origin/main` (PR #102 merged)**. Supersedes the former ≈7–8 Inference, which it falls inside |
| V9/cohort-9 occupancy-constrained entries (21-session alternate) | 11 | **Tool-computed** — same receipt, `occupancy_constrained_entries["21"]`; **on `origin/main` (PR #102 merged)** |
| Number of variants measured (multiple-testing disclosure) | **19** | **Tool-computed** — V0–V17 = 18 in `2026-08-14-entry-redesign-variant-menu.md`, plus the 2026-08-15 follow-up's 19th variant `V9_LANE_A_OR_COHORT9` (`variant_identity_hash 6e47a2cb…`), which is a distinct measured configuration and is counted as one. **All 38 receipt files and the menu document landed on `origin/main` via PR #102 (merged 2026-08-29, `7ddc2ef`)** |
| All H7a/b/c structure, cost, liquidity, and exit constants | unchanged | **Inherited-registered** (`ledger/h7_forward/events.jsonl` seq 0, `frozen.stage456_parameters`) |
| Entry-rule variant to freeze | **V0 — current rule, unchanged** | **Owner-selected in-session 2026-08-15** — `reports/2026-08-15-owner-rulings.md` ruling 10; transcribed in §4 |
| S1 earliest completion | 2026-08-19 (projected; **never met** — the bar was owner-overridden 2026-08-23, §0 row 4) | Owner's own ruling record + trading-calendar arithmetic shown in §1; override recorded in `data/ritual_authority.py` (`2e7eb3e`) |
| Namespace (`h7-forward-schwab-v1`) | proposed, not typed | **Owner-typed, blank** (`2026-08-09-owner-gate-packet.md` OD-3 line) |

---

## 6. Owner sign-off slot

```
OWNER RULING — H7 bar-7 registration (fill in only after §0 preconditions
all read MET):

Entry-rule variant to freeze: [ V0 current rule / V9_LANE_A_OR / other: ____ ]
Starvation-risk disclosure (§4): [ ACCEPT AS TYPED ABOVE / REDESIGN INSTEAD: ____ ]
OD-3 namespace line: [ typed / not yet ]
Final go to register through the guarded door: [ YES, DATE: ____ / NOT YET ]

Signature / session reference: ____________________
Date: ____________________
```

---

## 7. Next actions, in order, after preconditions clear

1. ~~Independent adversarial review of disposition B~~ — **DONE.** PASS WITH
   FIXES → all fixes applied in `60a999c` → reviewer re-verified → upgraded
   to PASS. (§0 row 2; see §7a for the one loose end.)
2. ~~Merge disposition B to `main`~~ — **DONE 2026-08-15 02:11 ET**, PR #46
   (`fd6af2f`). The unrelated WIP commit `c02558f` was correctly excluded.
3. ~~Re-run the runbook-08 step-8 restore drill~~ — **DONE 2026-08-20.** A
   fresh backup for completed session 2026-08-19 was taken and restored:
   `manifest OK`, `problems 0`, `notes 105`, `ok True` — exactly the predicted
   green. Receipts `reports/h7_receipts/backup/2026-08-19.json` and
   `reports/h7_receipts/backup_restore/2026-08-20.json`, both on `origin/main`
   (§0 row 3).
4. ~~Land 3a (`invocation_source` field)~~ — **DONE 2026-08-15**, `ef69c94`
   via PR #50 (`9e3e304`); present on `origin/main` (§0 row 4).
5. ~~Track S1 to completion~~ — **CLOSED BY OWNER OVERRIDE 2026-08-23**, not by
   the streak. The run reached 2 of 3 (08-19, 08-20) and broke on the 08-21
   gap; the owner overruled the bar and flipped
   `exact_session_source_active=True` (`2e7eb3e`). Spec §7 conditions 1 and 5
   were never executed — see §0 row 4 and §1 for what that does and does not
   entitle the packet to claim.
6. Owner completes §6 — **variant choice and starvation-risk disclosure are
   already answered** (V0 + ACCEPT, 2026-08-15, §4). What remains is the OD-3
   namespace line and the final go.
7. ~~If a non-baseline variant is chosen, re-run `tools.h7_entry_variant_menu`
   for the chosen-variant × 9-name-cohort × 70-session combination~~ — **MOOT:
   the owner chose the baseline V0, whose cohort-9 figure (3) was already
   receipt-bound.** The V9 × cohort-9 combination was measured anyway on
   2026-08-15 (7 entries, 42-session lockout); that receipt is on PR #102 and
   **must land** before this packet's §3b/§3c/§5 citations resolve on `main`.
8. **New, from the 2026-08-28 rulings:** the registration `reason` text must
   record the quote-age gate commitment described in §0 row 7, citing the
   Reviewer-measured 2026-08-28 evidence. This is an obligation created by
   registering, not a precondition of it.
9. Owner registers through the guarded door (`register_window_real` or the
   equivalent typed API for the `h7-forward-schwab-v1` namespace), citing
   this packet, the final feasibility receipt, and the completed §4
   disclosure verbatim in the registration `reason` text.
10. Independent adversarial review of the registration event itself, per
   this repo's standing practice for H7 registrations.

---

## 7a. One loose end found during re-verification (2026-08-15)

**The disposition-B adversarial review has no committed receipt file.**

The review itself is not in doubt — it ran, produced 5 blockers, the fixes
landed in `60a999c`, and the reviewer re-verified and upgraded to PASS. But
that record lives in the **PR #46 description and the commit message**, which
is a weaker home than the pattern this lane has otherwise followed:

| Review | Receipt |
|---|---|
| H7 Schwab lane, 2026-08-12 | `reports/h7_forward_schwab/2026-08-12-adversarial-review-receipt.md` (committed) |
| B2 receipt path, 2026-08-13 | `reports/h7_forward_schwab/2026-08-13-b2-adversarial-review-receipt.md` (committed) |
| Recovery branch, 2026-08-13 | `reports/h7_forward_schwab/2026-08-13-recovery-branch-adversarial-review-receipt.md` (committed) |
| **Disposition B, 2026-08-15** | `reports/h7_forward_schwab/2026-08-15-drill-disposition-b-review-receipt.md` (**committed 2026-08-29**, transcription — PR #133, `3155fab`) |

Why this matters, in plain terms: disposition B is the change that lets the
restore drill *accept* 105 hash mismatches it previously refused. That is
exactly the kind of relaxation whose justification a future reader will want
to audit from the repository itself, not from a GitHub API call. **The
durability argument is the sharper one:** the record currently lives on a
third-party service this project does not control. A PR description can be
edited after the fact, is not covered by the repo's backup or restore drill,
and disappears if the hosting account or repository does — none of which is
true of a committed file under `reports/`. Every other reviewed change in this
lane is auditable from a restic snapshot; this one is not. The gate
packet's prerequisite #4 language is about the H7 lane's reviews generally,
and every other review in that lane has a file.

**Recommendation — FULFILLED 2026-08-29 (owner-directed):** the transcription
now exists on `origin/main` via PR #133 (`3155fab`). Original wording kept for
the record: before registration, transcribe the PR #46 review trail into
`reports/h7_forward_schwab/2026-08-15-drill-disposition-b-review-receipt.md`,
naming the five blockers, the reviewer's M14–M16 mutations, and the
re-verification that upgraded PASS WITH FIXES → PASS. This is a docs-only
transcription of an event that already happened — it does not re-open the
review and does not change precondition row 2's **MET** status.

---

## 8. Re-verification log (2026-08-15, scheduled weekend-cleanup session)

Read-only checks run against `origin/main` @ `7b91ae3` from an isolated
worktree. No ledger write, no fact append, no provider call, no production
mutation.

| Check | Command | Result |
|---|---|---|
| Disposition B on main | `git merge-base --is-ancestor 54e9a00 origin/main` | exit 0 (ancestor) |
| Facts recorded | `git show origin/main:ledger/facts.log \| grep -c H7_INPUT_BINDING_INVALIDATION` | `7` |
| Facts cover the right receipts | same, path tokens extracted | 2026-07-17/20/21/22/23/24/27 — matches the spec's enumeration |
| PR #46 state | `gh pr view 46 --json state,mergedAt` | `MERGED`, `2026-08-15T06:11:42Z` |
| 3a landed? | `grep -rln invocation_source --include='*.py' --include='*.sh' --include='*.plist'` | **no matches** |
| Ops checkout synced | `git -C ~/options-validator-ops log -1` | `7b91ae3` (= `origin/main`) |
| V14 receipt figures | `V14_REGISTERED_COHORT_9.json` | `expected_entries_per_window` 4.0, CI [1.09, 10.19], `occupancy_constrained_entries["42"]` = **3** — §3a table confirmed |
| V9 receipt figures | `V9_LANE_A_OR.json` | 104.0, CI [85.73, 124.67], occupancy 42 = **10**, 21 = 16 — §3a table confirmed |
| V9 cohort-9 subtotal | `entries_per_symbol` summed over the 9 cohort names | MSFT 12 + NOW 28 + PLTR 37 + VST 2 = **79** — §3b table confirmed |
| Variant count | receipts in `comparable_70_common/` | V0–V17 = **18** — §4 multiple-testing disclosure confirmed. *(Superseded 2026-08-29: **19**, including the 2026-08-15 follow-up variant `V9_LANE_A_OR_COHORT9` — see §5 and §8a.)* |

**Nothing in §2–§6 changed.** The feasibility arithmetic, the provenance
labels, the starvation-risk pre-accept block, and the owner sign-off slot are
all as first drafted; every number in them re-verified against its receipt.

One wording note for the owner, since it affects how the shortfall reads: the
figure sometimes quoted for "the registered 9-name cohort" is **≈10**, but
that number is V9 measured on **all 15 names** (`V9_LANE_A_OR.json`,
`universe_size: 15`). The 9-name-cohort figures are **3** (current rule,
`V14_REGISTERED_COHORT_9.json`) and **≈7–8** (V9 re-aggregated, Inference —
no receipt). Against a 14-entry bar the distinction does not change the
verdict — all three fall short — but the packet quotes the cohort-correct
numbers rather than the more flattering one. *(Superseded in part on
2026-08-29: the "≈7–8, no receipt" figure is now the measured **7** — see §3b
and §8a. The 3-vs-10 point stands.)*

---

## 8a. Re-verification log (2026-08-29) + PR #102 review corrections

Read-only checks run against `origin/main` @ `4790cba`. No ledger write, no
fact append, no provider call, no production mutation.

| Check | Command | Result |
|---|---|---|
| Disposition B still on main | `git merge-base --is-ancestor 54e9a00 origin/main` | exit 0 |
| Review fix commit on main | `git merge-base --is-ancestor 60a999c origin/main` | exit 0 |
| Disposition-B review receipt | `git ls-tree -r --name-only origin/main -- docs/superpowers/reviews/`; `git grep -il 'disposition b' origin/main -- '*.md'` | **still none** — §7a stays open |
| Post-merge drill green | `git show origin/main:reports/h7_receipts/backup_restore/2026-08-20.json` | `manifest OK`, `problems` 0, `notes` 105, `ok true`, `completed_session 2026-08-19` |
| 3a landed | `git grep -l invocation_source origin/main -- '*.py'` | 7 files incl. `options_researcher/schwab_chain_capture.py`, `data/ritual_authority.py` |
| 3a landing commit | `git log -S invocation_source origin/main -- '*.py'` | `ef69c94`, 2026-08-15 13:10 ET (PR #50 `9e3e304`) |
| Preclose receipts carrying the field | `git ls-tree -r --name-only origin/main -- reports/schwab_chains/` to list them, then `git show origin/main:reports/schwab_chains/<date>/preclose.json` piped through a JSON read of the `invocation_source` key to get each value (`ls-tree` shows filenames only, never field values) | 2026-08-19, -20, -24, -25, -26, -27 all read `invocation_source: "launchd"`; **no 2026-08-21 preclose receipt exists**; 2026-08-14/preclose.json exists but predates the field and reads `<ABSENT>` (None) |
| S1 bar disposition | `git show origin/main:data/ritual_authority.py` | `exact_session_source_active=True`, owner-override comment, commit `2e7eb3e` (2026-08-23) |
| OD-3 line | `git show origin/main:reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` | still the un-typed template |
| Variant ruling | `git show origin/main:reports/2026-08-15-owner-rulings.md` | ruling 10 — V0, "Start it, shortfall in writing" |
| V9 × cohort-9 receipt | `git show origin/wt/brief09-variant-menu-0814:.../V9_LANE_A_OR_COHORT9.json` | `occupancy_constrained_entries {"21": 11, "42": 7}`, `expected_entries_per_window 80.0`, `entries_per_symbol.PLTR 38`, `code_sha ccd161f` |

**Reproduction note (F8) — SUPERSEDED 2026-08-29 evening; original text kept
below for audit.** The rerun directed by the owner **succeeded**, so
reproduction is no longer pinned to the receipts' recorded `code_sha`. It was
done by writing a **fresh receipt set to a new dated directory** via the menu
tool's own `--outdir` flag — never by an in-place overwrite, which
`write_receipt` correctly refuses and which nobody should attempt. See §0
row 5 and `reports/h7_forward_schwab/2026-08-29-variant-menu-rerun-current-config.md`
(PR #132).

Two corrections the rerun produced:

1. **The drift is nine constants, not five.** `config_hash()` hashes *every*
   uppercase name in `config.py`. Measured directly between the receipts' own
   `code_sha 5a00a50` and `86e8ba6` (`config.py` is byte-identical at
   `5a00a50` and `ccd161f`, which is why both receipt sets recorded
   `031e711a…`): eight constants added — `CONSISTENCY_DELTA_JUMP_ABS`,
   `CONSISTENCY_UNDERLYING_SMALL_MOVE`,
   `CONSISTENCY_SPREAD_BLOWOUT_MIN_RATIO`, `CONSISTENCY_MAX_EXAMPLES`,
   `CONTEXT_LANE_ENABLED`, `PICK_TOP_N`, `H5_RESUME_FLOOR_SESSION`,
   `H10B_RESUME_FLOOR_SESSION` — plus `SHORT_CONTEXT_ENABLED` `False → True`.
   The earlier count appears to have been taken against a different baseline.
   **No conclusion moves:** all nine are display-lane, chain-consistency-shadow
   or lane-resume constants, and none is an H7 entry-stack, arming, routing,
   liquidity, fill-realism, earnings-gate or risk-sizing constant.
2. **The byte-identity claim held empirically.** `h7_signals`, `h7_watch`,
   `h7_board`, `h7_lanes`, `h7_cohort`, `h7_scope`, `h7_earnings`, the chain
   reader, `underlying_closes`, `research/hashing.py` and
   `tools/h7_entry_variant_menu.py` are byte-identical between `5a00a50` and
   `86e8ba6`, and the rerun reproduced every figure exactly — the empirical
   confirmation of what that inspection predicted.

*Original wording (2026-08-29 afternoon, before the rerun):* "`config_hash()`
on current `origin/main` is `b86b3188…`, which no longer matches the variant
receipts' recorded `baseline_config_hash 031e711a…`. Five unrelated constants
moved since the receipts were written; the review that found this verified
that **no H7 entry-stack or fill-realism constant changed**, and that
`h7_signals` / `h7_watch` / `h7_board` / `h7_lanes` / the chain reader and
`research/hashing.py` are byte-identical to the merge-base. Consequence for
anyone re-checking these numbers: **reproduction is pinned to each receipt's
recorded `code_sha` (`5a00a50` for the 2026-08-14 menu, `ccd161f` for the
2026-08-15 cohort-9 follow-up) — not 're-run it on main.'** `write_receipt`
fail-closes with `FileExistsError` on drift, so an error there means config
drift, not tampering. (Repo-verified 2026-08-29: hash computed from a checkout
whose `config.py` and `research/hashing.py` are identical to `origin/main`.)"
