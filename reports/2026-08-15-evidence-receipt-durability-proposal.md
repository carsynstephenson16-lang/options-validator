# Receipt durability — why capture evidence isn't reliably tracked, and what to do

**Date:** 2026-08-15 (scheduled weekend-cleanup session)
**Status:** PROPOSAL — investigation + options for the owner. **No production
behavior was changed.** No file in `~/options-validator-ops` was written,
moved, or deleted; no provider call; no ledger write.
**Scope:** durability of *receipt* artifacts (`reports/schwab_chains`,
`reports/h7_receipts`). Chain **bytes** under `.cache/` are a separate,
already-covered question — see §5.

---

## 0. Plain-language summary

Every afternoon the Schwab capture writes two small JSON files that say "this
capture happened, here's what it contained, here's the hash." Those files are
the proof the capture was real. The question was: why don't they get saved
into git automatically?

The short answer: **the capture script never had that job.** Saving evidence
to git is the *daily ritual's* job, in its Step 8 — and Step 8 only saves the
Schwab capture receipts when the ritual is running at "full authority." Right
now the ritual runs at the lower "data" tier, because the H7 lanes are paused
pending switch-on. So the receipts get written to disk and then simply sit
there until somebody commits them by hand.

That's what happened on 2026-08-14: the canary receipt was committed manually,
and the commit message says so outright.

The good news is that nothing is actually lost, and the fix is small.

---

## 1. Correction to the premise

The task that commissioned this investigation stated that
`reports/schwab_chains/` "exists only in the ops checkout and is untracked
there." **That is no longer true, and it is worth being precise about why.**

| Claim | Measured 2026-08-15 |
|---|---|
| `reports/schwab_chains/` untracked in ops | **False.** `git -C ~/options-validator-ops ls-files reports/schwab_chains/` returns both files. |
| Exists only in ops | **False.** Both files are on `origin/main`. |

