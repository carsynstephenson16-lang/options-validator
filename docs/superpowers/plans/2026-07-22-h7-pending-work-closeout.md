# H7 Remaining Work Closeout — Plain-English Execution Plan

**Status:** PLAN ONLY. Nothing in this document opens a trade, changes an old
receipt, activates the exit system, or scores the study.

**Goal:** Finish the two items left open by the H7 window hardening work:

1. prove that the 07:10 automated run is using the merged code; and
2. build, review, and activate the paper-exit and one-time scoring paths before
   they are needed.

The morning job is alert-only today. It can show a possible entry, but it does
not create, approve, or fill one. Those three actions remain manual.

## Owner decisions recorded on 2026-07-22

- **No new software lock on the manual entry commands.** Carsyn instead commits
  not to run the commands that create, approve, or fill a paper entry until the
  exit system passes independent review and she types `PASS`.
- **Keep ThetaData active through 2027-02-26.** This covers the last possible
  late-window position through expiration, with a small calendar buffer.
- **Missing expiration-price rule:**
  1. If the normal option price is missing at expiration, calculate the paper
     result from the official expiration-day stock close and the contract's
     fixed strike prices.
  2. If that stock close is missing, allow five trading days to recover the
     official expiration-day close.
  3. Never substitute a later stock price.
  4. If the official close is still unavailable after the fifth trading day,
     record the position's maximum possible loss.

These choices must be recorded through `research.facts.append_fact`; existing
lines in `ledger/facts.log` must never be edited.

## Short dictionary

- **Receipt:** a saved proof of which data files and code were used that day.
- **Paper record:** the permanent history of simulated entries, exits, and
  results. It never sends an order to a broker.
- **Data date:** the most recent market day whose closing information is
  complete.
- **Decision date:** the day the system is making the paper decision.
- **Independent review:** a new reviewer checks the finished work without
  relying on the builder's explanation.

---

## Part 1 — Prove the next 07:10 run

**When:** after the 2026-07-23 07:10 America/New_York run finishes.

**Read only:**

- `/Users/carsynstephenson/options-validator-ops/.tmp/daily_ritual/*.log`
- `reports/h7_receipts/h7-forward-15-v1/`
- `reports/h7_data_gate/h7-forward-15-v1/receipts/`
- `ledger/h7_forward/events.jsonl`

- [ ] Open the newest morning log and confirm it came from the operations
  checkout on `main` at commit `3e79059` or a later evidence-only commit.
- [ ] Confirm the log ends with `RITUAL STATUS: OK` and has no `CRITICAL` line.
- [ ] Confirm it says `h7 entry preflight: real entry path REACHABLE`.
- [ ] Confirm the new data-gate receipt names a source-health receipt and that
  the recorded source-health hash exactly matches that receipt's own hash.
- [ ] Confirm the dashboard now shows the 2026-07-22 data date, three of seventy
  sessions elapsed, and the true entry count from the paper record.
- [ ] Confirm the automated evidence commit reached `origin/main` and the
  encrypted backup reports success. If there was nothing new to commit, record
  that exact log result rather than calling it a failure.
- [ ] Run the paper-record verifier:

  ```bash
  uv run python -m options_researcher.h7_event_ledger verify --base-dir ledger/h7_forward
  ```

  Expected: `VALID`, with no new paper entry unless Carsyn explicitly created
  one (which she has committed not to do yet).
- [ ] Append one plain fact named `H7_UNATTENDED_MAIN_PROOF` containing the log
  name, data date, commit, receipt hashes, push result, backup result, and paper
  record count.
- [ ] Mark Task 2 Step 8 complete in
  `docs/superpowers/plans/2026-07-22-h7-window-operations-hardening.md`, commit
  those documentation/evidence changes, and push them.

**If the morning run fails:** preserve the log and every receipt exactly as
written. Fix the cause, but do not delete or replace evidence. A same-morning
rerun is allowed only while the data date still points to the last completed
market day. Do not run an evening catch-up that could save an incomplete
same-day receipt; wait for the next safe morning instead.

---

## Part 2 — Freeze the agreed exit rules before building

**Files:**

- Modify:
  `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`
- Append through Python only: `ledger/facts.log`

- [ ] Add the three owner decisions above to the exit/scoring specification.
- [ ] Replace its rough January data horizon with the exact commitment through
  `2027-02-26`.
- [ ] Add the five-trading-day recovery rule. Make clear that the system is
  recovering the official expiration-day close, not using a future price.
- [ ] State plainly that no code lock will be added to the manual entry
  commands. Carsyn's no-entry commitment is the temporary control.
- [ ] Append a fact named `H7_EXIT_SCORING_OWNER_CHOICES` with the decisions
  verbatim and the date of this conversation.
