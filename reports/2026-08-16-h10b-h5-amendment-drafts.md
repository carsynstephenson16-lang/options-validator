# Amendment drafts — H10b resume + H5 recording path (2026-08-16, rev 2 2026-08-17)

**Status: DRAFT rev 2 — NOT appended.** Rev 1 FAILED independent adversarial
review 2026-08-17 (receipt:
`reports/2026-08-17-reopen-drafts-adversarial-review-receipt.md`; blockers
BL-A/BL-B/BL-C + fixes FX-A..FX-D, all addressed below). Recording
additionally awaits an **owner confirmation loop** (review FX-G/FX-H; the
2026-08-15 N-1 precedent): the owner must select among the explicitly listed
options in `reports/2026-08-16-owner-directives.md` §"Owner confirmations
required" before any append. Provenance: owner-directed in-session 2026-08-16;
owner-delegated standing 2026-07-25. Both targets are pre-result (H10b: 0
trades, 0 fires — Repo-verified from `reports/h10/observations.jsonl`; H5:
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
   OWNER CONFIRMATION REQUIRED before append (directives §confirmations, Q2).
2. **Data-source substitution + timing convention (review FX-A).** H10b's
   daily entry evaluation reads the Schwab 15:45 ET preclose chain captures
   in place of the frozen ThetaData cache (ended 2026-07-27). This changes
   TWO things and both are declared: the quote feed, and the decision
   timestamp — entry evaluation moves from EOD marks to the 15:45 snapshot,
   while exit/mark accounting that reads official closes
   (`_load_adjusted`) stays on closes; the mixed convention is disclosed and
   conservative-direction rules are unchanged (mid-or-worse +
   SLIPPAGE_HAIRCUT + COMMISSION_PER_CONTRACT). Schwab-source IV is stored
   in percent and MUST be normalized (÷100) to the repo's decimal
   convention before any comparison (`schwab_chain_view.py:223`) — a
   normalization test is a named obligation. All registered admission
   checks (>=5 NTM monthly contracts, spread<=5 pct, OI>=100), caps, and
   exits are UNCHANGED. Missing/partial/unverified captures ⇒ session
   skipped and logged, fail-closed. Coverage: H7_WATCHLIST (11 names) is a
   verified strict subset of the 15-name capture universe — no coverage gap.
3. **Closed-trial guard (review BL-B — named test obligation).** The H10
   watcher and observation store are shared between H10a and H10b today
   (`h10_watch.py`, single `observations.jsonl`, no hypothesis
   discriminator, no adjudication guard). Before resumption: (a) the
   watcher MUST refuse to evaluate or record H10a — H10a is ADJUDICATED
   (facts.log `H10A_RESULT` 2026-08-15/16) and its record is complete at 4
   receipts; a CLOSED-state guard with a test is required; (b)
   post-resumption H10b observations go to a NAMESPACED store
   (`reports/h10/h10b_observations.jsonl` or a per-row hypothesis field) so
   no write can extend H10a's closed record. H10b's record is then the
   union of its pre-starvation receipts (through 2026-07-28) and its own
   post-resumption receipts; the 2026-07-29 → first-capture hole is
   permanent and disclosed; nothing is interpolated.
4. **No authority expansion.** No verdict change, no FIRE authority, no
   live-order path; the 7-loss bar and 2027-01-06 window end are unchanged.
   Paper only.
5. **Implementation gate + hard no-backfill floor (review BL-C — named test
   obligation).** The amendment takes observational effect only when the
   reviewed watcher change lands (Codex brief, suite green). A frozen
   constant `H10B_RESUME_FLOOR_SESSION` = the first session ON OR AFTER
   that landing; the watcher MUST refuse to evaluate or record ANY session
   with `as_of` earlier than the floor, regardless of when the command
   runs and regardless of receipt date — closing the existing `--as-of`
   past-session hole (`h10_watch.py:428-449` refuses only future dates
   today). Enforced by the constant plus a test (the brief-14 `dryrun/`
   quarantine pattern). The floor date itself is mechanical (the landing
   session), not an invented frozen number.

## H5_AMENDMENT_V1 — receipted recording path for the defined-risk side

Target: H5 Sector Income Core (ledger trial 6, registered 2026-07-04).

**Corrected framing (review FX-D):** the frozen pre-registration
(`H5_ENTRY_TRIGGER_PREREG`, 2026-07-07) already says "Evaluate (never
auto-enter)" and "owner records any entry manually in
data/positions/positions.csv" — manual owner recording was ALWAYS permitted.
"Alert-only" describes the tool, not a prohibition. What this amendment
actually adds is narrower than rev 1 implied: a **receipted recording path**
(one receipt authorizes one book action, the H6 pattern) plus the Schwab
data-source substitution, so a FIRE can be recorded with evidence instead of
informally. "Never auto-enter" is carried forward verbatim and binding: no
code writes the book; the owner (or an explicitly authorized agent, per
standing rules) records entries manually against a receipt.

