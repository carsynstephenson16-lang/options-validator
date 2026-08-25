# Codex brief 26 — board declutter: Top-5 shortlist, dominated-card collapse, compact regime view (rev 5)

**Date:** 2026-08-25 (rev 5, Wave 0 reconciliation)
**Author:** Claude orchestrating session (Fable), 2026-08-25
**Executor:** Codex (GPT-5-class), high reasoning tier
**Status:** DRAFT rev 5 — pending one focused independent review with written PASS. The owner-directed hand-off recorded by source commit `839ddb3` becomes effective only when this Wave 0 documentation PR lands after that PASS; until then canonical `main` remains DRAFT. Receipt: `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`. Landing order still binds: this brief lands FIRST (26 → 25 → 27).
**Provenance:** Repo-verified against current reconciliation base `origin/main@77b1a46` unless labeled otherwise. Round-4 parameter decisions are transplanted from `7908919`; the owner-directed hand-off is transplanted from `839ddb3`. The relevant Brief 26 implementation surfaces are unchanged from its prior `720a20e` anchor except for unrelated later `config.py` additions; all cited symbols and six slot literals were re-verified on `77b1a46`. The committed ops-input fallback remains `options_researcher/attractiveness_dashboard.py:57`. Landing order is binding: **this brief lands first, then brief 25, then brief 27.**
**Owner directive source:** Carsyn in-session 2026-08-25 ("pull up to top 5 picks each day", "wasserstein regime view needs to be fixed, there's too much information", "if the option isn't as good as another one I don't think it should be shown") — spoken, not owner-typed.

## Why this exists (plain language)

The rendered board is ~660 KB (Estimate, measured 2026-08-25; the artifact
rebuilds daily) and roughly 92% of it is 18 per-symbol panels holding 188
candidate cards, 228 tables, and 1,072 rows. Within one symbol's lane, cards
are ordered but never pruned — a card worse than a sibling on every measured
axis still renders in full. Separately, the Wasserstein regime view is
unreachable from a dev-checkout build (published only into the ops
checkout's `.tmp/dashboard/`) and verbose when reachable (full per-symbol
transition matrices for a reader who wants "what regime is each name in").

Three changes: Top-5 shortlist, dominated-card collapse (collapse, never
delete — fail-visible is repo law), and a compact regime strip with the full
report demoted to a link.

## Scope

**IN**
- WP-A: shortlist n=3 → n=5 via `config.PICK_TOP_N`.
- WP-B: within-lane dominance collapse.
- WP-C: per-symbol panels collapsed by default.
- WP-D: compact regime strip + research-views publication for non-ops builds.
- WP-E: coordinated test updates (enumerated; every break intentional).

**OUT (hard stops)**
- No change to the frozen GREEN-fraction recipe's ordering semantics:
  `_display_quality_key`, `_admissible_pick_pool` vetoes, tie-breaks, and
  one-pick-per-symbol stay behavior-identical. n changes how many winners
  DISPLAY, not how candidates are ordered or admitted.
- No ledger writes, no registration/amendment, no authority flips, no
  live-order paths, no network providers.
- The worker may create only a **draft PR**. It may not merge, deploy, sync an
  ops/research checkout, enable a flag or LaunchAgent, modify a ledger, make a
  PR ready for review, or otherwise exercise owner authority. A green draft
  remains owner-held work; it is not permission for the repository reconciler
  or any worker to land it.
- No deletion of any card from the assembled payload — pruning is
  presentation-layer collapse; `sections_json()` stays complete.
- No `options_researcher.exp_*` import into `attractiveness_dashboard.py`
  (AST test `tests/test_experiments_baseline.py:92`).
- No change to `options_researcher/regime.py` math or `config.py` REGIME_*
  constants; WP-D touches rendering/publication only.
- DATA_BLOCKED / skipped / stale states are NEVER collapsed or pruned
  (pinned: `tests/test_attractiveness_dashboard.py:1116`).

## Interlock (rev-1 findings 12, 13 corrected)

