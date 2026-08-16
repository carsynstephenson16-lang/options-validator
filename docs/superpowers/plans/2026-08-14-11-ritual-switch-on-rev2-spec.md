# Brief 11 (rev-2.1) — Ritual switch-on: honest data-phase restart

**Date:** 2026-08-14 (rev-2.1; rev-2 same day)
**Status:** DRAFT SPEC, review-corrected. rev-2 received an independent
adversarial review with verdict **PASS WITH FIXES** (7 blockers, 11 cautions) —
receipt: `reports/2026-08-14-rev2-switch-on-review-receipt.md`. Every blocker
and every caution is applied below. Still requires the OWNER DECISIONS in §12
(now D-1 … D-6) before merge.
**Author:** Opus design agent, commissioned by the orchestrating session with
`reports/2026-08-14-brief-10-adversarial-review-receipt.md` as its charter.
rev-2.1 edits applied by the review-application session.
**Executor:** Codex (Sol, high) or an Opus implementation agent.
**Code truth for every measurement below:** `~/options-validator-ops` at
`origin/main` = **`c96ed4b`** (merge of PR #36, 2026-08-14 10:28 ET), measured
2026-08-14. rev-2's original measurements were taken at `58b1fd9`; every line
number quoted in rev-2.1 is a `c96ed4b` line number and was re-verified
against that tree.

## Change log — rev-2 → rev-2.1

Each entry names the review finding it discharges. Nothing else changed.

| Finding | Where applied |
| --- | --- |
| **B-1** H7 fence matcher unspecified | §8 P2, §8.1 matcher spec — provenance tests match `python -m <module>` invocation sites only; `daily_ritual.sh:98-99` classified explicitly as data-tier-permitted |
| **B-2** closure invariant broken six ways | §8 P4 rewritten (three registries); §8.1 gains the `python -c` site table (all seven), the `features` matcher fix, the `data.ritual_authority` gate exemption, all four `mkdir` sites, `git fetch` / `git merge --no-edit`, and separate matchers per registry |
| **B-3** false "resumes automatically" rider | §3 deliverable 5 replaced with the honest two-condition statement |
| **B-4** single wrap swallows the data tier | §6.2 replaced with TWO explicit full-tier regions (`:113-:216`, `:260-:340`) and a frozen-operator-order preservation clause |
| **B-5** hash-binding table wrong | §2 hashed-paths list completed; binding table corrected (`diagnostic_source_hash` vs `config_hash`); §11 landing window restated |
| **B-6** `INTRADAY_CAPTURE_TIMES` key count wrong | §10.8 and the test spec: **five** keys (`open_auction`, `open`, `midmorning`, `midday`, `preclose`) |
| **B-7** §8.1 vs §10.5 contradiction | §5 adds an authority-injection seam to `main()`; §8.1 and §10.5 reconciled; `require-data` / `require-full` stdout specified |
| **C-a** rewrite inventory incomplete | §8.1 gains the four other `daily_ritual.sh`-text-binding test modules |
| **C-b** rollback understated | §11 rollback: post-registration the flip also stops live-window evidence |
| **C-c** PREPARED patch | §5: regenerate at registration day; both hunks break; gate-packet two-flag assumption flagged |
| **C-d** `[DATA-STARVED]` mechanism unspecified | §6.4: dedicated starvation flag + `crit` counter |
| **C-e** intra-day behind-case | new **owner decision D-6**; §13 C4 disposition made conditional |
| **C-f** S1 not artifact-measurable | §7 S1 restated; unmeasurable conditions dropped or given a provenance field |
| **C-g** Schwab gate already partly wired | §2 and §4 Option A corrected (only the CLI lacks the flag) |
| **C-h** "fresh underlying closes" overclaimed | §3 deliverable 2, §11, §12 D-5: OHLCV for the 9-name watch universe only; the closes store stays frozen |
| **C-i** `git merge` unclassified | §6.1 table row 18 |
| **C-j** C7 closed prematurely | §13: C7 reopened and closed via B-2's fixed closure spec |
| **C-k** publisher export unclassified | §6.1 table row 1b + least-privilege note |
| **D-5** overstated network claim | §12 D-5 demoted to a disclosure; claim narrowed to market-data/provider calls |

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

**Schwab gate reachability (corrected in rev-2.1 — caution C-g).** rev-2 said
the Schwab gate is unreachable from `h7_data_gate`. That was wrong, and the
correction *reduces* Option A's stated cost without changing the
recommendation. Measured at `c96ed4b`:

* `h7_data_gate.evaluate()` **already takes an `evidence_mode` argument**
  (`h7_data_gate.py:513`) and refuses when it is not explicit.
* `h7_data_gate` **already imports** `options_researcher.h7_schwab_data_gate`
  and **already branches on** `h7_schwab_data_gate.EVIDENCE_MODE`
  (`h7_data_gate.py:522` in `_validate_result_scope_closure`, and
  `h7_data_gate.py:601-604`, which calls
  `h7_schwab_data_gate.validate_receipt_scope_closure` when the evidence mode
  is the Schwab one).
* What is genuinely missing is **only the CLI flag**: `h7_data_gate`'s argument
  parser exposes `--close-dir`, `--chain-dir`, `--reports-dir`,
  `--source-health-receipt` and `--write-receipt` (`h7_data_gate.py:813-829`)
  and **no `--evidence-mode`**. So today's CLI, pointed at Schwab bytes, still
  runs the ThetaData v2 audit-receipt validator against parquet that carries no
  such receipt: guaranteed NO_GO.
* `h7_schwab_data_gate.evaluate` itself still has no CLI; its only non-test
  caller remains `options_researcher/h7_schwab_window_registration.py`.

**Source-hash blast radius (generalization of blocker B8; corrected in rev-2.1
— blocker B-5):** `research/hashing.py:132-134` defines
`DIAGNOSTIC_SOURCE_PATHS_V2 = SOURCE_HASH_PATHS + ("options_researcher",
"tools")` and `DIAGNOSTIC_SOURCE_PATHS_V3 = DIAGNOSTIC_SOURCE_PATHS_V2`.
`SOURCE_HASH_PATHS` (`research/hashing.py:17-26`) is **wider than rev-2
claimed**. The complete v3 surface is:

| Kind | Entries |
| --- | --- |
| Whole files, hashed byte-for-byte | `pyproject.toml`, `uv.lock`, `config.py`, `metrics.py` |
| Directories, `*.py` globbed recursively (dot-prefixed components excluded in v3) | `analysis/`, `data/`, `harness/`, `research/`, `strategies/`, `options_researcher/`, `tools/` |

Therefore:

* editing `data/ritual_authority.py` or `options_researcher/ritual_receipt.py`
  **changes `diagnostic_source_hash()`**;
* editing `tools/daily_ritual.sh` **does not** (directories are globbed for
  `*.py` only, and `tools/` is a directory entry);
* **but** a dependency bump touching `pyproject.toml` or `uv.lock` **does** —
  those are file entries, not `*.py` globs. Anyone treating "no `.py` changed"
  as "hash unchanged" is wrong. This is the un-named half of B8 that rev-2
  missed;
* `config_hash()` hashes every uppercase name in `config.py` — **this spec adds
  no constant to `config.py`**, so `config_hash()` is unchanged. That is the
  positive disposition of B8's second half, and it is an acceptance test (§10,
  `test_config_hash_surface_unchanged`).

**Which hash actually binds which refusal (rev-2 stated this wrongly; corrected
here, measured at `c96ed4b`):**

| Refusal site | Binds |
| --- | --- |
| `options_researcher/h7_exit_session.py:247` (gate receipt) | `diagnostic_source_hash` |
| `options_researcher/h7_exit_session.py:267` (source-health receipt) | `diagnostic_source_hash` |
| `options_researcher/h7_watch.py:197` | `diagnostic_source_hash` |
| `options_researcher/h7_data_gate.py:748` | `diagnostic_source_hash` |
| `options_researcher/h7_activation_guard.py:177` | `diagnostic_source_hash` |
| `tools/h7_data_audit.py:668` | `diagnostic_source_hash` |
| `options_researcher/intraday_capture.py:495` | **`config_hash`** — NOT the source hash |
| `options_researcher/intraday_preview.py:81` | **`config_hash`** |
| `options_researcher/h7_schwab_window_registration.py:175` (data-gate receipt) | **`config_hash`** |
| `options_researcher/h7_schwab_window_registration.py:263` (feasibility receipt) | **`config_hash`** |

