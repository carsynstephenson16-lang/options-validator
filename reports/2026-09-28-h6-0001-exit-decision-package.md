# H6-0001 exit — owner decision package

**Date:** 2026-09-28 · **Revision:** 3 (adversarial review round 1: FAIL → all 15 findings applied; round 2: PASS WITH FIXES → all 8 applied; receipt `reports/2026-09-28-h6-0001-exit-package-adversarial-review.md`) · **Status:** DRAFT — owner ruling required · **Author:** Claude session (agent-drafted; no frozen number typed, nothing booked)

**What this session did NOT touch:** `ledger/`, `data/positions/h6_positions.csv`, `config.py`, any cache byte, any receipt. Every number is **Tool-computed** in this session from committed receipts or local caches unless labelled otherwise; formulas are shown so each can be re-derived. The independent reviewer re-derived the rev-1 numbers (round 1) and the rev-2 additions (round 2); the rev-3 F15 counterfactual was re-derived by both the reviewer and this session.

---

## 1. Plain English

**The idea.** On 2026-07-13 the H6 paper book "bought" one NVDA call (a bet that NVDA rises) for $920.65. H6's rules said: sell it once only 21 days remain (2026-08-28), or sooner if it doubles. It never doubled. But nothing could run on 08-28 under H6's registered machinery: its evaluator reads only the ThetaData end-of-day cache, which stopped on 2026-07-27, and since 2026-08-14 the lane has also been paused by **your ruling D-1=F1**. When you approved moving H10b and H5 (only them) to Schwab data on 2026-08-17/19, the recorded amendment text — agent-drafted, appended under delegation — added "All other lanes' D-1=F1 pause is unchanged"; nobody raised H6's open position at the time. The ritual printed "H6: MISSING - stale" on 08-31, and nothing acted on it. The option expired on 2026-09-18, and the book still shows it open. You are deciding **which number goes into the record as this trade's result, and how it gets there.**

**Terms used**
- **Call option** — the right to buy 100 shares at a fixed price until a set date.
- **Strike** — that fixed price ($220 here).
- **Expiration** — the last day the right exists (2026-09-18).
- **Premium** — what the call cost ($920.65 with commission); for a bought call, also the most you can lose.
- **Bid / ask** — the best price a buyer is offering / a seller is asking at that moment. Selling realistically happens near the bid.
- **DTE (days to expiration)** — calendar days left. H6 counts calendar days (`h6_watch.py:430`).
- **Intrinsic value** — what the call is worth if used right now: share price minus strike, or zero if below.
- **End-of-day (EOD) vs 15:45 pre-close** — H6 was built on end-of-day quotes; the Schwab lane captures quotes at 3:45 pm, 15 minutes before the close.

**The bet.** This trade makes money if NVDA rises enough that the call is worth more than $920.65 when the rules sell it; it loses if NVDA doesn't rise enough before then.

**Numbers.** Max profit: unlimited in principle (the rules sell at +100%). Max loss: $920.65. Breakeven at expiration: NVDA ≈ $229.21. Early assignment: not possible — only an option *seller* can be assigned, and the H6 book only bought (Official-source: OCC defines assignment as notice to an option writer, as sourced in H7 spec §11 — not re-fetched this session; the book holds no short leg — Repo-verified, `h6_positions.csv:2`).

**One thing beginners get wrong here.** "It expired, so the loss is whatever it was worth at expiry." That depends on what the record is supposed to measure. If the record measures *the registered strategy*, the rule said sell at 21 days. If it measures *what the lane actually did under your rulings*, the lane was dark and the option ran to expiry. That is the whole decision below.

---

## 2. The crux, in one question

**Which do you trust more for this one trade: the registered exit *date*, or the registered exit *data source*?** No option keeps both.

- **A** keeps the registered **date** (08-28) but prices it from a data source H6 never registered (Schwab 15:45), evaluated after the fact.
- **B** keeps your pause ruling and the no-backfill precedent — it uses no new quote source at all (only the underlying close) — but uses an exit time H6 never registered (expiration).
- **C** introduces no new source and no new exit time; what it gives up is the trade itself, removed from H6's evidence.