Clauses:

1. **Recording path, defined-risk structures only.** A FIRE from the H5
   entry watch (owner-frozen triggers: VST <=160 per V2 amendment
   2026-07-15, AMZN <=220, IVR <=0.5) may be recorded as a paper position
   against a watch receipt. Destination by name (review FX-C): VST (also
   MSFT/CEG if ever triggered) → LEAPS core or tactical call; **AMZN → 
   tactical call only** ($600 defined-risk cap), because AMZN is not an
   authorized LEAPS name (`H4_THESIS_NAMES` = MSFT/VST/CEG) and its CSP
   lane stays alert-only. OWNER CONFIRMATION REQUIRED on this AMZN reading
   (directives §confirmations, Q3). Caps (review FX-B, correctly
   attributed): the shared H4/H5 thesis bucket $10k/name and $16k total
   (facts.log-noted 2026-07-06 — advisory, un-chained provenance,
   disclosed as such) and the $600 defined-risk cap per tactical trade.
2. **Income side (CSP / covered call / PMCC) stays alert-only.**
   Collateral-scale structures with no owner-typed cap; no cap is invented
   here; a further owner-typed amendment is the only path.
3. **Data source + IVR honesty (review BL-A — the load-bearing clause).**
   Same substitution, timing declaration, normalization obligation, and
   fail-closed skip rule as H10B clause 2. Consequence stated plainly:
   `iv_rank` needs 126 finite observations of a SINGLE-SOURCE IV series
   (`features.py:25,73-81`); the ThetaData series ended 2026-07-27 and
   splicing it onto Schwab IV is fabrication
   (`schwab_chain_view.py:334-337`). Therefore under this amendment the
   IVR leg renders fail-visible UNAVAILABLE until ~126 Schwab preclose
   sessions accumulate (~6 months from the first capture), and **H5 cannot
   FIRE during that dead period** (NaN compares false in
   `entry_watch.py:33`; price legs alone never suffice). This dead period
   is pre-disclosed, not discovered. Alternatives (drop/replace the IVR
   leg, or price-legs-only) would change an owner-frozen trigger and are
   NOT proposed here — owner-only. OWNER CONFIRMATION REQUIRED that the
   dead period is accepted (directives §confirmations, Q4).
   Implementation note: `entry_watch.py:136-137` hardcodes
   `.cache/chains/` paths — the rebuild is real code work for the brief.
4. **No authority expansion.** Paper only; never auto-enter; no live
   orders; no verdict machinery.
5. **Implementation gate + no-backfill floor.** Identical mechanism to
   H10B clause 5 (`H5_RESUME_FLOOR_SESSION`, refusal + test).

---

**Not amended here (owner-only):** H10a-v2 registration (separate packet);
any income-side collateral cap; any change to the frozen IVR trigger; the
$16k-vs-$14k sleeve tension.