rev-2 named `h7_schwab_window_registration`, `intraday_capture` and
`intraday_preview` as `diagnostic_source_hash` refusal sites. They are not —
all four of those refusals bind `config_hash`, which this change set does not
touch. The real `diagnostic_source_hash` refusal sites are the six H7 surfaces
in the top half of the table, **every one of which sits behind the
`require-full` fence** under Option B. The corrected landing-window consequence
is in §11.

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

**Deliverable of switch-on (rev-2.1):**
1. The daily ritual stops being dead: it runs, logs, and notifies every weekday.
2. **OHLCV for the 9-name watch universe only refreshes to the current session;
   the closes store stays frozen.** (Corrected in rev-2.1 — caution C-h.)
   Precisely: `qm_dashboard --refresh-ohlcv` calls
   `refresh_qm_ohlcv(watch_universe(), …)` (`qm_dashboard.py:440`), so it tops
   up **`.cache/underlying_ohlcv`** for the 9 H7 watch-universe names, and even
   then only for names covered by the frozen QM study sidecar — an uncovered
   name is rejected before any load or fetch (`qm_dashboard.py:350-364`).
   **`.cache/underlying`** — the closes store read by
   `data/underlying_closes.py` — is **not** refreshed and stays frozen at
   **2026-08-05**. Its only refresher is `data/recent_topup.py`, which the
   ritual deliberately never calls; `tests/test_daily_ritual_provenance.py:47`
   asserts `assertNotIn("data/recent_topup.py", source)` to keep it that way.
   Plain consequence: any consumer reading the closes store — including the
   Wasserstein/composite display lanes and anything else built on
   `data/underlying_closes.py` — stays as stale after switch-on as before it.
   Switch-on does not fix that, and no artifact may say it does.
3. The attractiveness feature store and both dashboards rebuild daily, carrying
   their existing honest as-of / staleness banners.
4. A daily, machine-readable record of exactly which hypothesis lane is starved,
   with the cache edge named in the log and the notification.
5. Research refresh remains **honestly blocked**. (Corrected in rev-2.1 —
   blocker B-3; rev-2's "resumes automatically with no further code change"
   rider was false and is deleted.) The honest statement: research refresh
   stays blocked until **both** (i) fresh evidence exists **and** (ii)
   `require-full` is satisfied. Neither arrives on its own.
   `attractiveness_research_v2` raises `UpstreamBlocked` unless the ritual run
   status is exactly `"OK"` (`attractiveness_research_v2.py:366-367`), and
   under the data tier the capture receipt refuses on starved lanes →
   `CRITICAL=1` → terminal status `BROKEN`. Condition (ii) requires
   `h7_active=True` **and** `exact_session_source_active=True` — that is
   registration day plus the owner flips of §7's bar, and **each flip is itself
   a code change to `data/ritual_authority.py`, a file inside
   `diagnostic_source_hash`**. There is no configuration in which research
   refresh resumes without a hashed-file edit.

Anything more requires either fresh chains or an owner decision (§12).

---

## 4. Blocker B5 — the honest data path: TWO OPTIONS, ONE RECOMMENDATION

### Option A — wire ritual consumers to Schwab evidence (`.cache/schwab_chains`)

What it would take, measured (**cost restated in rev-2.1 — caution C-g;
the gate seam is cheaper than rev-2 claimed, the recommendation is unchanged**):

* ~~Build a CLI/evidence-mode seam for `h7_schwab_data_gate` (none exists).~~
  **Corrected:** the *library* seam already exists — `h7_data_gate.evaluate()`
  takes `evidence_mode` (`:513`) and the module already branches on
  `h7_schwab_data_gate.EVIDENCE_MODE` (`:522`, `:601-604`). The only missing
  piece is an `--evidence-mode` CLI flag on `h7_data_gate`'s parser
  (`:813-829`). That is roughly a one-flag change, not a subsystem.
* Parameterize `chains.load_range` / `pandas_feed.load_cached_chains` /
  `thetadata_adapter._cache_path` — the shared, non-parameterized loader behind
  `features.build_all` and `h10_watch`.
* Un-hardcode `.cache/chains` in `entry_watch.py:191` and `h7_watch.py:216`.
* Build a schema/audit-receipt bridge: every consumer *other than the gate*
  validates a ThetaData v2 audit receipt that Schwab parquet does not carry
  (`h7_data_gate.validate_v2_audit_receipt`).

The gate being cheaper does not move the recommendation, because reasons 1-4
below are about **evidence and registration**, not about plumbing cost. A
cheap wiring job into an unregistered input substitution is still an
unregistered input substitution.

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
| D1 | `data/ritual_authority.py` | add `ritual_data_phase_active` flag (default `False`); add `evaluate_data_phase()`; make `evaluate_full_ritual()` require all three flags; **add the `authority=` injection seam to `main()` (B-7)**; CLI gains `require-data`, and `status` reports both tiers and all three flags per §5's stdout table | **yes** (`data/`) |
| D2 | `tools/daily_ritual.sh` | top gate becomes `require-data`; **TWO** inner `require-full` regions fence the H7 surfaces (`:113-:216` and `:260-:340`), leaving the data-tier island `:218-:258` unfenced (B-4); tier-scoped durability allow-list + commit message; cache-edge note; push-failure escalation; `[DATA-STARVED]` label via the `CRIT_COUNT`/`STARVED_CRIT` counters (C-d) | no (`.sh`) |
| D3 | `tests/test_ritual_authority.py` | rewritten for three flags / three modes, driven through the injection seam | n/a |
| D4 | `tests/test_daily_ritual_provenance.py` | rewritten per §8 invariants, including the **closure** test with three registries and three matchers | n/a |
| D4b | `tests/test_h7_daily_exit_order.py`, `tests/test_qm_dashboard.py`, `tests/test_shell_banner_guard.py`, `tests/test_h8_watch.py` | **run and, where the restructure moves their offsets, corrected — never weakened** (rev-2.1, caution C-a; see §8.1) | n/a |
| D4c | `reports/h7_forward_schwab/2026-08-09-authority-flip.PREPARED.patch`, `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md:55` | mark the patch `STALE — REGENERATE AT REGISTRATION`; correct the packet's two-flag assumption (rev-2.1, caution C-c) | no |
| D5 | `tools/schwab_chain_capture.sh` | *(owner decision D-3 only)* evidence-only-divergence tolerance in the alignment gate | no (`.sh`) |
| D6 | `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`, `docs/h7-forward-operations.md` | record the §1 supersession, the §9 fast-forward rule, and (per owner decision D-6) the pre-15:45 alignment check | no |

**Not changed by Option B:** `config.py` (zero lines), `options_researcher/*.py`
(zero files), `h7_data_gate.py`, `h7_schwab_data_gate.py`, `ritual_receipt.py`,
`attractiveness_research_v2.py`, any ledger, any registered number.
*(Caveat added in rev-2.1: if the owner ratifies S1 with option **3a** under
D-4, the capture receipt gains an `invocation_source` field — that **is** an
`options_researcher/` change and therefore a hashed one. It is not part of this
landing; it is a consequence of D-4 that §7 now names explicitly rather than
letting it arrive as a surprise.)*

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
  Every mode remains read-only and side-effect free.

* **Authority-injection seam in `main()` (NEW in rev-2.1 — blocker B-7).**
  rev-2 contradicted itself: §8.1 forbade any test from reading
  `CURRENT_AUTHORITY` and asserting a flip state, while §10.5 asserted CLI exit
  codes "at the pre-flip defaults" — which is exactly reading
  `CURRENT_AUTHORITY`. Today's `main()` hardcodes the live object
  (`ritual_authority.py:48` calls `evaluate_full_ritual()` with no argument),
  so there is no way to test the CLI without depending on the live flags.
  Required signature:

  ```python
  def main(
      argv: list[str] | None = None,
      *,
      authority: RitualAuthority = CURRENT_AUTHORITY,
  ) -> int:
  ```

  Both `evaluate_data_phase(authority)` and `evaluate_full_ritual(authority)`
  are evaluated on the **injected** object. Tests assert behavior at explicit
  flag combinations they construct themselves and **never** at the live
  `CURRENT_AUTHORITY` values, so the §12 D-2 flip commit cannot break the
  suite. The default keeps the shell call site (`daily_ritual.sh:37,47`)
  byte-identical.