All three need a **post-result** ruling: both candidate results are visible, so none of them can be recorded under the 2026-07-25 delegated-amendment rule. They need your ruling in §6; the agent only records it.

---

## 3. Facts the decision rests on

| # | Fact | Label | Source |
|---|---|---|---|
| F1 | Registered exit: "close at 21 DTE at conservative fills OR take-profit at +100% of premium, whichever first; NO stop-loss." Fills: "mid-or-worse + SLIPPAGE_HAIRCUT + commissions both legs/ways." No expiration clause; no data source named. | Repo-verified | `ledger/experiments.jsonl:7` (seq 6) |
| F2 | Code: calendar DTE; take-profit if proceeds ≥ 2 × entry; else close if DTE ≤ 21. Proceeds = floor(bid × 0.99, cents) × 100 − $0.65. Haircutting from the **bid** is the conservative end of "mid-or-worse" (fill model `conservative_bid_ask_plus_haircut_v1`); the `config.py:95` comment "beyond mid" is stale. A mid-based reading would give $553.35 on 08-28 ($5 better). Exits check quote validity only, not open interest or spread. | Repo-verified | `h6_watch.py:416-452,431-440`; `strategies/base.py:12-19`; `config.py:94-95,242,347-348` |
| F3 | Allowed exit reasons are exactly `take_profit` and `time_21_dte`; `validate_book` rejects anything else. No expiry/settlement/data-gap reason exists for H6. | Repo-verified | `h6_watch.py:62,544-545` |
| F4 | H6's evaluator reads only the ThetaData cache (`--chain-dir` default `.cache/chains`), last session 2026-07-27. After that, every session fails "exact chain missing" and `build_receipt` refuses any receipt carrying an error, so **even without the pause, no exit could have been evaluated.** H6 receipts exist only for 07-13 and 07-22→07-27. | Repo-verified | `h6_watch.py:991,1014,1037,1306`; `reports/h6_forward/` |
| F5 | **D-1=F1** (owner ruling 2026-08-14): no hypothesis lane (H5/H6/H8/H10) runs under data-tier authority, because feeding chain-starved lanes would append starved observations to a registered record. | Repo-verified | `reports/2026-08-14-switch-on-owner-decisions.md:16-21`; `reports/2026-08-14-owner-decision-package.md:32-35` |
| F6 | The only Schwab-source precedent (seq 28, owner-directed **pre-result**, 2026-08-19) made the 15:45 capture a qualifying source "for H10b's entry evaluation only"; "All other lanes' D-1=F1 pause is unchanged" (clause 1). It declared the data hole "permanent and disclosed; nothing is interpolated" (clause 3) and set a **hard no-backfill floor**: the watcher must refuse any past session (clause 5). It also flagged Schwab IV being stored in percent (clause 2). Seq 29 did the same for H5. | Repo-verified | `ledger/experiments.jsonl:29-30`; `tools/daily_ritual.sh:392` |
| F7 | The book is hand-maintained CSV, checked after the fact: each exit row must cite the hash of an H6 receipt for that exact session with one `CLOSE` decision. No typed writer exists. The receipt is **whole-session** (it re-evaluates entries for NVDA/PLTR/AMZN, needs IV-rank features, refuses any error, and must be schema v2 for sessions on/after 2026-08-03). | Repo-verified | `h6_watch.py:614,947,1037,1175-1199,1218-1293` |
| F8 | The gap was flagged on 2026-09-03 (with this A/B choice), 2026-09-09, and in `wiki/hypotheses.md`; never ruled. | Repo-verified | `reports/2026-09-03-attractiveness-scanner-pm-evaluation.md:155-172,386-390`; `reports/2026-09-09-pm-sweep-and-pattern-findings.md:93,137,183` |
| F9 | The registered close session is **2026-08-28**: DTE 21 (08-27 = 22 → HOLD). The ritual evaluates the last completed session, so the 08-31 run was the one that should have closed it. | Repo-verified (reviewer ran the logic) | `daily_ritual.sh:120`; `h6_watch.py:430,450` |
| F10 | A verified Schwab 15:45 pre-close capture exists for 08-28: `overall_status ok`, captured 15:45:08 ET, file SHA-256 `bf45130e…6f38`; the NVDA chain file's SHA-256 matches the receipt (`951ad293…`); committed in `0dc4013`. NVDA 2026-09-18 $220 call: bid **$5.55** / ask $5.65. Running `evaluate_exit` read-only on it returns CLOSE / `time_21_dte` / $548.35. The quote would also pass the liquidity gates (open interest 46,198; spread 1.79%). | Repo-verified (hashes recomputed this session) | `reports/schwab_chains/2026-08-28/preclose.json`; `.cache/schwab_chains/NVDA_2026-08-28.parquet` |
| F11 | A second, disposable 15:45 capture the same day (intraday lane) shows bid $5.50 → $543.35 (−$377.30), $5 worse. The verified pre-close receipt is preferred because it is the lane with a committed receipt and the one H10b uses. Same-day path: 09:31 bid $11.05, 13:00 $6.80, 15:45 $5.50. | Tool-computed | `.cache/intraday/NVDA_2026-08-28T1545.parquet` (not a verified receipt) |
| F12 | Timing bias of a 15:45 mark (Inference): put-call-parity spot at 15:45 on 08-28 ≈ $216.99 vs the $217.55 close; with delta ≈ 0.45 a true end-of-day bid is estimated ≈ $0.25 higher, so A's mark is probably ≈ $25 *adverse* to the book. On the two overlap days (07-24, 07-27), Schwab 15:45 vs ThetaData EOD bids for comparable NVDA calls differed by a median of −7.1% and +2.8%. | Inference (reviewer-computed, assumes r = 4%) | review receipt §6 |
| F13 | Take-profit was never reached on any observed mark. Threshold: proceeds ≥ $1,841.30 (bid ≈ $18.61). Highest observed: ThetaData EOD +$315.70 (07-15, bid $12.50; no H6 receipt that day); verified Schwab receipts +$414.70 (08-14); any capture incl. disposable intraday ≈ +$567.70 (08-14 09:31). NVDA's highest close 07-13→08-28 was $227.98 (08-27). | Tool-computed; "never reached on unobserved sessions" is Inference (≈ $19 of value needed, far above every observed mark at any NVDA level reached) | caches; `.cache/underlying/NVDA.parquet` |
| F14 | NVDA closed **$222.27** on 2026-09-18 → intrinsic $2.27/share = $227.00. **No committed receipt binds this close**; `.cache/underlying/NVDA.parquet` is a mutable, daily-refreshed store (the 2026-08-14 backup drill recorded a closes refresh breaking sealed receipts — `reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`). | Tool-computed; Repo-verified (no binding receipt) | `load_closes(allow_oos=True)`, same pattern as `pick_tracker.py:1797` |
| F15 | **How the entry was made.** NVDA qualified only under H6_TRIAL7_AMENDMENT_1 (IVR cap 0.50 → 0.70), which the ledger says was decided in-session 2026-07-14 "after seeing the 2026-07-13 gate readouts (NVDA IVR 0.53 … all BLOCKED …; no outcome or P&L data existed)", labelled "forward-only". The 07-13 receipt and the book row were committed the evening of 07-14 (`ae8b4ec` 21:05, `d6660ca` 21:13, `c0fd820` 21:54 ET), after the 07-14 session closed with NVDA up 4.1% ($203.53 → $211.80) and this call's bid at $12.30. The entry was priced at the 07-13 ask ($9.10 → $9.20 after the haircut → $920.65). Whether the owner's in-session decision preceded the 07-14 open is not recorded. **Sensitivity:** the $220 call could not have been bought at 07-14 prices under H6's own rules — its ask ($12.55, i.e. $1,255 per contract) fails the $1,000 ask cap (`h6_watch.py:216-219`). Re-running H6's contract selection on the 07-14 chain picks the **$230 call at $894.65** (ask $8.85, delta 0.37; on 07-15 it would cost $904.65). That counterfactual trade: **A −$658.30** (08-28 bid $2.40 → $236.35); **B −$894.65** (NVDA $222.27 < $230, expires worthless). I.e. ≈ $286 (A) and ≈ $200 (B) worse than the booked trade. | Repo-verified (commits, `facts.log:11997`, receipt `cc8ccd80…`) + Tool-computed (marks) + Inference (timing of the decision) | `ledger/facts.log:11997` |
| F16 | Verdict rules: reject after **8 completed positions** if CI90 upper bound < 0; v1 hard kill = 3 consecutive months each realizing the full $2,000 cap as losses, keyed on **exit month**. H6-0001 is a v1 row (KILL_V2 covers entries on/after 2026-08-03). Completed positions today: 0. The scorer reads the 8-position bar and kill count **live from `config.py`** (flagged "DEFECT REAL" 2026-09-08, unfixed). | Repo-verified | seq 6; seq 22 (`experiments.jsonl:23`); `h6_watch.py:719,741,826`; `reports/2026-09-08-loss-bar-source-audit.md:45-47` |

