# Backup-drill disposition B — recorded input-binding invalidations

**Status:** implemented on `claude/drill-disposition-b`.
**Owner sign-off:** `reports/2026-08-14-owner-answers-decision-menu.md` ruling 1
("Drill disposition = B"), provenance label
`owner-directed in-session 2026-08-14 (disposition B)`.
**Failure evidence this answers:**
`reports/h7_forward_schwab/2026-08-14-backup-drill-failure-receipt.md`.

## Plain-language summary

The restore drill takes the backup, unpacks it somewhere safe, and re-checks
every file the sealed July "data gate" receipts said they used. On 2026-08-14
that check went red: an owner-approved refresh of the closing-price cache on
2026-08-05 rewrote files that those July receipts had already committed to.
The receipts cannot be edited (append-only), and the old bytes are gone, so
those particular checks can never pass again on their own.

Disposition B says: write down exactly what was invalidated, and let the drill
accept exactly that and nothing else. So the drill now says "PASS, with a note
naming the record" for the recorded cases, and still says FAIL for anything
that was not recorded.

## What was actually broken (measured, not asserted)

- Check: `verify_restored_tree` in `tools/h7_forward_backup.py` re-hashes each
  restored receipt's `input_files` entries inside the restored tree.
- Failing receipts: **seven**, not six —
  `reports/h7_data_gate/h7-forward-15-v1/receipts/2026-07-{17,20,21,22,23,24,27}.json`.
- Failing labels: the 15 `close:<SYM>` bindings in each receipt (the 15
  `chain:<SYM>` bindings in the same receipts still verify).
- Measured problem count: **105** (7 x 15), re-measured read-only against the
  ops checkout on 2026-08-14.
- Discrepancy with the failure receipt (recorded here, not silently fixed):
  the receipt's prose says "six ... receipts" and "90 problems" while its own
  enumeration lists seven dates. 7 x 15 = 105 is what the code produces today.
  It also calls `h7-forward-15-v1` the "old namespace"; that string is the
  CURRENT `scope_identity()["scope_id"]`, which is why none of these receipts
  also raises a `stale scope` problem.

## Mechanism

### The record

One typed fact per sealed receipt, appended through `research/facts.py`
(`append_fact`, never a hand edit), on one line:

```
H7_INPUT_BINDING_INVALIDATION <repo-relative receipt path> <canonical JSON>
```

JSON fields (exact key set; any missing or extra key voids the record):

| field | meaning |
| --- | --- |
| `schema` | `h7-input-binding-invalidation/v1` |
| `receipt` | repo-relative path, must equal the path token on the line |
| `receipt_hash` | the receipt's own content hash — the identity that matters |
| `bindings` | `{label: sealed sha256}` — what the receipt committed to |
| `observed` | `{label: sha256 at recording time}` — evidence, not a condition |
| `invalidated_by` | what rewrote the bytes (the 2026-08-05 closes refresh) |
| `recorded_session` | `2026-08-14` |
| `provenance` | `owner-directed in-session 2026-08-14 (disposition B)` |

Recording is idempotent: replaying the identical line is a no-op, and a
divergent line for the same receipt is REFUSED by `append_fact`'s dedupe
(`dedupe_prefix` = token + receipt path), so a record can never be quietly
restated.

### The acceptance rule

For a mismatch on `(receipt, label)` the drill emits PASS-WITH-NOTE only if
ALL of these hold; otherwise it FAILS exactly as before:

1. a well-formed fact exists whose `receipt_hash` equals this receipt's hash,
2. its `bindings` contain this label with **the sealed hash this receipt
   records**,
3. its `receipt` path matches where the receipt actually restored,
4. the file **exists** on both sides — only a changed hash is coverable,
5. the facts come from `ledger/facts.log` **inside the restored tree**, so the
   acceptance evidence must itself be part of the backup being drilled.

