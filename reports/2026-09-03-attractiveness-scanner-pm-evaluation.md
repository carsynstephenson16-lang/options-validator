# Attractiveness scanner — portfolio-manager evaluation (2026-09-03)

**Session type:** autonomous orchestration (Fable main session; Sonnet agents for
web research, scanner inventory and paper-trade inventory; Opus agents for the
statistical red-team, the signal-combination assessment and the layout
implementation). Owner directive (verbatim intent): evaluate the scanner as a
top PM would, judge whether "adding the groups together" gives a better signal,
make the layout shorter and easier to read, check whether any trade placed has
worked and if so whether it was edge or luck, then close every PR and leave
nothing lying around.

**Vocabulary discipline applies throughout:** nothing here is "proven",
"confirmed" or "an edge". The permitted words are *survived this test*, *not yet
rejected*, *rejected*, *consistent with zero edge*. No trade is recommended.

**Claim labels:** Repo-verified (read from files at the cited path),
Test-verified (recomputed in-session), Official-source, Inference, Assumption.

---

## 0. The one-paragraph answer

The scanner is well-guarded but is currently answering yesterday's question
with five-week-old prices. Every option quote on the live board is from the
2026-07-27 close (28 sessions old, all 18 names DATA_BLOCKED), even though the
Schwab 15:45 chain capture succeeded 15/15 on 2026-09-02. The board refuses a
fresh chain unless a same-instant 15:45 stock quote exists, and the LaunchAgent
that produces that quote had been booted out of launchd after 09:35 on
2026-09-02. It was reloaded this session (§3). On the trading record: exactly
one paper option trade has ever been opened (H6-0001, NVDA $220 call), it was
down ~48% at its last quoted mark, it has no mark for 38 days, and it passed its
own mandatory close date with nothing running to enforce it. The only positive
result in the repo (the H9 one-run, +$4,645 on 16 trades) does not survive the
red-team: half the profit is one trade and another 47% is exit overshoot the
rule never promised. On "adding the groups together": today it cannot be
tested, because there are zero settled outcomes to score any group against, and
an offline redundancy audit shows the groups that dominate the ranking are four
re-labels of two inputs (trend and implied volatility). The honest path is
unfreeze quotes → shrink the group set by measured redundancy → let outcomes
settle → one pre-registered equal-weight comparison.

---

## 1. What the scanner is (plain English)

