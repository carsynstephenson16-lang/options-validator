# H7 forward repair operations

The official scope is `h7-forward-15-v1`. Its names and hash are recorded in
every current H7 receipt. Reports from the former 12-name scope remain
historical and cannot satisfy the current watcher or activation checks.

The safe command order for one completed session is:

```text
source health -> data gate -> watcher
```

Source health writes a receipt. The data gate must be given that receipt and
writes its own receipt. The watcher must be given the successful data-gate
receipt; it rechecks every close and chain hash before it can show actionable
entries.

The refresh runner starts with four workers, retries only transport-shaped
failures, writes cache files atomically, and records a resumable task manifest.
Use `--manifest` to choose a run-specific manifest. No refresh command is
invoked by the data gate or watcher.

Backups use Restic. Set `RESTIC_REPOSITORY` and either
`RESTIC_PASSWORD_COMMAND` or `RESTIC_PASSWORD_FILE`; passwords are never
passed as command arguments. The backup allow-list includes H7 chains,
underlying closes, earnings stores, facts, manifests, receipts, and H7
reports. It excludes environment files, credentials, temporary files, and
unrelated caches.

The allow-list also includes the prepared Schwab restart paths:
`.cache/schwab_chains/`, `reports/schwab_chains/`,
`reports/h7_forward_schwab/`, and `ledger/h7_forward_schwab/`. A real restore
drill for that lane requires a verified live canary package; do not substitute
synthetic bytes for operational durability evidence.

```sh
uv run python tools/h7_forward_backup.py backup \
  --completed-session YYYY-MM-DD
uv run python tools/h7_forward_backup.py restore-check \
  --backup-receipt <path of the backup receipt written by the command above> \
  --completed-session YYYY-MM-DD
```

`restore-check` no longer accepts `--snapshot latest` (hardening, 2026-08-14).
`--backup-receipt` is REQUIRED: the tool reads that receipt, restores the exact
`snapshot_id` it names, and refuses unless the restored inventory equals the
receipt's `input_files` exactly. `--snapshot` is now optional and only asserts
that the caller's expected id matches the receipt's; a mismatch is refused.
"Latest" was never durability evidence — it can silently resolve to a different
snapshot than the one being attested.

Stage 8 remains closed. The only real-store writer is
`tools/h7_manual_activate.py`; it requires the literal confirmation token,
owner fields, independent review, a valid empty ledger, current 15-name
receipts, a fresh verified restore, and a clean source tree. Do not run it as
part of routine refresh or repair verification.

## Preclose Schwab chain capture (audit M7)

`tools/schwab_chain_capture.sh` runs `options_researcher.schwab_chain_capture`
once, intended for 15:45 ET on weekdays via its own LaunchAgent (installed in
production since 2026-08-15). Read-only; never trades; independent of the
display-only intraday capture lane.

*Since 2026-09-02 (owner-directed; Brief 30's isolated-lane design):* a
SEPARATE wrapper, `tools/schwab_chain_intraday_capture.sh`, fires at 10:00
and 13:00 ET via `com.carsyn.options-validator.schwab-chain-intraday.plist`.
It self-selects only among its own `morning` / `midday` slots (a late fire
inside the pre-close window resolves to NONE and refuses) and passes
`--session-tag`; those slots write to the isolated
`.cache/schwab_chains_intraday/<tag>/` + `reports/schwab_chains_intraday/<tag>/`
namespace with their own receipt kind and convention, precisely so they can
never collide with the first-write-wins pre-close artifacts described below.
Everything in this section about the pre-close lane (namespace, retry
constraint, H7 evidence status) is unchanged; the intraday packages are not
H7 evidence. Details: `tools/launchagents/README.md` "Schwab chain intraday".

**Same-day-retry constraint.** Each run refetches the WHOLE watch universe
live in one pass -- there is no per-symbol resume. Both the per-symbol
parquet writes and the session-level receipt are immutable:
`_write_parquet_once` refuses to overwrite an existing file unless the new
bytes hash-match it exactly, and `_write_receipt` is first-write-wins for the
session (a second write for the same session must be byte-identical text or
it is refused). Live market data and the receipt's own wall-clock timestamp
fields (`captured_at_et` / `captured_at_utc`) differ between any two
invocations, so in practice a session's receipt can be durably completed in
only **one atomic run per day**:

- A first run that succeeds completely writes the session's receipt once;
  that receipt is now locked for the day.
- A first run that fails partially (some symbols captured, some not) still
  writes a `failed` receipt. A second run the same day does **not** pick up
  where the first left off and fill the gap -- it refetches everything live,
  which will very likely produce different bytes for the already-captured
  symbols (hash mismatch -> refused) and a different receipt text (refused ->
  `RECEIPT CONFLICT`, exit 2) rather than a completed session.
- Bottom line: treat a partial or failed preclose day as needing **explicit
  operator handling** (accept the gap for that session, or otherwise
  investigate before touching anything under `.cache/schwab_chains/` or
  `reports/schwab_chains/`) -- never as "just re-run the wrapper." A blind
  same-day re-run is the wrong reflex and will usually just add a
  `RECEIPT CONFLICT` on top of the original problem.

The wrapper's own failure-taxonomy mirrors the intraday lane: it classifies a
nonzero exit from evidence in the module's printed output (never the exit
code alone, since exit 2 is shared between a genuine receipt conflict and an
unrelated argparse usage error) into `SCHWAB REAUTH REQUIRED` (expired Schwab
refresh token), `SCHWAB CHAIN REFUSED` (outside the regular session or
preclose timing tolerance), `SCHWAB CHAIN RECEIPT CONFLICT`, a partial
per-symbol `SCHWAB CHAIN PARTIAL FAILURE`, or a generic unrecognized-failure
fallback -- and fires a single `osascript` desktop notification (a silent
no-op off macOS) summarizing the result either way.