Both files — `2026-08-14/manifest.json` and `2026-08-14/preclose.json` — were
committed in **`13d48a9`** ("evidence: first real Schwab preclose canary —
2026-08-14 15/15 OK, manifest verified"), which is an ancestor of `main`.

That commit's own message is the diagnosis:

> "Persisted manually because the daily ritual (normal committer) is
> authority-blocked pending switch-on."

So the premise was true of the *mechanism* and false of the *outcome*: the
automation did not track these files, and a human noticed and did it by hand.
**The gap is real; it was papered over by manual effort, which is exactly the
failure mode worth fixing** — the next capture won't have a session watching
it.

There **is** a still-untracked receipt today, and it is the cleanest possible
illustration (§3).

---

## 2. Why the capture wrapper didn't track it: it has no commit step

`tools/schwab_chain_capture.sh` (159 lines) contains **no `git add`, no `git
commit`, no `git push`, and no `restic` call.** Every one of its git
invocations is read-only — `branch --show-current`, `rev-parse`,
`rev-list --count`, `diff --name-only`, and a bounded `fetch`.

Its `EVIDENCE_ALLOW` array is easy to mistake for a staging allow-list. It is
not. It is a **divergence-tolerance** list used by
`alignment_divergence_is_evidence_only()`: the wrapper refuses to run if the
ops checkout's tree differs from reviewed `origin/main` anywhere *outside*
those paths. Its purpose, per owner decision D-3, is "no unreviewed CODE runs
unattended" — it decides **whether to proceed**, never **what to persist**.

```
EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
                reports/h7_receipts reports/h7_data_gate reports/h5
                reports/h6_forward reports/h8_forward reports/h10
                reports/ritual reports/intraday_capture reports/live_probe
                reports/cache_runs reports/schwab_chains)
```

**Repo-verified.** So "the capture wrapper's evidence commit" does not exist —
there is nothing in the wrapper that failed. Persistence was always delegated
to the daily ritual.

---

## 3. Where it actually falls through: the ritual's tier gate

`tools/daily_ritual.sh` Step 8 ("DURABILITY") builds its staging list in two
tiers (`tools/daily_ritual.sh:454-468`):

```sh
DATA_TIER_PATHS=(reports/ritual reports/intraday_capture reports/live_probe reports/cache_runs)
GIT_ADD_PATHS=("${DATA_TIER_PATHS[@]}")
...
if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then
  FULL_TIER_PATHS=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
                   reports/h7_receipts reports/h7_data_gate reports/h5
                   reports/h6_forward reports/h8_forward reports/h10
                   reports/schwab_chains)
  GIT_ADD_PATHS=("${GIT_ADD_PATHS[@]}" "${FULL_TIER_PATHS[@]}")
fi
```

`reports/schwab_chains` and `reports/h7_receipts` are in **`FULL_TIER_PATHS`
only**. The H7 lanes are paused pending switch-on, so `FULL_AUTHORITY_RC` is
non-zero and neither path is ever staged. The ritual then commits and pushes
the data-tier paths and reports "evidence: committed" — **truthfully, for the
paths it staged.** Nothing errors. Nothing warns. The Schwab receipt is simply
not in the set.

**The live proof, measured today:**

| Backup receipt | Written when | Tracked? |
|---|---|---|
| `reports/h7_receipts/backup/2026-07-17.json` | during the live H7 window (full authority) | **tracked on `origin/main`** |
| `reports/h7_receipts/backup/2026-08-14.json` | 2026-08-14 (data tier) | **untracked — still `??` in ops today** |

Same directory, same writer, same allow-lists. The only difference is which
authority tier was in force. This is the gap, reproduced without ambiguity.

### 3a. A second, smaller gap: the backup receipt lags its own snapshot

In `tools/h7_forward_backup.py`, `run_backup()` takes the restic snapshot
**first** and writes the receipt to
`reports/h7_receipts/backup/<session>.json` **after** (lines ~150-174). Since
`reports/h7_receipts` is itself in `BACKUP_PATHS`, the receipt for snapshot
*N* is only captured by snapshot *N+1*.

This is benign in steady state and probably not worth code churn — but it does
mean the newest backup receipt is always the one least protected, which
compounds §3 rather than offsetting it. Worth a sentence in the runbook, not a
rewrite.

---

## 4. What `tools/h7_forward_backup.py` already covers

The restic allow-list is **broader** than the ritual's git staging list, and
notably it is **not tier-gated**:

```python
BACKUP_PATHS = (
    Path(".cache/chains"), Path(".cache/schwab_chains"), Path(".cache/underlying"),
    Path("data/earnings/gating_v3.csv"), Path("data/earnings/assertions_v2.csv"),
    Path("data/earnings/assertions.csv"), Path("data/chain_cache_manifest.txt"),
    Path("ledger/facts.log"), Path("reports/h7_data_gate"),
    Path("reports/h7_receipts"), Path("reports/h7_forward"),
    Path("reports/schwab_chains"), Path("reports/h7_forward_schwab"),
    Path("ledger/h7_forward_schwab"),
)
```

So **`reports/schwab_chains` and `reports/h7_receipts` are already inside the
restic backup**, whenever a snapshot runs. `RESTIC_REPOSITORY` is present in
the ops `.env` (key existence checked; value not read).

**Honest caveat — unverified:** this session did **not** run `restic
snapshots`, because that needs the repository credentials and this is a
read-only cleanup session. So "restic covers it" is established from the
allow-list (**Repo-verified**) but the existence and recency of actual
snapshots is **not verified here**. The 2026-08-14 restore drill is on record
as FAILED for an unrelated reason (input-binding invalidation, now addressed
by disposition B), which is a reminder that backup coverage on paper and a
green restore are different claims.

**Net position today:** the receipts have **one** durable copy (restic,
assuming snapshots run) and **zero** automatic git copies. Git is described in
the ritual's own comments as "the primary durable copy," with restic as
"belt-and-suspenders." Right now that's inverted for these two paths.

---

## 5. Out of scope, deliberately

Chain **bytes** (`.cache/schwab_chains/*.parquet`, 15 files for 2026-08-14) are
gitignored by design and covered by restic. They are not part of this proposal
and **must not** be added to any git staging list. Note also that
`~/options-validator-ops/.cache` is a **symlink** to the main checkout's
`.cache` — so a restic run from ops and one from main cover the same bytes,
and the ops checkout does not hold a second copy.

---

## 6. Options

### Option A — extend the ritual's data-tier staging list (recommended)

Move `reports/schwab_chains` and `reports/h7_receipts` from `FULL_TIER_PATHS`
into `DATA_TIER_PATHS`, so they are staged at every tier.

- **Why it fits:** the tier gate exists to stop the ritual from *claiming H7
  authority it doesn't have* — publishing watcher/gate decisions as if the
  lanes were live. A capture receipt is not an authority claim; it is a record
  that a capture happened, and it is produced under data tier already. The
  fence that matters (`ledger/h7_forward*`, `reports/h7_data_gate`,
  `reports/h5`, `reports/h6_forward`, `reports/h8_forward`, `reports/h10`)
  stays exactly where it is.
- **Cost:** a one-line-ish change to a scheduled production script, so it
  needs the usual treatment — a test that the data-tier list contains the two
  paths and still excludes the H7-authority paths, plus a red/green proof.
- **Risk:** the commit message under data tier currently asserts "No H7
  evidence was produced by this run." Staging `reports/h7_receipts` would make
  that sentence misleading. **The message must be amended in the same change**
  — this is the part most likely to be missed.
- **Interaction:** both paths are already in the wrapper's `EVIDENCE_ALLOW`,
  so the resulting commit stays evidence-only and will **not** trip the 15:45
  alignment gate. Verified against the two lists.

### Option B — give the capture wrapper its own commit step

Have `schwab_chain_capture.sh` stage and commit its own receipt.

- **Against:** it duplicates Step 8's commit/push/retry logic (including the
  bounded-push discipline and the CRITICAL-on-push-failure rule), and it makes
  the wrapper a git *writer* when today it is a pure reader whose only git role
  is refusing to run. That's a meaningful increase in what can go wrong at
  15:45, in the one process whose failure loses irreplaceable data.