- RQ2-v1/A2-v1 do not consume top-3 membership. Correct citations: ledger
  **seq 27** (`A2_AMENDMENT_V1_1`, single clause: "TERCILES IS THE RULE;
  'top 6 versus bottom 6' is its instantiation on the current 18-name
  board") and **seq 18** ("no badge reorders the frozen GREEN-fraction
  baseline"). Repo-verified in `ledger/experiments.jsonl`.
- Brief 25 consumes `PICK_TOP_N` and inserts its (flag-gated) section after
  this brief's renamed hero heading; brief 27 records `PICK_TOP_N` picks.
  This brief owns ALL heading-string renames and the shared ordering-test
  edits; briefs 25/27 add only their own new, flag-gated tests.

## Work packages

### WP-A — Top-5 shortlist

1. `config.py`: `PICK_TOP_N: int = 5` beside the PICK_* display constants
   (`config.py:635-646` region), comment: "display-layer shortlist width;
   owner-directed in-session 2026-08-25 (spoken, not owner-typed);
   presentation only, never a strategy gate."
2. Thread it: `select_top_picks` (`attractiveness_dashboard.py:421` @720a20e)
   and `select_qm_top_picks` (`:470`) default `n=config.PICK_TOP_N`; replace
   ALL SIX slot literals (rev-1 finding 14; Repo-verified @720a20e):
   - `:3278` `for slot in range(len(py_picks) + 1, 4):`
   - `:3283` `open_count = max(0, 3 - len(py_picks))`
   - `:3348` `for slot in range(1, 4)`
   - `:3350` `selected_count, open_count = 0, 3`
   - `:3371` `for slot in range(len(cards) + 1, 4):`
   - `:3373` `selected_count, open_count = len(picks), max(0, 3 - len(picks))`
   After editing, grep `range(1, 4)|range(len(|, 4)|0, 3` in the module to
   confirm no seventh site exists at the final SHA.
3. Copy updates (this brief owns them): "TOP 3 PICKS TODAY" → "TOP 5 PICKS
   TODAY"; "Rule-based top 3" → "Rule-based top 5"; "…FOR MECHANICAL TOP 3"
   → "…FOR MECHANICAL TOP 5". Then grep user-visible "top 3"/"Top-3"/"Pick 3"
   strings; update display copy only. Identifiers (`top3_snapshot`,
   `top3_context`, schema strings) stay — renaming identity plumbing buys
   nothing.
4. Update `render()`'s page-order docstring (rev-1 finding 38; the "rule-based
   Top-3 -> movement lane" lines at `attractiveness_dashboard.py:4024`
   @720a20e — rev-2 finding N-10 corrected the line).
5. `tools/research_context_assemble.py` inherits n via `select_top_picks`
   (`:49-60,:67-69`) with no edit. The cost consequence (more research
   packets per run) is an OWNER decision surfaced in brief 25 WP-E.4 D-2 —
   not silently shipped here and not buried in a PR description.

### WP-B — dominated-card collapse (rev-1 findings 16, 17, 18, 40 applied)

1. Pure function `dominated_partition(cards, lane_kind, close)` in the
   dashboard module. Per-lane axis sets, each field Repo-verified to exist on
   that lane's cards (`options_researcher/attractiveness.py`):
   - `put` (`:223-227`): numeric axes `annualized_yield` (higher better),
     `cushion` (higher better).
   - `cc` (`:280-284`): numeric axes `annualized_yield` (higher better) AND
     `upside` (higher better) — a higher-yield card must not hide a card
     preserving materially more upside; that trade-off is the lane's point
     (rev-2 finding N-5).
   - `pmcc` (`:339-343`): EXEMPT from collapse entirely. It carries neither
     `cushion` nor `upside`; one numeric axis plus grade-dominance would
     degenerate "dominated" into "lower yield," hiding real structure
     choices. State the exemption in the function docstring.
   - `long_call` (`:421-429`): numeric axes `cost` (lower better),
     `breakeven_move` (lower better).
   - `leaps` (`:379-381`): numeric axes `cost` (lower better), breakeven
     distance `abs(breakeven - close)/close` (lower better) — `close` is the
     SECTION's close, passed in as the third argument.
   Plus grade-dominance on every lane: over badge keys present on BOTH
   cards, Y's rank ≥ X's for all (GREEN>AMBER>RED>UNKNOWN).
   **Dominance rule:** Y dominates X iff Y is equal-or-better on every
   numeric axis AND grade-dominant, AND strictly better on at least one
   numeric axis or at least one badge (single strictness clause — rev-1
   finding 40). Cards with a missing/None value on any compared axis are
   NEVER dominated (incomparable ≠ worse).
2. **Fixpoint against the retained set** (rev-1 finding 17): iterate — a card
   may be hidden only if a card that REMAINS SHOWN dominates it; recompute
   until stable. Named test: every hidden card's dominator is in the shown
   set (no hidden-by-a-hidden-card chains).