* **Specified stdout per mode (NEW in rev-2.1 — blocker B-7, second half).**
  The existing test asserts `assertEqual(required, status)`
  (`tests/test_ritual_authority.py:47`) — true today only because both modes
  print the same single `RitualReadiness`. With three modes that assertion has
  no meaning and needs a defined replacement, so the output contract is fixed
  here:

  | Mode | stdout (one JSON object, `sort_keys=True`) | Exit |
  | --- | --- | --- |
  | `status` | `{"data_phase": {"blockers": [...], "ready": bool}, "flags": {"exact_session_source_active": bool, "h7_active": bool, "ritual_data_phase_active": bool}, "full_ritual": {"blockers": [...], "ready": bool}}` | always 0 |
  | `require-data` | `asdict(evaluate_data_phase(authority))` — i.e. exactly the `data_phase` sub-object of `status` | 0 iff ready, else 1 |
  | `require-full` | `asdict(evaluate_full_ritual(authority))` — i.e. exactly the `full_ritual` sub-object of `status` | 0 iff ready, else 1 |

  The replacement for `assertEqual(required, status)` is therefore two
  assertions with defined meaning:
  `assertEqual(json.loads(data_out), status["data_phase"])` and
  `assertEqual(json.loads(full_out), status["full_ritual"])`.

* **No `require-source` mode is added.** With Option B, nothing consumes an
  exact-session source, so a `require-source` tier would be a mode with no
  caller. It is specified here as future work (§7) so the tier's meaning is
  fixed *before* anyone is under pressure to invent it.

**Consequence to record (caution C1 neighbour; expanded in rev-2.1 — caution
C-c):** adding a field to `RitualAuthority` and rewriting the authority tests
**invalidates**
`reports/h7_forward_schwab/2026-08-09-authority-flip.PREPARED.patch`. Verified
at `c96ed4b`: the patch has **two hunks and both break** under rev-2.1.

1. Hunk 1 patches `data/ritual_authority.py` and its context is the
   **two-field** `CURRENT_AUTHORITY(...)` constructor, which gains a third
   field. Context mismatch → will not apply.
2. Hunk 2 patches `tests/test_ritual_authority.py` and rewrites exactly the two
   tests rev-2.1 replaces — `test_full_ritual_is_blocked_without_source_and_h7_authority`
   and `test_status_succeeds_but_require_full_refuses`, including the
   `self.assertEqual(required, status)` line that B-7 retires. Both targets
   disappear → will not apply.

Because the patch content depends on the tests as they exist on registration
day, a one-time regeneration in this landing would go stale again. **The
requirement is therefore: regenerate the PREPARED patch AT registration day,
against the then-current tree, and in this landing replace the file with (or
add beside it) a prominent `STALE — DO NOT APPLY; REGENERATE AT REGISTRATION`
marker naming this brief.** A registration-day operator finding a patch that
silently fails to apply is a foreseeable, preventable incident.

**Also check in the same landing:** the owner-gate packet
`reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md:55` states the flip
is "only `exact_session_source_active=True`, `h7_active=True`, and matching
tests" — a **two-flag assumption** that is no longer complete once
`ritual_data_phase_active` exists. Update that line, or the registration-day
operator will flip two flags and be surprised by a third.

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
| 1b | `export OPTIONS_VALIDATOR_CACHE_ROLE=publisher` (89) | nothing directly — **grants cache-publisher authority for the whole process** | no | **data** (see least-privilege note) |
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
| 18 | `git add` (385) / `git commit` (391) | Git index + history on `main` | no | **data** (tier-scoped allow-list, §6.4) |
| 18b | `git fetch` (402) / **`git merge -q --no-edit origin/main` (403)** / `git push` (404) | **`git merge` mutates the working tree and creates a merge commit** | no | **data** (see below) |
| 19 | `restic backup` (417) | restic repository | no | **data** |

**Row 18b, `git merge`, is a data-tier mutation surface (NEW in rev-2.1 —
caution C-i).** rev-2's inventory listed "`git add/commit/push`" and silently
omitted the `git merge --no-edit` at `:403`. It is the most consequential verb
in that block: it can rewrite tracked files in the working tree and create a
commit, and it runs **unattended**, fail-soft, with no allow-list scoping at
all (unlike `git add`, which is allow-listed). It must be (a) named in the
§6.1 tier table — done here, (b) present in the closure test's mutation-verb
registry — §8.1, and (c) behind the `require-data` gate like every other
mutation surface. Nothing in this spec changes its behavior; the fix is that it
stops being invisible.

**Row 1b least-privilege note (NEW in rev-2.1 — caution C-k).**
`OPTIONS_VALIDATOR_CACHE_ROLE=publisher` is exported at `:89`, unconditionally,
for the **entire remaining process** — every step in this table inherits it.
`data/thetadata_adapter.py` independently re-verifies the role, repo root,
branch, and `origin/main` identity before any OOS-cache or `BLIND_CACHE` fact
mutation, so the export alone writes nothing. It is classified **data tier**
here, which is the honest reading (the guard is fail-closed at the point of
use, not at the point of export) and matches its current position ahead of
everything.

Least-privilege observation, recorded not fixed: under Option B **no data-tier
step needs publisher authority** — the only publisher-gated writer is the
ThetaData cache path, which OD-2/OD-4 forbid and which no data-tier step
reaches. Narrowing the export to the `require-full` region would be strictly
tighter. rev-2.1 **declines to change it in this landing** because it is not on
the critical path to what the owner asked for, and because moving a
process-wide environment export in the same change set that restructures both
gates multiplies the ways a mistake hides. It is written into
`ideas-parking-lot.md` instead, and the tier table now makes the grant visible
to the next reader.

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
`RITUAL STATUS: BLOCKED BY TRACKED AUTHORITY (data phase)`).

**TWO full-tier regions, not one (CORRECTED in rev-2.1 — blocker B-4).** rev-2
said "wrap the entire region from step 3 through the end of the `GATE_GO`
block". That instruction is **wrong and would break the switch-on**: the
literal region `:113`–`:340` contains the data-tier steps in the middle of it —
`qm_dashboard --refresh-ohlcv` (`:235`) and **both** `features.build_all` calls
(`:249` and `:252`). Wrapping them in the `require-full` fence would pause the
only steps that actually produce anything under the data tier, leaving a
"switch-on" that switches nothing on. The H7 surfaces are **not contiguous**;
they occupy two disjoint regions with a data-tier island between them.

The fence is therefore applied **twice**, to these exact regions:

| Region | Lines (at `c96ed4b`) | Contents | Gate |
| --- | --- | --- | --- |
| **Full-tier region A** | `:113` – `:216` | `EXPECTED_*_RECEIPT` vars, `h7_source_health` (`:115`), `h7_data_gate` (`:140`), the `GATE_GO` verdict read (`:154-173`), `evaluation session` note (`:174`), `h7_exit_session fill` (`:191`) and `monitor` (`:202`), `H7_EXIT_READY` | inside `require-full` |
| **Data-tier island — MUST STAY OUTSIDE THE FENCE** | `:218` – `:258` | comment block, `qm_dashboard --refresh-ohlcv` (`:235`), `features.build_all` ×2 (`:249`, `:252`) and their `else` branch | runs under `require-data` |
| **Full-tier region B** | `:260` – `:340` | the whole `if [ "$GATE_GO" -eq 1 ]` block: `h7_watch` (`:263`), `h7_entry_preflight` (`:279`), and steps 10-14 (`h6_features` `:293`, `h6_watch` `:294`, `entry_watch` `:312`, `h8_watch` `:325`, `h10_watch` `:335`, `h10_observe` `:336`) per D-1 | inside `require-full` |

Evaluate the gate **once**, before region A, and reuse its return code for both
regions — a single subprocess, two `if` blocks:

```zsh
env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority require-full
FULL_AUTHORITY_RC=$?

# ---- full-tier region A (:113-:216 at c96ed4b) ----
if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then
  ...source health, data gate, GATE_GO verdict, h7 exit fill/monitor...
else
  GATE_GO=0
  H7_EXIT_READY=0
  note "H7 lanes: PAUSED — full ritual authority not granted (h7_active / exact-session source)"
fi

# ---- data-tier island (:218-:258) — UNFENCED, runs every day ----
...qm_dashboard --refresh-ohlcv; features.build_all x2...

# ---- full-tier region B (:260-:340) ----
if [ "$FULL_AUTHORITY_RC" -eq 0 ] && [ "$GATE_GO" -eq 1 ]; then
  ...h7_watch, h7_entry_preflight (+10-14 per D-1)...
elif [ "$FULL_AUTHORITY_RC" -ne 0 ]; then
  note "H5/H6/H8/H10 lanes: PAUSED — gated behind the H7 data gate; see brief 11 §6.1"
fi
```

`GATE_GO=0` and `H7_EXIT_READY=0` must be set explicitly in the `else` of
region A: region B and the capture receipt both read them, and an unset
variable under a paused tier is exactly the class of silent-success bug this
brief exists to avoid.

**Frozen operator order is preserved byte-for-byte in relative order.** The
order fixed by `tools/daily_ritual.sh:2-10` — H7 amendment v1.4 (2026-07-14:
source health → data gate HARD → h7 exit management) and the 2026-07-24
`H10_RITUAL_ORDER_FIX` (QM OHLCV refresh and attractiveness feature rebuild
moved **ahead of** `h10_watch`/`h10_observe` and `entry_watch`, because each
consumer was running before its own data refresh and producing false
DATA/stale-IV-rank skips) — is **unchanged by this restructure**. The two-region
fence adds `if`/`fi` lines around existing blocks and moves **no step relative
to any other step**. Region A stays before the island; the island stays before
region B; within each, the sequence is untouched. Any implementation that
reorders a step to make the fencing tidier has broken a frozen order recorded
in `facts.log` and must be rejected in review.
`tests/test_h7_daily_exit_order.py` is the standing guard on this and must
still pass without weakening its assertions (§8.1).

**Requirement:** when `require-full` refuses, both fenced regions must be
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
* **The human label changes — and the mechanism is specified, not implied
  (rev-2.1 — caution C-d).** rev-2 said the title flips when "the only CRITICAL
  line is the capture-receipt line", but today's `crit()`
  (`daily_ritual.sh:63`) only sets a boolean `CRITICAL=1` and appends text to
  `$SUMMARY`. There is no way to ask "how many CRITICALs, and which one" — so a
  naive implementation would grep `$SUMMARY`, and **any future CRITICAL whose
  text happens to contain "capture receipt" would silently downgrade a
  genuinely broken run to `[DATA-STARVED]`**. That is a mislabeled alert on the
  one class of day it matters. Required mechanism instead — two additions, both
  shell-only:

  ```zsh
  CRITICAL=0
  CRIT_COUNT=0
  STARVED_CRIT=0          # set ONLY at the capture-receipt call site
  crit() { CRITICAL=1; CRIT_COUNT=$((CRIT_COUNT + 1)); note "CRITICAL: $1"; }
  ```

  At the capture-receipt call site (`:350-353`) **only**, the failure branch
  additionally sets `STARVED_CRIT=1` alongside its `crit`. The title rule is
  then a pure counter comparison, with no text matching anywhere:

  ```zsh
  if [ "$CRITICAL" -eq 1 ]; then
    if [ "$DATA_STARVED" -eq 1 ] && [ "$STARVED_CRIT" -eq 1 ] && [ "$CRIT_COUNT" -eq 1 ]; then
      TITLE="[DATA-STARVED] $TITLE"
    else
      TITLE="[BROKEN] $TITLE"
    fi
  fi
  ```

  **The invariant, stated so review can check it:** the summary line logic must
  never relabel a genuinely CRITICAL run as merely starved. `CRIT_COUNT -eq 1`
  is what enforces it — the instant a second CRITICAL exists from any source,
  `[BROKEN]` wins, regardless of what any line says. Two acceptance tests
  (§10) pin this: `test_starved_label_requires_single_capture_critical` and a
  mutation test M7 that adds a second `crit` and asserts the title reverts to
  `[BROKEN]`. This is a display-only distinction in the shell; nothing on disk
  and no exit code changes.
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

**Bar S1 — RECOMMENDED (LLM-proposed 2026-08-14; owner ratification required).**
**Restated in rev-2.1 in artifact-measurable terms (caution C-f).** rev-2's
version contained conditions no artifact can settle — "unattended LaunchAgent
fires, not manual wrapper runs" and "no re-auth inside the span" are not
recorded anywhere on disk today, so an operator checking the bar would be
asserting them from memory. A bar you cannot check is not a bar. Each condition
below is either measurable from a named artifact, or dropped, or given the
provenance field that would make it measurable.

1. **MEASURABLE — three consecutive scheduled trading sessions verify.** Three
   preclose capture receipts exist for three consecutive sessions on the
   session calendar, each verifying offline via
   `tools/schwab_chain_manifest.verify_session` for the full registered watch
   universe. Artifact: the three receipts under `reports/schwab_chains/`.
   Checked by running the verifier, not by reading a log.
2. **MEASURABLE — no forced capture in the span.** No receipt in the span
   carries the forced-capture marker. Forced captures are already refused as
   gate evidence by design, so this is a receipt-field check.
3. **PROVENANCE FIELD REQUIRED — unattended vs manual.** No artifact currently
   distinguishes a LaunchAgent fire from a manual wrapper run. Two honest
   options, owner's choice as part of D-4:
   * **(3a) Add the field.** The capture receipt gains an
     `invocation_source` field with values `"launchd"` / `"manual"`, set from
     an environment marker the plist sets and the wrapper does not. Then the
     condition is checkable. **Landing constraint:** the receipt writer lives
     under `options_researcher/`, which is **inside `diagnostic_source_hash`**
     (§2) — so this is a hashed-file change and must land with the same
     out-of-session discipline as §11, batched with other
     `options_researcher/` work rather than dripped in.
   * **(3b) Drop the condition.** Accept that the bar cannot distinguish the
     two, and rely on conditions 1, 2 and 4. Weaker, but honest.
   rev-2.1 does **not** choose; it refuses to leave an uncheckable condition
   standing as if it were checkable.
4. **DROPPED AS WRITTEN — "zero operator intervention / no re-auth in the
   span".** Re-auth count is not recorded anywhere; the condition was
   unverifiable. What survives it, and is measurable: **condition 1 already
   fails if a session is missed**, and a refresh-token expiry produces exactly
   that — a missing session. The 7-day Schwab refresh-token expiry documented
   in `docs/2026-08-04-underlying-closes-source-decision.md` is therefore
   already caught by condition 1 for any span it actually breaks. If the owner
   wants the stronger claim, it needs the same treatment as 3a: a recorded
   field, not an operator's recollection.
5. **MEASURABLE — the job is loaded and last exited 0.**
   `launchctl list com.carsyn.options-validator.schwab-chain-preclose` output
   captured verbatim into the flip commit's provenance note.

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
> byte index of the first occurrence of **every** H7 surface in the script,
> where "H7 surface" means a **`python -m <module>` invocation site** whose
> module is in `H7_TIER_SURFACES`. Import-probe and value-resolution
> `python -c` sites are **not** H7 surfaces for P2 — see the explicit
> classification in §8.1.
>
> **P3 (tier ordering).** `status` precedes `require-data`, and `require-data`
> precedes `require-full`. The `status` mode `exec`s and therefore reaches no
> gate; no other mode may bypass either gate.
>
> **P4 (closure).** Every `python -m` invocation site, every `python -c`
> invocation site, and every mutation verb present in the script is classified
> in exactly one of the **three** registries the test declares, each with its
> **own matcher**. An unclassified surface fails the test. A test that only
> checks a hand-written list of tokens is vacuous the moment a new step is
> added; P4 is what makes P1 and P2 binding over time.
>
> *(P2 and P4 corrected in rev-2.1 — blockers B-1 and B-2. rev-2's P4 said "two
> registries" while §8.1 declared three, ignored `python -c` entirely, and
> compared module names against verb strings in one set. As written it could
> not pass.)*