### Mark history under the registered sale formula (Schwab 15:45 pre-close receipts)

Proceeds = floor(bid × 0.99, cents) × 100 − $0.65; P&L vs $920.65. Tool-computed.

| Session | DTE | Bid / Ask | Proceeds | P&L | Note |
|---|---:|---|---:|---:|---|
| 08-14 | 35 | 13.50 / 13.60 | $1,335.35 | +$414.70 (+45.0%) | |
| 08-17, 08-18 | — | — | — | — | no pre-close capture (ops behind origin/main) |
| 08-19 | 30 | 9.25 / 9.30 | $914.35 | −$6.30 | |
| 08-20 | 29 | 8.55 / 8.65 | $845.35 | −$75.30 | |
| 08-21 | — | — | — | — | capture refused ("could not refresh origin/main" — network) |
| 08-24 | 25 | 4.85 / 4.95 | $479.35 | −$441.30 | |
| 08-25 | 24 | 6.15 / 6.25 | $607.35 | −$313.30 | |
| 08-26 | 23 | 5.05 / 5.10 | $498.35 | −$422.30 | NVDA reported after the close (company IR, gating G0025) |
| 08-27 | 22 | 12.55 / 12.70 | $1,241.35 | +$320.70 (+34.8%) | rule may not sell yet (22 > 21) |
| **08-28** | **21** | **5.55 / 5.65** | **$548.35** | **−$372.30 (−40.4%)** | **registered close session** |
| 08-31, 09-01 | — | — | — | — | captures failed (token expired ~08-30) |
| 09-02 | 16 | 8.60 / 8.70 | $850.35 | −$70.30 | |
| 09-03 | 15 | 11.70 / 11.80 | $1,157.35 | +$236.70 | |
| 09-04 | — | — | — | — | capture refused (network) |
| 09-08 | 10 | 8.50 / 8.60 | $840.35 | −$80.30 | |
| 09-09 | 9 | 6.95 / 7.00 | $687.35 | −$233.30 | |
| 09-10 | 8 | 3.75 / 3.80 | $370.35 | −$550.30 | last verified pre-close capture |
| 09-11 → 09-17 | — | — | — | — | 09-11/09-14 refused (ops misaligned); 09-15 on: token expired |
| 09-18 | 0 | no capture | $227.00 intrinsic | −$693.65 (−75.3%) | expiration |

