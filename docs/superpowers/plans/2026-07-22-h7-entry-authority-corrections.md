# H7 entry authority — two corrections

**Status:** APPLIED 2026-07-22 at owner direction. Both corrections touch the
live forward window's entry path; the implementation and verification are
recorded below.
**Date:** 2026-07-22
**Context:** [2026-07-22 preflight work](../../../2026-07-22.md), commit `f56dff6`.

The live H7 forward window (registered 2026-07-20, seq-0 `a1ea228c`) currently
cannot take an entry on any day, for two independent reasons. Neither is about
the hypothesis. Both were found by running the new read-only
`options_researcher.h7_entry_preflight` against real receipts.

---

## Correction 1 — the whole-board health veto contradicts registered amendment v1.4

### What the code does

`h7_session.open_real_session` ([h7_session.py:115-118](../../../options_researcher/h7_session.py#L115))
computes `names = watch_universe()` — all **15** scope names — and refuses the
entire session if any one of them is not source-healthy:

```
unhealthy = sorted(name for name in names if symbols[name].get("healthy") is not True)
if unhealthy:
    raise SessionRefused(f"source-health receipt has unhealthy official names: {unhealthy}")
```

`record_session_evidence` repeats the same whole-board check
([h7_session.py:191-194](../../../options_researcher/h7_session.py#L191)).

Probe (fixture with a linked, fresh, GO receipt chain; all 9 cohort names
healthy and CLEAR; only the 6 registered-excluded names unhealthy):

```
ok:          False
refusal:     source-health receipt has unhealthy official names:
             ['AVGO', 'CRWV', 'IREN', 'NVDA', 'SMCI', 'USAR']
entry_ready: ()
```

### What is actually registered

**Amendment v1.4** (`ledger/facts.log:11998`, owner decision 2026-07-14), verbatim:

> a source-unhealthy name is entry-banned **per-name** by the registered
> fail-closed gate (unknown next report -> EARNINGS-UNKNOWN, no entry;
> test-verified via Stage 7 synthetic proof b632feb) and is reported with the
> run, **no longer blocking the whole board**. Data-gate NO_GO still blocks the run.

The window's own immutable registration manifest (seq-0 payload) records:

```
included:  [AMD, AMZN, CEG, ET, MSFT, NOW, PLTR, TEM, VST]      # 9
excluded:  [AVGO, CRWV, IREN, NVDA, SMCI, USAR]  reason: EARNINGS-UNKNOWN
trim_rule: source_health_ready_at_pinned_session
```

So the six names blocking every entry are the six the registration already
recorded as excluded, for precisely the reason being used to block. The
registered rule is per-name. The code implements a whole-board veto that no
amendment registers.

The alert layer already does this correctly:
[h7_watch.py:233](../../../options_researcher/h7_watch.py#L233) is
`banned = gate != GATE_CLEAR` — strictly per-symbol, no board-level health
veto. Only the entry door disagrees.

### Why this is a bug fix, not an amendment

I called this "loosening a registered gate" on 2026-07-21. That was wrong, and
the evidence above is why. The registered gate *is* per-name (v1.4). The
whole-board veto entered with the Stage-8 entry door on 2026-07-20
(`7a12b6a`), unregistered. Correcting it **restores** the registered rule
rather than relaxing it. It should still be recorded in the ledger as a
correction, but it does not need a new owner-typed parameter.

### Counter-arguments considered

1. *"The activation spec says one unhealthy name blocks the board."* It does —
   at §3.2, scoped to `activation_preconditions()`, the checks run **once at
   activation**. §3a (Option C, `--trim-unhealthy`) is the documented opt-in
   that overrides it for window composition, and it was used. Applying an
   activation-time precondition to every daily decision is a category error:
   the trim already happened and is immutable.
2. *"Whole-board health is the anti-cherry-pick protection."* It is not.
   `_source_symbol_map` ([h7_session.py:67-73](../../../options_researcher/h7_session.py#L67))
   independently refuses any receipt whose symbol set is not the full 15-name
   scope. Whole-universe *evidence coverage* survives this correction
   untouched; only the all-must-be-healthy verdict changes.
3. *"Maybe real entry should be stricter than the alert layer."* Defensible in
   principle, but then it needs registering as an amendment with a stated
   reason — and it would mean the window can never trade, which the owner did
   not choose when opting into Option C.

### Proposed change

In both `open_real_session` and `record_session_evidence`, evaluate health over
`cohort.included` (the 9 registered names) instead of `watch_universe()` (15).
Unchanged: full-scope receipt coverage; the per-symbol
`gate == "CLEAR" and healthy is True` check for the target symbol; data-gate
GO; the decision-window bounds; every frozen strategy number.

### Risk if applied

A name inside the cohort that later goes unhealthy is still entry-banned
per-name, so no unhealthy name can trade. The residual risk is the intended
Option C risk the owner already accepted at activation: the window scores on 9
names, not 15.

### Risk if NOT applied

H7 runs to its ~2026-10-26 scoring date with zero trades, and a zero-trade
window reads as INCONCLUSIVE / "no edge" for a reason that has nothing to do
with the hypothesis. This is the expensive failure mode: it looks like a
result.

---

## Correction 2 — `diagnostic_source_hash` is 98% gitignored virtualenv

### Measured, not asserted

`DIAGNOSTIC_SOURCE_PATHS_V2` ([hashing.py:121](../../../research/hashing.py#L121))
is `SOURCE_HASH_PATHS + ("options_researcher", "tools")`, and the walker
recurses every `*.py` under those directories, excluding only `__pycache__`.
Measured against the current tree:

| | files |
|---|---|
| total bound into every H7 receipt | **7,658** |
| `tools/financepy_validation/.venv` | 4,570 |
| `tools/bs_parity/.venv` | 2,953 |
| `tools/repo_rag` | 27 |
| `options_researcher` | 57 |
| everything else (config, research, strategies, data, harness, analysis, …) | 51 |
| **not tracked by git** | **7,526 (98%)** |

`git check-ignore` confirms both `.venv` directories match `.gitignore:5`. They
are scratch virtualenvs created 2026-07-18, two days before the window opened.

### Three consequences

1. ~~**The hash is unreproducible.** A fresh clone at the registered
   `code_commit` (`83ed268`) computes a *different* `source_hash` than the
   registration recorded, because 98% of the inputs are not in git. The
   registered `gates.source_hash = 1dcb79c8…` can never be re-derived or
   verified by anyone, including future-Carsyn. As an integrity anchor it is
   inert.~~ **RETRACTED 2026-07-22 — this was wrong; see "Correction to
   consequence 1" below. It is reproducible, and it re-derives exactly.**
2. **Receipts expire on unrelated activity.** `pip install` into either venv,
   or deleting them (they are scratch), silently invalidates every outstanding
   receipt — `data-gate receipt source identity is stale`, which is exactly the
   refusal the 07-17 receipt now gives. The three `repo-rag` commits on this
   branch (`85909ac`, `d7d2b29`, `9a25ab0`) would each have done the same, via
   an offline RAG tool that cannot touch an H7 entry decision.
3. **It punishes the right behavior.** Fixing a bug mid-window kills that
   session's entry authority, and since receipts are immutable the day cannot
   be re-issued. Today's own preflight work did this to the 07-17 receipt.

### Proposed change (versioned, per the existing contract)

`hashing.py:114-122` already anticipates this: the contract is explicitly
versioned "so the contract is versioned, never retro-changed." So:

- Add `DIAGNOSTIC_SOURCE_HASH_VERSION = 3`, leaving v2 byte-identical so every
  historical record keeps verifying.
- v3 walker skips any path with a dot-prefixed component (`.venv`, `.tmp`,
  `.cache`), mirroring the existing `__pycache__` exclusion.

Measured result: **7,658 → 133 files**, and every one of them is git-tracked
(the single exception, `options_researcher/market_context.py`, is an uncommitted
work-in-progress from another session). The hash becomes reproducible from a
clean checkout, which is the property it was supposed to have.

Optional and *not* proposed here: narrowing the paths further to only modules
that can affect an H7 verdict. That is a bigger judgement call and 133 files is
already tractable.

### ~~What this does not fix, honestly~~ (RETRACTED — see below)

~~The registered window's `gates.source_hash` stays a v2 value and stays
unreproducible. Nothing can repair that — it is immutable and its inputs are
gone. Correction 2 stops the bleeding going forward; it does not retroactively
make the registration verifiable. That limitation should be recorded in the
ledger rather than papered over.~~

### Correction to consequence 1 (measured 2026-07-22, after the corrections landed)

The claim above was inferred from the *local working tree* and never tested
against a clean checkout. Tested, it is false. The registered
`gates.source_hash` re-derives **exactly**:

```
git archive 83ed2683345aee578be155d145c76d2fa56c25a6 | tar -x -C <tmp>
diagnostic_source_hash(root=<tmp>, version=2) ->
diagnostic_source_hash(root=<tmp>, version=3) ->
    1dcb79c81dfff91c9829036ad8cd486f6c8207d535e044da97649e535f628d28
```

which is the value in `ledger/h7_forward/events.jsonl` seq-0
`payload.gates.source_hash`. Re-derived twice by two independent routes (a
detached `git worktree` and a `git archive` extraction into a bare temp dir),
104 files, no `.git` required by the second route.

Why the inference failed: a clean checkout of `83ed268` contains **no**
dot-prefixed directories under the scanned paths, so v2 and v3 walk the same
104 files and produce the same digest. The 7,658-file surface is a property of
*this* working tree, not of the registered commit — the two scratch `.venv`
directories are untracked, so they never existed in whatever checkout produced
the activation receipts (`83ed268` is itself "regenerate activation receipts at
current source identity").

So consequence 1 was wrong; consequences 2 and 3 stand unchanged, and they are
what Correction 2 actually fixes — the *live* tree's hash does drift on
unrelated activity (live v2 = `3b728227…`, live v3 = `ea497f35…`), which is why
receipts kept going stale. The registration itself was never at risk.

`tests/test_source_hash_reproducibility.py` now pins both properties: (a) the
active contract binds zero gitignored files — measured 0 of 133 under v3 versus
7,525 of 7,658 under v2, so the test is not vacuous; (b) the live window's
registered `gates.source_hash` re-derives from a clean checkout of its own
`code_commit`. Both skip rather than fail when the git object is absent (shallow
CI clone).

### Counter-argument considered

*"Binding a wide surface is conservative — more is safer."* Only if the extra
surface is reproducible. An input that no one can reconstruct does not make a
check stricter, it makes it random: it fails for reasons unrelated to the
verdict and cannot be verified when it passes. Breadth without reproducibility
is not conservatism.

---

## Applied decisions

1. Correction 1 was applied as a registered bug fix, restoring v1.4's
   per-name source-health rule. No new owner-typed strategy parameter was
   added.
2. Correction 2 was applied by activating source-hash contract v3. The v2
   path set and walker remain available for historical compatibility; v3
   excludes dot-prefixed scratch/cache components.
3. The correction is recorded in `ledger/facts.log`. The immutable 2026-07-20
   registration and its v2 source hash were not rewritten; future receipts use
   v3.
4. **2026-07-22, later the same day:** the "v2 reproducibility limitation"
   recorded in items 1–3 was tested and retracted — the registered
   `gates.source_hash` re-derives exactly from a clean checkout of the
   registered `code_commit`. See "Correction to consequence 1" above. Both
   properties are now regression-tested, and the retraction is appended to
   `ledger/facts.log` rather than editing the earlier entry.
