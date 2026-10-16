# Adversarial review — H6-0001 exit owner decision package

**Target:** `reports/2026-09-28-h6-0001-exit-decision-package.md` (untracked draft in `.tmp/worktrees/h6-exit-pkg`, code at `98907dd`)
**Reviewer:** independent Opus session, 2026-09-28. Adversarial framing ("show how this could be lying"). Read-only on everything except this file. Numbers re-derived with read-only Python in `~/options-validator-ops` (`origin/main @98907dd`); closes read via `load_closes(..., allow_oos=True)` from 2026-07-01 onward only. No network. No ledger, book, config, cache or receipt was touched.

## Verdict: **FAIL** (text-only fixes; re-review after they land)

The arithmetic is good. Every figure in the marks table, the take-profit threshold, the 08-28 close, the intrinsic value and the file hashes re-derive exactly. The package fails on **framing and omissions that bear on the owner's choice**:

- It cites the H10b/H5 amendments as precedent for option A. Those amendments forbid A's core step (evaluating a past session after the fact), and they explicitly left H6 paused.
- It says the H7 settlement precedent is silent on commission, but it is not.
- It leaves out an integrity problem with how H6-0001 was *entered*, and that problem changes how option C should be judged.

---

## Findings

### 1. BLOCKER — The precedent cited for option A is misrepresented by omission

**Where:** package line 82 ("Precedent: H10b and H5 moved to the Schwab pre-close lane by owner-directed amendments (ledger seq 28–29, 2026-08-19)").

**Evidence (Repo-verified):**
- Seq 28 (`ledger/experiments.jsonl` line 29), clause 1: it declares the Schwab 15:45 capture a qualifying source "**for H10b's entry evaluation only** … All other lanes' D-1=F1 pause is unchanged." H6 was therefore deliberately left paused on 2026-08-19, nine days before its 21-DTE session. `tools/daily_ritual.sh:392` repeats this: "H6 and H8 stay paused inside region B."
- Seq 28, clause 3: "the 2026-07-29 → first-capture hole is **permanent and disclosed; nothing is interpolated**."
- Seq 28, clause 5: a "**hard no-backfill floor** … the watcher MUST refuse to evaluate or record ANY session with `as_of` earlier than the floor, regardless of when the command runs."
- Seq 28 is titled an "owner-directed **pre-result** amendment". `reports/2026-08-16-owner-directives.md:62` ties its delegability to the fact that "H10b has zero results". The owner's 08-17 confirmation is recorded as a "partial reversal" of D-1=F1 for H10b and H5 only (`:132`).
- The package never names **D-1=F1** (`reports/2026-08-14-switch-on-owner-decisions.md:16-21`). That is the owner's own 2026-08-14 ruling that paused H6, and its rationale was that feeding starved lanes would be "pre-registration dishonesty" (`reports/2026-08-14-owner-decision-package.md:32-35`).

**Why it matters:** option A would be the first retroactive, post-result data-source substitution in this ledger. The nearest precedent points against it, not for it. The owner's §5 answer on the mark source would rest on a distorted picture.

**Fix (replace the "Precedent:" sentence on line 82):**
> "Precedent, read in full: seq 28–29 made the Schwab 15:45 lane a qualifying source for H10b and H5 only, as PRE-result amendments (zero results existed then). They explicitly left every other lane, H6 included, paused under your 2026-08-14 ruling D-1=F1 (seq 28 clause 1). The same amendment set a hard no-backfill floor: the H10b watcher must refuse to evaluate any past session, and its data hole is 'permanent and disclosed; nothing is interpolated' (clauses 3 and 5). Option A would be the first retroactive, post-result data-source substitution in this ledger. It runs against the nearest precedent, not with it. That is a legitimate choice, but it is yours alone."

Also add D-1=F1 as a fact row (it is the cause of the pause the package describes in F6).

### 2. MAJOR — The claim that A can be recorded under delegation conflicts with repo precedent

**Where:** line 82 ("delegable per the 2026-07-25 standing rule after adversarial review + sign-off") and §7 step 2 (line 132).

**Evidence:**
- Both candidate numbers (08-28 and 09-18) are visible to the drafter, so any source or exit-reason change is **post-result**.
- Repo precedent treats delegability as flowing from pre-result status (`reports/2026-08-16-owner-directives.md:62`).
- RQ2 clause 5b escalates a post-result price-source switch to **re-registration** (`reports/2026-08-15-monday-ship-adversarial-review-receipt.md:76-80`).
- `ledger-discipline` rules 2–3: "Never fill in rejection criteria after seeing results"; "a tweak after seeing results is the definition of overfitting."

