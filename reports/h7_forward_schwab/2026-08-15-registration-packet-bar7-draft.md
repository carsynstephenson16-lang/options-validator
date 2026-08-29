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

## 0. Blocking preconditions — current status (checked this session, 2026-08-15)

> **Refreshed 2026-08-29** against `origin/main` @ `4790cba`. Every status in
> the table below was re-verified that day by a command run against main; the
> command is named in each row's Evidence cell. The original 2026-08-15
> 00:38 ET wording is preserved in git history (`d3e0a66`).

Registration of the bar-7 window **cannot happen** until all five of these
clear. As of the 2026-08-29 refresh, **rows 1–4 are cleared and row 5 remains
open** — with two clearances that must not be read as clean passes: row 2
cleared with a recorded provenance gap (no committed review receipt), and row
4 cleared by owner override rather than by the observed three-session streak.

| # | Precondition | Status found | Evidence |
|---|---|---|---|
| 1 | **Disposition B merged to main** | **MET (re-verified 2026-08-29).** Commit `54e9a00` ("feat(drill): disposition B — recorded input-binding invalidations") is an ancestor of `origin/main` @ `4790cba`: `git merge-base --is-ancestor 54e9a00 origin/main` exits 0. It landed via **PR #46** (merge `fd6af2f`, 2026-08-15) from `claude/drill-disposition-b-final`. The unrelated WIP commit `c02558f` ("D-6a alignment check partial ... NOT green"), which sat on the older `claude/drill-disposition-b` branch, was correctly **not** merged as part of it. | `git merge-base --is-ancestor 54e9a00 origin/main` (exit 0); `git log --merges --ancestry-path 54e9a00..origin/main` |
| 2 | **Independent adversarial review of disposition B, PASS or PASS WITH FIXES resolved** | **MET, with a recorded provenance gap (re-verified 2026-08-29).** The review ran and resolved: PR #46's description records *"independent adversarial review PASS WITH FIXES (5 blockers incl. two novel mutation survivors and a detection-only bypass via `git branch -f`); all fixes applied; reviewer re-verified with its own repros → upgraded to PASS"*, and the corresponding fix commit `60a999c` ("fix(review): apply adversarial-review blockers B1-B5 and C2") is an ancestor of `origin/main`. **The gap:** unlike the 2026-08-12 and 2026-08-13 receipts, this review has **no committed receipt file**. A tracked-file search of `origin/main` over `docs/superpowers/reviews/`, `reports/**` and every `*.md` mentioning "disposition B", restricted to 2026-08-15..2026-08-29, returns no disposition-B review receipt. The record therefore lives in GitHub PR metadata and a commit message rather than in this repo's own receipt convention — a documentation debt to close, not evidence that the review is missing. | `gh pr view 46 --json body`; `git merge-base --is-ancestor 60a999c origin/main` (exit 0); `git ls-tree -r --name-only origin/main -- docs/superpowers/reviews/`; `git grep -il 'disposition b' origin/main -- '*.md'` |
| 3 | **Drill re-run GREEN post-merge** | **MET (re-verified 2026-08-29).** A restore-drill receipt newer than the 2026-08-14 failure now exists on `origin/main`: `reports/h7_receipts/backup_restore/2026-08-20.json` — `receipt_type "backup_restore"`, `completed_session 2026-08-19`, `verified_at_utc 2026-08-20T14:18:21Z`, and a `verification` block reading `manifest "OK"`, `problems` empty (length 0), `notes` 105 entries, `ok true`, over 25 receipts / 7 data gates on scope `h7-forward-15-v1`. It restores the paired fresh backup `reports/h7_receipts/backup/2026-08-19.json` (snapshot `0774b5c8…`) — a snapshot taken *after* the disposition-B facts landed, which the spec identified as the only route to green (the immutable 2026-08-14 snapshot predates the facts and can never pass). This supersedes `reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`. | `git show origin/main:reports/h7_receipts/backup_restore/2026-08-20.json` (fields quoted verbatim above); `git show origin/main:reports/h7_receipts/backup/2026-08-19.json` |
| 4 | **S1 — three consecutive verifying trading sessions** (§7 of `docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md`, ratified via owner decision D-4/menu item 3, sub-fork **3a**) | **CLEARED BY OWNER OVERRIDE — not by the observed streak (re-verified 2026-08-29).** Sub-fork **3a** HAS landed: `invocation_source` is present on `origin/main` in `options_researcher/schwab_chain_capture.py`, `data/ritual_authority.py`, `tools/job_health_digest.py` and four test modules; introduced by `ef69c94` (2026-08-15 13:10 ET), merged via PR #50 (`9e3e304`, 2026-08-15). **Recomputed S1 arithmetic:** the original row assumed a Friday 2026-08-14 landing; 3a in fact landed Saturday 2026-08-15, which is not an XNYS session, so the next three consecutive sessions are unchanged — Mon 2026-08-17, Tue 2026-08-18, Wed 2026-08-19 (no US market holiday in span; Labor Day is 2026-09-07) — and the projected earliest completion stays **2026-08-19**. **What actually happened:** the first tracked preclose receipt carrying the field is `reports/schwab_chains/2026-08-19/preclose.json` (`invocation_source: "launchd"`), followed by 2026-08-20; **2026-08-21 has no tracked preclose receipt**, so the streak broke at 2 of 3. The owner then **overruled the streak bar in-session 2026-08-23**, recorded on main in `data/ritual_authority.py` beside `exact_session_source_active=True` (commit `2e7eb3e`): *"S1's 3-session streak bar is overruled … Evidence at flip time: clean launchd receipts 08-19 and 08-20 (streak 2 of 3); the 08-21 gap was a network outage, not a source defect."* Not re-run for this refresh: spec §7 conditions 1 and 5 (executing `tools/schwab_chain_manifest.verify_session` across the span, and capturing `launchctl list` verbatim). §1 below still describes 3a as not-yet-landed; that text predates this refresh and is superseded by this row. | `git grep -l invocation_source origin/main -- '*.py'`; `git log -S invocation_source origin/main -- '*.py'`; `git show origin/main:data/ritual_authority.py`; `git ls-tree -r --name-only origin/main -- reports/schwab_chains/` |
| 5 | **Owner final go** — registration through the guarded door, plus the still-blank OD-3 namespace line from `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` ("`OD-3 2026-__-__: future H7 paper observations MUST USE NEW NAMESPACE h7-forward-schwab-v1`" — currently `[NOT TYPED / NOT AUTHORIZED]`), and (separately, see §3) explicit confirmation of which entry-rule variant is being frozen | **NOT MET (re-verified 2026-08-29).** Owner has typed the loss bar (7) and the drill disposition (B) in `reports/2026-08-14-owner-answers-decision-menu.md`. Of this row's three sub-items, one has since been answered on main and two have not. (a) **Entry-rule variant — ANSWERED 2026-08-15:** ruling 10 of `reports/2026-08-15-owner-rulings.md` records *"Start it, shortfall in writing"* — configuration **V0** (the current registered rule, unchanged), loss bar 7, with the explicit starvation pre-acceptance. §2/§2a/§3/§4 of **this branch copy** still present the variant as unresolved; that wording predates the ruling and is stale (see the divergence note below the table). (b) **OD-3 namespace line — STILL BLANK:** on `origin/main`, `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` still carries the un-typed template `OD-3 2026-__-__: …`. (c) **Final go — NOT GIVEN:** nothing has been registered through a guarded door. | `git show origin/main:reports/2026-08-15-owner-rulings.md` (ruling 10); `git show origin/main:reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` |
| 6 | **Quote-age gate commitment recorded in registration text** (not a registration blocker — a forward obligation created BY registering) | **Not a gate on this registration.** A descriptive daily quote-age sidecar report ships now (`options_researcher/schwab_quote_age_report.py`, brief 32 rev 4, HANDED OFF 2026-08-28; display-only, `"display_only": true` / `"verdict_eligible": false`, no threshold, no GO/NO_GO effect). Owner ruled 2026-08-28 ("Report now, gate later"): the BLOCKING gate + owner-typed threshold are a binding requirement of the H7 Schwab registration **arc**, triggered by the registration event itself — explicitly NOT satisfied by merging PR #71's caller of `h7_schwab_data_gate.evaluate()` (brief 32 round-3 finding F2). The registration `reason` text must record this commitment and cite the evidence: worst SELECTABLE quote age 0.61–10.38 min across 7 timestamped sessions (10-min block ⇒ 1/7 NO_GO; 15/20-min ⇒ 0/7; n=7, Reviewer-measured 2026-08-28, not owner-typed). | `docs/superpowers/plans/2026-08-28-32-schwab-quote-age-gate-codex-brief.md` ("Recorded for the H7 registration arc"); `reports/2026-08-28-deferred-closeout-rulings.md` ruling 1 + correction addendum |