3. Exclusions from hiding (never collapsed): DATA_BLOCKED/skipped cards;
   `rank_leader` cards; Top-5 or pinned picks; **any card carrying a RED
   grade on a SAFETY badge — `liquidity` only** (rev-2 finding N-4
   correcting rev-1 finding 18: 77% of live cards carry a RED somewhere,
   dominated by `portfolio` (143/222) and `fits_cap` (53/222)
   concentration/fit flags — a blanket RED exclusion nullifies the collapse
   and defeats the owner's request; a RED on `portfolio`/`fits_cap`/
   `iv_for_buyer`/`yield`/`cushion` is an assessment, not a data-safety
   warning, and may be hidden behind the expandable block); lanes with ≤2
   candidates.
4. Rendering: hidden cards go into one collapsed `<details>` per lane,
   summary exactly: "N candidates hidden — each is matched or beaten by a
   shown card on every measure (expand to verify)". Expanding shows full
   existing card HTML unchanged; nothing leaves the DOM.

### WP-C — collapsed symbol panels

1. Wrap each per-symbol panel body in `<details>` with the symbol heading +
   one-line summary visible (close, as-of, best card headline, panel
   status). Panels containing any DATA_BLOCKED card or stale banner render
   OPEN by default; all other panels collapsed. Rev-4 design decision
   (responding to round-3 finding NEW-1, LLM-proposed 2026-08-25): a
   liquidity-RED card does NOT force its panel open — 14 of 18 live panels
   contain one, so a liquidity-open rule would nullify WP-C. The safety
   guarantee liquidity-RED keeps is WP-B.3's: such a card is never buried a
   second level down inside the dominated-cards block; a collapsed panel is
   one click from visible and its summary line states the panel status.
   Fail-visible law stays absolute for DATA_BLOCKED/stale.
2. No content change inside panels beyond WP-B.

### WP-D — regime view and generation publication (rev-1 findings 19, 20;
Wave 0 atomicity repair)

1. **Machine-readable sidecar, not text parsing:** `regime_report.py` gains a
   JSON sidecar named **`wasserstein-regime.json`** (rev-2 finding N-7):
   `{"schema": "regime_report/v1", "as_of_written": <ISO ts>, "symbols":
   {SYM: {"label", "high_dispersion", "max_asof", "skipped_reason"}}}`.
   Add `regime_report --json-out <path>` alongside its existing `--out`; the
   wrapper passes both paths inside one caller-supplied staging generation.
   Add `experiments_dashboard --out <path>` with
   `config.EXPERIMENTS_OUTPUT_PATH` preserved as its default, and have the
   wrapper pass the staging `experiments.html` path. Both CLIs use
   `main(argv: Sequence[str] | None = None)` so argument parsing is unit
   testable. A builder may leave a partial file only inside unpublished
   staging; any nonzero builder exit aborts the generation in WP-D.4. The
   report's markdown layout ALSO moves tables below a per-symbol "— details —"
   separator (latest label + dispersion + as-of stay on top). The dashboard
   never parses markdown.
2. Shared disclaimer constant: move the DISCLAIMER string to
   `options_researcher/regime_constants.py` (no heavy imports); both
   `regime_report.py` and the dashboard import it — no duplicated drifting
   string, no regime-math import into the dashboard.
3. Compact strip: new dashboard section "REGIME (descriptive)" — one line per
   `REGIME_SYMBOLS` name from the SIDECAR: label, high-dispersion yes/no, max
   as-of. Staleness rule (rev-2 N-7; round-3 NEW-6 pins the reference): the
   strip-level banner fires when the NEWEST per-symbol `max_asof` across the
   sidecar is more than 5 trading sessions older than the BUILD's NY
   evaluation date — computed with `trading_sessions_between`, the same
   convention `_page_chain_age_sessions` uses for chain age (threshold
   LLM-proposed, display-only) — OR the sidecar is absent/malformed;
   rendering loudly: "regime view unpublished/stale — see Experiments
   shelf". Per-symbol lines always show their own `max_asof`.
   Strip always carries the shared DISCLAIMER sentence.
