# Brief 11 (rev-2) — Ritual switch-on: honest data-phase restart

**Date:** 2026-08-14
**Status:** DRAFT SPEC — requires its own independent adversarial review before
implementation, and the OWNER DECISIONS in §12 before merge.
**Author:** Opus design agent, commissioned by the orchestrating session with
`reports/2026-08-14-brief-10-adversarial-review-receipt.md` as its charter.
**Executor:** Codex (Sol, high) or an Opus implementation agent.
**Code truth for every measurement below:** `~/options-validator-ops` at
`origin/main` = `58b1fd9`, measured 2026-08-14.

---

## 1. What this document supersedes

1. **Brief 10** (`2026-08-14-10-switch-on-decoupling-and-ten-am-chain-session-codex-brief.md`)
   is WITHDRAWN as an implementation instruction (FAIL receipt, 8 blockers).
   This spec replaces it. Brief 10's Task C (10:00 ET chain capture) is
   **entirely out of scope here** and is deferred to its own future spec; that
   split is what disposes of blockers B1, B2, B3 and B8's capture-tag half.
2. **Runbook 08** (`2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`),
   "Deliberately NOT in this runbook", final bullet:

   > "Any change to `data/ritual_authority.py` — that flip is the owner's, last,
   > after registration."

   **This line is superseded, owner-directed 2026-08-14** (owner wording in
   session: "I want to switch it back on"). The supersession is *partial and
   named*: the owner has directed that the **non-verdict-bearing data/display
   phase** may be switched on before registration. `h7_active` remains
   registration-day-only and is untouched by this spec. Recording this
   supersession explicitly is caution C2's disposition; runbook 08 must be
   edited in the same landing to point at this document.

---

## 2. Ground truth measured 2026-08-14 (ops @ `58b1fd9`)

Every design choice below rests on these measurements, not on recollection.

| Fact | Evidence |
| --- | --- |
| Canonical chain cache edge is **2026-07-27** | newest dated file in `.cache/chains` |
| ops `.cache` is a **symlink** to the main checkout's `.cache` | `ls -ld ~/options-validator-ops/.cache` |
| `.cache/schwab_chains` **does not exist** in ops or the main checkout | `ls` — no such directory |
| `reports/schwab_chains` **does not exist** in ops or the main checkout | `ls` — no such directory; **no canary bytes exist yet** |
| Last ritual artifacts are from **2026-07-27**; last ritual log `2026-07-28_0710.log` | `reports/ritual/run_status_2026-07-27.json`, `.tmp/daily_ritual/` |
| `data/ritual_authority.py` was created **2026-08-02** (`db3f907`), not 07-28 | `git log --diff-filter=A` — corrects caution C9 |
| `.cache/underlying` last written **2026-08-05** | `ls -lt .cache/underlying` |
| The research worktree is already fast-forwarded to `58b1fd9` on `deploy/research` | `git -C ~/options-validator-research log -1` |

**Chain-consumer map** (which ritual step reads which chain directory):

| Consumer | Chain source | Parameterizable? |
| --- | --- | --- |
| `options_researcher/entry_watch.py:191` (H5) | `.cache/chains` | **No** — hardcoded |
| `options_researcher/h7_watch.py:216` | `.cache/chains` | **No** — hardcoded |
| `options_researcher/h6_features.py:40` | `.cache/chains` | default arg |
| `options_researcher/h6_watch.py:951,1306` | `.cache/chains` | `--chain-dir` |
| `options_researcher/h8_watch.py:794,891` | `.cache/chains` | `--chain-dir` |
| `options_researcher/features.py` → `chains.load_range` → `data/pandas_feed.load_cached_chains` → `thetadata_adapter._cache_path` | `.cache/chains` | **No** |
| `options_researcher/h10_watch.py:111` → same `load_range` path | `.cache/chains` | **No** |
| `options_researcher/h7_source_health.py` | **no chains at all** — earnings assertions only | n/a |

**Schwab gate reachability:** `options_researcher/h7_schwab_data_gate.evaluate`
has **no CLI**. Its only non-test caller is
`options_researcher/h7_schwab_window_registration.py`.
`h7_data_gate.main()` calls `evaluate()` — the ThetaData full-audit validator —
with `DEFAULT_CHAIN_DIR = Path(".cache/chains")` (`h7_data_gate.py:70`). There
is a `--chain-dir` flag but **no evidence-mode flag**, so pointing the existing
CLI at Schwab bytes would run the ThetaData v2 audit-receipt validator against
parquet that carries no such receipt: guaranteed NO_GO, not a wiring win.

**Source-hash blast radius (generalization of blocker B8):**
`research/hashing.py:132-134` — `diagnostic_source_hash` v3 hashes `*.py` under
`data/`, `options_researcher/`, `tools/`, `research/`, plus `config.py`.
Therefore:

* editing `data/ritual_authority.py` or `options_researcher/ritual_receipt.py`
  **changes `diagnostic_source_hash()`**;
* editing `tools/daily_ritual.sh` **does not** (only `*.py` is globbed);
* `config_hash()` hashes every uppercase name in `config.py` — **this spec adds
  no constant to `config.py`**, so `config_hash()` is unchanged. That is the
  positive disposition of B8's second half, and it is an acceptance test (§10,
  `test_config_hash_surface_unchanged`).

Consequence, and a **hard sequencing constraint**: because
`diagnostic_source_hash` is a refusal binding in `h7_exit_session`,
`h7_schwab_window_registration`, `intraday_capture` and `intraday_preview`, the
Python half of this change set **must land outside the trading session** (before
the day's first receipt or after the day's last), never between two receipts of
the same session. See §11.

---

## 3. Design goal and what "on" honestly means

The owner directed: restore the daily ritual's data phase, research refresh, and
dashboard freshness — **without `h7_active=True` and without dishonest
receipts.**

The measurements above force an unpleasant but honest reading:

> With `.cache/chains` frozen at 2026-07-27 and OD-2/OD-4 forbidding a refill,
> **no chain-dependent lane can produce fresh evidence today.** "Switching on"
> cannot mean "H5/H6/H8/H10 start producing signals again." It can only mean
> **the ritual runs again, refreshes what is genuinely refreshable, rebuilds the
> display layer, and records precisely and daily which lane is starved and why.**

Brief 10 promised "dashboards go fresh same day" and "research refresh resumes."
Both were false (blocker B5). This spec deletes those promises and replaces them
with what is actually deliverable:

**Deliverable of switch-on (rev-2):**
1. The daily ritual stops being dead: it runs, logs, and notifies every weekday.
2. Underlying OHLCV refreshes to the current session (its source is *not* the
   frozen chain cache).
3. The attractiveness feature store and both dashboards rebuild daily, carrying
   their existing honest as-of / staleness banners.
4. A daily, machine-readable record of exactly which hypothesis lane is starved,
   with the cache edge named in the log and the notification.
5. Research refresh remains **honestly blocked** and resumes *automatically*, with
   no further code change, on the first day its inputs exist.

Anything more requires either fresh chains or an owner decision (§12).

---

## 4. Blocker B5 — the honest data path: TWO OPTIONS, ONE RECOMMENDATION

### Option A — wire ritual consumers to Schwab evidence (`.cache/schwab_chains`)

What it would take, measured:

* Build a CLI/evidence-mode seam for `h7_schwab_data_gate` (none exists).
* Parameterize `chains.load_range` / `pandas_feed.load_cached_chains` /
  `thetadata_adapter._cache_path` — the shared, non-parameterized loader behind
  `features.build_all` and `h10_watch`.
* Un-hardcode `.cache/chains` in `entry_watch.py:191` and `h7_watch.py:216`.
* Build a schema/audit-receipt bridge: every consumer validates a ThetaData v2
  audit receipt that Schwab parquet does not carry
  (`h7_data_gate.validate_v2_audit_receipt`).

Why this spec **rejects Option A for now**:

1. **There are no bytes.** `.cache/schwab_chains` and `reports/schwab_chains` do
   not exist in either checkout. The first canary has not run. Option A would be
   written and "verified" entirely against fixtures — the exact conditions that
   produced the 2026-08-14 FAIL.
2. **It is an unregistered input substitution, not plumbing.** The Schwab package
   is a **15:45 pre-close snapshot for the H7 watch universe**, byte-bound as H7
   evidence (`h7_schwab_data_gate.EVIDENCE_MODE = "REAL-H7-SCHWAB-PRECLOSE-AUDIT"`).
   H5's registered trigger, H6/H8's feature manifests and H10's registered design
   were all pre-registered against **EOD** ThetaData chains. Silently re-pointing
   them at pre-close Schwab data changes the registered input of four live
   hypotheses. That is a registration amendment with its own review — never a
   side effect of "switch the ritual on."
3. **Timing semantics differ and would be invisible.** 15:45 pre-close ≠ EOD.
   Feeding it into consumers that label their output "chain as of `<date>`" makes
   the label a lie unless every consumer grows explicit as-of-time semantics —
   a much larger change than the one the owner asked for.
4. **It is not on the critical path to the thing the owner wants.** The owner
   asked for the ritual to run again. Option B delivers that today.

### Option B — re-scope the data phase to the frozen cache, with explicit starvation labeling *(RECOMMENDED)*

The ritual runs. Every chain-dependent lane stays **off** under the new data
tier, and the ritual's own artifacts state, every day, that the canonical chain
cache edge is 2026-07-27 and therefore lane X has no exact-session input. No
receipt claims evidence that does not exist; no registered hypothesis's input is
substituted; no `.cache/chains` write occurs (OD-2/OD-4 intact).

**Code deltas for Option B** — the complete list, nothing else changes:

| # | File | Change | Hashed? |
| --- | --- | --- | --- |
| D1 | `data/ritual_authority.py` | add `ritual_data_phase_active` flag (default `False`); add `evaluate_data_phase()`; make `evaluate_full_ritual()` require all three flags; CLI gains `require-data`, and `status` reports both tiers and all three flags | **yes** (`data/`) |
| D2 | `tools/daily_ritual.sh` | top gate becomes `require-data`; a second, inner `require-full` gate fences every H7 surface and the whole GATE_GO block; tier-scoped durability allow-list + commit message; cache-edge note; push-failure escalation; `[DATA-STARVED]` notification label | no (`.sh`) |
| D3 | `tests/test_ritual_authority.py` | rewritten for three flags / three modes | n/a |
| D4 | `tests/test_daily_ritual_provenance.py` | rewritten per §8 invariants, including the **closure** test | n/a |
| D5 | `tools/schwab_chain_capture.sh` | *(owner decision D-3 only)* evidence-only-divergence tolerance in the alignment gate | no (`.sh`) |
| D6 | `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`, `docs/h7-forward-operations.md` | record the §1 supersession and the §9 fast-forward rule | no |

**Not changed by Option B:** `config.py` (zero lines), `options_researcher/*.py`
(zero files), `h7_data_gate.py`, `h7_schwab_data_gate.py`, `ritual_receipt.py`,
`attractiveness_research_v2.py`, any ledger, any registered number.

> Note this is *narrower* than brief 10 and narrower than the reviewer's own
> framing: D1 is the only hashed Python file in the whole change set.

---

## 5. Task 1 — three-flag ritual authority (`data/ritual_authority.py`)

Brief 10 proposed flipping `exact_session_source_active=True` to unlock the data
phase. **That is a category error and the root of blocker B5:** under Option B
the data phase consumes no exact-session source at all, so gating it on a flag
that asserts "an approved ongoing exact-session options source is active" would
make the switch-on itself the dishonest act.

Three flags, each naming one authorization the owner actually holds:

```
ritual_data_phase_active      # NEW. "The owner authorizes the daily
                              #  non-verdict-bearing data/display phase to run
                              #  from cached data." Asserts NOTHING about a
                              #  live source and NOTHING about H7.
exact_session_source_active   # UNCHANGED MEANING. "An approved ONGOING
                              #  exact-session options source is active."
                              #  Stays False. Its flip bar is §7.
h7_active                     # UNCHANGED. Registration day only.
```

