# H7 entry authority — two corrections

**Status:** PROPOSED, not applied. Both touch the live forward window's entry
path, so both wait on owner sign-off.
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

1. **The hash is unreproducible.** A fresh clone at the registered
   `code_commit` (`83ed268`) computes a *different* `source_hash` than the
   registration recorded, because 98% of the inputs are not in git. The
   registered `gates.source_hash = 1dcb79c8…` can never be re-derived or
   verified by anyone, including future-Carsyn. As an integrity anchor it is
   inert.
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

### What this does not fix, honestly

The registered window's `gates.source_hash` stays a v2 value and stays
unreproducible. Nothing can repair that — it is immutable and its inputs are
gone. Correction 2 stops the bleeding going forward; it does not retroactively
make the registration verifiable. That limitation should be recorded in the
ledger rather than papered over.

### Counter-argument considered

*"Binding a wide surface is conservative — more is safer."* Only if the extra
surface is reproducible. An input that no one can reconstruct does not make a
check stricter, it makes it random: it fails for reasons unrelated to the
verdict and cannot be verified when it passes. Breadth without reproducibility
is not conservatism.

---

## Owner decisions requested

1. Correction 1: apply as a registered bug fix (restores v1.4 per-name), or
   register the whole-board veto as a deliberate stricter entry rule and accept
   a zero-trade window?
2. Correction 2: bump the diagnostic source-hash contract to v3 (dot-dir
   exclusion), or leave as-is?
3. Whether either correction, both of which change how a live registered window
   behaves mid-window, needs a ledger amendment entry beyond a correction fact.
