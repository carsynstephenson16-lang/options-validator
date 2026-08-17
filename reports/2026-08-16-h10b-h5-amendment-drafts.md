# Amendment drafts — H10b resume + H5 recording path (2026-08-16)

**Status: DRAFT — pending independent adversarial review + Fable sign-off
before any ledger append.** Provenance: owner-directed in-session 2026-08-16
(source of record: `reports/2026-08-16-owner-directives.md`); recording path
is the owner-delegated standing 2026-07-25. Both targets are pre-result
(H10b: 0 trades, 0 fires; H5: no recorded paper positions), so these are
pre-result amendments, not result reinterpretations.

---

## H10B_AMENDMENT_V1_1 — observation resumption + data-source substitution

Target: H10b (ledger seq 16, registered 2026-07-19, window ends 2027-01-06,
7-loss bar, zero positions, zero fires).

Clauses:

1. **D-1=F1 override, H10b only.** The 2026-08-14 owner ruling D-1=F1 (no
   hypothesis lane runs under data-tier authority) is overridden by the owner
   for H10b alone (owner-directed 2026-08-16: "reopen … 10b"). All other
   lanes' pause status is unchanged by this amendment.
2. **Data-source substitution.** H10b's daily entry evaluation may read the
   Schwab 15:45 ET preclose chain captures (the lane proven by the 2026-08-14
   canary, 15/15) in place of the frozen ThetaData chain cache, which ended
   2026-07-27. All registered admission checks (>=5 NTM monthly contracts,
   spread<=5 pct, OI>=100), fill rules (mid-or-worse + SLIPPAGE_HAIRCUT +
   COMMISSION_PER_CONTRACT), caps, and exits are UNCHANGED — only the feed
   that supplies quotes changes. Sessions where the preclose capture is
   missing, partial, or fails verification are skipped and logged
   (fail-closed), identical in spirit to the registered
   source-health-per-name entry ban.
3. **Coverage disclosure (append-only honesty).** No observation is possible
   for 2026-07-29 → the first post-amendment capture session; that hole is
   permanent and disclosed. The observation record remains the union of the
   pre-starvation receipts (through 2026-07-28) and post-resumption receipts;
   nothing in between is interpolated.
4. **No authority expansion.** This amendment grants no verdict change, no
   FIRE authority, no live-order path, and does not alter the 7-loss bar or
   the 2027-01-06 window end. Paper only.
5. **Implementation gate.** The amendment takes observational effect only
   when the watcher re-pointing lands (Codex brief, adversarially reviewed,
   suite green). Until then H10b stays paused in fact; no receipt may be
   backfilled to before that landing.

## H5_AMENDMENT_V1 — paper-position recording for the defined-risk side

Target: H5 Sector Income Core (ledger trial 6, registered 2026-07-04).

Clauses:

1. **Alert-only removed for defined-risk structures.** A FIRE from the H5
   entry watch (owner-frozen triggers: VST <=160 per V2 amendment 2026-07-15,
   AMZN <=220, IVR <=0.5) may now result in a recorded paper position (LEAPS
   core or tactical call), written to the positions store via the same
   manual/receipted pattern the other lanes use — one receipt authorizes one
   book action. Existing owner-frozen caps bind unchanged: $10k premium/name,
   $16k LEAPS total, $600 defined-risk per tactical trade.
2. **Income side (CSP / covered call / PMCC) stays alert-only.** These are
   collateral-scale structures with no owner-typed cap in existence; no cap
   is invented here. They remain alert/display-only until the owner types a
   collateral cap in a further amendment.
3. **Data source.** Same substitution and fail-closed skip rule as
   H10B_AMENDMENT_V1_1 clause 2 (Schwab preclose captures; frozen cache is
   historical only). Same D-1=F1 override scope: H5's watch lane only.
4. **No authority expansion.** Paper only; no live orders; no verdict
   machinery is created — H5 remains a registered forward lane whose
   evaluation design is unchanged apart from positions now being recordable.
5. **Implementation gate.** Same as H10b clause 5: effect begins when the
   reviewed implementation lands; no backfill.

---

**Not amended here (owner-only):** H10a-v2 registration (separate packet);
any income-side collateral cap; the $16k-vs-$14k sleeve tension.