### 8.1 Exact test rewrites in `tests/test_daily_ritual_provenance.py`

**Rewritten in rev-2.1 (blockers B-1, B-2, B-7; caution C-a).** rev-2's version
was not implementable: it declared three registries but P4 said two; it mixed
module names and shell-verb strings into sets that were then compared to a
module regex's output; it listed `options_researcher.features` as if it were a
`python -m` site when it is a `python -c` site; and it left the seven
`python -c` sites and the gate's own `python -m` sites unclassified, so the
closure test would have failed on the unmodified script.

#### Three registries, three matchers — they are never compared to each other

Each registry is extracted from the script by **its own** regex and compared
only against **its own** extracted set. This is the coherence fix (B-2f).

| Registry | Matcher (regex over the script text) | Compared against |
| --- | --- | --- |
| `MODULE_SITES` | `python -m ([A-Za-z0-9_.]+)` — matches only `"$UV" run python -m …`; the gate's own `"$PYTHON" -m` sites do **not** contain the literal `python -m` and are handled by `GATE_SITES` below | union of `DATA_TIER_MODULES + H7_TIER_SURFACES + GATE_GO_SURFACES` |
| `DASH_C_SITES` | `python -c` occurrences, each keyed by its 1-based line number | `PYTHON_DASH_C_CLASSIFICATION` keys |
| `MUTATION_VERBS` | one regex per verb string, each occurrence keyed by line number | `MUTATION_VERB_SITES` |

```python
# ---- registry 1: `python -m <module>` invocation sites -------------------
DATA_TIER_MODULES = (
    "options_researcher.ritual_status",          # :107 RUNNING and :368 terminal
    "options_researcher.qm_dashboard",           # :235
    "options_researcher.dashboard",              # :344
    "options_researcher.attractiveness_dashboard",  # :345
    "options_researcher.ritual_receipt",         # :350
)
H7_TIER_SURFACES = (
    "options_researcher.h7_source_health",       # :115
    "options_researcher.h7_data_gate",           # :140
    "options_researcher.h7_exit_session",        # :191 fill, :202 monitor
    "options_researcher.h7_watch",               # :263
    "options_researcher.h7_entry_preflight",     # :279
)
GATE_GO_SURFACES = (   # membership per owner decision D-1
    "options_researcher.h6_features",            # :293
    "options_researcher.h6_watch",               # :294
    "options_researcher.entry_watch",            # :312
    "options_researcher.h8_watch",               # :325
    "options_researcher.h10_watch",              # :335
    "options_researcher.h10_observe",            # :336
)
GATE_SITES = ("data.ritual_authority",)          # :37, :47 — the gate itself
```

Three corrections inside registry 1, each a rev-2 defect:

* **`options_researcher.features` is REMOVED from this registry.** It is
  invoked via `python -c` at `:249` and `:252`, never `python -m`. Left where
  rev-2 put it, the closure test's `MODULE_SITES` comparison fails on the
  unmodified script — the registry claims a module the regex can never
  extract. It is classified in registry 2 instead.
* **`h7_exit_session fill` / `h7_exit_session monitor` collapse to the module
  name.** The regex captures `[A-Za-z0-9_.]+`, which stops at the space before
  the subcommand. Two-token entries never match. Subcommand ordering
  (fill-before-monitor) is `tests/test_h7_daily_exit_order.py`'s job, not this
  test's.
* **`--status RUNNING`, `'mkdir -p "$LOGDIR"'`, `git add --` and
  `restic backup` are REMOVED** from the module registry. They are shell verbs,
  not modules; they belong to registry 3. `ritual_status` (the module behind
  both `--status` flags) is what registry 1 tracks.

#### Registry 2 — every `python -c` invocation site, classified (B-1, B-2b)

All seven sites, verified at `c96ed4b`. Keyed by line number so a moved or
added site fails closed.

```python
PYTHON_DASH_C_CLASSIFICATION = {
    98:  "DATA_TIER_PERMITTED",   # AS_OF via options_researcher.h7_watch.evaluation_session
    99:  "DATA_TIER_PERMITTED",   # SCOPE_ID via options_researcher.h7_scope.scope_identity
    156: "FULL_TIER",             # research.receipts.load_receipt — reads the gate receipt
    249: "DATA_TIER",             # options_researcher.features.build_all (watch universe)
    252: "DATA_TIER",             # options_researcher.features.build_all (display extras)
    323: "FULL_TIER_PROBE",       # `import options_researcher.h8_watch` availability probe
    334: "FULL_TIER_PROBE",       # `import options_researcher.h10_watch` availability probe
}
```

**Line 98 is explicitly data-tier-permitted, and this is the whole point of
B-1.** `:98` imports `options_researcher.h7_watch` to call
`evaluation_session(date.today())`. A naive H7 matcher that greps the script
for the substring `h7_watch` would see it, conclude an H7 surface appears at
byte index 98 — **before** the `require-full` gate — and fail P2 on a correct
script. The classification is not a convenience; it is what makes P2 pass on a
correct implementation and fail on a wrong one.

The justification, and the rule to apply to future sites: `:98` **reads a
session calendar and mutates nothing** — no receipt, no ledger, no cache, no
network. Same for `:99` (`h7_scope.scope_identity` returns an identity dict).
Both resolve values the data tier itself needs: `AS_OF` gates the
`ritual_status` marker, the QM OHLCV refresh, both feature builds, and the
capture receipt. Fencing them behind `require-full` would blank `AS_OF` under
the data tier and skip the entire data phase — the same class of error as B-4.

`:323` and `:334` are **availability probes** (`import x` inside
`if …; then`), inside full-tier region B, and mutate nothing; they are
classified `FULL_TIER_PROBE` so their position is asserted but they are never
required to be absent under the data tier — the enclosing `if` already skips
them.

**The P2 matcher rule, stated once so it cannot be re-derived wrongly:**
*provenance tests match `python -m <module>` invocation sites only.* A
`python -c` site is never an H7 surface for P2, regardless of what it imports.
Its classification lives in registry 2 and is asserted there.

#### Registry 3 — every mutation verb site (B-2e)

All occurrences, verified at `c96ed4b`, keyed by line number.

```python
MUTATION_VERB_SITES = {
    'mkdir -p "$LOGDIR"':      (55,),    # data tier
    'mkdir -p "$PF_RECEIPT_DIR"': (278,), # full tier (region B)
    "mkdir -p reports/h5":     (311,),   # full tier (region B, GATE_GO)
    "mkdir -p reports/h8_forward": (324,), # full tier (region B, GATE_GO)
    "git add --":              (385,),   # data tier, allow-list scoped (§6.4)
    "git commit":              (391,),   # data tier
    "git fetch":               (402,),   # data tier  -- ADDED in rev-2.1
    "git merge --no-edit":     (403,),   # data tier  -- ADDED in rev-2.1 (C-i)
    "git push":                (404,),   # data tier
    "restic backup":           (417,),   # data tier
}
```

rev-2 named a single `mkdir -p "$LOGDIR"` and omitted three other `mkdir`
sites, plus `git fetch` and `git merge --no-edit` entirely. All four `mkdir`
sites and both git verbs are now enumerated. `git merge` in particular mutates
the working tree unattended (§6.1 row 18b).

#### The closure test, made coherent (B-2f)

`test_every_script_surface_is_classified` performs **three separate
comparisons**, never one merged set:

```python
self.assertEqual(set(module_sites),
                 set(DATA_TIER_MODULES + H7_TIER_SURFACES + GATE_GO_SURFACES))
self.assertEqual(set(dash_c_lines), set(PYTHON_DASH_C_CLASSIFICATION))
self.assertEqual(dict(verb_lines), MUTATION_VERB_SITES)
```

`GATE_SITES` is asserted separately (P3's ordering test already pins `:37` and
`:47`) and is **excluded** from the module comparison: `data.ritual_authority`
is the gate, not a gated surface, and requiring it to precede itself is
incoherent. Note it is also invoked as `"$PYTHON" -m`, not
`"$UV" run python -m`, so the `python -m` regex does not capture it — the
exclusion and the matcher agree, and the test must assert both facts rather
than relying on the regex accident.

