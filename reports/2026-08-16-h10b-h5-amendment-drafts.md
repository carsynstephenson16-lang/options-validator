# Amendment drafts — H10b resume + H5 trigger retirement/observe mode (2026-08-16, rev 3 2026-08-17)

**Status: DRAFT rev 3 — pending confirmation review, then append.** Rev 1
FAILED independent adversarial review 2026-08-17 (receipt:
`reports/2026-08-17-reopen-drafts-adversarial-review-receipt.md`; blockers
BL-A/BL-B/BL-C + fixes FX-A..FX-D addressed in rev 2). The owner
confirmation loop (review FX-G/FX-H) COMPLETED 2026-08-17: Q1–Q4 answered
and follow-ups selected — see `reports/2026-08-16-owner-directives.md`
§"Owner answers — recorded 2026-08-17". Rev 3 rewrites the H5 amendment to
the owner's actual ruling (retire the frozen trigger; observe-only during
the Schwab ramp), which moots rev 2's BL-A dead-period clause and the FX-C
AMZN-destination clause (recorded for any future rule). Provenance:
owner-directed in-session 2026-08-16 + 2026-08-17; owner-delegated standing
2026-07-25. Both targets are pre-result (H10b: 0 trades, 0 fires —
Repo-verified from `reports/h10/observations.jsonl`; H5:
`data/positions/positions.csv` has 0 rows).

---

## H10B_AMENDMENT_V1_1 — observation resumption + data-source substitution

Target: H10b (ledger seq 16, registered 2026-07-19, window ends 2027-01-06,
7-loss bar, zero positions, zero fires).

Clauses:

1. **D-1=F1 override, H10b only — with its rationale confronted (review
   FX-H).** The 2026-08-14 ruling D-1=F1 exists to prevent appending starved
   observations under an authority tier that asserts no exact-session data.
   This amendment does not wave that away: it declares the Schwab 15:45
   preclose capture lane a qualifying exact-session source **for H10b's
   entry evaluation only**, on the strength of its verification chain
   (canary 2026-08-14 15/15; per-session capture receipts). Sessions without
   a verified capture are not "starved observations recorded anyway" — they
   are skipped (clause 2). All other lanes' D-1=F1 pause is unchanged.
   Owner confirmation RECEIVED 2026-08-17 (directives §"Owner answers", Q2:
   "ya confirm overrid").
2. **Data-source substitution + timing convention (review FX-A; corrected
   per confirmation-round NEW-4).** H10b's daily entry evaluation reads the
   Schwab 15:45 ET preclose chain captures in place of the frozen ThetaData
   cache (ended 2026-07-27). The post-substitution timing convention,
   stated precisely: the QM breakout SIGNAL stays on completed-session
   OHLCV (`_load_adjusted` → `_signals_at_session`); the reference SPOT is
   `_load_raw`'s official close; ADMISSION, contract selection (delta
   0.40–0.60 within +/-10 pct of that spot), and FILL pricing come from the
   15:45 chain snapshot. The genuine mixed-timing hazard — a 15:45 chain
   priced against an official close — is disclosed here and stamped in
   every output row; conservative-direction rules are unchanged
   (mid-or-worse + SLIPPAGE_HAIRCUT + COMMISSION_PER_CONTRACT). Schwab-source IV is stored
   in percent and MUST be normalized (÷100) to the repo's decimal
   convention before any comparison (`schwab_chain_view.py:223`) — a
   normalization test is a named obligation. All registered admission
   checks (>=5 NTM monthly contracts, spread<=5 pct, OI>=100), caps, and
   exits are UNCHANGED. Missing/partial/unverified captures ⇒ session
   skipped and logged, fail-closed. Coverage: H7_WATCHLIST (11 names) is a
   verified strict subset of the 15-name capture universe — no coverage gap.
3. **Closed-trial guard (review BL-B — named test obligation; extended per
   confirmation-round NEW-1 + test tightening).** The H10 watcher and
   observation store are shared between H10a and H10b today (`h10_watch.py`,
   single `observations.jsonl`, no hypothesis discriminator, no
   adjudication guard). Before resumption: (a) the watcher MUST refuse to
   evaluate or record H10a — H10a is ADJUDICATED (facts.log `H10A_RESULT`
   2026-08-15/16) and its record is complete at 4 receipts; the guard's
   test obligation is concrete and red-green: run the watcher for a session
   inside H10a's old window and assert BOTH zero H10a evaluation AND zero
   write to any H10a record; (b) post-resumption H10b observations go to a
   NAMESPACED store (`reports/h10/h10b_observations.jsonl` or a per-row
   hypothesis field) so no write can extend H10a's closed record; (c) the
   per-session RECEIPT schema is covered too, not just the rollup:
   receipts today carry `"signals": {"H10a": ..., "H10b": ...}` and
   `hypothesis_evidence.py` asserts that exact key set — post-resumption
   receipts must drop live H10a evaluation without breaking that invariant
   (e.g. an explicit `"H10a": "ADJUDICATED"` marker or a deliberate,
   test-covered schema/invariant update), so no receipt constitutes a
   post-adjudication H10a evaluation. H10b's record is then the
   union of its pre-starvation receipts (through 2026-07-28) and its own
   post-resumption receipts; the 2026-07-29 → first-capture hole is
   permanent and disclosed; nothing is interpolated.