Evidence caveat: the variant receipts cited in §2a/§3a/§3b/§5 currently exist
only on PR #102 (wt/brief09-variant-menu-0814, additive-only, conflict-free).
Landing #102 before or alongside this ruling is a packet-integrity
prerequisite; the numbers are otherwise branch-only evidence.

Divergence note (recorded 2026-08-29, not yet reconciled): `origin/main`
@ `4790cba` already carries a file at this same path, and it is **not** this
document. Main's copy descends from a 2026-08-15 ~10:00 ET re-verification
plus a 2026-08-16 update (`3b688bc`, `32d1881`); this branch copy is the
original 2026-08-15 00:38 ET draft (`d3e0a66`) and never saw either. The
material difference is §4: main's copy records the owner's 2026-08-15
selection of **V0 + ACCEPT the shortfall**, while §2/§2a/§3/§4 here still ask
that question as open. Merging this branch as-is would overwrite main's copy
and remove that recorded ruling. Reconciling the two copies is a prerequisite
to putting this document in front of the owner; only §0 was refreshed here.

**Until rows 1–5 all read MET, this document is inert. Row 6 is not a registration gate; it records the obligation the registration event itself creates.**

---

## 1. S1 — earliest completion date, shown worked

Owner ruling text (`reports/2026-08-14-owner-answers-decision-menu.md`,
ruling 2) already states the answer verbatim: *"S1's three clean sessions
(earliest ≈ 2026-08-19)."* Shown here so the arithmetic is checkable rather
than taken on faith:

- 3a (the `invocation_source` field) is scheduled to land batched with "the
  current §11 regime-1 landing window" — per the ruling, "tonight" relative
  to the 2026-08-14 ~23:00 ET session. As of this drafting session it has
  **not yet landed** (§0 row 4).
- S1 condition 1 (§7 of the rev-2.1 spec) requires **three consecutive
  scheduled XNYS trading sessions**, each with a verified preclose capture
  receipt carrying the new field, before the honesty bar is met.
- The next three XNYS trading sessions after a 2026-08-14 (Friday) landing
  are **Monday 2026-08-17, Tuesday 2026-08-18, Wednesday 2026-08-19** — no
  US market holiday falls in that span (Labor Day is 2026-09-07).
- The third session's verified receipt completes S1 at the earliest on
  **2026-08-19**, matching the owner's own record. If 3a lands later than
  the night of 2026-08-14, the three-session count shifts forward by the
  same number of trading days.

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
| Entry-rule variant | **UNRESOLVED — see §3.** This draft prices the **V9_LANE_A_OR** variant per the drafting instruction that produced this packet, but the owner ruling record itself types only the loss bar, not an entry-rule change. | Flagged, not asserted as decided |
| All other frozen parameters (fills, costs, liquidity gates, structures/exits, `H7_MONTHLY_AT_RISK=$6,000`, `H7_MAX_OPEN_PER_UNDERLYING=1`, `H7_CLOSE_AT_DTE=30`, `H7_DELTA_TOLERANCE=0.07`, earnings-ban/grace windows, bootstrap config) | Unchanged | **Inherited-registered** — `ledger/h7_forward/events.jsonl` seq 0, `frozen.stage456_parameters`; original design doc `docs/superpowers/specs/2026-07-09-h7-swing-options-design.md` + amendments v1.1–v1.7 |
| Namespace | Proposed `h7-forward-schwab-v1` (per the still-blank OD-3 line) | **Owner-typed, not yet entered** — `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md` |

### 2a. Why "V9" appears here at all

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

**No receipt in the variant menu computes V9 restricted to the 9-name
registered cohort with the registered position limit applied.** The menu
computed V9 only on the full 15-name `official_scope_15` universe. The
numbers below are the closest sourced figures, laid out so the gap between
"what the menu measured" and "what this registration would actually run
against" is visible rather than papered over.