(09-07, Labor Day, is not a session; its capture is inert per Brief 40 WP-C.) The same contract went from +35% to −40% in one day (08-27 → 08-28). A calendar rule's result depends on where the calendar lands; that is noise the rule accepted up front, not a reason to prefer either day. Data-availability sensitivity: had the 08-28 capture failed, A's logic would have landed on 09-02 (−$70.30).

---

## 4. Options

### A. Book the registered rule-date exit (2026-08-28, `time_21_dte`) from the Schwab 15:45 capture
- **Result:** $548.35, **−$372.30 (−40.4%)**.
- **For:** keeps the registered exit date; the session is fixed by the calendar rule, not chosen; the quote was captured at the time by a verified, committed receipt (F10); the exit reason already exists (F3). It is the closest available estimate of what the *registered strategy* would have done — the source substitution plausibly moves the number by roughly $5–40 (F11–F12: a $5 same-day capture gap, ≈ $25 timing bias, and −7.1% / +2.8% cross-provider gaps on a $5.55 bid), while the A-vs-B choice moves it by $322.
- **Against:**
  1. **It runs against the nearest precedent.** Seq 28–29 were pre-result and deliberately left H6 paused under D-1=F1, and they forbid backfilling any past session (F6). A would be the **first retroactive, post-result data-source substitution in this ledger**. The difference from H10b (the date is fixed, not selected among sessions) is real but is an argument, not a precedent.
  2. **It departs from a hard guardrail, disclosed:** "EOD GAPS … Prefer SKIPPING the day (log it) over silently using an intraday snapshot" (`.cursorrules`). Its booked row mixes providers (ThetaData EOD entry, Schwab 15:45 exit), a hazard seq 28 clause 2 disclosed for H10b.
  3. **The hindsight test only protects the date.** "Would you still book 08-28 if NVDA had rallied to $250 by 09-18?" — yes, by construction. But the *source* choice is being made with both outcomes visible.
  4. **Recording path.** Needs a Codex brief for an **exit-only reconstruction receipt** (new schema or explicit carve-out), because the existing receipt is whole-session (F7). Running the existing CLI with `--chain-dir .cache/schwab_chains` is **not** acceptable: Schwab IV is stored in percent (F6) and would contaminate reconstructed 08-28 entry decisions for a paused lane.