4. **No authority expansion.** No verdict change, no FIRE authority, no
   live-order path; the 7-loss bar and 2027-01-06 window end are unchanged.
   Paper only.
5. **Implementation gate + hard no-backfill floor (review BL-C — named test
   obligation).** The amendment takes observational effect only when the
   reviewed watcher change lands (Codex brief, suite green). A frozen
   constant `H10B_RESUME_FLOOR_SESSION` = the LATER of (i) the first
   session on/after the implementation landing and (ii) this amendment's
   ledger append date (confirmation-round NEW-2, matching the seq-26
   append-timestamp precedent so no agent-chosen merge date can start a
   verdict-bearing record); the watcher MUST refuse to evaluate or record
   ANY session with `as_of` earlier than the floor, regardless of when the
   command runs and regardless of receipt date — closing the existing
   `--as-of` past-session hole (`h10_watch.py:428-449` refuses only future
   dates today). Enforced by the constant plus a test (the brief-14
   `dryrun/` quarantine pattern). The floor date itself is mechanical, not
   an invented frozen number.

## H5_AMENDMENT_V1 — entry-trigger retirement + observe mode (rev 3, owner-ruled 2026-08-17)

Target: H5 Sector Income Core — ledger seq 5, trial_count 6, registered
2026-07-04 (`hypothesis_id` is null in that entry's original schema, so this
amendment binds its target by seq number explicitly; confirmation-round
NEW-6 — note seq 6 is H6, a different hypothesis).

**What the owner ruled (2026-08-17, in-session + explicit option
selection):** "get rid of the h5 frozen rule entry i want to observe while
its testing" (sic); selected option "Retire rule; observe-only"; rejected
the IVR dead period (Q4). Context carried from review FX-D: the frozen
prereg's "alert-only" described the tool, and manual owner recording was
always permitted — but with the trigger retired there is nothing to fire,
so the recording-path machinery of rev 1/2 is NOT enacted here.

Clauses:

1. **Trigger retirement (NAMED SUPERSESSION; attribution corrected per
   confirmation-round NEW-5).** `H5_ENTRY_TRIGGER_PREREG` (2026-07-07,
   owner-frozen: VST <=140, AMZN <=220, IVR <=0.5) and
   `H5_ENTRY_TRIGGER_AMENDMENT_V2` (2026-07-15, which changed ONE number:
   VST 140→160; AMZN 220 and IVR 0.5 unchanged) are RETIRED as entry
   rules, owner-directed 2026-08-17. In the same landing as observe mode,
   `entry_watch`'s trigger evaluation output is disabled or relabeled
   (confirmation-round NEW-3) so the daily ritual cannot print trigger
   prose the ledger says is retired. They remain on
   the append-only record as history; any fire-like output computed from
   them after this amendment is void. No replacement rule is created here
   — a future entry rule is a new owner-typed frozen decision, and per
   owner ruling Q3 (2026-08-17) any future AMZN entry routes to a tactical
   call only ($600 defined-risk cap; AMZN LEAPS unauthorized).
2. **Observe mode during the Schwab ramp.** The H5 watch lane converts to
   a daily OBSERVER on the Schwab 15:45 preclose captures (D-1=F1 override
   owner-confirmed, Q2 — same qualifying-source declaration, timing
   convention, IV percent→decimal normalization obligation, and
   fail-closed skip rule as H10B clause 2): it records per-name price,
   data availability, and single-source IV-history accumulation (count of
   finite Schwab IV observations toward the 126 needed for a computable
   IV rank — `features.py:25`), fail-visible on anything missing. It
   fires nothing, alerts nothing as an entry signal, and records no paper
   positions. Output is observational and non-verdict-bearing.
3. **Income side (CSP / covered call / PMCC) unchanged.** Display-only;
   no owner-typed collateral cap exists; no cap is invented here.
4. **No authority expansion.** Paper only; never auto-enter (carried
   forward verbatim from the retired prereg); no live orders; no verdict
   machinery; observe-mode output cannot authorize a book action.
5. **Implementation gate + no-backfill floor.** Identical mechanism to
   H10B clause 5 (`H5_RESUME_FLOOR_SESSION`, refusal + test); observer
   rows exist only for sessions on/after the floor.

---

**Not amended here (owner-only):** H10a-v2 registration (separate packet;
owner selections recorded — ~2.5-month window, starvation pre-accepted
pending the quoted number); any income-side collateral cap; any FUTURE H5
entry rule (new owner-typed decision); the $16k-vs-$14k sleeve tension.