Required implementation:

* `RitualAuthority` gains `ritual_data_phase_active: bool`. `CURRENT_AUTHORITY`
  sets it `False` in the same commit that adds it; the flip to `True` is a
  separate, single-line commit (§6).
* `evaluate_data_phase(authority=CURRENT_AUTHORITY) -> RitualReadiness` —
  blocks iff `not ritual_data_phase_active`, with blocker text
  `"Ritual data phase is not authorized."`
* `evaluate_full_ritual()` — **monotone**: requires all three. Its existing
  blocker strings for the source and H7 flags are preserved **verbatim**
  (`tests/test_ritual_authority.py` asserts on the substrings `"exact-session"`,
  `"H7"`, `"ThetaData"`; downstream operators read these lines). It gains the
  data-phase blocker when that flag is false.
* CLI `mode` choices become `("status", "require-data", "require-full")`.
  `status` exits 0 always and prints a single JSON object containing **both**
  tiers and all three flag values; `require-data` exits 0 iff
  `evaluate_data_phase().ready`; `require-full` exits 0 iff
  `evaluate_full_ritual().ready`. Every mode remains read-only and side-effect
  free.
* **No `require-source` mode is added.** With Option B, nothing consumes an
  exact-session source, so a `require-source` tier would be a mode with no
  caller. It is specified here as future work (§7) so the tier's meaning is
  fixed *before* anyone is under pressure to invent it.

**Consequence to record (caution C1 neighbour):** adding a field to
`RitualAuthority` **invalidates**
`reports/h7_forward_schwab/2026-08-09-authority-flip.PREPARED.patch` — the patch
diffs a two-field constructor and will no longer apply. The implementation MUST,
in the same landing, either regenerate that patch against the new file or add a
one-line `STALE — regenerate` marker beside it. A registration-day operator
finding a patch that silently fails to apply is a foreseeable, preventable
incident.

---

## 6. Task 2 — `tools/daily_ritual.sh` restructure

### 6.1 Surface classification (blocker B4's enumeration; corrects caution C3)

Brief 10's "data phase (closes refresh, source health, quotes, dashboard inputs,
research-refresh preflight receipt)" does not match the script. There is **no
closes step and no quotes step**, and **source health is an H7 receipt writer**.
The real inventory, in script order:

| # | Step (line) | Writes | Reads chains? | Tier |
| --- | --- | --- | --- | --- |
| 1 | branch + `origin/main` alignment guard (72-85) | nothing | no | pre-gate |
| 2 | `ritual_status --status RUNNING` (107) | `reports/ritual/run_status_*.json` | no | **data** |
| 3 | `h7_source_health` (115) | `reports/h7_receipts/<scope>/source_health/*.json` | **no** (earnings only) | **full** — H7-scoped receipt |
| 4 | `h7_data_gate` (140) | `reports/h7_data_gate/<scope>/receipts/*.json` + artifact | yes (`.cache/chains`) | **full** |
| 5 | `h7_exit_session fill` / `monitor` (191, 202) | **appends `ledger/h7_forward` via `ledger.append_event`** | yes | **full** |
| 6 | `qm_dashboard --refresh-ohlcv` (235) | `.cache/underlying_ohlcv` (network fetch, `data/underlying_ohlcv.py:193`) | no | **data** |
| 7 | `features.build_all` ×2 (249, 252) | attractiveness feature store | yes (stale-tolerant) | **data** |
| 8 | `h7_watch` (263) | `reports/h7_receipts/<scope>/watcher/*.json` | yes | **full** |
| 9 | `h7_entry_preflight` (279) | `reports/h7_receipts/<scope>/preflight/*.txt` | yes | **full** |
| 10 | `h6_features` / `h6_watch` (293-295) | feature store, `reports/h6_forward/*.json` — **never writes the book** (`h6_watch.py:5`) | yes | GATE_GO — see D-1 |
| 11 | `entry_watch` (312) | `reports/h5/entry_watch_*.txt` — **never writes positions** (`entry_watch.py:6`); **can print FIRE** | yes | GATE_GO — see D-1 |
| 12 | `h8_watch` (325) | `reports/h8_forward/*.json` — never writes the book (`h8_watch.py:5`) | yes | GATE_GO — see D-1 |
| 13 | `h10_watch` (335) | `reports/h10/receipts/*.json` | yes | GATE_GO — see D-1 |
| 14 | `h10_observe` (336) | **appends `reports/h10/observations.jsonl`** — a registered hypothesis's append-only observation record | (via 13) | GATE_GO — see D-1 |
| 15 | `dashboard`, `attractiveness_dashboard` (344-345) | `.tmp/dashboard/…` | no | **data** |
| 16 | `ritual_receipt` (350) | `reports/ritual/capture_receipt_*.json` | no | **data** |
| 17 | `ritual_status` terminal (368) | `reports/ritual/run_status_*.json` | no | **data** |
| 18 | `git add/commit/push` (385-408) | Git history on `main` | no | **data** (tier-scoped allow-list, §6.4) |
| 19 | `restic backup` (417) | restic repository | no | **data** |

Steps 10-14 are the fence question. **They are not decided here** — see owner
decision D-1 (§12). The recommendation is F1: leave them off.

### 6.2 Gate placement

```
RITUAL_MODE=status  →  ritual_authority status  (unchanged, exec's, read-only)
        ↓
require-data   ← the ONLY top gate; before mkdir, before the log redirect,
                 before ANY mutation surface in the table above
        ↓
[data-tier body: steps 2, 6, 7, 15, 16, 17, 18, 19]
        ↓
require-full   ← inner gate; guards steps 3, 4, 5, 8, 9 and (per D-1) 10-14
```