- [ ] Review the specification diff for accidental changes to the already
  fixed entry, exit, cost, timing, or scoring rules.
- [ ] Commit this specification amendment by itself.

**Stop condition:** if the specification cannot express these choices without
changing a previously fixed strategy rule, stop and ask Carsyn. Do not silently
change the study.

---

## Part 3 — Build a safe paper-exit door

**Create:**

- `options_researcher/h7_exit_session.py`
- `tests/test_h7_exit_session.py`

**Modify only where required:**

- `options_researcher/h7_paper_lifecycle.py`
- `options_researcher/h7_event_ledger.py`
- `options_researcher/h7_session.py`
- `tests/test_h7_session_real_path.py`

The existing paper-exit calculations stay unchanged. This part adds a narrow
permission path that proves the paper record, receipts, and saved market files
are correct before those calculations may write an exit.

### 3A — Tests first

- [ ] Write tests proving a plain file path, a made-up permission object, the
  entry-only permission object, a damaged paper record, or a changed data file
  cannot write an exit.
- [ ] Write tests proving every exit attempt uses the exact receipt and exact
  saved market files for that data date.
- [ ] Prove all fifteen official names remain covered even though only nine are
  eligible for entries.
- [ ] Prove a market-data failure can still be recorded honestly for an open
  position. A data failure may stop a new entry, but it must not make an open
  position disappear from monitoring.
- [ ] Prove a name that later becomes banned for new entries can still be
  closed.
- [ ] Prove a position filled today is checked for an exit during the same
  data session.
- [ ] Prove positions opened by 2026-10-26 keep being managed after that date,
  while new entries after 2026-10-26 remain forbidden.
- [ ] Cover every existing fixed exit reason: profit goal, loss limit, time
  limit, earnings protection, unknown earnings information, missing price,
  and the next-day retry.

### 3B — Add the permission path

- [ ] Add a separate `RealExitSession` type. It must be created only by a
  function that verifies the permanent paper record and that day's receipts.
- [ ] Keep the existing entry-only `RealStoreSession` unable to write exits.
- [ ] Carry both the data date and decision date explicitly; never derive
  either from the computer clock after the checks begin.
- [ ] Recheck every named file before and after reading it so an in-progress
  change cannot slip through.
- [ ] Record one visible evidence line for every monitoring day, including days
  with no exit and days with missing data.
- [ ] Make repeated identical calls harmless; make different repeated calls
  fail visibly.
- [ ] Keep this paper-only. Add no broker connection, order command, or live
  trading switch.

### 3C — Add the expiration ending

- [ ] At expiration, prefer the normal saved option closing price.
- [ ] If it is missing, calculate each contract leg from the official
  expiration-day stock close and its fixed strike price.
- [ ] If the stock close is missing, record a visible pending-data state and
  retry recovery for exactly five trading days.
- [ ] Use only the recovered official expiration-day close, never a later day's
  market value.
- [ ] After the fifth trading day, record maximum possible loss if the official
  close still cannot be recovered.
- [ ] Test the profitable, worthless, partial-value, maximum-loss, missing-close,
  recovered-close, and fifth-day-fallback cases.

### 3D — Add owner-visible commands

Add three paper-only commands:

```text
python -m options_researcher.h7_exit_session status
python -m options_researcher.h7_exit_session fill
python -m options_researcher.h7_exit_session monitor
```

- [ ] `status` checks readiness and writes nothing.
- [ ] `fill` handles exits already due, including retries.
- [ ] `monitor` checks every open position for a new exit reason.
- [ ] Each command prints what it checked, what it wrote, and why it refused.
- [ ] A partial failure must never look like full success.
- [ ] Once this reviewed exit system is activated, make the existing manual
  paper-entry `fill` command immediately check that newly filled position for
  an exit using the same verified data date. This closes the same-day gap; it
  does not add the temporary entry lock Carsyn rejected.

- [ ] Run the focused tests and commit the exit door as one reviewable change.

---

## Part 4 — Put paper exits into the morning run

**Files:**

- Modify: `tools/daily_ritual.sh`
- Create: `tests/test_h7_daily_exit_order.py`

- [ ] Put the exit step immediately after the day's data result is known and
  before possible-entry messages are produced.
- [ ] Process already-due exit fills and retries first.
- [ ] Then monitor every position that was already open when the morning run
  began. A paper entry filled manually later that day receives its first check
  immediately from the reviewed entry-fill handoff in Part 3.
- [ ] Run exit monitoring even when the day's market-data result is bad; write
  the honest missing-data record and retry on the next valid day.
- [ ] If exit management fails, mark the morning run broken and do not present
  the session as ready for a new paper entry.
- [ ] Preserve Carsyn's decision: do not add a new code lock to the three manual
  entry commands. The morning runner remains unable to create an entry on its
  own.