**Fix (line 82 and §7.2):**
> "Because both candidate results are already visible, any source substitution, new exit reason, or exclusion rule for H6-0001 is a POST-result amendment. It is not delegable under the 2026-07-25 standing rule and needs your ruling in §5. The agent may only record your ruling (provenance 'owner-directed <date>'), after independent review."

### 3. MAJOR — Option B's commission: the H7 precedent is *not* silent

**Where:** line 87 ("the H7 precedent does not say; owner choice") and the §5 row on line 115.

**Evidence (Repo-verified):** `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md:191` says "exit commissions apply only to legs settled in the money (Assumption: no commission on a leg expiring worthless)." NVDA closed $222.27 on 09-18, above the $220 strike, so the leg is in the money and §4a charges the commission.

**Fix:**
- Line 87 → "Result under the H7 §4a convention it mirrors: **$226.35 proceeds, −$694.30 (−75.4%)**. §4a charges the exit commission on legs settled in the money. ($227.00 / −$693.65 applies only if you choose to deviate from §4a.)"
- §5 row → "If B: follow H7 §4a's commission-on-in-the-money-settlement convention? (yes / no)"

### 4. MAJOR — Option B's mechanics are understated: three possible values, not one

**Where:** lines 86–89 and F12.

**Evidence:**
- §4a values the position "against the **receipt-bound** adjusted underlying close" (`SPEC.md:188`). If that close is unavailable, it books "ITM or undeterminable defined-risk structures at **full-width loss**" (`:198-201`).
- No committed receipt binds NVDA's 09-18 close. I searched `reports/ritual/run_status_*` and `capture_receipt_*` for 09-18 and 09-21: neither binds `.cache/underlying/NVDA.parquet`.
- That closes file is a mutable, daily-refreshed store (mtime 2026-09-28 09:09). The 2026-08-14 drill-RED recorded a closes refresh breaking sealed July receipts.
- §4a's own justification is that it was "declared now, **before results** … so it can never be chosen with visible P&L" (`:172`, `:183`). Porting it to H6 now is post-result, which is exactly what that sentence rules out.
- "What actually happened" (line 88) is a paper convention (Assumption). In a real account, a call $2.27 in the money is exercised automatically into 100 shares at $220 ($22,000 of cash or margin, well beyond H6's $2,000/month premium sleeve), and its value then moves with NVDA after the Friday close (09-21 close $227.38).

**Fix (add to B):**
> "Three candidate values, not one: $226.35 (§4a with commission), $227.00 (no commission), or a full loss of −$920.65 if §4a's own fallback for 'no receipt-bound close' is applied. No committed receipt binds NVDA's 09-18 close; `.cache/underlying/NVDA.parquet` is a mutable, daily-refreshed store (Repo-verified). Porting §4a now is itself post-result, and §4a's stated justification is that it was frozen before any result existed. 'What actually happened' is a paper convention (Assumption): a real in-the-money long call is exercised automatically into 100 shares at $220."

### 5. MAJOR — The cause of the stranding is misstated in the plain-English section

**Where:** §1 line 11 ("on 08-28 nothing ran — the daily ritual had H6 switched off … so the 'sell at 21 days' rule never fired") and B's "measures the pause (an operations failure)" (line 89).

**Evidence (Repo-verified):**
- H6's registered evaluator reads only `.cache/chains`, whose last session is 07-27. Even without the pause, every session after 07-27 raises `exact chain missing` (`h6_watch.py:991,1014`), and `build_receipt` refuses any receipt that carries an error (`:1037`). The 08-31 ritual log, which evaluated session 08-28, says at line 4: "chain-dependent lanes are STARVED: no exact-session chain for 2026-08-28".
- The pause is the owner's ruling D-1=F1. It was re-affirmed for H6 by seq 28 clause 1.
- H6 receipts exist only for 07-13 and 07-22 → 07-27. The ops ritual log directory has no run between `2026-07-28_0710.log` and `2026-08-14_2151.log`.
- The same 08-31 log printed "H6: MISSING - stale" (line 101), and nothing acted on it.

**Fix (§1):**
> "…But nothing could run on 08-28 under H6's registered machinery. Its evaluator reads only the ThetaData end-of-day cache, which stopped on 2026-07-27. Since 2026-08-14 the lane has also been paused by your ruling D-1=F1, which you re-affirmed for H6 when you moved H10b and H5 to Schwab data on 2026-08-19. The ritual printed 'H6: MISSING - stale' that morning, and nothing acted on it."

In B, replace "measures the pause (an operations failure)" with: "measures the result under the lane's actual, owner-ruled operating state (data source frozen plus the D-1=F1 pause)".

### 6. MAJOR — The end-of-day-gaps guardrail is not cited, and A vs B is framed unevenly

**Where:** line 80 ("the only option that the pre-registered rule itself selects"), line 84 (the hindsight test), line 103.

**Evidence:**
- `.cursorrules` hard guardrail: "EOD GAPS: … Prefer SKIPPING the day (log it) over silently using an intraday snapshot inside an EOD backtest."
- `h6_watch.py` docstring: it applies the exit rules to "cached EOD facts".
- The 2026-08-14 Schwab directive says these captures are labeled "15:45 pre-close (Schwab) — never as an end-of-day close".
- The guardrail's default path (skip days that have no end-of-day data) never reaches a valid end-of-day session after 07-27. So the registered machinery's own path ends at expiry.
- The two options depart in mirror-image ways. A keeps the registered *date* but uses an unregistered source and a retroactive evaluation. B keeps the registered source and accounting but uses an unregistered exit time.
- A's booked row would mix providers: entry at ThetaData end-of-day on 07-13, exit at Schwab 15:45 on 08-28. The H10b amendment disclosed its own "mixed-timing hazard" (seq 28 clause 2).
- The hindsight test protects A's *date*. It does not protect the *source* choice, which was made with both outcomes visible.
- On timing bias (Inference, assuming r = 4%): the put-call-parity NVDA spot at 15:45 on 08-28 was about $216.99, against a $217.55 close. With the call's delta of 0.449, a true end-of-day bid is estimated about $0.25 higher, so A's 15:45 mark is probably about $25 *adverse* to the book. On the two overlap days (07-24 and 07-27, 0.30–0.70 delta NVDA calls, 9–10 contracts), Schwab 15:45 bids differed from ThetaData end-of-day bids by a median of −7.1% and +2.8%. The 15:45 timing is noise of the same order as the effect being argued about.

**Fix (new fact row; rewrite line 80's "For" and line 103):**
> "A is the option that keeps the registered DATE. B keeps the registered DATA SOURCE and accounting. Neither keeps both. A also departs from the hard guardrail 'prefer skipping the day over using an intraday snapshot inside an end-of-day evaluation' (disclosed here, so not silent), and its row would mix providers (ThetaData end-of-day entry, Schwab 15:45 exit). The hindsight test protects A's date; it does not protect the source choice. The 15:45 mark is probably about $25 below a true end-of-day mark (Inference: parity spot $216.99 vs close $217.55, delta 0.449)."

### 7. MAJOR — The recording path for A is understated, and the obvious shortcut is hazardous

**Where:** line 83 ("No path produces one today… run the existing `evaluate_exit` against the 08-28 Schwab chain … write a receipt").

**Evidence (Repo-verified):**
- The receipt is **whole-session**. `build_snapshot` (`h6_watch.py:947`) re-evaluates ENTRIES for NVDA, PLTR and AMZN. It needs exact chains plus manifest-verified IV-rank features for all three.
- It refuses any error (`:1037`); `_bound_snapshot` requires `errors == []` (`:1175`); any session on or after 2026-08-03 must use schema v2 (`:1176-1199`).
- The CLI already takes `--chain-dir` (`:1306`), so `h6_watch --as-of 2026-08-28 --chain-dir .cache/schwab_chains` is the naive path. It would compute 08-28 *entry* decisions from Schwab IV, which is stored in percent (the 08-28 file shows `iv` 58.35), with no 252-session IV-rank history. Seq 28 clause 2 names the ÷100 normalization as an obligation.
- The result would be reconstructed entry decisions for a lane that was paused.

**Fix (line 83):**
> "Needs a Codex brief for an EXIT-ONLY reconstruction receipt (a new schema or an explicit carve-out). The existing receipt is whole-session: it re-evaluates entries for NVDA, PLTR and AMZN, needs manifest-verified IV-rank features, refuses any error, and must be schema v2 for any session on or after 2026-08-03. Running the existing CLI with `--chain-dir .cache/schwab_chains` is NOT an acceptable shortcut: Schwab IV is stored in percent (seq 28 clause 2) and would contaminate the reconstructed entry decisions."

### 8. MAJOR — How H6-0001 was *entered* is omitted, and it changes how option C should be judged

**Where:** missing entirely. Line 11 says "On 2026-07-13 the H6 paper book 'bought'…". Option C's "Against" (line 94) calls exclusion outcome-selection and "the weakest provenance of the three."

**Evidence:**
- Commits: `ae8b4ec` (2026-07-14 21:05 ET, "owner amendments 2026-07-14 — H6 IVR max 0.70"), `d6660ca` (21:13 ET, the 07-13 receipt: "NVDA ELIGIBLE … IVR 0.53 under amendment-1's 0.70 max"), `c0fd820` (21:54 ET, book row, "Owner-approved in session 2026-07-14").
- `ledger/facts.log:11997` (H6_TRIAL7_AMENDMENT_1) calls the change "forward-only" and says it was "made after seeing the 2026-07-13 gate readouts (NVDA IVR 0.53 … all BLOCKED". Seq 6 registered IVR ≤ 0.5.
- NVDA closed 07-14 at $211.80, up 4.1% from $203.53 (Tool-computed). The ThetaData end-of-day bid for this call on 07-14 was $12.30, a mark of +$295.70 (Tool-computed). The entry was booked at the 07-13 ask ($9.10, or $9.20 after the adverse adjustment, giving $920.65), and the booking commits postdate the 07-14 close. Whether the owner's in-session decision came before the 07-14 open is not recorded (Inference).
- The receipt and book bind correctly (`load_book()` verifies; `receipt_hash` cc8ccd80…).

**Why it matters:** there is an **outcome-independent** reason to consider C that was knowable on 07-14. Every booked P&L also inherits an entry at a price that had already been superseded when it was booked. And all three options need a post-result amendment (A: source plus a retroactive receipt; B: a new exit reason; C: an exclusion rule), so "weakest provenance" is not established.

**Fix (add fact F15 and revise C):**
> "F15 — H6-0001's entry was evaluated and booked on the evening of 2026-07-14 (commits ae8b4ec, d6660ca, c0fd820, 21:05–21:54 ET), after the 07-14 session had closed with NVDA up 4.1% and this call bid at $12.30. It was priced at the 07-13 ask. NVDA qualified only under H6_TRIAL7_AMENDMENT_1 (IVR cap 0.50 → 0.70), which the fact itself says was decided after seeing the 07-13 readout that blocked NVDA at IVR 0.53, and which it labels 'forward-only'. You approved the entry in-session on 07-14. | Repo-verified (commits, facts.log:11997, receipt) + Tool-computed (07-14 marks)."
>
> C "For" (add): "An outcome-independent ground exists: the entry was priced at a session that had already been superseded when it was booked (F15)."
>
> C "Against": replace "the weakest provenance of the three" with "like A and B, it needs a post-result amendment."

### 9. MINOR — F11's "highest observed ThetaData mark" is wrong

- **Evidence:** the ThetaData end-of-day cache gives +$315.70 on 07-15 (bid $12.50) and +$295.70 on 07-14 (bid $12.30), not +$191.70 on 07-22. Those sessions have no H6 receipt; the error is inherited from `reports/2026-09-03-…:167-168` ("peak was +21%"), which read receipts only. The highest mark in any capture, including intraday snapshots, is about +$567.70 (08-14 09:31, disposable intraday). The conclusion stands, since take-profit needs +$920.65.
- **Fix:** "Highest observed: ThetaData end-of-day +$315.70 (07-15; no H6 receipt that day); any capture including intraday ≈ +$567.70 (08-14 09:31, disposable)."

### 10. MINOR — Wrong line number in a citation

- `h6_watch.py:1305` → `:1306`. Line 1305 is `--book`; line 1306 is `--chain-dir`.

### 11. MINOR — Two 15:45 captures on 08-28 disagree, and the package mentions neither the second one nor the intraday path

- **Evidence:** I ran `evaluate_exit` read-only on both files. The verified pre-close capture (bid 5.55) gives $548.35 / −$372.30. The disposable intraday `NVDA_2026-08-28T1545` capture (bid 5.50) gives $543.35 / −$377.30.
- The same day's intraday path: 09:31 bid 11.05 (+$171.70), 13:00 bid 6.80, 15:45 bid 5.50.
- **Fix:** add one sentence under the table disclosing both captures, the $5 gap, and why the verified receipt is preferred (it is the same verified view H10b uses).

### 12. MINOR — Missing sessions are omitted from the table without comment, and "last capture before the outage" is inaccurate

- **Evidence:** there is no pre-close capture for 08-17, 08-18 or 08-21. On 08-31 and 09-01 the token had expired and the receipts are unverified. On 09-04 the capture was refused ("could not resolve github.com"). On 09-11 and 09-14 it was refused because "HEAD is not aligned with origin/main", while the token was still alive; the 09-15 log is the first "Refresh token … expired".
- Data-availability sensitivity: had the 08-28 capture failed, A's logic would have booked 09-02 (−$70.30).
- **Fix:** list these sessions with their causes, and change the 09-10 note to "last verified pre-close capture (09-11/09-14 refused: ops misaligned; 09-15 onward: token expired)".

### 13. MINOR — Labels

- "Tool-verified this session" (F9) is in neither taxonomy. Use "Repo-verified (hashes recomputed this session)".
- Line 24 ("Early assignment: not possible…") and B's OCC Rule 805(d) reference need claim labels. Carry the H7 spec §11 sourcing caveat: the $0.01 threshold rests on OCC-affiliated secondary confirmation. It makes no difference here at $2.27 in the money.
- F10's "evaluator not run on it" can now be upgraded: `evaluate_exit` on the 08-28 Schwab chain returns CLOSE / time_21_dte / 548.35 / −372.30 (run read-only in this review).

### 14. MINOR — The fill formula is not reconciled with the registration

- **Evidence:** the registration says "mid-or-worse + SLIPPAGE_HAIRCUT". The comment at `config.py:95` says the haircut applies "beyond mid". The code (`FILL_MODEL_ID conservative_bid_ask_plus_haircut_v1`, `config.py:242`) applies it beyond the **bid**, which is the conservative end of "mid-or-worse", so the two are consistent.
- A mid-based reading gives floor(5.60 × 0.99) = 5.54, i.e. $553.35 / −$367.30 (a $5 difference).
- The exit path checks quote validity only, with no open-interest or spread gate (`h6_watch.py:431-440`). The 08-28 quote would pass those gates anyway (open interest 46,198; spread 1.79%).
- **Fix:** add one line to F2 saying this.

### 15. MINOR — A related open item is missing from §6

- The global `MAX_LOSS_PER_TRADE = 600` (`config.py:42`) conflicts with H6's $920.65 premium. The 09-03 report flagged it (`:179`, `:389-390`), and it is not carried into §6.

---

## On the seven attack questions (summary)

1. **Numbers.** All re-derive exactly, except F11's ThetaData peak (#9) and B's commission precedent (#3).
2. **Registered close session.** It is 2026-08-28.
   - The ritual sets `AS_OF` to the last completed session (`daily_ritual.sh:120`). The 08-31 09:09 run evaluated session 08-28.
   - `exit_date` equals `evaluation_session` and is priced at that session's chain.
   - Calendar DTE with `dte <= 21` makes 08-27 a HOLD at 22 DTE and 08-28 a CLOSE.
   - Take-profit could not have fired earlier on any observed mark.
   - Receipt schema: an 08-28 exit receipt must be v2. That changes the mechanics, not the session.
3. **Fill formula.** The code is accurately described. Bid minus the haircut is the conservative end of "mid-or-worse", so this is not a violation. The stale `config.py:95` comment and the $5 mid-based alternative should be disclosed (#14).
4. **Self-serving?** Not in stakes: the numbers differ by about $321, and no option moves the verdict or the kill rule. The framing is uneven, though (#6). The strongest case for B is that the registered source, the owner-ruled pause, the end-of-day-gaps guardrail and the H10b no-backfill precedent all point the same way; the package omits this (#1, #5, #6). The strongest case for C (#8) is omitted. B's mechanics are misstated (#3, #4).
5. **Citations.** 22 checked; 1 wrong (#10).
6. **Missing facts.** D-1=F1, entry provenance, two conflicting 15:45 captures, missing-session causes, the IV-units hazard, and the mutable closes store (#1, #4, #7, #8, #11, #12).
7. **Compliance.** Owner fields are all blank. There is no banned vocabulary (grep for proven / confirmed / works / edge found / guaranteed: 0 hits). Label gaps are listed in #13, and a claim that should have been labeled Inference is covered in #5 (causation).

## Verified correct

- **All 14 table rows.** Bid/ask, proceeds, P&L, % and DTE re-derived from `.cache/schwab_chains/NVDA_*.parquet` via `strategies.base.adverse_sell`.
  - 08-28: 5.55 / 5.65 → 5.49 → $548.35 / −$372.30 (−40.4%).
  - 08-27: $1,241.35 / +$320.70.
  - 08-14: $1,335.35 / +$414.70.
- **Take-profit threshold.** $1,841.30. The minimum bid is $18.61 (proceeds $1,841.35).
- **NVDA closes** (`load_closes`, allow_oos):
  - Highest close 07-13 → 08-28 is $227.98 on 08-27.
  - 09-18 close $222.27, so intrinsic value is $227.00 and P&L −$693.65 (−75.3%).
  - Breakeven $229.21.
- **F9.**
  - `preclose.json` SHA-256 is `bf45130e…6f38`; the NVDA parquet is `951ad293…` and matches `names.NVDA.sha256`.
  - `overall_status` is `ok`; captured 15:45:08 ET; timing text as quoted; commit `0dc4013` (2026-08-31).
  - `verified_sessions()` lists 08-28.
- **Book and entry.**
  - The book loads with receipt verification; entry `receipt_hash` is cc8ccd80….
  - Entry cost $920.65 = ceil(9.10 × 1.01) = 9.20 × 100 + 0.65.
  - Score: INSUFFICIENT_SAMPLE, 0 completed.
- **Kill rule.** v1 row; the v1 kill is keyed on exit month (`h6_watch.py:741`), so A lands the loss in August and B in September. Neither triggers the kill.
- **08-28 quote quality.** It passes quote validity and would pass the liquidity gates (open interest 46,198; spread 1.79%).
- **Earnings date.** NVDA reported 08-26 after the close (`gating_v3.csv` G0025, company IR).
- **Table omission.** Leaving out 09-07 is correct: it was not a session, and the capture shows delta −999.
- **Citations confirmed:**
  - `h6_watch.py:62, 416-452, 430, 544-545, 614, 719, 826, 1218-1293`
  - `strategies/base.py:17-19`
  - `config.py:94-95, 347-348`
  - `daily_ritual.sh:151, 371`
  - `pick_tracker.py:1797`
  - `h7_real_scoring.py:198`
  - `research/facts.py:17`
  - loss-bar audit `:45-47`
  - 09-03 report `:155-172, 386-390`
  - 09-09 report `:93, 137, 183`
  - H7 spec `:172-204`
  - `experiments.jsonl` lines 7 and 23
  - `h6_positions.csv:2`

---

## Round 2 — review of package revision 2 (same reviewer, 2026-09-28)

**Target:** revision 2 of the package (163 lines, still untracked). Same rules as round 1: read-only, and the numbers re-derived in `~/options-validator-ops`.

### Verdict: **PASS WITH FIXES**

The round-1 blocker is resolved, and 13 of the 15 round-1 findings are fully resolved. Revision 2 introduces four new major problems, each fixable with a sentence or a corrected number:
- the F15 sensitivity prices a trade H6's rules would have refused;
- the §5 cost comparison understates the source error using the package's own F12 data;
- the §5 no-backfill argument leaves out the precedent's direct counterexample;
- the §1/§5 "you re-affirmed for H6" wording overstates what the owner actually did. This originated in my own round-1 fix text.

Apply the fix text below verbatim. No third round is needed if the coordinator checks the four major fixes.

### Round-1 findings: status

| # | Round-1 finding | Status | Where resolved |
|---|---|---|---|
| 1 | Seq 28 precedent misrepresented; D-1=F1 missing | RESOLVED | F5, F6, §2, §4A.1 |
| 2 | "Delegable" claim | RESOLVED | §2, §8.2 |
| 3 | B's commission under H7 §4a | RESOLVED | §4B, §6 row 3 |
| 4 | B has three values; exercise convention | RESOLVED | F14, §4B |
| 5 | Cause of the stranding | RESOLVED (but see R2-4 on wording) | §1, F4, §7.1 |
| 6 | EOD-gaps guardrail; uneven framing | RESOLVED (new quantitative issue in R2-2) | §2, §4A.2-3, F12 |
| 7 | Recording path | RESOLVED | F7, §4A.4 |
| 8 | Entry provenance | RESOLVED in substance (the new sensitivity is wrong: R2-1) | F15, §4C |
| 9 | ThetaData peak mark | RESOLVED | F13 |
| 10 | Line 1305 → 1306 | RESOLVED | F4 |
| 11 | Two 08-28 15:45 captures | RESOLVED | F11 |
| 12 | Missing sessions and their causes | PARTIAL: the 08-21 cause is missing (R2-6) | table |
| 13 | Labels | RESOLVED (small citation nit, R2-8) | F10, line 25, §4B.4 |
| 14 | Fill formula | RESOLVED | F2 |
| 15 | Per-trade cap | RESOLVED | §7.3 |

### New findings

#### R2-1. MAJOR — The F15 sensitivity prices a trade H6's rules forbid

**Evidence:**
- The $220 call at the 07-14 ask ($12.55, i.e. a $1,255 raw ask) fails H6's $1,000 raw-ask gate (`h6_watch.py:218`, `config.py:343`).
- A $1,268.65 entry would also be rejected by `validate_book`, whose maximum entry cost is $1,010.65 (`h6_watch.py:477-482,512-515`).
- I ran `choose_contract` read-only on the ThetaData chains:
  - 07-13 → the 220 call at $920.65 (matches the book);
  - 07-14 → the **230 call** for 09-18 (delta 0.369, ask $8.85, entry **$894.65**);
  - 07-15 → the 230 call at **$904.65**.
- The rule-consistent counterfactual is therefore a different contract:
  - **A:** the 230 call bid $2.40 on 08-28 (Schwab pre-close), giving proceeds $236.35 → **−$658.30** (07-14 entry) or **−$668.30** (07-15 entry);
  - **B:** out of the money at $222.27, so $0 with no commission under §4a → **−$894.65 / −$904.65**;
  - take-profit is never reached: the 230 call's highest proceeds were $870.35 (ThetaData, 07-15) and $840.35 (Schwab, 08-14).
- These are Tool-computed. The IVR gate would have passed: the current feature store shows NVDA IVR 0.510 on 07-14 and 0.504 on 07-15, both under the 0.70 cap. That store is mutable (Inference): it shows 0.512 for 07-13, while the committed receipt recorded 0.5317.

**Fix (replace F15's "Sensitivity" sentence):**
> "**Sensitivity (Tool-computed):** this contract could not have been bought at a later price under H6's rules, because at the 07-14 ask ($1,255) it fails the $1,000 raw-ask gate. Re-running H6's own contract selection on 07-14 (or 07-15) picks the **$230 call** for 09-18 at $894.65 (or $904.65). That trade's results: A −$658.30 (−$668.30), and B −$894.65 (−$904.65, expires worthless). So an entry made at the first price available after the decision would have booked about $286 worse under A and about $200 worse under B."

#### R2-2. MAJOR — "$5–25 source error vs $322" understates the source error and mislabels the $322

**Evidence:**
- F12's own overlap data show median Schwab-vs-ThetaData bid gaps of −7.1% and +2.8%. On the 08-28 bid of $5.55 that is about $39 and $16 per contract. The honest band is roughly **$5–40**, not $5–25.
- $322 is the **A-minus-B difference** (−$372.30 vs −$694.30). Calling it "B's error against the registered rule" treats A's own number as the registered-rule truth, which is circular.

**Fix (§4A "For" and §5):**
> "the source substitution plausibly moves the number by about $5–40 (Inference: F11's $5 capture gap, F12's ≈$25 timing estimate, and F12's −7.1%/+2.8% overlap gaps applied to a $5.55 bid), while A and B differ by $322."

Delete "B's error against the registered rule is ~$322".

#### R2-3. MAJOR — The §5 no-backfill argument leaves out the direct counterexample

**Evidence:** §5 says the concern "doesn't bite the same way" because the session is fixed by the calendar and the quote was captured at the time. The precedent excluded exactly that kind of data:
- `H10B_RESUME_FLOOR_SESSION = "2026-08-19"` (`config.py:629`) excluded the verified, committed 2026-08-14 pre-close capture (same lane, `overall_status ok`, the 15/15 canary day). That is a session fixed by the calendar, with a quote captured at the time.
- Seq 28 clause 3 declared the 07-29 → 08-18 hole permanent even though disposable intraday captures of the H10b names existed for those days (for example NVDA on 08-05 through 08-18 in `.cache/intraday/`).

**Fix (append to §5's first paragraph):**
> "Counterweight: the precedent did not grant this exception either. H10b's floor (2026-08-19, `config.py:629`) left out the verified 08-14 pre-close capture of the same lane, a calendar-fixed session with a quote captured at the time. So this distinction is the agent's argument; the precedent does not support it."

#### R2-4. MAJOR — "You re-affirmed D-1=F1 for H6" overstates what the owner did (my round-1 wording)

**Evidence:**
- The owner's act on 08-17 was a *scoped* override: Q2 "ya confirm overrid", recorded as overriding D-1=F1 "for H10b specifically" plus H5 (`reports/2026-08-16-owner-directives.md:59,127-133`).
- The sentence "All other lanes' D-1=F1 pause is unchanged" is text an agent drafted into seq 28. It was appended under the delegated standing rule ("[RECORDING PROVENANCE] … owner-delegated standing 2026-07-25"), not typed by the owner, and the H6 open position was not raised then.
- The phrase appears in §1 line 11, §4B "For", and §5.

**Fix:** replace "which you re-affirmed for H6 on 2026-08-19 when you moved H10b and H5 (and only them) to Schwab data" with:
> "and when you moved only H10b and H5 to Schwab data (your 08-17 confirmation, appended 08-19), H6's pause was left in place by the amendment's scope; the open position was not raised at the time."

Make the same substitution in §4B and §5 ("D-1=F1, left in place for H6 by the scoped 08-19 amendment").

#### R2-5. MINOR — The §2 crux line is unfair to C and imprecise about B

**Evidence:**
- C uses no Schwab data and invents no exit time, so "C keeps neither" is inaccurate. What C gives up is the trade itself.
- B uses no option-quote source at all. Its input, the NVDA close in a mutable store (F14), is not H6's registered exit source either.

**Fix:**
> "B keeps your pause ruling and uses no new quote source (only the underlying close, via a settlement convention H6 never registered). C also uses no new source and invents no exit time, but gives up the trade itself: the only H6 data point is removed by a rule written after the result."

#### R2-6. MINOR — The 08-21 table row has no cause

**Evidence:** `.tmp/schwab_chain_capture/2026-08-21_1557.log` says "wrapper REFUSED: could not refresh origin/main".

**Fix:** change the row to "capture refused (could not refresh origin/main)".

**Verified:** the other gap causes are correct:
- 08-17 and 08-18: "HEAD is not aligned with origin/main";
- 08-31 and 09-01: receipt note "Refresh token is invalid, expired or revoked";
- 09-04: DNS failure, then "could not refresh origin/main";
- 09-11 and 09-14: not aligned with origin/main;
- 09-15 onward: token expired;
- 09-07 inert: Brief 40 F11/WP-C.

#### R2-7. MINOR — The F14 drill claim is uncited, and §6's "hashed into the new receipt now" would break the next day

**Evidence:** the source is `reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`. A closes refresh *rewrote* `.cache/underlying/*.parquet` and broke the whole-file hash bindings in sealed receipts. The closes file is rewritten daily, so a whole-file hash taken now stops matching after the next refresh.

**Fix (add the citation to F14; reword §6 row 4):**
> "…bound as the value (NVDA, 2026-09-18, $222.27) with its source and retrieval time, not as a whole-file hash, which changes on every daily refresh (drill receipt 2026-08-14)."

#### R2-8. MINOR — Small wording and citation fixes

- **Line 25:** the assignment definition is labeled "Official-source … not re-fetched". The repo already holds a directly-read citation, so cite `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md` §11 (≈ lines 511-514, OCC "Characteristics and Risks of Standardized Options", read directly).
- **Header, line 5:** "The round-1 reviewer re-derived every number independently" is no longer true for revision 2's new numbers (the F15 sensitivity, $5–25, $322, gap rows). Change it to "every round-1 number; revision-2 additions are covered in the receipt's Round 2 section."
- **§6 row 5 (F15):** it is a yes/no with no stated consequence for "no". Append: "(if no: void the entry → C; note that re-pricing this contract at a later price is not rule-permitted, see F15)".

### Compliance re-check

- All 9 §6 owner fields are literally blank.
- Banned vocabulary: 0 hits (grep for proven / confirmed / works / edge found / guaranteed).
- The recommendation (§5) stays outside the owner fields and is labeled "not an owner field".
- Provenance labels appear on every fact row. The new inference in F12 is labeled Inference, with the r = 4% assumption.
- Post-result, non-delegable status is stated in §2 and §8.2.

### Verified correct in revision 2 (new material)

- **F15 sensitivity arithmetic** (as written, before R2-1): 12.55 × 1.01 = 12.6755, rounded up to 12.68, giving $1,268.65. A −$720.30, B −$1,042.30, delta $348.00.
- **Price facts:** NVDA $203.53 → $211.80 (+4.06%); 07-14 bid $12.30.
- **Commits and ledger:** `ae8b4ec` / `d6660ca` / `c0fd820` times; the `facts.log:11997` quote.
- **$322** = 694.30 − 372.30.
- **B's three values** and the −75.4% figure.
- **Citations:** seq 28/29 no-backfill floors (29 via `H5_RESUME_FLOOR_SESSION`); `ledger/experiments.jsonl:29-30`; `h6_watch.py:947,991,1014,1037,1175-1199,1306`; `strategies/base.py:12-19`; `config.py:242`.
- **§4 kill-rule range:** $372–$921, and the sensitivity worst case of −$1,268.65, are all below the $2,000 cap.