Concretely, replace lines 44-52 with the `require-data` gate (identical
structure, identical fail-closed comment, message
`RITUAL STATUS: BLOCKED BY TRACKED AUTHORITY (data phase)`), and wrap the entire
region from step 3 through the end of the `GATE_GO` block in:

```zsh
env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority require-full
FULL_AUTHORITY_RC=$?
if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then
  ...steps 3,4,5,8,9 (+10-14 per D-1)...
else
  note "H7 lanes: PAUSED — full ritual authority not granted (h7_active / exact-session source)"
  note "H5/H6/H8/H10 lanes: PAUSED — gated behind the H7 data gate; see brief 11 §6.1"
fi
```

**Requirement:** when `require-full` refuses, the H7/GATE_GO region must be
`note`d, **never `crit`ed**. Today's `crit "h7 exit management: receipt/…
unavailable"` (line 183) would fire every single day under the data tier and
train the operator to ignore CRITICAL lines. A deliberately paused lane is not a
failure.

### 6.3 Cache-edge honesty note (shell-only; no hash churn)

Immediately after `AS_OF` resolves, compute and log the canonical cache edge:

```zsh
CHAIN_EDGE="$(ls .cache/chains 2>/dev/null | sed -n 's/.*_\([0-9-]\{10\}\)\.parquet$/\1/p' | sort -u | tail -1)"
note "canonical chain cache edge: ${CHAIN_EDGE:-none} (evaluation session ${AS_OF})"
if [ -n "$CHAIN_EDGE" ] && [ "$CHAIN_EDGE" \< "$AS_OF" ]; then
  DATA_STARVED=1
  note "chain-dependent lanes are STARVED: no exact-session chain for ${AS_OF} (cache frozen at ${CHAIN_EDGE}; OD-2/OD-4 forbid refill)"
fi
```

This is deliberately implemented in the shell and **not** in
`options_researcher/ritual_receipt.py`: putting it in Python would change
`diagnostic_source_hash` for a purely explanatory string. The machine-readable
capture receipt keeps its exact current semantics and status vocabulary
(`CAPTURED` / `NO_SIGNAL` / `REFUSED` / `MISSING`). **No new capture status is
introduced.**

### 6.4 Terminal status, notification, and durability under the data tier

* **On-disk status and exit code are unchanged.** With every hypothesis lane
  starved, `ritual_receipt` exits nonzero → `CRITICAL=1` → terminal status
  `BROKEN`, ritual exit 1. That is correct and must not be softened: research
  refresh's `UpstreamBlocked` path depends on it (`attractiveness_research_v2.py:366`).
* **The human label changes.** When `DATA_STARVED=1` **and** the only CRITICAL
  line is the capture-receipt line, the notification title becomes
  `[DATA-STARVED] options-validator daily ritual` instead of `[BROKEN] …`. If any
  other CRITICAL line is present, `[BROKEN]` wins. This is a display-only
  distinction in the shell; nothing on disk and no exit code changes.
* **Durability allow-list is tier-scoped (caution C6).** Under the data tier the
  ritual produces **no H7 evidence**, so it must not `git add` H7 paths under a
  commit message that calls them "the LIVE H7 forward window's daily evidence".
  Split the allow-list:

  ```zsh
  DATA_TIER_PATHS=(reports/ritual reports/intraday_capture reports/live_probe reports/cache_runs)
  FULL_TIER_PATHS=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab \
                   reports/h7_receipts reports/h7_data_gate reports/h5 \
                   reports/h6_forward reports/h8_forward reports/h10 \
                   reports/schwab_chains)
  ```

  `git add` receives `DATA_TIER_PATHS` always and `FULL_TIER_PATHS` **only when
  `FULL_AUTHORITY_RC -eq 0`**. The commit message is selected the same way:
  under the data tier it reads `data(ritual): daily ritual data-phase artifacts
  <RUN_DATE>` with a body stating that no H7 evidence was produced because the
  H7 lanes are paused. `reports/schwab_chains` stays in the FULL list — it is
  written by the independent capture wrapper, not by the ritual, and belongs
  with H7 evidence.

---

## 7. Blocker B5's honesty bar — what would justify `exact_session_source_active=True`

Not needed for this switch-on (§5), and specified now precisely so it cannot be
improvised later.

The flag's sentence is *"an approved **ongoing** exact-session options source is
active."* "Ongoing" is a claim about a **schedule**, not about a single run. One
canary proves the code path; it does not prove the schedule.

**Bar S1 — RECOMMENDED (LLM-proposed 2026-08-14; owner ratification required):**
all four conditions, simultaneously:

1. **Three consecutive scheduled trading sessions** produce a preclose capture
   whose receipt verifies offline via `tools/schwab_chain_manifest.verify_session`
   for the full registered watch universe.
2. All three were **unattended LaunchAgent fires** — not manual wrapper runs, and
   with `force=True` never used (forced captures are already refused as gate
   evidence by design).
3. **Zero operator intervention** between them — specifically, no re-auth, no
   `git` realignment, no plist reload inside the span. (A re-auth inside the span
   restarts the count: the 7-day Schwab refresh-token expiry documented in
   `docs/2026-08-04-underlying-closes-source-decision.md` is exactly the failure
   mode "ongoing" is supposed to exclude.)
4. `launchctl list com.carsyn.options-validator.schwab-chain-preclose` shows the
   job loaded with last exit status 0, captured into the flip's provenance note.

Cost: three trading days. Cheap relative to what the flag authorizes.

**Bar S2 — faster alternative, offered for completeness, NOT recommended:** one
verifying canary plus evidence the LaunchAgent is loaded and calendar-scheduled,
plus a written commitment to revert the flag on the first non-completing session.
S2 asserts "ongoing" about a schedule that has never fired unattended; it makes
the flag's own sentence a forecast rather than an observation.

Whichever bar the owner ratifies, the flip commit must carry a provenance
comment naming the bar, the three (or one) session dates, and the receipt paths.

---

## 8. Blocker B7 — the replacement provenance invariant, verbatim