### 3a. Menu-computed numbers (exact, receipt-bound)

| Configuration | Universe | Unconstrained entries / window | 95% CI | Occupancy-constrained (42-session hold, matches `H7_CLOSE_AT_DTE=30`) | Source |
|---|---|---|---|---|---|
| V0 (current registered rule) | 15 names | 4.00 | [1.09, 10.21] | 3 | `variant-receipts/comparable_70_common/V0_BASELINE.json` |
| **V14 — current registered rule, restricted to the 9-name registered cohort** | **9 names (exact registered cohort)** | **4.00** | **[1.09, 10.19]** | **3** | `variant-receipts/comparable_70_common/V14_REGISTERED_COHORT_9.json` |
| V9 (OR-armed lane a) | 15 names (`official_scope_15`) | 104.00 | [85.73, 124.67] | 10 (21-session hold: 16) | `variant-receipts/comparable_70_common/V9_LANE_A_OR.json` |

V14 is the number that actually matches this draft's proposed universe (the
9-name registered cohort) **if the entry rule does not change**: **3
occupancy-constrained entries against a 14-entry bar.** That is a shortfall,
not a near-miss.

### 3b. Derived number — V9's per-symbol receipt data, re-aggregated to the 9-name cohort

This is **not** a new tool run. It is arithmetic on the V9 receipt's own
published `entries_per_symbol` field
(`variant-receipts/comparable_70_common/V9_LANE_A_OR.json`), restricted to
the 9 cohort names:

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

**No occupancy-constrained (position-limit-applied) figure for this
cohort-9 subtotal exists in any receipt.** The menu's 104 → 10 deflation was
computed once, on all 15 names together, by the position-limit replay tool;
it cannot be validly re-scaled by a simple ratio, because which names
compete for calendar-time under the one-open-position-per-name cap changes
when 6 of the 15 names are removed. A rough, explicitly low-confidence bound
using that ratio (10/104 ≈ 9.6%) applied to 79 gives **≈7–8**, offered only
as an order-of-magnitude check, not a number fit to register against.
**(Inference — not menu-computed, not receipt-bound. A registration must
either re-run `tools.h7_entry_variant_menu` with the exact cohort-9 + V9
combination, or accept this gap explicitly.)**

The arithmetic ceiling in the menu (§5 of the menu doc) puts an upper bound
on *any* rule for the 9-name cohort at a 70-session window regardless of
entry logic: 70 ÷ 42 sessions-per-position × 9 names ≈ **15**. So even a
maximally permissive redesign on the registered cohort cannot structurally
clear much past 15 entries in 70 sessions — comfortably above the 14-entry
bar in principle, but the *measured* V9-on-cohort-9 estimate (≈7–8) sits far
below that ceiling, meaning firing frequency, not the schedule, is what
would need to close the gap.

### 3c. Conclusion against the 14-entry bar

| Configuration | Best available number | Clears 14? |
|---|---|---|
| V0/current rule, 9-name cohort, occupancy-constrained | 3 (menu-computed) | **No** |
| V9, 15-name universe, occupancy-constrained | 10 (menu-computed) | **No** |
| V9, 9-name cohort, occupancy-constrained | ≈7–8 (Inference, not receipt-bound) | **No** |

**Every configuration this draft can price fails the 14-entry pass
condition.** This is not close to a rounding-error miss (3.0 or 10.0 vs.
14) — the shortfall persists even for the most permissive high-drift
variant measured, and worsens once that variant is properly restricted to
the smaller registered cohort.

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

**Filled-in pre-accept block for this registration (DRAFT — not yet
owner-ratified; template only):**