4. **Single-commit publication protocol (replaces the impossible two-rename
   design):** add a stdlib-only
   `options_researcher/research_views_publication.py` helper for canonical JSON,
   validation, hashing, fsync, locking, publication, and copy. The shell
   wrapper orchestrates builders but delegates filesystem commit semantics to
   this helper. A `generation_id` is exactly UTC basic time plus UUID hex,
   regex `^[0-9]{8}T[0-9]{12}Z-[0-9a-f]{32}$`; `published_at` is canonical UTC
   RFC 3339 with six fractional digits and `Z`. Parse it as timezone-aware
   UTC, never order timestamp strings or accept offsets. The helper rejects an
   ID that fails the regex, disagrees across pointer/manifest/status/directory,
   resolves outside the generations root, or collides with an existing final
   directory (collision is a hard error, never overwrite).

   Build inside same-filesystem
   `.tmp/dashboard/research-views-generations/.staging-<generation_id>/`.
   Run BOTH builders to collect both exits. If either is nonzero, acquire the
   same publication lock and atomically write+fsync
   `.tmp/dashboard/research-views-last-failure.json` with strict schema
   `research_views_failure/v1`, attempt id, UTC attempted/completed timestamps,
   producer commit/root, both exits, and `outcome: FAILED`; include no hashes
   from partial outputs. Mint `completed_at` while holding the lock. Re-read
   any existing failure under the lock and replace it only when the new parsed
   completion is later; identical attempt id is an idempotent no-op and equal
   completion with a different id is `ATTEMPT_CONFLICT`. Remove only that
   attempt's staging directory; leave current pointer and immutable generations
   unchanged; exit nonzero. On success,
   create four logical artifacts — `experiments.html`,
   `wasserstein-regime.txt`, `wasserstein-regime.json`, and
   `research-views-status.txt`. Status records the id, timestamp, both zero
   exits, and SHA-256/byte size for the first three.

   Canonical `research-views-manifest.json` has schema
   `research_views_manifest/v1`, generation id, parsed publication time,
   producer commit, and an EXACT four-entry allow-listed file map with
   SHA-256/byte size for all four logical artifacts, including status. Verify
   that status identity/outcomes and its three file hashes/sizes equal the
   manifest entries. Canonical `research-views-current.json` has schema
   `research_views_current/v1`, generation id, publication time, and the
   manifest's SHA-256/byte size; for a copied generation it may additionally
   carry `copied_from_root`, but the immutable source manifest and generation
   bytes remain byte-identical.

   Flush and fsync every artifact plus manifest and the staging directory;
   under an exclusive `fcntl` lock at
   `.tmp/dashboard/.research-views.lock`, rename staging once to the final
   immutable generation, fsync the generations parent, write+fsync a temporary
   current pointer, rename that ONE pointer over the old pointer, then fsync
   the dashboard parent. The durable current pointer IS the success receipt;
   do not write a second PUBLISHED-attempt file. A failure before pointer rename
   leaves the prior complete generation current; a crash after pointer
   durability cannot make an older failure look current because readers apply
   WP-D.5's timestamp rule. Never rollback by a second rename, and never edit
   or delete a published generation in this brief.
5. **Reader and ops-copy hash/locking protocol:** a reader snapshots and parses
   the current pointer once, verifies the pointer's manifest hash/size, then
   resolves that exact immutable generation (never re-reads the pointer
   mid-operation). Validate strict schemas, UTC timestamp, id equality and
   containment, exact relative-file allow-list, sizes, hashes, and
   status/manifest agreement before using the sidecar or emitting links to
   `research-views-generations/<validated_id>/...`. Missing, malformed,
   path-escaping, hash-mismatched, or split generations render visibly as
   `unpublished/integrity failed`; no loose-root-file or previous-generation
   fallback is allowed after the pointer has been read.

   In `_build_and_write`, capture `deployment_root = Path.cwd().resolve()`
   before entering `_input_root_cwd()`, bind its yielded value as
   `input_root`, and after exiting call the helper explicitly with
   `source_root=input_root` and `destination_root=deployment_root` BEFORE
   loading local research-view status. If the roots resolve equal, perform no
   copy and load locally. Otherwise snapshot/validate the source pointer and
   immutable generation, copy its bytes into destination staging, validate
   again, and commit under the destination's SAME lock/protocol. Under that
   lock, re-read the destination pointer immediately before commit: source
   time newer means install; destination newer means skip; identical id means
   idempotent no-op; equal parsed timestamps with different ids means
   `GENERATION_CONFLICT` and no pointer change. Snapshot and strictly validate
   the source `research-views-last-failure.json` independently of the current
   generation. Under the destination lock, reconcile it by parsed
   `completed_at` using the same newer/idempotent/equal-time-conflict rules as
   the producer, even when source and destination generation ids are identical.
   Copy the byte-identical source failure BEFORE any destination pointer update;
   a crash after pointer durability therefore cannot omit a source failure that
   was newer than that source publication. This locked recheck is the
   compare-and-swap that prevents a stale copy from clobbering a concurrent
   local publish. The local pointer records `copied_from_root`; source manifest
   and generation stay byte-identical. Copy/integrity failure is visible but
   nonfatal to the independent board build. The implementation worker may not
   run an ops deployment or mutate the ops checkout.