`tests/test_daily_ritual_provenance.py::test_authority_preflight_precedes_every_mutation_surface`
currently asserts `require-full` precedes every mutation surface. Task 1
necessarily rewrites it. The replacement invariant, to be quoted verbatim in the
test module's docstring:

> **P1 (mutation fence).** In `tools/daily_ritual.sh`, the byte index of
> `"$PYTHON" -m data.ritual_authority require-data` is strictly less than the
> byte index of the first occurrence of **every** mutation surface in the script.
>
> **P2 (H7 fence).** The byte index of
> `"$PYTHON" -m data.ritual_authority require-full` is strictly less than the
> byte index of the first occurrence of **every** H7 surface in the script.
>
> **P3 (tier ordering).** `status` precedes `require-data`, and `require-data`
> precedes `require-full`. The `status` mode `exec`s and therefore reaches no
> gate; no other mode may bypass either gate.
>
> **P4 (closure).** Every `python -m <module>` invocation and every mutation verb
> present in the script is classified in exactly one of the two registries the
> test declares. An unclassified surface fails the test. A test that only checks
> a hand-written list of tokens is vacuous the moment a new step is added; P4 is
> what makes P1 and P2 binding over time.

### 8.1 Exact test rewrites in `tests/test_daily_ritual_provenance.py`

Declare two module-level registries:

```python
DATA_TIER_MUTATIONS = (
    'mkdir -p "$LOGDIR"',
    "--status RUNNING",
    "options_researcher.qm_dashboard",
    "options_researcher.features",          # via the python -c build_all calls
    "options_researcher.dashboard",
    "options_researcher.attractiveness_dashboard",
    "options_researcher.ritual_receipt",
    '--status "$RITUAL_TERMINAL_STATUS"',
    "git add --",
    "restic backup",
)
H7_TIER_SURFACES = (
    "options_researcher.h7_source_health",
    "options_researcher.h7_data_gate",
    "options_researcher.h7_exit_session fill",
    "options_researcher.h7_exit_session monitor",
    "options_researcher.h7_watch",
    "options_researcher.h7_entry_preflight",
)
GATE_GO_SURFACES = (   # membership per owner decision D-1
    "options_researcher.h6_features",
    "options_researcher.h6_watch",
    "options_researcher.entry_watch",
    "options_researcher.h8_watch",
    "options_researcher.h10_watch",
    "options_researcher.h10_observe",
)
```

| Test | Replaces / new | Asserts |
| --- | --- | --- |
| `test_require_data_precedes_every_mutation_surface` | replaces `test_authority_preflight_precedes_every_mutation_surface` | P1 over `DATA_TIER_MUTATIONS + H7_TIER_SURFACES + GATE_GO_SURFACES` |
| `test_require_full_precedes_every_h7_surface` | new | P2 over `H7_TIER_SURFACES` (+ `GATE_GO_SURFACES` under F1) |
| `test_tier_ordering_status_then_data_then_full` | replaces `test_status_mode_is_read_only_and_bypasses_full_authority_requirement` and `test_authority_commands_use_installed_python_without_uv_sync` | P3, plus the retained assertions `PYTHON="$REPO/.venv/bin/python"`, `PYTHONDONTWRITEBYTECODE=1 "$PYTHON"`, and `assertNotIn('$UV" run python -m data.ritual_authority')` |
| `test_every_script_surface_is_classified` | **new — the closure test** | P4: regex-extract every `python -m ([A-Za-z0-9_.]+)` and every mutation verb (`mkdir -p`, `git add`, `git commit`, `git push`, `restic backup`) from the script; assert the resulting set is exactly the union of the three registries. Fails on any unclassified addition. |
| `test_authority_gate_replaces_provider_topup_dependency` | amended | first index becomes `require-data`; ordering `require-data < require-full < h7_source_health < h7_data_gate`; keeps `assertNotIn("H7_DATA_READY")` |
| `test_status_preserves_log_tree_and_lockfile_bytes` | amended | unchanged behaviour; the `assertIn('"ready": false', stdout)` assertion is updated for the new combined-tier `status` JSON |
| `test_ops_publisher_requires_current_main` | unchanged | branch guard < origin/main guard < publisher role < source health |
| `test_durability_allow_list_is_tier_scoped` | replaces `test_durability_allow_list_includes_schwab_ledger_and_reports` | the H7 paths (`ledger/h7_forward`, `ledger/h7_forward_schwab`, `reports/h7_receipts`, `reports/h7_data_gate`, `reports/h5`, `reports/h6_forward`, `reports/h8_forward`, `reports/h10`, `reports/schwab_chains`) appear only inside the `FULL_AUTHORITY_RC -eq 0` branch; `reports/ritual` is added unconditionally |
| `test_paused_lanes_are_noted_not_critical` | new | when `require-full` refuses, the else-branch contains `note` and contains no `crit` |
| `test_h5_h6_h8_h10_failure_lines_stay_critical` | keeps `test_h6_and_h8_nonzero_results_are_critical`, `test_h5_rerun_failure_is_critical_before_terminal_publish`, `test_h10_rerun_failures_are_critical_before_terminal_publish` | unchanged text assertions, re-verified against the restructured script |
| `test_ritual_terminal_status_is_separate_from_capture_receipt` | unchanged | RUNNING < capture < terminal < durability |

`tests/test_ritual_authority.py` rewrites: keep
`test_tracked_authority_module_exists`; extend
`test_module_exposes_readiness_and_cli_interfaces` to require
`evaluate_data_phase`; replace the readiness tests with a matrix over the eight
flag combinations asserting (a) data tier ready iff `ritual_data_phase_active`,
(b) full tier ready iff all three, (c) **monotonicity** — full ready implies data
ready, for every combination, (d) the preserved blocker substrings
`"exact-session"`, `"H7"`, `"ThetaData"` on the full tier; and
`test_status_succeeds_but_require_modes_refuse` covering all three CLI modes and
their exit codes. Every case constructs its own `RitualAuthority` — **no test may
read `CURRENT_AUTHORITY` and assert a specific flip state**, or the flip commit
(§12 D-2) breaks the suite.