| Test | Replaces / new | Asserts |
| --- | --- | --- |
| `test_require_data_precedes_every_mutation_surface` | replaces `test_authority_preflight_precedes_every_mutation_surface` | P1 over `DATA_TIER_MUTATIONS + H7_TIER_SURFACES + GATE_GO_SURFACES` |
| `test_require_full_precedes_every_h7_surface` | new | P2 over `H7_TIER_SURFACES` (+ `GATE_GO_SURFACES` under F1) |
| `test_tier_ordering_status_then_data_then_full` | replaces `test_status_mode_is_read_only_and_bypasses_full_authority_requirement` and `test_authority_commands_use_installed_python_without_uv_sync` | P3, plus the retained assertions `PYTHON="$REPO/.venv/bin/python"`, `PYTHONDONTWRITEBYTECODE=1 "$PYTHON"`, and `assertNotIn('$UV" run python -m data.ritual_authority')` |
| `test_every_script_surface_is_classified` | **new — the closure test** | P4 via the **three separate comparisons** above: `MODULE_SITES` vs the union of the three module registries; `python -c` line numbers vs `PYTHON_DASH_C_CLASSIFICATION`; mutation-verb line numbers vs `MUTATION_VERB_SITES`. Fails on any unclassified addition, in any of the three categories. |
| `test_dash_c_sites_are_classified_and_data_tier_ones_are_unfenced` | **new (B-1/B-2b)** | `:98` and `:99` are `DATA_TIER_PERMITTED` and appear **before** the `require-full` gate; `:249`/`:252` are `DATA_TIER` and lie **outside** both fenced regions; `:156` lies inside region A; `:323`/`:334` lie inside region B |
| `test_data_tier_island_is_outside_the_full_fence` | **new (B-4)** | the byte indices of `qm_dashboard --refresh-ohlcv`, and of both `features.build_all` calls, lie **outside** full-tier regions A and B — the direct regression guard on rev-2's wrong single-wrap instruction |
| `test_frozen_operator_order_is_preserved` | **new (B-4)** | relative order unchanged: `h7_source_health` < `h7_data_gate` < `h7_exit_session fill` < `h7_exit_session monitor` < `qm_dashboard` < `features.build_all` ×2 < `h7_watch` < `h6_features` < `h6_watch` < `entry_watch` < `h8_watch` < `h10_watch` < `h10_observe` < `dashboard` |
| `test_authority_gate_replaces_provider_topup_dependency` | amended | first index becomes `require-data`; ordering `require-data < require-full < h7_source_health < h7_data_gate`; keeps `assertNotIn("H7_DATA_READY")` |
| `test_status_preserves_log_tree_and_lockfile_bytes` | amended | unchanged behaviour; the `assertIn('"ready": false', stdout)` assertion is updated for the new combined-tier `status` JSON |
| `test_ops_publisher_requires_current_main` | unchanged | branch guard < origin/main guard < publisher role < source health |
| `test_durability_allow_list_is_tier_scoped` | replaces `test_durability_allow_list_includes_schwab_ledger_and_reports` | the H7 paths (`ledger/h7_forward`, `ledger/h7_forward_schwab`, `reports/h7_receipts`, `reports/h7_data_gate`, `reports/h5`, `reports/h6_forward`, `reports/h8_forward`, `reports/h10`, `reports/schwab_chains`) appear only inside the `FULL_AUTHORITY_RC -eq 0` branch; `reports/ritual` is added unconditionally |
| `test_paused_lanes_are_noted_not_critical` | new | when `require-full` refuses, **both** else-branches (region A and region B) contain `note` and contain no `crit` |
| `test_starved_label_requires_single_capture_critical` | **new (C-d)** | the `[DATA-STARVED]` title requires `DATA_STARVED`, `STARVED_CRIT` and `CRIT_COUNT -eq 1`; no text matching on `$SUMMARY` appears in the title logic |
| `test_h5_h6_h8_h10_failure_lines_stay_critical` | keeps `test_h6_and_h8_nonzero_results_are_critical`, `test_h5_rerun_failure_is_critical_before_terminal_publish`, `test_h10_rerun_failures_are_critical_before_terminal_publish` | unchanged text assertions, re-verified against the restructured script |
| `test_ritual_terminal_status_is_separate_from_capture_receipt` | unchanged | RUNNING < capture < terminal < durability |

#### The other test modules that bind `daily_ritual.sh` text (caution C-a)

rev-2's inventory covered only `tests/test_daily_ritual_provenance.py` and
`tests/test_ritual_authority.py`. Four **other** modules read the script's text
and assert on it; the restructure in §6.2 will move the byte offsets they
depend on. All four must be run and, where they break, corrected **without
weakening an assertion** — each exists because of a real past incident:

| Module | Binding sites | Why it exists / what to preserve |
| --- | --- | --- |
| `tests/test_h7_daily_exit_order.py` | `:12` reads the script; assertions at `:16-24`, `:56-70`, `:98-111` | The frozen exit-management order (H7 amendment v1.4). This is the standing guard on §6.2's "operator order preserved byte-for-byte in relative order" clause — if it fails, the restructure reordered something and **the restructure is wrong**, not the test |
| `tests/test_qm_dashboard.py` | `:451-455` (`Path("tools/daily_ritual.sh").read_text()`) | Pins the QM OHLCV refresh's position/invocation. Directly affected: §6.2 moves the `if`/`fi` around `:235` |
| `tests/test_shell_banner_guard.py` | `:107`, `:117`, `:126` (script in the guarded list); rationale at `:43`, `:335`, `:381` | The LumiBot import-banner pollution guard (2026-07-23 `ef4b3f5`, 2026-07-24 `42ae8c8`). Any new shell capture added by the restructure must not reintroduce banner capture |
| `tests/test_h8_watch.py` | `:635-636` (`test_daily_ritual_passes_out_path_without_shell_redirection`) | The 2026-07-23 H8 `--out`-not-`tee` fix. `:325` must keep passing `--out` and must not gain a redirection |

#### `tests/test_ritual_authority.py` rewrites

Keep `test_tracked_authority_module_exists`; extend
`test_module_exposes_readiness_and_cli_interfaces` to require
`evaluate_data_phase`; replace the readiness tests with a matrix over the eight
flag combinations asserting (a) data tier ready iff `ritual_data_phase_active`,
(b) full tier ready iff all three, (c) **monotonicity** — full ready implies data
ready, for every combination, (d) the preserved blocker substrings
`"exact-session"`, `"H7"`, `"ThetaData"` on the full tier.

`test_status_succeeds_but_require_modes_refuse` covers all three CLI modes,
their exit codes, and the stdout contract in §5. **It passes an explicitly
constructed `RitualAuthority` through `main(..., authority=…)`** — the B-7
injection seam — so it asserts behavior at named flag combinations, never at
whatever `CURRENT_AUTHORITY` currently holds. Every case constructs its own
`RitualAuthority`: **no test may read `CURRENT_AUTHORITY` and assert a specific
flip state**, or the flip commit (§12 D-2) breaks the suite. The retired
`assertEqual(required, status)` is replaced by the two sub-object assertions
specified in §5.

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