6. **Consumer migration (no hidden compatibility gap):** change
   `load_research_views_status` and the regime-sidecar loader to the validated
   pointer/manifest helper; have `_experiments_shelf_html` link to exact
   generation paths. Parse the local last-failure record strictly and show it
   separately only when `failure.completed_at` is later than the validated
   current pointer's `published_at` (or when no valid current publication
   exists); suppress an older failure as stale history. A malformed failure
   channel renders its own integrity warning but cannot invalidate a valid
   current generation. Update
   `tools/launchagents/README.md` operator curl examples to fetch the pointer,
   then its exact manifest/generation paths. Do not keep individual loose-file
   aliases: they cannot provide set atomicity and must not be treated as a
   compatibility surface.

### WP-E — coordinated test updates (rev-1 findings 15, 36 applied)

Intentional updates (same commit as the feature that breaks them):
- `tests/test_attractiveness_v3.py:279` hero-card count 6 → `2*PICK_TOP_N`;
  `:280` "…FOR MECHANICAL TOP 3" string; `:281` "Rule-based top 3 — best
  policy-and-liquidity fit today"; `:282` "Pick 3" → "Pick 5". RENAME the
  now-false test names too (rev-2 finding N-11):
  `test_partial_top3_keeps_three_visible_slots_in_each_list` and
  `test_six_slots_render_as_two_lists_and_duplicate_is_allowed`
  (`tests/test_attractiveness_dashboard.py:1685`) get n-neutral names.
- `tests/test_attractiveness_dashboard.py:2260`
  (`test_full_lane_board_order_keeps_named_sections_distinct`), `:1677`,
  `:1776`, `:1790`, and the freshness/shelf ordering tests — heading strings
  only (all line numbers @720a20e).
- Slot tests: `:1685`-area (six slots → `2*PICK_TOP_N`), blocked-QM-slot
  tests (`test_stale_qm_context_renders_three_blocked_slots…` and sibling —
  three → `PICK_TOP_N`).
- `select_top_picks` invariance tests that pin membership on fixtures where
  more than 3 candidates qualify (locate by name:
  `test_evidence_cannot_change_top3_order_or_card_grades`,
  `test_tracker_attachment_cannot_change_mechanical_selection_bytes`
  (`:2230`),
  `test_movement_fires_leave_canonical_mechanical_selection_bytes_unchanged`
  (`:1661`) — the byte-identity pair compares like-for-like builds and is
  expected to pass unmodified; verify rather than edit).
- `tests/test_research_context_assemble.py` mocks that patch
  `select_top_picks` (locate by grep) — confirm they are n-agnostic.
- `tests/test_experiments_dashboard.py`: preserve the default output-path test
  and add the explicit `--out` staging-path contract.
- `tests/test_regime_report.py`: add paired `--out` / `--json-out` schema and
  partial-staging failure coverage.
- `tests/test_research_display_refresh.py`: replace loose-file and partial
  success expectations. On either builder failure, both builders still run,
  the prior current pointer/generation remain byte-identical, the staging
  directory is removed, `last-failure` records both exits and FAILED, and the
  wrapper exits nonzero. On success, assert exact generation files, manifest
  chain, pointer swap, no second success receipt, and no loose aliases. Replace
  the old status-rename failure case with pointer-rename/fsync failure cases
  that preserve the old current generation.