The attractiveness board ranks 18 AI-infrastructure names for defined-risk
options trades. For each name it prices five "lanes" — cash-secured put
(agree to buy shares at a lower price, paid to wait), covered call (own shares,
sell someone the right to buy them higher), poor-man's covered call (same idea
using a long-dated call instead of shares), LEAPS (a call expiring a year or
more out) and a plain long call — and grades each candidate contract
GREEN/AMBER/RED on yield, downside cushion, implied-volatility rank (where
today's option price sits against its own past year), a volatility-premium
proxy (are options priced richer than the stock has actually moved), earnings
and Fed-meeting timing, and liquidity. The **baseline ranking** sorts every
admissible card by the fraction of its badges that are GREEN, then by lane
leadership, then by a technical-trend tiebreak, one pick per name, top five
(`display_rank.py:11-27`, `attractiveness_dashboard.py:438-485`; Repo-verified).

Around that baseline sit several **display-only lanes** that never touch the
ranking or any trade authority: a composite board (four angles — trend, vol
premium, regime, options-market internals — combined by a plain count, never a
weighted average), a context lane (the baseline order with the composite count
spliced in as a strict second tiebreak), a momentum lane (QM), a regime
descriptor, four parking-lot experiments plus FINRA short interest, and an
LLM-written market backdrop. The registered RQ2 badges are **not wired into
the board at all** (zero imports of `a2_runner` from the ranking stack;
Repo-verified). Full inventory with file:line citations: §7.

Guardrail posture (Repo-verified): no live-order path; every lane carries its
max as-of date; a chain older than 3 sessions is DATA_BLOCKED and excluded from
the shortlist (`CHAIN_STALE_BLOCK_SESSIONS=3`, LLM-asserted, `config.py:689-690`);
the pick tracker that scores past picks has no verdict or ledger authority and
writes only under `reports/pick_tracker/dryrun`.

---

## 2. What a PM sees today (the live board, ops build 2026-09-03 09:12)

| Item | Value | Source |
|---|---|---|
| Page size | 795,546 bytes, one HTML file, zero JavaScript | ops `.tmp/dashboard/attractiveness.html` (Repo-verified) |
| Sections | 30 `<h2>`; 2,196 table rows; 317 native `<details>` (18 open by default) | Sonnet inventory, re-rendered from main (Test-verified) |
| Per-name panels | 18 panels are ~90% of the bytes; VST 63 KB, MSFT 62 KB, CEG 54 KB | same |
| Estimated length | roughly 18–25 screen-heights at 1080 px (structural estimate, not measured) | Inference |
| Option quotes | frozen EOD 2026-07-27; 28 sessions old; 18/18 names BLOCKED | freshness block on the page (Repo-verified) |
| Underlying closes | max session 2026-09-02 | same |
| Schwab pre-close chains | 2026-09-02 capture `overall_status=ok`, 15/15 names | ops `reports/schwab_chains/2026-09-02/preclose.json` (Repo-verified) |
| Why they were refused | "no verified 15:45 spot for 2026-09-02" on 13 names (ET/USAR are display-excluded; NBIS/AMAT/CLSK are a separate lane) | page text; rule at `schwab_chain_view.py:380-427` (Repo-verified) |
| Shortlist | 0 of 5 slots filled in all three strips; the identical five-line "no qualifying contract" card is printed 15 times | page text (Repo-verified) |
| Schwab token | OK, expires 2026-09-09 13:22 UTC | `schwab_token_age` run at 14:4x ET (Test-verified) |

**PM reading.** The page is honest — every stale figure is banner-flagged and
excluded from the shortlist — but it is not *usable*: the decision-relevant
layer (positions, then today's admissible opportunities) is either buried
(positions are section 7 of 30) or empty (five slots, three times, same
reason). The bulk of the page is 18 fully-expanded contract ladders that a PM
would open one at a time, not read top to bottom. Design literature agrees
(Few, *Information Dashboard Design*; Tufte's data-ink ratio; Practitioner):
show the single most decision-relevant view on one screen and push detail one
click down. §5 records what was changed.

---

## 3. Root cause of the stale board, and what was done

**Chain of evidence (Repo-verified unless noted):**

1. `select_display_source` returns a fresh Schwab chain only if a verified
   session exists for the name AND `load_preclose_spot` finds a `stock_snapshot`
   spot in `reports/intraday_capture/<session>/preclose.json`
   (`schwab_chain_view.py:270-325, 380-427`).
2. The intraday quote lane's 09-02 outputs are `open.json` and
   `open_auction.json` only (09:31 and 09:35); no 11:00, 13:00 or 15:45 run.
   09-03 has no runs at all.
3. `launchctl print gui/501/com.carsyn.options-validator.intraday-capture`
   → "Could not find service"; `launchctl print-disabled` → **enabled**; no
   reboot since 2026-08-14 (`uptime` 19 days). So the agent was booted out of
   launchd without being disabled, sometime after 09:35 on 09-02. No log line
   or report records who did it (`log show` over 2 days: nothing; Inference:
   most likely collateral from the 09-02 outage work).
4. The installed plist is byte-identical to the tracked template
   (`tools/launchagents/com.carsyn.options-validator.intraday-capture.plist`).

**Action taken (state change, evidence above):** `launchctl bootstrap` +
`enable` per `tools/launchagents/README.md` "Intraday capture". Verified
registered (`launchctl list` shows the label, exit 0, waiting on its
StartCalendarInterval). **Proof: the 2026-09-03 15:45 slot fired** —
`reports/intraday_capture/2026-09-03/preclose.json` (ops), `receipt_kind
intraday_capture/v1`, `session_tag preclose`, `force false`, 15/15 names
`status ok` with `spot_source stock_snapshot` (e.g. VST spot_mid 144.20 at
19:45:17 UTC) — exactly what `load_preclose_spot` requires (Test-verified). If it did, the next 09:09 ritual renders
2026-09-03 Schwab chains for the 13 Schwab-eligible names and the shortlist
can fill.

**Two downstream defects the stale board exposed (not fixed here):**

- `pick_tracker` recorder raises `TrackerError: snapshot schema is not
  picks_snapshot/v1` every morning because the board wrote a
  `picks_snapshot/unavailable` snapshot (reason CAPTURE_RECEIPT_UNAVAILABLE).
  The ritual isolates it, but an UNAVAILABLE snapshot should be a recorded
  no-op, not an exception (`pick_tracker.py:139`; Repo-verified).
- The H6/H8 evaluators have no Schwab data path at all, so they stopped on
  2026-07-27 with the ThetaData cache (see §4).

---

## 4. Did any trade placed work? Edge or luck?

**Inventory (Sonnet agent, every row cited; Repo-verified):** across the whole
repo, **one** options paper position has ever been opened. H7, H8, H10a, H10b
have zero entries in their books (H10a closed STARVED on 2026-08-15). H5 holds
39 VST shares from 2026-06-15 at $142.28 (close $143.46 on 09-02, ≈ +0.8%).

### 4a. H6-0001 — NVDA $220 call, expiry 2026-09-18, 1 contract

| Date | Days to expiry | Conservative sell proceeds | P&L vs $920.65 entry |
|---|---|---|---|
| 2026-07-13 (entry) | 67 | — | — |
| 2026-07-22 | 58 | $1,112.35 | +$191.70 |
| 2026-07-23 | 57 | $964.35 | +$43.70 |
| 2026-07-24 | 56 | $860.35 | −$60.30 |
| 2026-07-27 | 53 | $479.35 | **−$441.30 (−47.9%)** — last mark |

No mark exists after 07-27 anywhere (main or ops). NVDA closed $224.41 on
09-02 (underlying-only), so the contract is not worthless, but intrinsic value
is not a registered mark. The registered rules: take-profit at +100% (never
reached; peak was +21%), mandatory close at ≤ 21 days to expiry
(`config.py:347-348`, `h6_watch.py:446-452`). **That threshold was crossed on
or about 2026-08-28 and nothing ran** — the calendar-only exit was made
dependent on a quote feed that stopped. The book still shows the position
open with blank exit fields (`data/positions/h6_positions.csv:2`).

**Edge or luck (Opus red-team, results-red-team protocol):** with n = 1 nothing
can be said either way; H6's own rule needs 8 completed positions before any
statement is computable (ledger seq 6). Reading −48% as "H6 is failing" or a
recovery as "H6 is working" are the same error. **Verdict: Needs repair** —
governance repair, not statistics. Two further gaps: the entry cost ($920.65)
exceeds the global `MAX_LOSS_PER_TRADE = 600` that H9 was ruled to respect,
while H6 still runs at `H6_MAX_ASK_DOLLARS = 1000` (same conflict, two answers);
and any eventual exit will be a reconstruction that must be labelled as one.
Owner decision required (§8).

### 4b. H9 one-run — the only positive number in the repo

16 trades, 12 wins / 4 losses, +$4,645.20, recorded INSUFFICIENT_SAMPLE (4
losses against a 10-loss bar), one-run spent forever. Red-team findings
(Opus; Test-verified where a number was recomputed from `reports/h9/receipt.json`):

- **Concentration:** the single best trade (VST 2024-08, +$2,292.70) is 49.4%
  of the P&L; top two are 65.8%; top three 76.3%.
- **Exit overshoot:** take-profit exits filled the session *after* the
  decision and realised 0.73×–3.84× cost against a +100% rule. Had every
  take-profit filled at exactly +100%, total P&L would be $2,460.75 — **47% of
  the result is fill timing the rule never promised.**
- **Regime:** three calendar years (2022, 2025, 2026) produced zero trades
  from 57 eligible events; all four losses sit in one seven-month stretch. The
  one bear year in the window was never traded.
- **Censoring the census never measured:** the $600 premium cap is applied at
  entry but not in the eligibility census (`h9_census.py:85` vs
  `h9_study.py:71`), so 77% of triggered events cancelled; NVDA 0 of 34
  events, NOW 0 of 21, SMCI 0 of 6. The traded set is "names with sub-$600
  calls during the AI run-up", which is the same channel as survivorship.
- **Effective sample:** 5 names, two simultaneous correlated losses, roughly
  3 independent loss episodes, not 4.
- **Naive tests and why they mislead:** sign test p = 0.038; permutation
  p = 0.025; drop the top trade p = 0.051; drop two p = 0.098; Bonferroni over
  the 15 registered trials p ≈ 0.38. All assume independent, symmetric trades;
  none of that holds.
- Recorded max drawdown $361.30 is superseded by the 2026-07-31 correction to
  $718.50 (`ledger/facts.log` METRIC_CORRECTION); the H9_RESULT fact still
  quotes the old number.

**Verdict: Reject** as evidence about post-earnings drift (the governance
record INSUFFICIENT_SAMPLE stands and was recorded correctly). Kill test if
anyone wants one: recompute the same 16 trades with every take-profit filled at
the decision session's close capped at exactly +100%, excluding the top trade.

### 4c. The scanner's own pick record

The dry-run pick tracker holds 6 long-call entries, all from **one decision
session (2026-08-27)**, 0 settled, 9 unreachable marks (token outage 08-31 and
09-01), and the two arms it exists to compare (frozen baseline vs context lane)
chose **identical contracts**, so the contrast is zero by construction
(`reports/pick_tracker/dryrun/2026-09-02/scoreboard.md`, ops; Repo-verified).
The scoreboard prints `Raw leg P&L = 0` with `Settled = 0`, which reads as
break-even and should be null (presentation defect). Picks expiring 09-09/09-11
cannot reach the +10/+20-session checkpoints. **Nothing can be concluded about
pick quality today** — not good, not bad. Verdict: the recorder is fit to keep
running (paper-only tracking); it is not a result.

---

## 5. Layout: what was changed and why

Delivered as display-only **PR #154** on branch
`claude/scanner-pm-layout-2026-09-03` (Opus implementation agent, TDD; full
offline suite `Ran 3780 tests … OK (skipped=5)` exit 0; ruff 0; pyright 0).
Measured on the ops receipts: visible top-level cards 35 → 5 and empty-slot
cards 17 → 5 on the stale 2026-09-02 board; on the fresh 2026-09-03 board (13
names on Schwab 15:45 chains after the §3 fix) bytes are flat (769,945 →
779,557) because nothing is deleted, only folded — 7 of 18 name panels open by
default (2 owner-pinned + 5 fail-visible DATA_BLOCKED names), the rest closed
(Test-verified). Design, recorded here because the session was autonomous and the PR is
the approval gate:

1. **Page order becomes a PM's morning sheet:** data status → positions & risk
   (the registered-bets tracker moved up from section 7, with a one-line
   open-position summary and an "unmarked N sessions" honesty flag) → today's
   shortlist → composite context → per-name detail on demand → diagnostics and
   provenance last.
2. **Empty-slot consolidation:** when shortlist slots are open for the same
   reason, one consolidated notice replaces the repeated cards (today: 15
   copies of the same five lines).
3. **Per-name panels closed by default** behind a one-line summary (symbol ·
   chain source and as-of · best grade or block reason), with a sticky symbol
   nav; the owner-pinned VST/AMZN stay open.
4. **Composite board as one 18-row table** instead of 18 cards, same label
   strings.
5. **Diagnostics & provenance drawer:** QM lanes, research coverage, passive
   views, quant-want background and the LLM market backdrop live inside one
   closed disclosure at the bottom, text unchanged.
6. **Nothing else moves:** no signal, ranking, constant with owner provenance,
   ledger, positions or authority sentence changes; zero JavaScript; every
   existing disclaimer survives verbatim; the pick tracker's HTML source-row
   digest keeps working.

What was deliberately **not** done: no charts, no new "score", no re-weighting,
no hiding of stale-data banners.

---

## 6. "Adding the groups together" — the honest assessment

**Straight answer (Opus assessment; Repo-verified evidence):** it cannot be
known today whether combining the groups improves the signal, because there
are **zero settled outcomes** to score any group against (pick tracker 0
settled; A2-v1, the registered per-lane after-cost battery, has never run and
is blocked on three named conditions). One free result already exists and is
unflattering: the context lane (baseline + composite tiebreak) has produced a
shortlist **identical** to the frozen baseline on every session run
(`frozen_baseline_only: 0`, `context_lane_only: 0`). A combination that never
changes a pick cannot produce a different outcome to measure.

**What the literature says (Sonnet web digest, all cited; Academic unless noted):**
adding signals helps only when they are genuinely independent (Grinold–Kahn:
information ratio ≈ skill × √breadth, breadth = *independent* bets); optimised
weights lose to equal weights out of sample once estimation error is counted
(DeMiguel–Garlappi–Uppal 2009); a "new" signal needs t > 3, not 2, after the
searching everyone has done (Harvey–Liu–Zhu 2016); an observed Sharpe ratio
must be deflated for every variant tried and needs a minimum track-record
length that grows with negative skew and fat tails (Bailey & López de Prado);
even one informal round of "let's adjust that cutoff" recreates the
multiple-comparisons problem (Gelman–Loken). Options specifics: the volatility
risk premium has the best evidence but at the *index* level (Bakshi–Kapadia
2003; AQR; Cboe PUT index — Official-source), extension to single names is
Inference; IV-rank thresholds are Practitioner heuristics; options-market
internals were shown with proprietary opening-trade data (Pan & Poteshman
2006) and are weaker with public volume/OI; trend overlays on option selling
are a research gap.

**Offline redundancy audit (no outcomes needed; Repo-verified file evidence):**
the whole stack draws on six raw inputs (closes, chains, volume, FINRA short
interest, Treasury rates, QQQ closes). Of the seven groups:

- **Vol premium is measured four times** — H5 `vrp_for_seller` badge
  (`attractiveness.py:159-172`), composite Angle 2 (a percentile of the *same*
  `iv_minus_rv` column, `composite_signals.py:24-27`), RQ2 B1 (that gap and
  term slope joined by AND, ledger seq 18) and RQ2 V1 (tenor-matched median of
  the same premium, seq 26). V1 is a *better measurement of the same thing*,
  not a second thing.
- **Trend is measured four times** on the same closes — baseline technical
  confluence (SMA 20/50/200), composite TREND (EMA 50/200 + 12-1 momentum),
  RQ2 A1 (distance to 52-week high, 1-month momentum), QM parabolic.
- **Liquidity is literally the same function call** — H5 badge and composite
  INTERNALS veto both call `passes_liquidity`.
- The context lane is the baseline key with one trend-dominated term spliced
  in at level 2: "ranking on trend, then breaking ties with trend."
- **Genuinely independent information, all of it:** open-interest change and
  25-delta skew (composite INTERNALS only), volume (QM only), FINRA short
  interest, Treasury carry, and regime (the one group with a *measured*
  redundancy receipt: adjusted mutual information 0.029 vs the 0.50 threshold,
  REGIME-AMI-v1, seq 23/24 — near-orthogonal, usefulness untested).

So the seven groups contain roughly four to six distinct signals, and the ones
that dominate today's ranking are the most redundant. Breadth, if it exists,
lives in the groups furthest from the ranking.

**On the repo's refusal of weighted sums:** refusing to *estimate* weights is
right and should stay (no outcomes to fit to; fitting to price history on
names selected for having risen is the forking path). Refusing to consider
*equal* weights is not supported by the literature it cites — DeMiguel et al.
argue for 1/N, not for lexicographic ordering, which is the most extreme
weighting there is. Equal-weight rank aggregation over pre-declared groups is
the combination worth pre-registering. (Verdict of the Opus assessment;
Inference.)

**The honest test, as a sketch (the owner types every number):** statistic =
equal-weight rank-sum over K pre-declared groups chosen for independence, ties
broken by the frozen baseline key; outcome = A2-v1's own per-lane after-cost
top-minus-bottom tercile spread over weekly non-overlapping cohorts (seq
19/27/31), no new metric; floor = A2's `MIN_ADVERSE_BOTTOM_BUCKET = 10` and the
2026-07-24 feasibility gate's 2× projection before registration; one
pre-declared comparison (combined vs frozen baseline), one shot; every design
looked at and discarded counts toward the trials counter.

**Order of operations:** (1) unfreeze quotes (§3 — done pending the 15:45 proof;
plus the owner's weekend re-auth before 09-09); (2) run a pairwise redundancy
audit modelled on `tools/regime_redundancy_audit.py` to shrink K *before* any
outcome exists; (3) let the pick tracker and A2 accumulate settled cohorts,
then run the single comparison. **Not to do:** compute several combinations
on cached history and register the best; fit weights to the 6 dry-run rows;
add or drop a group mid-window; treat 18 correlated names as 18 bets; stack
more trend/IV measures; read past `IN_SAMPLE_END`; let any combined score
touch entry, sizing or the paper book.

---

## 7. Signal-group inventory (condensed; full table in the Sonnet agent output, cited)

| Group | Where | Measures | Constants (provenance) | Status | Feeds ranking? |
|---|---|---|---|---|---|
| H5 trade-card badges | `attractiveness.py:96-430` | yield, cushion, IV rank, VRP proxy, event timing, liquidity | `H5_*` owner-frozen (`config.py:283-309`) | registered H5 | yes — raw material |
| Baseline GREEN-fraction | `display_rank.py:11-27` | fraction of GREEN badges, lane leadership, trend confluence | `PICK_*` LLM-asserted; `PICK_TOP_N=5` owner-directed in-session | baseline | is the ranking |
| Context lane | `context_lane.py:57-138` | composite aligned-count as strict 2nd tiebreak | `CONTEXT_LANE_ENABLED=True` owner-authorized 08-26 | display-only | secondary order only |
| Composite (4 angles) | `composite_signals.py:128-402` | trend, vol premium, regime, internals; plain count | `COMPOSITE_*` LLM-proposed, literature-anchored | display-only | no (count leaks into context lane) |
| Regime (Wasserstein) | `regime.py` | historical return-shape cluster, walk-forward | `REGIME_*` adapted defaults | display-only | feeds composite angle 3 |
| QM signals | `qm_signals.py` | breakout / parabolic patterns | owner-typed only | gated study | no |
| RQ2-v1 B1/A1/V1 | `a2_runner.py`, seq 25-27 | earnings-fire rule, momentum trio, tenor-matched VRP | owner rulings 08-15 | registered study | **not wired in** |
| EXP-BETA/TAIL/SPREAD/TBILL + short interest | `exp_*.py`, `experiments_dashboard.py` | beta to QQQ, tail shape, spread stability, T-bill carry, FINRA SI | LLM-proposed 08-09; `SHORT_CONTEXT_ENABLED` owner-directed 08-14 | display-only, separate artifact | no |
| H7 signals | `h7_signals.py` | drawdown/reclaim, IV routing | H7 registration `f1887c9d` | registered H7 | separate system, zero imports |

---

## 8. Owner actions (ordered; nothing below was done by this session)

1. **Ledger: the A2 ratification fact is not on main.** PR #145's GitHub squash
   carried only the `RQ2_A2_PIN_ADDENDUM_V1` line. The
   `A2_ENTRY_CONVENTION_RATIFIED_V1` payload that
   `reports/2026-08-31-a2-entry-convention-ratification-receipt.md` line 68-72
   asks the owner to append exists only in two unpushed rescue commits, now
   preserved as tag `archive/a2-ratified-fact-rescue-2026-09-02` (Repo-verified).
   The receipt says the append is the owner's act; append it once on main via
   `research.facts.append_fact` with the payload from line 72. Until then
   A2-v1 stays blocked (default-safe).
2. **H6-0001 disposition.** The position is past its registered 21-DTE close
   with no runner and no mark. Options are the owner's: rule a reconstruction
   method for the 2026-08-28 exit (provenance-labelled), or let it settle at
   expiry 09-18 under a written rule, and reconcile `H6_MAX_ASK_DOLLARS` with
   `MAX_LOSS_PER_TRADE`. Separately, a Codex brief to give `h6_watch` (and H8)
   a Schwab data path and a calendar exit that fires without quotes.
3. **Schwab re-auth** before 2026-09-09 13:22 UTC (weekend 09-05/06),
   `tools/setup_schwab.py` (owner-only, needs browser).
4. **Four remote branches** the permission classifier would not let this
   session delete (content verified on main by two-dot diff):
   `git push origin --delete claude/drill-disposition-b-final claude/drill-disposition-b-local-backup-0815 feat/source-standard-receipt-fields fix/data-guard-worktree-cwd`
5. **Merge PR #154** (the layout PR; display-only; CI green is the condition).
6. **H7 lane execution, unchanged from `reports/2026-09-03-brief-36-owner-rulings.md`:**
   regenerate the cohort-9 feasibility receipt at the post-merge config, then
   the owner runs `tools/h7_schwab_manual_activate.py`. Also the staged
   `schwab-chain-intraday` LaunchAgent install (one supervised capture, commit
   the floor, load the plist).
7. **Two small defects for a brief:** `pick_tracker` recorder should treat a
   `picks_snapshot/unavailable` snapshot as a recorded no-op; scoreboard
   `raw_pnl` should be null when `settled = 0`.

---

## 9. Cleanup record (this session)

- PRs #151, #152, #153 closed with evidence comments (all three were
  reconciler-born drafts on branches whose content was already on main; #153's
  head carried nothing main lacks — the missing ledger fact is item 8.1 above).
- Remote branches deleted: 55 (33 merged by ancestry + 22 whose content was
  verified on main by two-dot diff of every file they touched). Remaining:
  `main`, `deploy/research` (the research LaunchAgent's checkout), and the four
  in item 8.4.
- Worktrees removed: 8 (`brief36`, `pm-closeout`, `ops-fixes`,
  `brief-36-implementation`, `a2-facts-landing`, `a2-governance-facts`, the
  nested `h7-packet-draft`, and `.claude/worktrees/gracious-neumann-d938c9`),
  after `irreplaceable_data_guard.py verify` OK before and after, ignored-file
  inspection (only caches, `__pycache__`, empty `.cache/chains`), the two
  gitignored SDD progress notes copied to the main checkout, and the
  `.remember` contents confirmed duplicated in the main checkout.
- Local branches deleted: 19. Stale `refs/remotes/pr/9/head` removed.
- Worktrees now: main checkout, ops, research, and the layout PR's worktree.

---

## 10. Sources for the web digest (retrieved 2026-09-03)

DeMiguel, Garlappi & Uppal (2009) RFS — https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901 ·
Grinold & Kahn, *Active Portfolio Management* (1999) ·
FactSet, "A practical approach to weighting signals" — https://insight.factset.com/a-practical-approach-to-weighting-signals ·
Israelov & Nielsen, "Still Not Cheap" (AQR) — https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-Still-Not-Cheap.pdf ·
AQR, "Understanding the Volatility Risk Premium" — https://www.aqr.com/Insights/Research/White-Papers/Understanding-the-Volatility-Risk-Premium ·
Bakshi & Kapadia (2003) RFS — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=267106 ·
Cboe/Wilshire options-benchmark study — https://cdn.cboe.com/resources/spx/wilshire-options-based-benchmark-indexes-2019.pdf ·
Pan & Poteshman (2006) RFS — https://academic.oup.com/rfs/article-abstract/19/3/871/1646711 ·
Harvey, Liu & Zhu (2016) RFS — https://academic.oup.com/rfs/article/29/1/5/1843824 ·
Bailey & López de Prado, Deflated Sharpe Ratio — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 ; Probability of Backtest Overfitting — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 ·
Gelman & Loken, "The garden of forking paths" — https://sites.stat.columbia.edu/gelman/research/unpublished/p_hacking.pdf ·
Few, *Information Dashboard Design* (overview) — https://blogs.ischool.berkeley.edu/i247s12/files/2012/01/Dashboard-Design-Overview-Presentation.pdf