The note names the fact (`id=<12 hex of the payload hash>`, `recorded_session`,
`invalidated_by`, `provenance`) and is carried into the `backup_restore`
receipt's `verification.notes`.

### Deliberate limits

- **Sealed side only.** Coverage pins the receipt's own recorded hash, not the
  replacement bytes. The closes cache is refreshed on the ordinary operating
  cadence; pinning the replacement would re-break the drill every refresh and
  train the reflex "append another fact", which is exactly the habit that would
  hollow the rule out. The covered binding is already unverifiable forever, so
  no additional verification is given up — but this IS a relaxation, and it is
  scoped to the seven named receipts' `close:` labels.
- **No blanket amnesty — but be honest about today's scope.** A fact is bound
  to one receipt content hash and the labels it lists; every other receipt,
  every other label, every future data-gate receipt, and every `chain:` binding
  stay strictly checked. That said, those seven receipts are **the entire
  current data-gate receipt population** (measured: `data_gates: 7`), and their
  `close:` bindings are all 105 of the closes-cache bindings in play. So in
  practice the closes-cache half of this check is fully covered-by-acceptance
  right now, and only regains real force as new data-gate receipts accumulate
  under the current cache. The `chain:` half (another 105 bindings) is
  unaffected and still binds today.
- **Missing files never covered.** A vanished input is data loss, not drift.
- **Nothing pre-authorised.** The recorder only records labels that are
  mismatched at recording time.
- **Fail-closed parsing.** Unknown token, bad JSON, missing/extra field,
  non-hex hash, absolute or traversing path, or a path that disagrees with the
  payload: covers nothing.

### One more note the mechanism emits

Because coverage does not pin the replacement bytes, a *later* change to the
same file would otherwise pass silently. It does pass — and the note says so:
`WARNING: this input has changed AGAIN since the invalidation was recorded
(recorded observed=…, now=…)`. Tamper-visibility at zero fail-open cost.

## Tests (`tests/test_h7_backup.py::RecordedInvalidationTests`)

mismatch + fact = pass-with-note naming the fact; mismatch + no fact = fail;
another receipt's fact covers nothing (including one at the same path with
different content, and one naming the wrong sealed hash); a fact claiming
another path covers nothing; 13 malformed/partial records cover nothing; a
vanished input is never covered; coverage is per-label; a second change passes
but is called out in a distinct note; the recorder never pre-authorises an
intact binding; facts are read from the restored tree, not the operator's disk;
recorder is append-only, idempotent, refuses divergence, refuses a tampered
receipt.

Mutation evidence: accepting an uncovered mismatch turns every test in the file
red; dropping the receipt hash, or the sealed hash, from the coverage key each
turns exactly its isolating test red; tolerating an unexpected field turns the
malformed-record test red; tightening coverage to the observed side turns the
second-change characterization test red.

## Operating consequences

- The seven facts are appended on this branch; the drill only sees them once
  the branch merges and the ops checkout syncs. Run the drill after that, from
  the ops checkout, per runbook 08 step 8.
- **The existing 2026-08-14 backup receipt can never pass this drill**, and a
  red result on it is NOT disposition B failing. That snapshot predates the
  facts, so the `ledger/facts.log` it restores does not contain them; and the
  backup receipt for that session is immutable, so re-running `backup
  --completed-session 2026-08-14` hits the write-once conflict rather than
  producing a newer snapshot. Green is reachable only from a **fresh backup for
  a later completed session**, taken from a checkout that carries these facts.
- Expected result then: `manifest OK`, `problems 0`, `notes 105`, `ok True`.
  Verified read-only on 2026-08-14 against a temporary replica of the ops
  evidence tree (real receipts, real closes cache, no restic, ops untouched);
  the same tree with no recorded facts still produces 105 problems.
- A future closes refresh does NOT re-break these seven receipts (it does add
  the "changed AGAIN" note), and does NOT gain coverage for any other receipt.