- NEW tests (names track the rev-3/rev-4 rules — round-3 finding NEW-5):
  dominance partition units (incomparable-never-dominated,
  **liquidity-RED-never-hidden**, blocked-never-hidden,
  **portfolio-RED-only-card-IS-hideable** (positive case), ≤2-card lane
  exemption, pmcc exemption, fixpoint shown-dominator property);
  collapsed-panel default states (**DATA_BLOCKED/stale panel open**,
  liquidity-RED-only panel COLLAPSED with its card outside the dominated
  block, clean panel collapsed); regime strip present/absent-is-loud;
  sidecar schema round-trip; generation publish/copy (failure before pointer
  swap preserves the prior generation; pointer temp and both parent-directory
  fsyncs are exercised through injected failures; a reader pinned to one
  generation cannot observe a split pair; invalid id, directory escape,
  manifest mutation, status/manifest disagreement, size mismatch, and one-byte
  artifact mutation all fail closed; same-id is idempotent, newer-local wins,
  equal-time/different-id conflicts, a lock-delayed stale copier cannot clobber
  a concurrent publish, same-root skips copy, and no loose-file fallback).
  Failure-channel tests: a crash after durable pointer commit needs no second
  success receipt; a failure older than current publication is suppressed; a
  newer failure with an unchanged source generation is copied and rendered;
  concurrent failure writers cannot regress `completed_at`; equal completion
  with different attempt ids fails closed.
- MUST NOT change: `SelectTopPicksTests` recipe tests except the n default;
  fail-visible pins `:1116`, `:1126`, `:1137` (the exact
  `DISPLAY_ONLY_LABEL` count of 2 must survive WP-B/WP-C); AST boundary
  test.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests    # exit 0, offline
uv run ruff check . && uv run pyright          # exit 0
```
Plus, on one frozen copy of the REAL board input (rev-1 finding 15; rev-2 N-4;
round-3 NEW-1), record the input root, source artifact SHA-256, data/evaluation
dates, base commit, and the metric definition: "candidate cards visible
without user interaction" means cards not inside any closed `<details>`.

**Pre-implementation stop gate:** run the WP-B/WP-C rules as a dry projection
against that frozen input and write the predicted visible-card identity set and
before/after counts to the draft PR. The prior 18-panel / 14-liquidity-RED-panel
measurement is context, not an acceptance fixture. If the newly predicted
reduction is below **30%**, stop before implementation and report the measured
ceiling to the owner; do not weaken an exclusion or reinterpret the metric.

**Acceptance after the stop gate clears:** build against the SAME frozen input.
The rendered visible-card identity set must equal the dry projection exactly;
every pre-change `candidate_id` and multiplicity must remain in the assembled
payload and DOM; Top-5 membership must equal the first five items from the
byte-unchanged admission/order pipeline; every hidden card's recorded
dominator must be in the shown set; and the generation/hash failure tests in
WP-E must pass. The 30% figure is only the pre-implementation stop gate — it is
not a target that can substitute for exact rule-faithfulness.

The implementation ends at a green **draft PR** with the frozen-input receipt,
predicted and actual identity sets, manifest/hash test evidence, and command
exit codes. The worker must not make it ready, merge it, deploy it, update ops,
change any ledger, or flip any authority.

## Claim-discipline register

- Page composition percentages/byte figures: Estimate, measured 2026-08-25
  (artifact rebuilds daily; not byte-reproducible later).
- Six slot literals and both selector defs: Repo-verified @720a20e (lines
  quoted in WP-A.2).
- Card field availability per lane: Repo-verified
  `options_researcher/attractiveness.py:223-227,280-284,339-343,379-381,421-429`.
- RQ2/A2 non-consumption of top-3 membership: Repo-verified ledger seq 27
  (single clause) + seq 18.
- Ops-default input root committed: Repo-verified
  `attractiveness_dashboard.py:57,61-90` @720a20e.
- RED-badge prevalence (170/222 blocks carry ≥1 RED; portfolio 143,
  liquidity 82, fits_cap 53): Repo-verified, measured on the live board
  2026-08-25 by the round-2 reviewer (rev-2 finding N-4).
- `cc` carries `upside`; `pmcc` carries neither `cushion` nor `upside`:
  Repo-verified `attractiveness.py:280-284,339-343`.
- Dominance axis sets, ≤2-card exemption, pmcc exemption, 5-session sidecar
  staleness threshold, and the 30% pre-implementation stop gate:
  LLM-proposed 2026-08-25 (display-only), labeled in code; Assumptions. The
  stop gate is not an acceptance floor.
- Immutable-generation publication, one-pointer commit, allow-listed relative
  paths, and SHA-256/size verification: Inference from filesystem atomicity and
  fail-closed repository policy; the focused Wave 0 review must explicitly
  PASS this protocol before hand-off.