> **Starvation-risk pre-acceptance (H10 precedent).** This registration's
> proposed configuration [V0 current rule / V9 / other — OWNER TO CONFIRM]
> on the 9-name registered cohort over a 70-session window is measured at
> **[3 / ≈7–8 / OTHER — pending final variant choice] expected entries
> against a 14-entry bar (2× the owner-typed 7-loss verdict rule)**. The
> registration proceeds accepting that the window may end
> **INSUFFICIENT_SAMPLE**, the same outcome already recorded for H9 (4
> losses vs. a 10-loss bar) and currently open for H10a/H10b. Multiple-testing
> disclosure: this figure comes from a menu of **18 measured entry-rule
> variants** (`reports/h7_forward_schwab/2026-08-14-entry-redesign-variant-menu.md`);
> if a non-baseline variant is chosen, choosing the highest-firing
> non-forbidden candidate from that set of 18 is itself a search and is
> disclosed as such, per the menu's own multiple-testing note.
>
> **[OWNER TYPES: accept / redesign instead (longer window, shorter hold,
> wider universe — each is its own registration decision per menu §8) /
> other]**

This block **must be completed by the owner** before registration — Claude
proposes the number and the wording; the owner enters the frozen decision,
per the standing rule in `CLAUDE.md` ("You own the numbers").

---

## 5. Every number, labeled by provenance

| Number | Value | Provenance |
|---|---|---|
| Loss bar | 7 | **Owner-typed in-session 2026-08-14** |
| Feasibility bar | 14 (= 2×7) | Menu arithmetic rule (`docs/superpowers/2026-07-24-registration-feasibility-gate.md`), applied to the owner-typed number |
| Window length | 70 sessions | **Inherited-registered** (`ledger/h7_forward/events.jsonl` seq 0) |
| Cohort (9 names) | AMD/AMZN/CEG/ET/MSFT/NOW/PLTR/TEM/VST | **Inherited-registered** (same event, `universe.included`) |
| V0/cohort-9 occupancy-constrained entries | 3 | **Menu-computed** (`V14_REGISTERED_COHORT_9.json`) |
| V9/15-name occupancy-constrained entries | 10 | **Menu-computed** (`V9_LANE_A_OR.json`) |
| V9/cohort-9 unconstrained entries (subtotal) | 79 | **Derived** — arithmetic on menu-receipt per-symbol data, not a new tool run |
| V9/cohort-9 occupancy-constrained entries | ≈7–8 | **Inference** — not menu-computed, no receipt; explicitly flagged low-confidence |
| Number of variants measured (multiple-testing disclosure) | 18 | **Menu-computed** (`2026-08-14-entry-redesign-variant-menu.md`) |
| All H7a/b/c structure, cost, liquidity, and exit constants | unchanged | **Inherited-registered** (`ledger/h7_forward/events.jsonl` seq 0, `frozen.stage456_parameters`) |
| Entry-rule variant to freeze (V0 vs. V9 vs. other) | **not set** | **Owner decision required — see §2a** |
| S1 earliest completion | 2026-08-19 | Owner's own ruling record + trading-calendar arithmetic shown in §1 |
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

1. Independent adversarial review of disposition B (branch
   `claude/drill-disposition-b`, commit `54e9a00`) — request and land a
   PASS or PASS-WITH-FIXES-resolved receipt under
   `reports/h7_forward_schwab/`.
2. Merge disposition B to `main` (the unrelated WIP commit `c02558f` on the
   same branch stays separate — do not merge it as part of this).
3. Re-run the runbook-08 restore drill against the merged, reviewed state;
   confirm GREEN (0 problems, notes only) before treating the drill
   requirement as satisfied.
4. Confirm 3a (`invocation_source` field) has landed in the hashed
   `options_researcher/` landing window per ruling item 3.
5. Track S1 to completion: three consecutive verified preclose receipts,
   earliest Mon 2026-08-17 → Wed 2026-08-19 (§1); re-check the date if 3a
   lands later than assumed here.
6. Owner completes §6 (variant choice, starvation-risk disclosure, OD-3
   namespace line).
7. If a non-baseline variant (e.g. V9) is chosen, re-run
   `tools.h7_entry_variant_menu` for the exact chosen-variant ×
   9-name-cohort × 70-session combination to replace the §3b/§3c estimates
   with a receipt-bound number before the registration text is finalized.
8. Owner registers through the guarded door (`register_window_real` or the
   equivalent typed API for the `h7-forward-schwab-v1` namespace), citing
   this packet, the final feasibility receipt, and the completed §4
   disclosure verbatim in the registration `reason` text.
9. Independent adversarial review of the registration event itself, per
   this repo's standing practice for H7 registrations.