- [ ] Keep the existing narrow evidence commit, push, and encrypted backup.
- [ ] Test the exact order by reading the script in an offline test. Also run:

  ```bash
  zsh -n tools/daily_ritual.sh
  ```

- [ ] Commit the morning-run wiring separately from the exit-door code.

---

## Part 5 — Build the one-time score without changing its math

**Create:**

- `options_researcher/h7_real_scoring.py`
- `tests/test_h7_real_scoring.py`

**Modify only where required:**

- `options_researcher/h7_event_ledger.py`
- `options_researcher/h7_window_status.py`
- `options_researcher/dashboard.py`
- `tests/test_h7_window_status.py`
- `tests/test_dashboard.py`

- [ ] Leave `options_researcher/h7_forward_scoring.py` unchanged. It contains
  the fixed scoring calculation registered at the window's start.
- [ ] Add a read-only preview that clearly says `NOT FINAL` and writes nothing.
- [ ] Add a final command that cannot run until:
  - the October 26 decision window is finished;
  - every planned entry is settled;
  - every opened position is closed;
  - the paper record and fixed study settings still verify;
  - no earlier final score exists; and
  - the finished build has passed independent review and Carsyn has typed
    `PASS`.
- [ ] Save one unchangeable score receipt under
  `reports/h7_forward_scoring/h7-forward-15-v1/`.
- [ ] Add one permanent `window_score` line to the paper record that points to
  that receipt.
- [ ] If the receipt was saved but the permanent line was interrupted, permit
  recovery only when every saved byte and the paper-record ending still match.
- [ ] Make every second or different final score fail visibly.
- [ ] Show on the dashboard whether scoring is `NOT READY`, `READY`, or
  `FINAL`, without showing an early final result.
- [ ] State with the final result that this is a paper study, not permission to
  trade real money and not proof that the strategy works.
- [ ] Commit the scoring path separately.

The scoring software must be built and reviewed before 2026-10-26. The actual
score may occur later because a position opened near the end of the window must
be allowed to finish first.

---

## Part 6 — Prove data coverage through the last exit

- [ ] Append Carsyn's commitment to keep ThetaData active through
  `2027-02-26` using `research.facts.append_fact` as described in Part 2.
- [ ] Keep the morning top-up and receipt checks running every market day after
  October 26 until every position is closed.
- [ ] Add the promised-through date and latest successful data date to the H7
  status output and dashboard.
- [ ] Show a visible warning if the latest successful data date falls behind.
- [ ] Do not claim future data has been received. The February date is an owner
  commitment; each daily receipt proves only the data actually received.
- [ ] On or after the final close, verify that every market day needed by every
  open position has either valid evidence or a visible missing-data/retry line.

---

## Part 7 — Independent review and owner activation

After Parts 2–6 are built, use a fresh reviewer who did not implement them.

- [ ] Give the reviewer the specification, this plan, the full change list,
  test output, and a copy of the paper record verification result.
- [ ] Require the reviewer to try forged permissions, changed files, missing
  prices, duplicate calls, after-window positions, expiration recovery, and a
  second final score.
- [ ] Treat every finding that could lose, hide, duplicate, or invent a paper
  result as a blocker.
- [ ] Fix every blocker and repeat the review from a clean starting point.
- [ ] Run the complete checks:

  ```bash
  uv run python -m unittest discover -s tests
  uv run ruff check .
  uv run pyright
  zsh -n tools/daily_ritual.sh
  uv run python -m options_researcher.h7_event_ledger verify --base-dir ledger/h7_forward
  ```

- [ ] Present the plain-language review result to Carsyn.
- [ ] Carsyn types `PASS` or `FAIL`. Only `PASS` permits the paper-exit commands
  and morning-run exit step to be treated as ready.
- [ ] Append the exact owner verdict through `research.facts.append_fact`, then
  merge to `main`, push, and update the operations checkout.
- [ ] Run one supervised morning cycle with no open position, then an offline
  copy of the paper record containing a test position. Confirm due fills happen
  before monitoring and that no broker action is possible.

---

## Completion definition

This plan is complete only when all of the following are true:

- the 2026-07-23 automated-run proof is recorded;
- the owner choices are saved in the append-only facts log;
- the exit path is built, independently reviewed, owner-approved, merged, and
  running each morning;
- ThetaData remains available through every needed exit day, with the owner
  commitment extending through 2027-02-26;
- the one-time scoring path is built and reviewed before 2026-10-26;
- every opened paper position eventually closes under the fixed rules; and
- exactly one final score is saved after the window and all positions finish.

Nothing in this plan authorizes live trading, broker orders, changing the
strategy after seeing results, rewriting old evidence, or scoring twice.
