# RQ2 + A2 pre-result amendment drafts — 2026-08-15 owner rulings

**Status:** DRAFT for independent adversarial review. Nothing here is
appended yet. On review PASS, each block below is appended verbatim (minus
this document's headers) to `ledger/experiments.jsonl` via the
`research/ledger.py` typed API under the recording provenance
"owner-delegated standing 2026-07-25 (drafted by Fable session 2026-08-15;
independent adversarial review receipt:
`reports/2026-08-15-monday-ship-adversarial-review-receipt.md`)". The owner
retains veto by further append-only amendment.

**Pre-result attestation (applies to both blocks):** no RQ2 or A2 result,
historical or forward, exists for any candidate or lane as of this date
(Repo-verified 2026-08-15: no `run`/`retrospective_result` entry for
RQ2-v1 or A2-v1 anywhere in the ledger; no badge or battery code exists in
the repo). No promotion or rejection criterion is being altered after
seeing data.

**Owner rulings being recorded (2026-08-15, in-session, verbatim):**
1. B1 firing: "i dont want that to fire if theres confirmed earnings i want
   that fired daily and studied."
2. Window start: "start rq2 today" → clarified in-session to first scored
   session Monday 2026-08-17.
3. Universe: current 18-name board confirmed for RQ2 and A2 ("a2 bucket
   size fix"; 18-name option selected in-session).
4. V1 statistic: "do both and split each decesion 50% weight" → refined
   after the coverage disclosure (10 of 18 names have no usable
   earnings-event history): "do 100% the other one untill you can pull all
   company earnings."
5. Tiebreak form: raw statistic value (selected in-session).
6. rv21 bias slice: add it (selected in-session).

---

## Block 1 — RQ2_AMENDMENT_V1_2

> RQ2_AMENDMENT_V1_2 2026-08-15: owner-directed in-session pre-result
> amendment to RQ2-v1 (seq 18 owner-typed 2026-07-23; seq 25
> RQ2_AMENDMENT_V1_1 2026-08-10). Five clauses.
>
> (1) B1 FIRING RULE. Seq 18's earnings gate on Badge B/B1 ("earnings-GATED")
> is REMOVED as a gate. B1 computes and may fire daily on every universe
> name. The earnings-proximity context becomes a MANDATORY per-row study
> column (earnings_tag: event-priced / no earnings in window / UNKNOWN,
> fail-visible), recorded so the gated-vs-ungated question is studied rather
> than assumed. Owner wording 2026-08-15: "i dont want that to fire if
> theres confirmed earnings i want that fired daily and studied." B1's
> numeric thresholds are UNCHANGED (ts_pctl >= 0.75 AND vrp_pctl <= 0.25,
> seq 18 owner-typed).
>
> (2) FORWARD WINDOW. The RQ2-v1 forward window opens 2026-08-17 (first
> scored session) and its twelve-month backstop (seq 18, unchanged in
> length) therefore ends 2027-08-17. Disclosure: the 2026-09-01 date that
> propagated through reports and README was an LLM-proposed delegated-table
> draft never frozen in this ledger (see the 2026-08-10 attribution
> correction in reports/2026-08-09-attractiveness-experiment-authorization.md);
> this clause is the first ledger-recorded start date, owner-chosen
> 2026-08-15.
>
> (3) PRICE SOURCE (fills a blank; seq 18 and seq 25 are silent on price
> source). Forward-window badge computation and scoring marks use the daily
> 15:45 ET pre-close Schwab chain captures — the manifest-verified receipts
> under reports/schwab_chains/<date>/ with their parquet snapshots — not
> official closing prints, which no available provider supplies for these
> chains. Sessions with no verified capture are recorded as gaps
> (per-name DATA_BLOCKED), never bridged or substituted. Every output
> carries its capture receipt path and max as-of session.
>
> (4) UNIVERSE. RQ2-v1's board is the current 18-name
> config.ATTRACTIVENESS_UNIVERSE; bucket split remains terciles of the
> frozen GREEN-fraction ranking, now top 6 versus bottom 6. Disclosure:
> RQ2_A2_PIN_ADDENDUM_V1 (2026-07-23) said "15-name board gives 5 names per
> bucket"; ATTRACTIVENESS_EXTRA_NAMES (NBIS, AMAT, CLSK) landed 2026-07-25
> (commit 6c8941e), after that pin. Owner ruled 2026-08-15: the studies
> score the board actually displayed daily, i.e. 18 names.
>
> (5) V1 STATISTIC PIN (required by seq 25 before any V1 comparison).
> (5a) Statistic now in force: V1 ranks on brief line 1 alone — the
> tenor-matched volatility-risk-premium history. Definition: a cycle runs
> from standard monthly expiration E_k to the next monthly expiration
> E_k+1 (options_researcher/chains.is_monthly conventions); IV_entry(k) is
> the ATM implied volatility observed on the cached session at or nearest
> before E_k for expiration E_k+1 (repo ATM convention via chains.atm_row /
> chains.nearest_monthly); RV(k) is the annualized standard deviation of
> daily log closes over [E_k, E_k+1], ddof=1, annualized by
> config.RQ1_RV_ANNUALIZATION_SESSIONS = 252 (matching
> options_researcher/features.py); VRP(k) = IV_entry(k) − RV(k) in
> annualized volatility points. The V1 statistic on evaluation date D is
> the MEDIAN of VRP(k) over completed cycles with E_k+1 <= D, capped at the
> most recent 24 cycles (LLM-proposed 2026-08-15); cycles whose anchor
> session has no cached chain are SKIPPED, never bridged; the open cycle is
> excluded (seq 25, unchanged). Direction: higher ranks toward the top,
> matching the registered one-sided top-beats-bottom design. For the
> RANKING, all completed cycles are included (earnings-window cycles are
> NOT excluded); reason recorded: the point-in-time earnings gating store
> covers too few names for clean-only to be labelable board-wide, and
> excluding by coverage would make data coverage a hidden signal. Seq 25's
> separate clean-vs-earnings DISPLAY split stays binding where coverage
> exists. Names below the pinned 6-cycle floor are EXCLUDED FROM BOTH
> buckets for that date, counted and reported, never imputed or
> bottom-bucketed. Feasibility measured 2026-08-15 against the local cache:
> 18/18 names clear the floor (min 15 completed cycles — CRWV, USAR; max
> 102). Provider policy: the statistic is computed from ThetaData-anchored
> cycles (anchors <= 2026-07-27, the cache freeze) until a documented
> provider-parity check clears splicing Schwab-anchored cycles; Schwab
> implied volatility is stored in percent and MUST be normalized by 100 at
> ingest.
> (5b) Declared destination, owner-worded: once earnings-event history
> reaching the pinned 6-event floor exists for ALL 18 universe names, V1's
> statistic is INTENDED to become a 50/50 equal-weight blend of line 1 and
> line 2 (the post-earnings IV-drop history) — owner wording 2026-08-15:
> "do both and split each decesion 50% weight" / "do 100% the other one
> untill you can pull all company earnings." That switch is NOT automatic:
> it requires its own future append-only pre-result amendment (or
> new-window registration if RQ2-v1 results exist by then), plus the
> separately owner-gated earnings-data backfill project. Until that
> amendment exists the runner refuses any blended V1 comparison exactly as
> seq 25's refusal clause required before this pin.
> (5c) Tiebreak form: if promoted, V1 enters the lexicographic tiebreak
> within equal GREEN-fraction as its RAW statistic value (owner-selected
> 2026-08-15). This clause closes the tiebreak-form gap for V1 only; B1 and
> A1 are untouched.
> (5d) Diagnostic slice: the top-minus-bottom spread is additionally
> reported within rv21 terciles as a descriptive slice that NEVER gates,
> disclosing that volatility-point VRP differences scale with a name's own
> volatility level (owner-selected 2026-08-15).
>
> UNCHANGED: every other term of seq 18 and seq 25 — Holm step-down
> alpha=0.10 as one joint family across K=3; one-sided sidedness; promotion
> = Holm-adjusted CI90 lower bound > 0 AND MIN_ADVERSE_BOTTOM_BUCKET >= 10
> AND non-negative ablation spread; rejection = Holm-adjusted CI90 upper
> bound <= 0; else INSUFFICIENT_SAMPLE; historical pass exploratory-only;
> forward window sole verdict path; badges descriptive-only in this
> registration, never reordering the frozen GREEN-fraction baseline or
> creating a trigger.

## Block 2 — A2_AMENDMENT_V1_1

> A2_AMENDMENT_V1_1 2026-08-15: owner-directed in-session pre-result
> amendment to A2-v1 (seq 19, registered 2026-07-23, never run — no result
> exists). Single clause: A2-v1's board is the current 18-name
> config.ATTRACTIVENESS_UNIVERSE and its bucket split is terciles of the
> frozen GREEN-fraction ranking, top 6 versus bottom 6 (was "top third
> versus bottom third (15-name board gives 5 names per bucket)" per
> RQ2_A2_PIN_ADDENDUM_V1 2026-07-23, which predated the 2026-07-25 board
> growth to 18 — commit 6c8941e). Owner ruling 2026-08-15 ("a2 bucket size
> fix"; 18-name option selected in-session): the battery scores the board
> actually displayed daily. Everything else in seq 19 and the pin addendum
> is UNCHANGED, including MIN_ADVERSE_BOTTOM_BUCKET = 10, the five lanes,
> the CSP exit arms, Holm alpha=0.10 one-sided, the ±50% cost stress, the
> twelve-month backstop, and the historical-pass-is-exploratory-only /
> forward-window-is-verdict-bearing split.