### B. Book expiration settlement (2026-09-18)
- **Result — three candidate values, not one:**
  - **$226.35 / −$694.30 (−75.4%)** under the H7 §4a convention it mirrors, which charges the exit commission on legs settled in the money (`docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md:191`);
  - $227.00 / −$693.65 only if you deviate from §4a on commission;
  - **−$920.65 (full loss)** if §4a's own fallback for "no receipt-bound close" is applied (`SPEC.md:198-201`), since no receipt binds NVDA's 09-18 close (F14).
- **For:** matches the lane's actual operating state (source frozen + your D-1=F1 pause, which the 08-19 amendment text left unchanged for H6); consistent with the no-backfill precedent and the EOD-gaps guardrail; the more conservative number.
- **Against:**
  1. It departs from the registered exit rule (21 DTE) and records an exit time H6 never registered — it measures "the strategy as operated", not "the strategy as registered".
  2. Porting §4a now is itself post-result, and §4a's stated justification is that it was "declared now, before results … so it can never be chosen with visible P&L" (`SPEC.md:172,183`).
  3. Needs a new exit reason in code (F3) and a receipt path for a session with no option quote at all (only the underlying close).
  4. "What actually happened" is a paper convention (Assumption). In a real account, a call $2.27 in the money is exercised automatically into 100 shares at $220 — $22,000 of cash or margin, far beyond H6's $2,000/month sleeve — and its value then moves with NVDA after the Friday close (09-21 close $227.38). OCC's exercise-by-exception threshold ($0.01 in the money, per H7 spec §11, which rests on OCC-affiliated secondary confirmation — Official-source caveat carried) makes no difference at $2.27.

### C. Exclude H6-0001 from H6 evidence
- **Result:** no P&L counted; completed positions stay at 0.
- **For:** honest that the registered rules were never executed; and there is an **outcome-independent** ground knowable on 07-14 — the entry was priced at a session already superseded when it was booked (F15).
- **Against:** removing a losing trade after seeing it lost is how selection bias enters a ledger, and the entry-timing ground was not raised at the time; with one trade in the whole H6 book it erases the only data point. Like A and B, it needs a post-result amendment defining the exclusion.

### What each option does to the verdict
None moves H6 near a verdict: 1 of the 8 completed positions needed (A, B) or 0 (C). None triggers the v1 hard kill ($372–$921 is below the $2,000 full-month cap). Under v1 exit-month keying, A lands the loss in **August**, B in **September** (F16).

---

## 5. Agent recommendation (not an owner field)