## Checkout alignment rules R1 / R2 (brief 11 §9.1)

`docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md` §9 is the
source; these are the numbered operator steps.

1. **R1 — fast-forward after every merge.** *Any* merge to `origin/main`, by
   any session, agent, or the owner, is not complete until **both** production
   checkouts are fast-forwarded:

   ```bash
   git -C ~/options-validator-ops fetch -q origin main && git -C ~/options-validator-ops merge --ff-only origin/main
   git -C ~/options-validator-research fetch -q origin main && git -C ~/options-validator-research merge --ff-only origin/main
   git -C ~/options-validator-ops rev-parse HEAD          # must equal origin/main
   git -C ~/options-validator-research rev-parse HEAD     # must equal origin/main
   ```

   If `--ff-only` refuses, **STOP**: ops holds local commits — usually the
   ritual's own evidence commit after a failed fail-soft push. Do not merge or
   reset; diagnose first, and never drop the evidence commit to satisfy a
   guard.

2. **R2 — pre-canary self-check, before 15:45 ET on every trading day.**
   Confirm, after a fetch, that `git -C ~/options-validator-ops rev-parse HEAD`
   equals `git -C ~/options-validator-ops rev-parse origin/main`. A refusal at
   15:45 loses that session's chains **permanently**.

   Since owner decision D-3 (2026-08-14) the wrapper tolerates one specific
   divergence: HEAD **ahead** of `origin/main` by commits that touch only
   evidence allow-list paths (the ritual's own unpushed evidence). Everything
   else still refuses — a code commit ahead, or being **behind** `origin/main`
   at all. The ritual now also raises a failed push to CRITICAL with the
   realign command in the notification, so the ahead-case is loud on the
   morning it happens.

   > **R2 is unenforced today and has already failed once.** On 2026-08-14 PR
   > #36 merged at 10:28:03 ET and ops was realigned only at 14:28:10 ET — four
   > hours behind `origin/main`, undetected; nothing but a human happening to
   > act closed the gap. Whether R2 becomes a mechanism (**D-6a**: a scheduled
   > pre-15:45 alignment check — a NEW plist, so it needs an owner
   > `launchctl bootstrap`), stays this documented manual step (**D-6b**), or
   > the risk is explicitly accepted and written down (**D-6c**) is **owner
   > decision D-6 — PENDING**. This section is the D-6b minimum in the interim.

## Activation day (Schwab)

Run `tools/h7_activation_day.sh` in `~/options-validator-ops` on the intended
activation day, after that morning's ritual and before the next refresh.
The script produces and commits the qualifying receipt chain and prints the
manual activation command. It never activates H7, pushes Git, synchronizes a
checkout, or appends ledger or earnings rows.

The D−1 package must be for the last completed XNYS session strictly before
today: both `reports/schwab_chains/<session>/manifest.json` and `preclose.json`
must exist before any output. The chain cache itself is flat at
`.cache/schwab_chains/`. For example, 2026-09-08 requires the 2026-09-04
package. The 2026-09-07 holiday package remains unchanged and inert for H7:
`evaluation_session()` never selects it. The capture calendar refusal prevents
new holiday packages before authentication.

The script resolves its checkout from its own path. An explicitly approved
alternate checkout requires `--allow-checkout <exact-path>`. Preconditions are
`main`, a bounded fetch, alignment with `origin/main` or the capture wrapper's
unchanged evidence-only-ahead rule, the full Git status including untracked
files, the D−1 package, a usable token, Restic configuration, and a readable
feasibility receipt if one exists. Reuse compares both `source_hash` and
`config_hash`; a different `code_sha` alone does not trigger regeneration.

Set `RESTIC_REPOSITORY` and either `RESTIC_PASSWORD_FILE` or
`RESTIC_PASSWORD_COMMAND` in the environment or `.env`. Only those Restic
values are imported as inert strings. Other `.env` lines are never sourced or
printed. Restic itself may execute its configured password command.

A dirty tree normally refuses. The explicit `--stage-routine-evidence` flag
permits a prerequisite `data(ritual)` commit of only the intersection of the
ritual's `DATA_TIER_PATHS` and the capture wrappers' `EVIDENCE_ALLOW`.
`reports/pick_tracker`, `reports/closes_receipts`, code, and any other dirty
path outside that intersection still refuse, including pre-staged changes.
The final evidence commit contains the source receipt, Schwab artifact and
receipt, backup and restore receipts, new feasibility receipt if needed, and
the index at `reports/h7_forward_schwab/<date>-activation-day-receipts.json`.
The index is written before the commit. Success leaves `git status --porcelain`
empty. A requested routine-prerequisite commit is separate from that final
commit.

Source-health CLI exit status is ignored; every included name must be
explicitly healthy in its receipt. An unhealthy included name stops before
the data gate and prints `tools/h7_refresh_earnings.py --help`. Its immutable
receipt stays uncommitted by default; invoke with `--commit-partial` only when
the owner wants partial evidence committed. Review any failed run's remaining
dirty evidence before retrying. Immutable conflicts are not overwritten.

The new producer writes under `reports/h7_data_gate_schwab/<scope>/`. D-5's
default is exit 0 for included-cohort GO, while printing the whole-universe
verdict too. Exit 1 is included NO_GO; exit 2 refuses invalid invocation,
package, source link, or conflicting output before publication. Mode A quote
age remains non-blocking. Mode B over-threshold evidence exits 3 with an
unchanged receipt, and the runbook prints the warning and continues: that
arming obligation is not a registration input. Quote-age-only invalid evidence
is printed with its reason; it is not labelled an over-threshold exit 3 and
does not add a registration gate.

Backup runs after the receipts exist, followed by a restore check for the
same completed session. Per Brief 40 Amendment A1, Schwab receipts under
`reports/h7_data_gate_schwab` are backed up but are not scanned or validated
by restore drills. Legacy `reports/h7_data_gate` receipts continue to satisfy
the required data-gate count. The unchanged restore verifier still requires
whole-universe GO for every data-gate receipt it scans; its acceptance logic
is unchanged.

The script never pushes. It prints `git -C <repo> push origin main` for owner
realignment. If left unpushed, the next morning's ritual Step 8 attempts to push
the evidence commit. Same-day capture compatibility depends on all three
matching evidence allow-lists.

Success creates `.tmp/h7_activation_day/<date>-evidence.template.json` and
prints the manual activation command with owner placeholders. Complete every
`<OWNER TYPES>` field before use. Compare the reviewed specification with the
printed `shasum -a 256` command and type its hash yourself. The activation CLI
overwrites source/data fields from validated receipt arguments, as the template
notes. Its `code_commit` is HEAD after the evidence commit: if you commit
anything before activating, recompute it with `git rev-parse HEAD`. The ignored
`.tmp/h7_activation_day/<date>_<HHMM>.log` retains the run output.

Owner item D-6 remains open: `h7_watch.py` cannot bind Schwab evidence, while
`ritual_receipt.py` and `h7_entry_preflight.py` still use the legacy data-gate
namespace. The watcher is omitted here. Its future change affects feasibility
source closure and needs a separate brief and receipt regeneration. This
procedure does not establish post-activation operational readiness.
