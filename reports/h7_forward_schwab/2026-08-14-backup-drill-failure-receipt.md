# Backup/restore drill — 2026-08-14 — FAILED (verified diagnosis)

**Run:** post-canary, per runbook 08 step 8, with the hardened slice-B tool
(PR #38, merged). `backup --completed-session 2026-08-14` succeeded
(receipt `reports/h7_receipts/backup/2026-08-14.json`); `restore-check
--backup-receipt <that> --completed-session 2026-08-14` **exit 2,
ok: False** — 90 problems: `changed input close:<SYM>` for all 15 symbols
across the six old-namespace data-gate receipts
(`reports/h7_data_gate/h7-forward-15-v1/receipts/2026-07-{17,20,21,22,23,24,27}.json`).
No restore receipt was written (the tool raises before writing on failure).
The Schwab-lane artifacts verified clean (`manifest: OK`).

## Verified root cause (not a tool defect, not backup corruption)

The check re-hashes each restored receipt's recorded `input_files` INSIDE
the restored tree (`tools/h7_forward_backup.py:203-208`) — an internal-
consistency proof. Today's live state is internally inconsistent: the
owner-approved closes refresh (directed 2026-08-04, files stamped
2026-08-05 10:59) rewrote `.cache/underlying/*.parquet`, while the sealed
July receipts record the pre-refresh hashes. Verified concretely:
`2026-07-17.json` records `close:AMD` sha256 `555dc6cd…`; the current
`.cache/underlying/AMD.parquet` hashes `d5da4538…`. Every snapshot taken
since 2026-08-05 inherits this mismatch; it went undetected because the
last drill ran 2026-07-20.

**The drill did its job.** The failure is real evidence of state drift and
is recorded as such. Per the failure-stops rule, runbook 08 stops at step 8;
the registration chain's drill requirement is NOT satisfied.

## Disposition options (owner/spec decision — NOT decided here)

- **(A) Scope the binding check to the active namespace:** treat
  `h7-forward-15-v1` (PAUSED per OD-3) receipts as sealed history — verify
  their presence and JSON integrity, but bind input-hash checks to the
  active scope's namespace only. Smallest change; relaxes a check, so it
  needs its own spec + independent adversarial review + owner sign-off.
- **(B) Record the invalidation, then accept recorded invalidations:**
  append a fact/amendment explicitly acknowledging that the 2026-08-04
  closes refresh invalidated the input bindings of the six sealed July
  receipts; drill accepts input-hash mismatches ONLY when covered by such a
  recorded fact. More machinery, stronger honesty; same review path.
- **(C) — rejected:** repointing or rewriting the old receipts is forbidden
  (append-only), and the pre-refresh close bytes exist only in pre-08-05
  restic snapshots; receipts cannot be edited to reference an archival path.

Until (A) or (B) lands through review, the drill stays RED and registration
stays blocked on it. The canary itself is unaffected (its manifest verified
independently at 15:48 ET).