---

## 9. Blocker B6 — ops/research realignment and the fail-soft push

Two independent defects, both fixed here.

### 9.1 The fast-forward rule (mandatory, operational)

**Rule R1.** *Any* merge to `origin/main` — by any session, agent, or the owner —
is not complete until both production checkouts are fast-forwarded:

```bash
git -C ~/options-validator-ops fetch -q origin main && git -C ~/options-validator-ops merge --ff-only origin/main
git -C ~/options-validator-research fetch -q origin main && git -C ~/options-validator-research merge --ff-only origin/main
git -C ~/options-validator-ops rev-parse HEAD          # must equal origin/main
git -C ~/options-validator-research rev-parse HEAD     # must equal origin/main
```

If `--ff-only` refuses, **stop** — ops has local commits (see 9.2); do not merge
or reset, diagnose first. R1 must be written into
`docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`
and `docs/h7-forward-operations.md` as a numbered step, not left as tribal
knowledge. (Runbook 08 step 9 fast-forwards the research worktree once; R1
generalizes it to every merge and both checkouts.)

**Rule R2 (pre-canary self-check).** On every trading day the operator (or a
scheduled check) confirms before 15:45 ET that
`git -C ~/options-validator-ops rev-parse HEAD` equals
`git -C ~/options-validator-ops rev-parse origin/main` **after a fetch**. The
15:45 wrapper fetches and then refuses on any divergence
(`tools/schwab_chain_capture.sh`, "HEAD is not aligned with origin/main"), and a
refusal at 15:45 loses that session's chains **permanently**.

### 9.2 The fail-soft push (the actual kill vector)

`tools/daily_ritual.sh:389-408` commits evidence locally and then pushes
**fail-soft** (`note`, never `crit`). A failed push leaves ops HEAD **ahead** of
`origin/main`. From that moment:

* the ritual's own guard at line 80 refuses the next run (`crit`, exit 1) — the
  ritual self-blocks, which is at least loud; **but**
* `tools/schwab_chain_capture.sh` fetches, sees `LOCAL_SHA != REMOTE_SHA`, and
  refuses at 15:45. **That session's irreplaceable chains are lost.**

Required changes to `tools/daily_ritual.sh`:

1. **Escalate.** On push failure, additionally set a distinct flag and emit:
   `crit "evidence: PUSH FAILED — ops HEAD is AHEAD of origin/main; the 15:45 Schwab capture WILL REFUSE until this is realigned. Run: git -C <REPO> push origin main"`.
   It becomes a CRITICAL line (`[BROKEN]` notification), not a quiet `note`.
   Rationale: the current fail-soft comment ("persistence must not break the
   ritual that produces the evidence") is correct about the *exit code*; it is
   wrong about the *alert level*, because the consequence is not deferred
   persistence — it is a lost capture the same afternoon.
2. **Retry once, immediately**, with a bounded, prompt-free push
   (`GIT_TERMINAL_PROMPT=0`, `-c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20`,
   matching the capture wrapper's existing bounded-fetch discipline) before
   declaring failure. Most failures are a concurrent push; a fetch+merge+retry
   resolves them.
3. **State the realign step in the notification body**, not only in the log — the
   log is not read on a good day.

The ritual must **not** attempt to fix alignment by resetting or dropping the
evidence commit. Losing evidence to protect a guard is the wrong trade.

**Optional structural fix (owner decision D-3):** relax the capture wrapper's
alignment gate from `LOCAL_SHA == REMOTE_SHA` to "every commit in
`origin/main..HEAD` touches only evidence allow-list paths." This preserves the
guard's actual purpose — *no unreviewed code runs unattended* — while surviving
an unpushed evidence commit. It is a change to a guard on the irreplaceable-capture
critical path, so it is the owner's call, not the implementer's.

---

## 10. Acceptance tests (named)

Offline, `unittest`, no network, no provider calls. Run:
`uv run python -m unittest discover -s tests`.

**Authority (`tests/test_ritual_authority.py`)**
1. `test_module_exposes_readiness_and_cli_interfaces` — `evaluate_data_phase`,
   `evaluate_full_ritual`, `main` all present.
2. `test_tier_matrix_over_all_flag_combinations` — 8 combinations; data tier
   ready iff `ritual_data_phase_active`; full tier ready iff all three.
3. `test_full_tier_implies_data_tier` — monotonicity over all 8.
4. `test_full_tier_blocker_wording_is_preserved` — `"exact-session"`, `"H7"`,
   `"ThetaData"` substrings survive.
5. `test_status_succeeds_but_require_modes_refuse` — exit codes 0 / 1 / 1 for
   `status` / `require-data` / `require-full` at the pre-flip defaults; `status`
   JSON contains both tiers and all three flags.
6. `test_all_modes_are_side_effect_free` — no file created/modified under the
   repo root by any mode.

**Provenance (`tests/test_daily_ritual_provenance.py`)** — the full table in §8.1.
The load-bearing ones: `test_require_data_precedes_every_mutation_surface`,
`test_require_full_precedes_every_h7_surface`,
`test_every_script_surface_is_classified` (closure),
`test_durability_allow_list_is_tier_scoped`,
`test_paused_lanes_are_noted_not_critical`.

**Hash containment (new, `tests/test_ritual_switch_on_hash_containment.py`)**
7. `test_config_hash_surface_unchanged` — the set of uppercase names in
   `config.py` equals a frozen tuple checked into the test, and
   `config.INTRADAY_CAPTURE_TIMES` has exactly its four existing keys. This is
   blocker B8's standing guard: any future capture-tag work that adds a config
   entry fails here first, in a test whose name says why.

**Mutation tests (required before review sign-off, per the EC-1 lesson: a green
suite plus passing tests still hid a real defect).** Each must turn a test RED:
* M1 — move the `require-data` gate below `mkdir -p "$LOGDIR"` → P1 test fails.
* M2 — move an H7 step above the `require-full` gate → P2 test fails.
* M3 — add `"$UV" run python -m options_researcher.h9_something` to the script
  without registering it → closure test fails.
* M4 — add H7 paths to the unconditional `git add` → allow-list test fails.
* M5 — set `ritual_data_phase_active=True` in a copied authority object while
  leaving `h7_active=False` → full tier still refuses.
* M6 — add a constant to `config.py` → hash-containment test fails.

**End-to-end smoke (manual, after the flip, once):** run
`zsh tools/daily_ritual.sh status` (must stay byte-preserving, exit 0), then a
single supervised `zsh tools/daily_ritual.sh run` from ops, and confirm: log
written; cache-edge note present naming 2026-07-27; H7 lanes noted as PAUSED with
no CRITICAL; both dashboards rebuilt; capture receipt written with all five lanes
MISSING; terminal status `BROKEN`; notification titled `[DATA-STARVED]`;
`ledger/` and `reports/h7_*` untouched (`git status --short` shows no H7 path);
`origin/main` push succeeded or a CRITICAL push-failure line is present.

---

## 11. Landing sequence, failure behavior, rollback

### Landing sequence

1. Branch off `origin/main` (`58b1fd9`). Build D1-D4 + tests. Suite green, `ruff`
   + `pyright` clean.
2. Run the six mutation tests; record results in the review packet.
3. **Independent adversarial review** of this spec's implementation (house rule;
   brief 10 failed exactly here).
4. **Timing constraint (from §2's source-hash finding):** merge and fast-forward
   ops **outside the trading session** — before the first receipt of a session or
   after the last. `data/ritual_authority.py` is inside `diagnostic_source_hash`,
   so landing it mid-session invalidates same-session receipt reuse in
   `h7_exit_session`, `h7_schwab_window_registration`, `intraday_capture` and
   `intraday_preview`.
5. Merge to `origin/main`; **immediately apply rule R1** (§9.1) to both ops and
   research; verify both HEADs equal `origin/main`.
6. Confirm the daily-ritual LaunchAgent is loaded
   (`launchctl list | grep options-validator`). Caution C4's disposition: this
   spec adds **no new plist**, so no `launchctl bootstrap` is required — but the
   existing job has not produced a run since 2026-07-28 and must be confirmed
   loaded, not assumed.
7. **The flip is a separate commit** (owner decision D-2): the single line
   `ritual_data_phase_active=False → True` with a provenance comment
   `# owner-directed in-session 2026-08-14 (brief 11 §5); asserts NO source and NO H7 authority`.
8. Supervised manual run (§10 smoke). Then let the schedule take over.

### Failure behavior (fail-closed everywhere)

| Condition | Behavior |
| --- | --- |
| `ritual_data_phase_active` False | ritual prints read-only JSON, exits nonzero, creates no artifact — byte-identical to today |
| `require-full` refuses | H7 + GATE_GO lanes skipped with `note`; data tier still runs; **no** CRITICAL from the pause itself |
| ops not on `main`, or `main` != `origin/main` | existing branch guard refuses before any mutation — unchanged |
| capture receipt refuses (expected while starved) | CRITICAL, terminal status `BROKEN`, exit 1, notification `[DATA-STARVED]` |
| evidence push fails | CRITICAL + realign instruction in log and notification; ritual still exits per its own status |
| `.cache/chains` unreadable or empty | `CHAIN_EDGE` empty → note "canonical chain cache edge: none"; no crash |
| research refresh runs | `UpstreamBlocked` on the non-OK ritual status — unchanged, correct |

### Rollback

* **Fastest (no deploy):** flip `ritual_data_phase_active` back to `False`, land,
  fast-forward ops. The ritual returns to fail-closed silence in one line. This
  is why the flip is a separate commit.
* **Emergency, no merge available:** `launchctl bootout` the daily-ritual job in
  ops. The ritual cannot then run at all; nothing else depends on it.
* **Full revert:** `git revert` the D1-D4 commit range. Nothing in this change set
  writes an immutable receipt, a ledger entry, or any append-only record, so a
  revert leaves no orphaned state. The only side effects a data-tier run can
  leave behind are `reports/ritual/*` artifacts, `.cache/underlying_ohlcv`
  refreshes, feature-store rebuilds, and `.tmp/dashboard` output — all
  regenerable, none verdict-bearing.
* **Not rollback-able and therefore not in this spec:** anything that appends to
  `ledger/` or `reports/h10/observations.jsonl`. That is precisely why owner
  decision D-1's recommendation is F1.

---

## 12. OWNER DECISIONS

Recommendations are the design agent's; none is decided here.

### D-1 — The hypothesis fence (blocker B4). *Which lanes may run under data-tier authority?*

Context: steps 10-14 sit behind `GATE_GO`, which is the **H7** data gate. With
H7 paused they cannot run at all unless deliberately decoupled. And because
`.cache/chains` is frozen at 2026-07-27, **every one of them would return
DATA_GAP / stale today even if decoupled.**

| Option | Runs | Appends to a registered record? | Can emit an entry signal? |
| --- | --- | --- | --- |
| **F1 (recommended)** | nothing beyond the data tier | no | no |
| F2 | `h6_features`, `h6_watch`, `h8_watch`, `entry_watch`, `h10_watch` — all verified never to write the paper book | no | **yes** — `entry_watch` can print FIRE; `h6_watch` ELIGIBLE; `h8_watch` ENTRY-OK |
| F3 | F2 + `h10_observe` | **yes** — appends `reports/h10/observations.jsonl` for a registered hypothesis | yes |

**Recommendation: F1.** It costs nothing real — all five lanes are chain-starved,
so F2 would buy only a daily pile of DATA_GAP records — while F3 would write
starved observations into a live hypothesis's append-only record under an
authority tier that explicitly does not assert exact-session data. That is the
pre-registration honesty breach the review named. If the owner wants per-lane
visibility, the §6.3 cache-edge note plus the existing capture receipt already
provide it without touching any registered record.

*If the owner picks F2 or F3,* the implementation must also decouple those steps
from `GATE_GO` (they currently depend on the H7 gate), which is additional work
not specified here and would need its own review pass.

### D-2 — Flip `ritual_data_phase_active` to `True`?

This is the switch-on itself. It asserts only: *the owner authorizes the daily
non-verdict-bearing data/display phase to run from cached data.* It asserts
nothing about a live source and nothing about H7.
**Recommendation: yes**, as a separate one-line commit after D-1 is answered and
the implementation passes independent review. **Unlike brief 10's Task B, this
flip does NOT depend on the canary** — it makes no claim the canary would prove.

### D-3 — Relax the 15:45 capture wrapper's alignment gate to tolerate evidence-only divergence? (§9.2)

**Recommendation: yes**, because the current gate converts a transient push
failure into a permanently lost irreplaceable capture, and the narrowed rule
still guarantees no unreviewed *code* runs unattended. But it modifies a guard on
the irreplaceable-capture critical path, so it should not be an implementer's
call. If declined, rules R1 + R2 and the escalated push alert are the whole
mitigation, and they depend on the operator noticing.

### D-4 — Ratify the `exact_session_source_active` honesty bar (§7): S1 (three consecutive unattended verifying sessions) or S2 (one canary + loaded schedule)?

**Recommendation: S1.** LLM-proposed threshold ("three consecutive"), not an
owner-typed number — ratification requested. Not needed for D-2; needed before
any future flip of that flag.

### D-5 — The ritual's one network surface.

`qm_dashboard --refresh-ohlcv` fetches underlying OHLCV over the network
(`data/underlying_ohlcv.py:193`, `urllib.request`). This is the Yahoo lane
ratified in `docs/2026-08-04-underlying-closes-source-decision.md`, it is
**underlying prices only**, and it does not touch chains — OD-2/OD-4 are not
implicated. Switch-on re-enables it because it re-enables the step.
**Recommendation: leave it on** (it is the only lane that produces genuinely
fresh data). Flagged because "the ritual makes a provider call" should be an
owner-visible fact, not a surprise. This is caution C5's disposition.

---

## 13. Disposition of every blocker and caution

| ID | Disposition |
| --- | --- |
| B1 chain-cache poisoning | **Resolved by exclusion** — no 10:00 capture in this spec; no code writes `.cache/schwab_chains` |
| B2 `facts.log` dedupe collision | **Resolved by exclusion** — no second same-day capture; this spec appends no fact |
| B3 manifest convention / glob kill vector | **Resolved by exclusion** — `tools/schwab_chain_manifest.py` untouched |
| B4 research-refresh promise false | **Fixed** — §3 deletes the promise; §6.1 enumerates every step by tier; the fence is owner decision D-1 (recommendation F1), not a silent move |
| B5 flip asserts a source that feeds nothing | **Fixed at the root** — §4 recommends Option B (re-scope, with reasoning and the complete code-delta list) and §5 removes the source claim from the switch-on entirely by introducing `ritual_data_phase_active`; §7 fixes the bar for the source flag's future flip |
| B6 canary kill vector via fail-soft push | **Fixed** — §9: rules R1/R2, push escalated to CRITICAL with a realign instruction, bounded retry, plus optional structural fix D-3 |
| B7 provenance tests weakened | **Fixed** — §8 states P1-P4 verbatim, §8.1 gives the exact rewrites, and P4's closure test plus mutation tests M1-M3 make them non-vacuous |
| B8 `config_hash()` blast radius | **Resolved by exclusion + guarded** — no `config.py` change; `test_config_hash_surface_unchanged` (§10.7) makes any future addition fail loudly. §2 additionally documents the *un-named* half of the problem: `diagnostic_source_hash` covers `data/` and `options_researcher/`, giving §11's out-of-session landing constraint |
| C1 feasibility receipt config-hash stale | **Out of scope, unaffected** — registration-day work; this spec changes no `config.py` line, so it neither fixes nor worsens it |
| C2 supersedes runbook 08's "flip last" | **Done** — §1.2, named and owner-attributed; runbook 08 edited in the same landing |
| C3 data-phase enumeration wrong | **Fixed** — §6.1 is measured from the script; there is no closes step, no quotes step, and source health is correctly classified as an H7 receipt writer |
| C4 new plists need owner bootstrap | **N/A** — no new plist. §11.6 requires confirming the existing job is loaded |
| C5 provider call-count estimate | **N/A for a capture** (none added); the ritual's one existing network call is surfaced as owner decision D-5 |
| C6 commit labels morning chains as H7 evidence | **Fixed** — §6.4 tier-scoped allow-list and commit message; `test_durability_allow_list_is_tier_scoped` |
| C7 tests pass vacuously | **Fixed for this spec** — P4 closure test + mutation tests M1-M6; carried forward as a named requirement for the deferred 10:00 spec |
| C8 guard/backup namespace coverage | **N/A** — no new namespace; `reports/schwab_chains` remains in the FULL-tier allow-list and in the irreplaceable-data guard |
| C9 factual drift | **Corrected** — §2: `data/ritual_authority.py` was created 2026-08-02 (`db3f907`). `nearest_session_tag` is untouched (no new tag) |

---

## 14. Explicitly out of scope

* `h7_active` and anything registration-day (OD-3 wording, registered numbers,
  the feasibility receipt, the PREPARED patch's content beyond marking it stale).
* The 10:00 ET capture session — its own future spec, which must resolve B1, B2,
  B3, B8-capture, C5, C7 and C8 on its own evidence.
* Wiring any consumer to `.cache/schwab_chains` (Option A). If the owner later
  wants it, it is a registration-amendment-bearing project, not a plumbing task.
* Any change to preclose capture semantics, the FINRA `SHORT_CONTEXT_ENABLED`
  flag, or `.cache/chains` contents (OD-2/OD-4 stand: no refill, ever).
* Merging `codex/h7-schwab-recovery`, `codex/short-positioning-phases-1-4`, or
  `codex/handoff` — unchanged from runbook 08.