> **R2 is currently unenforced, and it already failed once (rev-2.1 — caution
> C-e).** On 2026-08-14, PR #36 merged at 10:28:03 ET and ops was realigned at
> 14:28:10 ET — four hours behind `origin/main`, undetected. Whether R2 becomes
> a mechanism or stays a hope is **owner decision D-6** (§12). Note the failure
> direction: §9.2 below covers ops being **ahead**; D-6 covers ops being
> **behind**, which is what actually happened.

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
5. `test_status_succeeds_but_require_modes_refuse` — **exit codes asserted
   against explicitly constructed authorities passed via
   `main(argv, authority=…)`, never against `CURRENT_AUTHORITY`** (rev-2.1,
   blocker B-7; rev-2's "at the pre-flip defaults" contradicted §8.1). With
   an all-`False` authority: 0 / 1 / 1 for `status` / `require-data` /
   `require-full`. With `ritual_data_phase_active=True` only: 0 / 0 / 1. With
   all three `True`: 0 / 0 / 0. `status` JSON contains both tiers and all three
   flags, per the §5 stdout table.
6. `test_require_mode_stdout_matches_status_sub_objects` — **new (B-7)**:
   `require-data` stdout equals `status["data_phase"]` and `require-full`
   stdout equals `status["full_ritual"]`, for the same injected authority.
   This is the defined replacement for the retired
   `assertEqual(required, status)`.
7. `test_all_modes_are_side_effect_free` — no file created/modified under the
   repo root by any mode.

**Provenance (`tests/test_daily_ritual_provenance.py`)** — the full table in §8.1.
The load-bearing ones: `test_require_data_precedes_every_mutation_surface`,
`test_require_full_precedes_every_h7_surface`,
`test_every_script_surface_is_classified` (closure),
`test_dash_c_sites_are_classified_and_data_tier_ones_are_unfenced`,
`test_data_tier_island_is_outside_the_full_fence`,
`test_frozen_operator_order_is_preserved`,
`test_durability_allow_list_is_tier_scoped`,
`test_paused_lanes_are_noted_not_critical`,
`test_starved_label_requires_single_capture_critical`.

**Hash containment (new, `tests/test_ritual_switch_on_hash_containment.py`)**
8. `test_config_hash_surface_unchanged` — the set of uppercase names in
   `config.py` equals a frozen tuple checked into the test, and
   **`config.INTRADAY_CAPTURE_TIMES` has exactly its FIVE existing keys**
   (rev-2.1, blocker B-6 — rev-2 said four). Verified at `c96ed4b`,
   `config.py:755-761`, the keys are exactly:
   `open_auction` (09:31), `open` (09:35), `midmorning` (11:00),
   `midday` (13:00), `preclose` (15:45). The test asserts the **key set**, not
   just the count, so a rename is caught as loudly as an addition. This is
   blocker B8's standing guard: any future capture-tag work that adds a config
   entry fails here first, in a test whose name says why. *(A spec that told
   the implementer to assert `len(...) == 4` would have shipped a test that
   fails on the unmodified repo — and the likely "fix" is deleting
   `preclose`, the 15:45 key the entire Schwab capture lane runs on.)*

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
* **M7 (new, C-d)** — add a second, unrelated `crit` line to the run →
  notification title reverts from `[DATA-STARVED]` to `[BROKEN]`. Guards the
  invariant that a genuinely CRITICAL run is never relabeled as merely starved.
* **M8 (new, B-4)** — move `qm_dashboard --refresh-ohlcv` or either
  `features.build_all` call inside a `require-full` region →
  `test_data_tier_island_is_outside_the_full_fence` fails. This is the direct
  regression test for rev-2's single-wrap error.
* **M9 (new, B-1)** — reclassify `daily_ritual.sh:98` as an H7 surface (or
  broaden the P2 matcher from `python -m` to a bare `h7_` substring) → P2
  fails on the correct script. Proves the matcher is specified, not accidental.
* **M10 (new, B-2)** — add a `git merge` or a fourth `mkdir -p` site without
  registering it → closure test's verb comparison fails.

**End-to-end smoke (manual, after the flip, once):** run
`zsh tools/daily_ritual.sh status` (must stay byte-preserving, exit 0), then a
single supervised `zsh tools/daily_ritual.sh run` from ops, and confirm: log
written; cache-edge note present naming 2026-07-27; H7 lanes noted as PAUSED with
no CRITICAL; **the data-tier island actually ran** — `qm_dashboard
--refresh-ohlcv` and both `features.build_all` calls appear in the log with
their `note` lines (rev-2.1, blocker B-4: this is the observable that rev-2's
single-wrap instruction would have silently destroyed); both dashboards
rebuilt; capture receipt written with all five hypothesis lanes
(H5/H6/H7/H8/H10) MISSING; terminal status `BROKEN`; notification titled
`[DATA-STARVED]` with exactly one CRITICAL line (`CRIT_COUNT == 1`);
**`.cache/underlying_ohlcv` shows fresh mtimes for the watch universe while
`.cache/underlying` is unchanged** (rev-2.1, caution C-h);
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
4. **Timing constraint — CORRECTED in rev-2.1 (blocker B-5).** rev-2 required
   landing "outside the trading session" and justified it with four modules,
   three of which bind `config_hash`, not `diagnostic_source_hash` (§2's
   corrected table). The accurate rule has two regimes:

   * **Now, while `ritual_data_phase_active` is the only live tier:** the six
     `diagnostic_source_hash` refusal sites are **all H7 surfaces behind the
     `require-full` fence**, and they are not running. `intraday_capture` /
     `intraday_preview` / `h7_schwab_window_registration` bind `config_hash`,
     which this change set does not touch. So the binding constraint is only
     **"do not land while a 07:10 ritual run is in flight"** — any time outside
     a ritual run is safe, including mid-session. The out-of-session rule is
     not required today and should not be stated as if it were; an invented
     constraint gets worked around, and the worked-around habit outlives it.
   * **After `h7_active` flips (registration day onward):** the six refusal
     sites go live, and the strict rule binds — land **outside the trading
     session**, before the session's first receipt or after its last, never
     between two receipts of the same session.

   Independent of both: a bump to `pyproject.toml` or `uv.lock` also changes
   `diagnostic_source_hash` (§2). Do not batch a dependency change into a
   post-registration landing on the assumption that "no `.py` changed" means
   "no hash changed".
5. Merge to `origin/main`; **immediately apply rule R1** (§9.1) to both ops and
   research; verify both HEADs equal `origin/main`.
6. Confirm the daily-ritual LaunchAgent is loaded
   (`launchctl list | grep options-validator`). Caution C4's disposition: this
   spec adds **no new plist**, so no `launchctl bootstrap` is required — but the
   existing job has not produced a run since 2026-07-28 and must be confirmed
   loaded, not assumed. **Conditional (rev-2.1, caution C-e):** if the owner
   picks **D-6a**, this step also installs a new pre-15:45 alignment-check
   plist, which *does* require an owner `launchctl bootstrap` (the classifier
   denies Claude) and is therefore an owner-blocking step, not an agent one.
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

  > **⚠ The cheap rollback stops being cheap after registration day (rev-2.1 —
  > caution C-b).** The three-flag design is deliberately **monotone**:
  > `require-full` requires all three flags, so `ritual_data_phase_active` is a
  > **master switch**, not a data-only switch. Today, flipping it back to
  > `False` costs nothing but display freshness, because the H7 lanes are
  > already paused. **Once `h7_active` is `True` and a forward window is live,
  > flipping `ritual_data_phase_active=False` also stops that live window's
  > daily evidence** — source-health receipt, data-gate receipt, watcher
  > receipt, exit fill/monitor — because the data gate fences the whole
  > `require-full` region. Each missed session is an irreplaceable gap in a
  > verdict-bearing record. Post-registration, this is an
  > incident-response-grade action, not a one-line convenience, and it must be
  > recorded with the sessions it skipped. If a data-only pause is ever wanted
  > post-registration, that needs a non-monotone design with its own review —
  > it does not exist today and must not be improvised under pressure.

* **Emergency, no merge available:** `launchctl bootout` the daily-ritual job in
  ops. The ritual cannot then run at all; nothing else depends on it. The same
  post-registration warning applies with equal force.
* **Full revert:** `git revert` the D1-D4 commit range. Nothing in this change set
  writes an immutable receipt, a ledger entry, or any append-only record, so a
  revert leaves no orphaned state. The only side effects a data-tier run can
  leave behind are `reports/ritual/*` artifacts, **`.cache/underlying_ohlcv`
  top-ups for the 9-name watch universe** (the closes store `.cache/underlying`
  is never written by the ritual and stays frozen — §3 deliverable 2),
  feature-store rebuilds, and `.tmp/dashboard` output — all regenerable, none
  verdict-bearing.
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

**Recommendation: S1**, as restated in artifact-measurable terms in rev-2.1
(caution C-f). LLM-proposed threshold ("three consecutive"), not an owner-typed
number — ratification requested. Not needed for D-2; needed before any future
flip of that flag.

**A sub-decision rides on this one (rev-2.1):** S1's condition 3
(unattended-vs-manual provenance) is **not measurable from any artifact that
exists today**. Ratifying S1 therefore also means choosing **3a** (add an
`invocation_source` field to the capture receipt — a hashed-file change under
`options_researcher/`, so it must be batched and landed per §11's discipline)
or **3b** (drop the condition and rely on conditions 1, 2 and 5). rev-2's
condition 4 ("no re-auth in the span") is dropped as written — re-auth count is
recorded nowhere, and the failure mode it targeted is already caught by
condition 1, which fails on any missed session.

### D-5 — *(DEMOTED to a disclosure in rev-2.1 — no owner decision required)*

**The ritual's one market-data provider call.**

rev-2 raised this as an owner decision. It is not one, for two reasons found in
review:

1. **It is already ratified.** `docs/2026-08-04-underlying-closes-source-decision.md`
   is the owner-directed decision record: *"Yahoo stays primary. Schwab is NOT
   adopted for this lane."* Re-asking a settled question invites an
   accidental reversal of a decision that was made with reasoning the spec does
   not restate.
2. **rev-2's claim was too broad.** "The ritual's **one network surface**" is
   false. `tools/daily_ritual.sh` also runs `git fetch` (`:402`),
   `git merge` (`:403`), `git push` (`:404`), `restic backup` (`:417`), and
   every `"$UV" run` can hit the network on a cold cache. Those are network
   surfaces. The accurate, narrower claim is: **`qm_dashboard --refresh-ohlcv`
   is the ritual's only MARKET-DATA / PROVIDER call.**

**Disclosure, stated plainly:** `qm_dashboard --refresh-ohlcv` fetches
underlying OHLCV from the Yahoo chart endpoint
(`data/underlying_ohlcv.py:185-200`, `urllib.request`). It is **underlying
prices only** for the 9-name watch universe, restricted to frozen QM-study
members; it does not touch chains, so OD-2/OD-4 are not implicated. Switch-on
re-enables it because it re-enables the step. It stays on. This is caution C5's
disposition, and it is recorded here so "the ritual makes a provider call" is
an owner-visible fact rather than a surprise — **not** because the owner needs
to re-decide it. Owner veto remains available by amendment, as always.

### D-6 — *(NEW in rev-2.1 — caution C-e)* Intra-day "ops is behind" detection: scheduled check, manual check, or accept the risk?

**The gap.** §9.1's rule R1 says fast-forward ops immediately after any merge.
§9.2 handles the case where ops is **ahead**. Neither covers the case where ops
is **behind** for hours because R1 was simply not performed — and R1 is a human
rule with no enforcement, so "not performed" is its default failure mode.

**Today's real incident, measured, not hypothetical.** On 2026-08-14, PR #36
merged to `origin/main` at **10:28:03 ET** (`c96ed4b`). The ops checkout was
fast-forwarded at **14:28:10 ET** (ops reflog). For **four hours** ops HEAD was
behind `origin/main`. The 15:45 capture wrapper refuses on **any** divergence
between local HEAD and `origin/main` after a fetch
(`tools/schwab_chain_capture.sh`, "HEAD is not aligned with origin/main") — so
had the realignment happened an hour later than it did, that session's
irreplaceable chains would have been lost. Nothing detected the gap; it closed
because a human happened to act. R2 ("the operator confirms before 15:45")
is the same class of unenforced rule that already failed once today.

| Option | What it costs | What it buys |
| --- | --- | --- |
| **D-6a — scheduled pre-1545 alignment check** | A **new plist** — therefore a new standing configuration item requiring `launchctl bootstrap` by the owner (the classifier denies Claude), plus one more scheduled job to maintain | Detects both behind- and ahead-divergence in time to fix it; converts R2 from a hope into a mechanism |
| **D-6b — documented manual check** | Nothing to build; a numbered step in runbook 08 and `docs/h7-forward-operations.md` | Makes the check discoverable; still depends entirely on a human performing it on a day when nothing looks wrong |
| **D-6c — accept the risk** | Nothing | Honest if the owner judges lost sessions tolerable; must then be **written down** as accepted, not left implicit |

**Recommendation: D-6a**, but flagged as the owner's call precisely because it
creates a new standing scheduled job — the exact category the owner has
reserved (caution C4's original point). If D-6a is declined, D-6b is the
minimum: the risk must at least be written into the runbook rather than
surviving as tribal knowledge.

**This also reopens C4.** rev-2 disposed of C4 as "N/A — no new plist". That is
true of rev-2's own change set and remains true under D-6b/D-6c, but D-6a
**would** add a plist and an owner `launchctl bootstrap` step. §13's C4 row is
therefore conditional on this decision.

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
| B8 `config_hash()` blast radius | **Resolved by exclusion + guarded** — no `config.py` change; `test_config_hash_surface_unchanged` (§10.8) makes any future addition fail loudly, asserting the **five**-key `INTRADAY_CAPTURE_TIMES` set (rev-2.1, B-6). §2 additionally documents the *un-named* half: the `diagnostic_source_hash` surface also covers `pyproject.toml`, `uv.lock`, `metrics.py`, `analysis/`, `harness/` and `strategies/`, and §11's landing rule is corrected to the two regimes it actually has (rev-2.1, B-5) |
| C1 feasibility receipt config-hash stale | **Out of scope, unaffected** — registration-day work; this spec changes no `config.py` line, so it neither fixes nor worsens it |
| C2 supersedes runbook 08's "flip last" | **Done** — §1.2, named and owner-attributed; runbook 08 edited in the same landing |
| C3 data-phase enumeration wrong | **Fixed** — §6.1 is measured from the script; there is no closes step, no quotes step, and source health is correctly classified as an H7 receipt writer |
| C4 new plists need owner bootstrap | **CONDITIONAL on owner decision D-6** (rev-2.1, caution C-e). Under rev-2.1's own change set and under D-6b/D-6c: N/A — no new plist, and §11.6 requires confirming the existing job is loaded. Under **D-6a** it is **NOT N/A**: a pre-15:45 alignment check is a new plist and a new standing configuration item requiring the owner's `launchctl bootstrap` |
| C5 provider call-count estimate | **N/A for a capture** (none added). rev-2 escalated the existing call to owner decision D-5; rev-2.1 **demotes it to a disclosure** — already ratified in `docs/2026-08-04-underlying-closes-source-decision.md`, and the claim is narrowed from "the ritual's one network surface" to "the ritual's one market-data/provider call" (git, restic and `uv` are network surfaces too) |
| C6 commit labels morning chains as H7 evidence | **Fixed** — §6.4 tier-scoped allow-list and commit message; `test_durability_allow_list_is_tier_scoped` |
| C7 tests pass vacuously | **REOPENED in rev-2.1, then closed (caution C-j).** rev-2 claimed C7 fixed, but its own closure spec could not have passed — P4 said two registries while §8.1 declared three, the registries mixed module names with shell-verb strings in a single comparison, `options_researcher.features` was registered as a `python -m` site it is not, and the seven `python -c` sites plus four `mkdir` sites plus `git fetch`/`git merge` were unclassified. A closure test that fails on the unmodified script gets "fixed" by deleting assertions — which is vacuity arriving by the front door. **Now closed** by B-2's corrected spec: three registries with three separate matchers and three separate comparisons (§8.1), full `python -c` and mutation-verb enumeration, and mutation tests M3, M9, M10 proving the closure test bites. Carried forward as a named requirement for the deferred 10:00 spec |
| C8 guard/backup namespace coverage | **N/A** — no new namespace; `reports/schwab_chains` remains in the FULL-tier allow-list and in the irreplaceable-data guard |
| C9 factual drift | **Corrected** — §2: `data/ritual_authority.py` was created 2026-08-02 (`db3f907`). `nearest_session_tag` is untouched (no new tag) |

### 13.1 rev-2's own review — blockers B-1…B-7 and cautions C-a…C-k

Verdict **PASS WITH FIXES**. Full receipt with condensed findings and
dispositions: `reports/2026-08-14-rev2-switch-on-review-receipt.md`. Every
blocker and every caution is applied in rev-2.1; none was declined. The
change-log table at the top of this document maps each finding to the section
that discharges it.

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