- **For:** it decouples receipt durability from the ritual running at all.
  That is a real advantage if the ritual is ever skipped — but the ritual is
  the thing that runs daily, so the scenario is narrow.
- **Verdict:** not recommended over A.

### Option C — accept backup-only, document it

Leave the code alone; state plainly in the runbook that Schwab receipts are
restic-only until switch-on, and that anyone landing a canary commits it by
hand (as 13d48a9 did).

- **For:** zero production change during a canary-sensitive period.
- **Against:** it depends on a human noticing, every time. It already required
  exactly that once. Once the forward window is live and the ritual is writing
  receipts unattended over ~70 sessions, "someone will notice" is not a
  durability plan — and §4's caveat means the single remaining copy is one
  whose snapshots this session could not verify.

### Recommendation

**Option A, with the commit-message amendment treated as part of the change,
and not landed until after the canary period.** The switch-on arc is mid-flight
(S1 needs three clean sessions, earliest Mon 2026-08-17 — see
`reports/h7_forward_schwab/2026-08-15-registration-packet-bar7-draft.md` §1),
and `tools/daily_ritual.sh` is a scheduled production script. Landing a
staging-list change in the middle of a provenance-proving window would muddy
the very sessions S1 is meant to certify.

**Interim, at zero risk:** commit the one untracked receipt
(`reports/h7_receipts/backup/2026-08-14.json`) by hand, exactly as 13d48a9 did
for the canary. That closes today's actual exposure without touching a
scheduled script. **This session did not do it** — it is a write into the ops
production checkout, which the session's terms make read-only.

---

## 7. Claim labels

| Claim | Label |
|---|---|
| `schwab_chain_capture.sh` contains no commit/push/restic call | **Repo-verified** (full-file grep) |
| `EVIDENCE_ALLOW` is a divergence-tolerance list, not a staging list | **Repo-verified** (its only consumer is `alignment_divergence_is_evidence_only`) |
| `reports/schwab_chains` + `reports/h7_receipts` are `FULL_TIER_PATHS`-only | **Repo-verified** (`tools/daily_ritual.sh:454-468`) |
| Both paths are in restic `BACKUP_PATHS`, untiered | **Repo-verified** (`tools/h7_forward_backup.py:60-74`) |
| `2026-08-14.json` untracked while `2026-07-17.json` is tracked | **Measured** 2026-08-15 |
| Both files under `reports/schwab_chains/` are on `origin/main` via `13d48a9` | **Measured** 2026-08-15 |
| restic snapshots actually exist and are current | **NOT VERIFIED** — needs credentials; see §4 |
| An Option-A commit would not trip the 15:45 alignment gate | **Inference** from comparing the two lists; would be pinned by the test Option A requires |