**Lean: A, with B's §4a value (−$694.30) and the F15 entry-timing sensitivity disclosed in the same ledger fact.** Reason: the H6 verdict is about the expectancy of the *registered* strategy, and A is the closer estimate of it — its source uncertainty is roughly $5–40, while A and B differ by $322. The session is fixed by the calendar rather than selected, and the quote was captured at the time by a verified receipt.

**Counterexample to that last point, stated plainly:** the H10b floor (`config.py:629`, `H10B_RESUME_FLOOR_SESSION = "2026-08-19"`) deliberately left out the verified 2026-08-14 capture from this same Schwab lane — exactly this kind of contemporaneous, verified data. The precedent excluded it anyway, so "captured at the time" did not earn admission there.

**The strongest case against this lean — and it is strong:** your D-1=F1 ruling (left unchanged for H6 by the 08-19 amendment text), the only Schwab precedent (pre-result, no-backfill, and it excluded even a verified capture), and the EOD-gaps guardrail all point to B. If you read the record's job as "log only what the registered machinery produced under my rulings," B is the consistent answer, and A becomes the first post-result source swap in the ledger. This is a judgment about what the record is for; it is yours.

---

## 6. Owner ruling (leave blank until decided)

| Field | Ruling |
|---|---|
| Option chosen (A / B / C / other) | |
| If A: accept the verified Schwab 15:45 pre-close capture of 2026-08-28 (bid $5.55) as the mark source for this one exit, as a disclosed post-result exception to D-1=F1? (yes / no) | |
| If B: follow H7 §4a's commission-on-in-the-money-settlement convention? (yes / no) | |
| If B: which close binds the settlement — the value $222.27 (NVDA 09-18 close, read 2026-09-28 from `.cache/underlying/NVDA.parquet`) written into the new receipt as a number, not a file hash (the store is rewritten daily) — or §4a's full-loss fallback? | |
| F15: acknowledge the entry-timing facts and keep the entry as booked ($920.65)? (yes / no — "no" means you want a further post-result ruling on the entry itself, e.g. exclusion under C or a re-priced entry; the agent would draft that as a separate package) | |
| Disclose the non-chosen values (and F15 sensitivity) in the same ledger fact? (yes / no) | |
| Authorize a Codex brief to build the recording path (exit-only receipt + book row)? (yes / no) | |
| Authorize a separate prevention brief (§7.1)? (yes / no) | |
| Owner wording + date | |

---

## 7. Related, but not part of this ruling

1. **Why it happened:** H6's calendar exit was wired to a quote feed that stopped on 07-27, and the lane was then paused by D-1=F1 without anything watching its open position. Any paused or starved lane holding a position can strand it the same way. The 09-03 evaluation already proposed the fix (give `h6_watch`/H8 a Schwab data path and a calendar exit that fires without quotes) — that change would itself be an amendment for H6.
2. **Scorer reads config live (F16).** Whatever gets booked is scored against `config.py` on scoring day; the 09-08 audit's fix (read the bar from the registration event, as `h7_real_scoring.py:198` does) is still open.
3. **Per-trade cap conflict.** The global `MAX_LOSS_PER_TRADE = 600` (`config.py:42`) conflicts with H6's $1,000 ask cap and this $920.65 premium; flagged 2026-09-03 (`reports/2026-09-03-…:179,389-390`), unresolved.
4. **H6 has no registered window end**, and with one trade in ~11 weeks and the lane dark, 8 completed positions are not in sight.

## 8. After the ruling — who does what

1. You fill §6.
2. Agent drafts the ledger fact text for the chosen option, provenance "owner-directed <date>" (**not** "owner-delegated standing 2026-07-25" — post-result rulings are not delegable), gets independent review, and writes a Codex brief for the recording path (`codex-brief-writing`).
3. Codex implements; the return leg goes through `executor-handback-verification` (a committed receipt is required — no PASS without an artifact).
4. The fact is appended via the typed API (`research/facts.py:17` `append_fact`); the book row is written only with a receipt that passes `verify_book_receipts`. Never a hand edit to `ledger/`.
