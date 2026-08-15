# RQ2 + A2 pre-result amendment drafts — 2026-08-15 owner rulings

**Status:** review round 1 (2026-08-15,
`reports/2026-08-15-monday-ship-adversarial-review-receipt.md`) returned
**FAIL on this document as then written** (blockers B-2, B-3 + fixes); the
named blockers and fixes were applied in this revision, which goes back for
a confirmation round. Only on a confirmation-round PASS is each block below
appended verbatim (minus this document's headers) to
`ledger/experiments.jsonl` via the `research/ledger.py` typed API under the
recording provenance "owner-delegated standing 2026-07-25 (drafted by Fable
session 2026-08-15; adversarial review round 1 FAIL → fixes applied →
round 2 verdict recorded in the receipt)". The owner retains veto by further
append-only amendment.

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
> than assumed. NAMED SUPERSESSION (per the seq-25 precedent of naming
> supersessions): RQ2_A2_PIN_ADDENDUM_V1 clause (iv) is superseded IN PART —
> its UNKNOWN-refuses behavior applied to B1's FIRING is superseded (an
> UNKNOWN earnings state no longer blocks the badge; it renders as the
> fail-visible earnings_tag UNKNOWN), while its applicable-event-window
> definition SURVIVES unchanged as the frozen definition of
> earnings_tag = "event-priced", and its earnings-provenance-via-h7_earnings
> sourcing rule survives unchanged. OWNER-WORDING DISCLOSURE: the owner's
> first sentence 2026-08-15 — "i dont want that to fire if theres confirmed
> earnings i want that fired daily and studied" — admits two literal
> readings; the ambiguity was put to the owner in-session as an explicit
> three-option question (fire daily on every name / fire only when NO
> earnings near / keep both versions) and the owner selected "Fire daily on
> every name", which is the rule recorded here. B1's numeric thresholds are
> UNCHANGED (ts_pctl >= 0.75 AND vrp_pctl <= 0.25, seq 18 owner-typed).
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
> source — verified by search of both entries and the pin addendum).
> Forward-window OPTIONS-DERIVED marks (badge inputs and scoring marks that
> come from option chains) use the daily 15:45 ET pre-close Schwab chain
> captures — the manifest-verified receipts under
> reports/schwab_chains/<date>/ with their parquet snapshots — not official
> closing prints, which no available provider supplies for these chains.
> Underlying-price inputs (A1's dist_52w_high, mom_1m, rv21) continue to
> come from the completed-session closes store (data/underlying_closes.py),
> unchanged. Sessions with no verified capture are recorded as gaps
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
> most recent 24 cycles. CAP PROVENANCE (mirroring seq 25's treatment of its
> own LLM-proposed 6-cycle floor): the 24-cycle cap is LLM-proposed
> 2026-08-15, not owner-typed, chosen for regime comparability across names
> whose histories span 15 to 102 cycles; it remains subject to
> re-confirmation and owner veto by further pre-result amendment. SCOPE
> DISCLOSURE: seq 25 enumerated the pin scope as which line ranks, its
> direction, and insufficient-history handling; this clause additionally
> pins cycle geometry, the entry-anchor convention, the aggregator, the
> annualization convention, and the lookback cap — deliberately, so no free
> parameter survives to be chosen after results exist; that extra pinning
> is this amendment's choice, not a seq-25 requirement. Cycles whose anchor
> session has no cached chain are SKIPPED, never bridged; the open cycle is
> excluded (seq 25, unchanged). Direction: higher ranks toward the top,
> matching the registered one-sided top-beats-bottom design. For the
> RANKING, all completed cycles are included (earnings-window cycles are
> NOT excluded); reason recorded: the point-in-time earnings gating store
> covers too few names for clean-only to be labelable board-wide, and
> excluding by coverage would make data coverage a hidden signal. Seq 25's
> separate clean-vs-earnings DISPLAY split stays binding: where coverage
> exists it renders; where coverage is absent it renders UNKNOWN,
> fail-visible — never silently omitted. Names below the pinned 6-cycle floor are EXCLUDED FROM BOTH
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
> 2026-08-15). NO-AUTHORITY CLAUSE: 5c defines only the FORM a tiebreak
> would take IF a promotion ever occurs; it confers no promotion authority,
> changes no ordering of any board or output today or at any time before a
> promotion, and adopting the tiebreak in practice requires a separate
> owner-typed promotion decision passing the registered promotion rule plus
> every applicable registration gate. This is the first tiebreak concept in
> this ledger for RQ2 and it is form-only. This clause closes the
> tiebreak-form gap for V1 only; B1 and A1 are untouched.
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
> actually displayed daily. TERCILES IS THE RULE; "top 6 versus bottom 6"
> is its instantiation on the current 18-name board. For HISTORICAL
> exploratory cohorts, each cohort takes terciles of the names with cached
> data at that cohort's formation date, with per-cohort name counts
> printed; every historical output carries a permanent disclosure that the
> universe is the 2026-08 board applied retroactively and that name
> inclusion is outcome-informed (several names joined the board because of
> what they became — the H10 precedent for permanent outcome-informed
> disclosures applies directly). Everything else in seq 19 and the pin
> addendum is UNCHANGED, including MIN_ADVERSE_BOTTOM_BUCKET = 10, the five
> lanes,
> the CSP exit arms, Holm alpha=0.10 one-sided, the ±50% cost stress, the
> twelve-month backstop, and the historical-pass-is-exploratory-only /
> forward-window-is-verdict-bearing split.
