# Codex brief 29 — Schwab inventory binding (rev 5)

**Date:** 2026-08-25; rev 2 (blocked) 2026-08-26 morning; rev 3, rev 4, rev 5 2026-08-26 evening
**Author:** Claude Fable 5 orchestrating session (claude/codex-handoff-plan-2026-08-22)
**Executor:** Codex, high reasoning
**Status:** READY FOR HAND-OFF — round-2 (final) independent correction review **PASS** on rev 5, 2026-08-26 evening; the reviewer hand-traced all five `RepoRootAnchoringTests` methods through the new code and found "no new defect that can produce wrong behavior, data mutation, or an un-implementable step"; all five round-2 minor residuals are applied in this revision. Receipt: `reports/2026-08-26-briefs-24-29-31-adversarial-review-receipts.md`. The owner package's reopened-decision condition (revision against current main answering all blockers + fresh independent written PASS) is satisfied; hand-off proceeds under the owner's 2026-08-26 evening in-session directive (see Hand-off gate).
**Provenance:** Repo-verified against `origin/main@4ab1a385c3ee6a5c97285f9bf0a341f5a69feac5` unless labeled otherwise. Review lineage: rev 2's source proposal FAILED (`reports/2026-08-26-brief-29-independent-review-receipt.md`, blockers 1–8); rev 3 FAILED round-2 independent review (R3-F1…R3-F15); rev 4 answered 14 of 15 but FAILED the bounded correction round on R3-F1 — its CLI-scoping premise was false (the CLI fixture tests do NOT override `--inventory`; they isolate by cwd) — with residuals N-1…N-4. Rev 5 answers all of them.

## Why this exists (plain language)

This closes audit finding **DATA-01** (2026-08-25 repository audit,
`reports/repository-audits/2026-08-25-options-validator/04-candidate-registry.csv`).

`.cache/schwab_chains` holds gitignored Schwab chain parquet that cannot be
re-acquired under the repository's provider restrictions (OD-4).
**Repo-verified 2026-08-26 (corrected per R3-F4), commands beside values:**
`find .cache/schwab_chains -type f | wc -l` → **90 files**;
`find .cache/schwab_chains -type f -exec stat -f %z {} + | awk '{s+=$1} END {print s}'`
→ **9,700,050 bytes**; filenames span **15 symbols** (AMD, AMZN, AVGO, CEG,
CRWV, ET, IREN, MSFT, NOW, NVDA, PLTR, SMCI, TEM, USAR, VST) across **six
sessions, 2026-08-14 through 2026-08-26** — the whole pre-close capture
lane's cache, growing each ritual session. Yet
`data/irreplaceable_data_inventory.json` records the namespace
`"present": false, 0 files, 0 bytes`, and `verify()` skips every
recorded-absent entry (`tools/irreplaceable_data_guard.py:147-149`). The
guard therefore gives this namespace **zero protection**: it could be deleted
tomorrow and `verify` would still exit 0. That is the exact silent-loss class
the 2026-08-03 incident created this tool to prevent.

## Verified current state (all Repo-verified @4ab1a38 unless labeled)

- `DEFAULT_NAMESPACES` (`tools/irreplaceable_data_guard.py:54-63`) contains
  both `.cache/schwab_chains` and `reports/schwab_chains`.
- `verify()` (`tools/irreplaceable_data_guard.py:138-192`) iterates only keys
  present in the inventory and `continue`s on `recorded["present"] == false`
  (:147-149) before any comparison.
- The committed inventory records `.cache/schwab_chains` and
  `reports/schwab_chains` both `present: false / 0 / 0`; the other six
  namespaces carry real floors.
- **CLI inventory-path resolution (drives WP-B's design and the acceptance
  commands; R3-F2):** `main()` resolves a RELATIVE `--inventory` against the
  MAIN checkout root, never the cwd
  (`tools/irreplaceable_data_guard.py:216,233-235`); an absolute path is
  taken verbatim. From a linked worktree, `resolve_repo_root()` returns the
  main checkout (:66-86).
- **Consumers that must keep working (receipt blocker 6):**
  `tools/h7_forward_backup.py:55,61` derives `BACKUP_PATHS` from
  `DEFAULT_NAMESPACES`; `tests/test_h7_backup.py:21-28` requires
  `reports/schwab_chains` in the allow-list;
  `tests/test_irreplaceable_data_guard.py:146-169` requires both Schwab keys
  in `DEFAULT_NAMESPACES` AND in the committed inventory (membership
  assertions only — no floor values pinned).
- **Library-fixture contract, BOTH doors (receipt blocker 3 + R3-F1):**
  (a) direct calls: `verify(inventory)` / `verify(inventory,
  allow_absent=True)` with temporary absolute-path namespaces
  (`tests/test_irreplaceable_data_guard.py:65,75,88,111,123,129,138-139`);
  (b) **CLI-path fixtures**: `RepoRootAnchoringTests` (:172-278) shells out
  to `main()` via subprocess against throwaway repos whose inventory holds a
  SINGLE key (`myns`, :209) — and, corrected per correction-round N-1, those
  runs pass the BARE subcommand with NO `--inventory` override
  (:226,237,244,255,273); they isolate by cwd inside a throwaway repo, so
  the un-overridden default inventory path is exactly the path they
  exercise. WP-B.3's fixture seeding exists for precisely this reason —
  `test_verify_from_linked_worktree_is_not_a_loss_report` (:217-230) and
  `test_verify_from_subdirectory_anchors_on_repo_root` (:232-238) are the
  regression tests for the 2026-08-09 false-alarm fix and MUST stay green on
  their original assertions, unmodified. WP-B is designed around them.
- `reports/schwab_chains` is **git-tracked** ritual-grown evidence — 12
  files, all tracked (`git ls-files reports/schwab_chains` count equals the
  `find` count), latest committed by `4ab1a38`. Standing lesson (2026-08-25
  verification arc, recorded in
  `reports/2026-08-25-codex-audit-verification-owner-package.md`): guard
  inventory floors must NEVER bind git-tracked ritual-grown directories — a
  branch-lagged checkout drops tracked files, trips `LOST FILES`, and the
  daily reconciler treats a guard failure as "no actions in this repo"
  (`tools/anti-stranding/repo-reconcile:68-73`), halting the repo's whole
  anti-stranding layer for the day. **Standing assumption (R3-F14): the
  tracked-namespace exemption below is valid only while that directory is
  100% git-tracked; a gitignored file placed under it would inherit the
  exemption and get zero protection.**
- **Deployed-caller truth (receipt blocker 2):** the deployed
  `/Users/carsynstephenson/bin/repo-reconcile:48-53` gates the guard behind
  `[ -x ... ]`; the file is mode 0644, so the deployed daily automation
  **currently skips the guard entirely**. The repo copy uses `[ -f ... ]`
  (`tools/anti-stranding/repo-reconcile:68`) and would invoke it, but that
  copy is not deployed. Any blast-radius claim about daily automation is
  therefore **conditional on the separately owner-authorized brief 24
  redeployment**, not current fact.
- **Brief 27 coordination resolved upstream (receipt blocker 4):** canonical
  brief 27 (rev 6, landed via PR #92 @092bfa0) explicitly REMOVED the
  disputed guard addition
  (`docs/superpowers/plans/2026-08-25-27-pick-tracker-scoreboard-codex-brief.md:437-440,614-617`),
  and the in-flight implementation draft PR #93 (head `5877939`,
  `isDraft: true`) touches no guard file. No landing-order constraint
  remains between brief 27 and this brief.
- **Downstream dependent (R3-F5): brief 30.**
  `docs/superpowers/plans/2026-08-25-30-midday-chain-refresh-codex-brief.md:283-292`
  declares itself BLOCKED until this brief's guard-semantic repair lands,
  then instructs adding `.cache/schwab_chains_midday` to the guard and
  regenerating the inventory "so the new cache key is recorded even while
  absent". Binding coordination: brief 30's regeneration MUST use this
  brief's `generate --only .cache/schwab_chains_midday` (which creates a
  missing key additively — WP-D.1 edge (a)), never a plain whole-list
  `generate`; and rev 5's WP-A/WP-D make plain `generate`
  tracked-namespace-safe in any case.
- The repository-reconciler default-draft gap
  (`tools/anti-stranding/repo-reconcile:178` vs `AGENTS.md:98-104`) is real
  and is routed to the brief 24 arc. OUT of scope here.

## Scope

### IN

- WP-A: fail closed when a recorded-absent **gitignored** namespace has
  become populated; tracked namespaces exempted from the ENTIRE verify loop
  body and pinned absent by `generate` (R3-F3).
- WP-B: fail closed when the repo's own production inventory is missing a
  required namespace key — scoped to the production inventory, with
  fixture-helper seeding so the CLI fixture tests stay green (R3-F1;
  round-2 residual 1).
- WP-C: regression tests proving the new behaviors AND unchanged behavior of
  every existing test, RED first.
- WP-D: a `--only` scoped, additive-only `generate` mode with specified edge
  cases, plus exactly one scoped inventory regeneration for
  `.cache/schwab_chains`, landing **in the same draft implementation PR as
  the WP-A/B code** (atomicity — see WP-D), under a capture-window quiesce
  rule (R3-F6).

### OUT — hard stops

- No deletion or rename of any inventory namespace key; no decrease to any
  existing `file_count` / `total_bytes` floor (receipt blocker 1: the rev-1
  proposal to delete the `reports/schwab_chains` key stays rejected — the
  key remains, recorded absent, exempt from the verify loop).
- No removal of any entry from `DEFAULT_NAMESPACES`; no change to
  `tools/h7_forward_backup.py`, its tests' allow-list expectations, brief
  27, brief 30, the reconciler, hooks, scheduler, LaunchAgents, or any
  deployed script.
- No modification of `RepoRootAnchoringTests`' existing ASSERTIONS
  (`tests/test_irreplaceable_data_guard.py:217-238`); the `_fixture_repo`
  helper (:194-215) may be extended exactly as WP-B.3 specifies, nothing
  else. If any WP still turns those assertions red, the WP design is wrong;
  STOP and report, do not weaken the tests.
- No data deletion, movement, rewrite, provider call, or network access.
- No hand-edit of the inventory JSON: every inventory change is produced by
  the tool itself and proven by the WP-D delta gate.
- No make-ready, merge, deploy, operational-checkout sync, ledger write,
  registration, authority flip, live-order path, or frozen-value change.

## Work packages

### WP-A — recorded-absent-but-populated fails closed; tracked namespaces fully exempt

In `tools/irreplaceable_data_guard.py`:

1. Add a module constant next to `DEFAULT_NAMESPACES`:

   ```python
   # Git-tracked ritual-grown namespaces: the backup allow-list derives from
   # DEFAULT_NAMESPACES so these stay listed, but the guard must never bind
   # them -- verify() skips them entirely and generate records them absent.
   # A branch-lagged checkout drops tracked files and would false-alarm,
   # halting the daily anti-stranding run (2026-08-25/26 review arc). Valid
   # only while the directory is 100% git-tracked.
   TRACKED_NAMESPACES = frozenset({"reports/schwab_chains"})
   ```

2. In `verify()`: at the TOP of the per-namespace loop, `continue` for any
   `ns in TRACKED_NAMESPACES` — before the recorded-absent check AND before
   every floor comparison, so no code path can ever bind a tracked
   namespace (R3-F3: rev 3 exempted only the recorded-absent branch, which
   left the :174-184 floor comparisons live if a floor ever got recorded).
3. Then, for recorded-absent entries (:147-149): `scan()` the namespace; if
   the scan reports `present` with `file_count > 0`, append a problem in the
   existing style:
   `f"{ns}: RECORDED ABSENT BUT POPULATED -- {n} files, {b} bytes on disk "
   f"with no inventory floor. Regeneration must follow the reviewed "
   f"additive procedure (generate --only, isolated worktree); do not run "
   f"bare generate against the production inventory."`
   (R3-F7: routes to the reviewed procedure, never a bare mutating command;
   correction-round N-3: no dated plan filename in shipped source — the
   wording above is stable.) A namespace whose directory is absent, or exists with
   zero files (the auto-mkdir case, :153-164), stays a silent skip.
   `allow_absent` must NOT suppress this check — it governs absence; this is
   unexpected presence.
4. In `build_inventory()` / `generate`: entries for `TRACKED_NAMESPACES` are
   ALWAYS written as `{"present": false, "file_count": 0, "total_bytes": 0}`
   regardless of what is on disk, so no future plain `generate` can create
   the tracked-floor hazard (R3-F3; this also protects brief 30's flow).
5. Cost note (R3-F13): the new populated-check adds one recursive `scan()`
   per recorded-absent namespace per `verify`. Acceptable because a
   namespace should not stay recorded-absent long (this brief's WP-D
   registers the only populated one), and `verify` already scans every
   present namespace.

### WP-B — production-inventory completeness check (scoped; fixture-safe)

1. Extend the signature compatibly (receipt blocker 3):

   ```python
   def verify(inventory, deep=False, allow_absent=False, root=".",
              *, required_namespaces=None) -> list[str]:
   ```

   When `required_namespaces` is provided, any name in it missing from
   `inventory["namespaces"]` appends
   `f"{ns}: NO INVENTORY KEY -- required namespace is not recorded at all."`.
   Default `None` preserves every existing caller byte-for-byte.
2. **CLI scoping (R3-F1, corrected in rev 5):** `main()` passes
   `required_namespaces=DEFAULT_NAMESPACES` **only when `args.inventory ==
   DEFAULT_INVENTORY`** (the un-overridden default). Any explicit
   `--inventory` override — this brief's own WP-D acceptance, and the WP-C
   bespoke-inventory tests — gets `required_namespaces=None`. Semantics:
   "the production inventory must record every production namespace" —
   INCLUDING the tracked ones: the required check demands KEY PRESENCE for
   every `DEFAULT_NAMESPACES` entry, `reports/schwab_chains` included; only
   floor BINDING is exempted for tracked namespaces (round-2 residual 2). A
   bespoke inventory is checked only against itself. NOTE the corrected
   fact (correction-round N-1): the `RepoRootAnchoringTests` fixtures use
   the un-overridden DEFAULT path, so the scoping rule alone does NOT
   exclude them — WP-B.3's seeding is what keeps them green.
3. **Fixture-helper seeding (correction-round required change, option (a)):**
   extend `_fixture_repo` (`tests/test_irreplaceable_data_guard.py:194-215`)
   to ALSO seed, programmatically from `guard.DEFAULT_NAMESPACES` (never a
   hand-copied list, so future namespace additions auto-seed), an entry
   `{"present": false, "file_count": 0, "total_bytes": 0}` for every
   production namespace alongside the fixture's own `myns` key. The
   `present: false` value is LOAD-BEARING, not stylistic: it keeps the
   fixture's `recorded_present` count at 1 so
   `test_genuine_loss_still_alarms_from_the_main_checkout`'s "canonical"
   hint (`tools/irreplaceable_data_guard.py:263-274`) still fires — do not
   "helpfully" flip it to `present: true` (round-2 residual 3). The
   ASSERTIONS at :217-238 stay byte-for-byte unmodified — the helper is the
   one permitted test-file change. With seeding: the required-namespaces
   check finds every key present (satisfied); the WP-A populated-check
   skips them (directories absent in the fixture repo → scan
   `present: False`); `reports/schwab_chains` is skipped as tracked. Verify
   BEFORE writing any implementation code that
   `test_verify_from_linked_worktree_is_not_a_loss_report` and
   `test_verify_from_subdirectory_anchors_on_repo_root` pass on their
   original assertions, and state that in the PR body.

### WP-C — tests, RED first

Extend `tests/test_irreplaceable_data_guard.py` (fixtures stay hermetic
temp dirs; no test reads real data or runs `generate` against the real
checkout; NO test monkeypatches `TRACKED_NAMESPACES` — R3-F9). Demonstrate
RED (each new test failing against unmodified code) before implementing
WP-A/B/D and record the RED output in the PR body:

1. Recorded-absent namespace + populated directory → problem mentioning
   `RECORDED ABSENT BUT POPULATED`.
2. Tracked-namespace exemption, hermetically (R3-F9 recipe): create
   `tmpdir/reports/schwab_chains/x`, build an inventory whose key literally
   is `reports/schwab_chains` (recorded absent), call
   `guard.verify(inventory, root=tmpdir)` → no problem. Also: same key with
   a POSITIVE recorded floor and a now-smaller directory → still no problem
   (the whole-loop exemption of WP-A.2).
3. Recorded-absent + directory exists but empty → no problem (use
   `root=tmpdir` likewise).
4. Recorded-absent + populated + `allow_absent=True` → STILL a problem.
5. `verify(inventory, required_namespaces=["missing/ns"])` → NO INVENTORY
   KEY problem; same inventory with `required_namespaces=None` → clean.
6. CLI scoping, BOTH paths exercised hermetically (correction round):
   (a) bare `verify` (no `--inventory`) in a seeded fixture repo → exit 0,
   `irreplaceable data: OK`; (b) same fixture with ONE seeded production
   key deleted from its inventory file → bare `verify` exits 1 with a
   NO INVENTORY KEY problem naming that namespace; (c) `verify --inventory
   <abs bespoke path>` whose inventory holds a subset of keys → NO required
   check applied (no NO INVENTORY KEY problems).
7. Plain `generate` in a fixture repo with a POPULATED
   `reports/schwab_chains` records it `present: false, 0, 0` (WP-A.4;
   R3-F3).
8. Every existing test in the file passes with its ASSERTIONS unmodified;
   the `_fixture_repo` helper extension of WP-B.3 is the one permitted
   change to existing test code. Do not weaken any assertion.
9. `generate --only`, in a throwaway temp repo: (a) only the named namespace
   is rescanned, every other entry AND the top-level `note` key preserved
   byte-identically; (b) a rescan that would LOWER a recorded floor exits 2
   without writing; (c) a namespace not in `DEFAULT_NAMESPACES` exits 2;
   (d) an absolute in-tree `--inventory` target is honored verbatim AND the
   fixture repo's default `data/irreplaceable_data_inventory.json` is
   byte-identical afterwards (R3-F11); (e) `--only` for a namespace in
   `DEFAULT_NAMESPACES` with NO existing key CREATES it additively
   (brief 30's case); (f) `--only` with a nonexistent `--inventory` file
   exits 2 (only plain `generate` may create the file).

### WP-D — scoped additive regeneration (same PR, atomic)

**Atomicity constraint (do not split):** once WP-A lands, `verify` against
the production inventory will alarm on `.cache/schwab_chains` (recorded
absent, actually populated) until the inventory records real floors. The
WP-A/B/C code and the WP-D inventory update must land in ONE draft
implementation PR so no commit on main ever alarms.

1. Add `--only <namespace>` (repeatable) to `generate`: loads the existing
   inventory from `--inventory`, rescans ONLY the listed namespaces,
   preserves every other entry and the top-level `note` byte-for-byte, and
   refuses (exit 2, no write) if: a listed namespace is not in
   `DEFAULT_NAMESPACES`; a rescan would LOWER an existing key's
   `file_count` or `total_bytes`; or the `--inventory` file does not exist.
   A listed namespace with no existing key is CREATED (additive; brief 30
   depends on this). A listed namespace in `TRACKED_NAMESPACES` is written
   absent per WP-A.4. `--deep` with `--only` computes `content_digest` for
   rescanned entries only; untouched entries keep whatever they had. Plain
   `generate` keeps its current whole-list behavior except for WP-A.4.
2. **Quiesce rule (R3-F6):** the regeneration run must happen OUTSIDE
   15:00–16:30 ET on weekdays (the reconciler's own ops pre-capture
   blackout, `tools/anti-stranding/repo-reconcile:207-210`), and must assert
   `find .cache/schwab_chains -name '.*.tmp'` is empty immediately before
   AND after the `generate` — the capture path stages temp files in the same
   directory (`data/atomic_io.py:22`), and freezing a floor that counts a
   phantom temp file would be unfixable by this brief's own additive-only
   rules. Recovery path if a floor is ever frozen high anyway: STOP; a
   correction is an owner-authorized decision recorded in a dated report —
   not a silent re-run.
3. Isolated activation (receipt blocker 5):
   - Pin base: record `git rev-parse origin/main` in the PR body.
   - `git worktree add .tmp/worktrees/data01-inventory-binding -b
     codex/brief29-data01 origin/main` (worktree location rule).
   - Assert in-worktree: `git rev-parse --show-toplevel` is the worktree
     path, branch is `codex/brief29-data01`, `git status --porcelain` empty.
   - Run FROM the worktree, writing INTO the worktree:
     `uv run python tools/irreplaceable_data_guard.py generate
     --only .cache/schwab_chains
     --inventory <abs worktree path>/data/irreplaceable_data_inventory.json`
     — the guard anchors its scan on the MAIN checkout (where the gitignored
     bytes live, :66-86,216) while the absolute `--inventory` path keeps the
     write inside the worktree (:233-235). The main checkout's committed
     files are never touched.
4. Main-checkout sentinels (receipt blocker 5): before and after the whole
   session, record the main checkout's branch, HEAD,
   `git status --porcelain`, and
   `shasum -a 256 data/irreplaceable_data_inventory.json`; all four must be
   unchanged. Stop and report on any difference.
5. Machine-checkable delta (receipt blocker 1), in the PR body:
   - `git diff --name-status origin/main...HEAD` contains no `D` or `R`
     status and no path outside the declared file list.
   - A JSON comparison (command + output shown) proving: namespace key set
     unchanged; every pre-existing floor unchanged; the ONLY changed entry
     is `.cache/schwab_chains` with new `file_count`/`total_bytes` > 0 and
     ≥ the old values; `reports/schwab_chains` remains recorded absent; the
     top-level `note` unchanged.
6. Draft authority (receipt blocker 7): create the PR with
   `gh pr create --draft`, prove `isDraft=true` via
   `gh pr view <n> --json isDraft` in the PR body or a comment, and STOP:
   no make-ready, no merge, no deploy, no ops sync. Do not rely on the
   reconciler to create or adopt the PR. (Repo-verified: the deployed
   automerge filters out drafts — `~/bin/repo-reconcile:146` selects
   non-draft PRs only — so a draft cannot be swept up.)

## Acceptance / verification (implementation PR)

```bash
uv run python -m unittest discover -s tests -p 'test_irreplaceable_data_guard.py'
uv run python -m unittest discover -s tests -p 'test_h7_backup.py'
uv run python -m unittest discover -s tests      # full suite; exit code is the verdict
uv run ruff check .
uv run pyright
git diff --check
# From the PR worktree — the default --inventory resolves against the MAIN
# checkout (:233-235), so the worktree's regenerated inventory must be named
# explicitly (R3-F2):
uv run python tools/irreplaceable_data_guard.py verify \
  --inventory <abs worktree path>/data/irreplaceable_data_inventory.json   # exit 0
# EXPECTED to exit 1 until the PR merges (new code + old main inventory);
# record it, do not "fix" it — the fix that makes it exit 0 is the merge:
uv run python tools/irreplaceable_data_guard.py verify || true
```

On unmodified main, `verify` exits 0 today (Repo-verified 2026-08-26) and
must still exit 0 at merge time. Plus, recorded in the PR body: the WP-C RED
log, the two `RepoRootAnchoringTests` methods re-run green on their
unmodified assertions (helper seeded per WP-B.3), the
WP-D worktree assertions, quiesce proofs, sentinels, delta proof, and the
`isDraft=true` proof. The PR description must state plainly that the
deployed daily reconciler currently skips the guard (receipt blocker 2) so
nobody over-reads the protection this change delivers before brief 24's
redeploy.

## Blocker map

**Receipt (rev-2 review) blockers → rev 5:** 1 → OUT list + WP-D.1 refusal +
WP-D.5 delta gate; 2 → Verified current state + mandatory PR-body statement;
3 → WP-B keyword-only arg + CLI scoping to the production inventory
(both fixture doors now covered); 4 → brief 27 resolution verified (PR #92 /
PR #93); 5 → WP-D.3/D.4 exact SHA, worktree assertions, sentinels; 6 → OUT
list preserves `DEFAULT_NAMESPACES` + key + `test_h7_backup` in acceptance +
the `RepoRootAnchoringTests` no-modify stop; 7 → WP-D.6; 8 → provenance
@4ab1a38, corrected data description with commands, Status stays DRAFT.

**Round-2 (rev-3 review) findings → rev 5:** R3-F1 → WP-B.2 CLI scoping +
OUT-list no-modify stop + WP-C.6/C.8; R3-F2 → corrected acceptance commands
with the :233-235 explanation and the expected-exit-1 companion; R3-F3 →
WP-A.2 whole-loop exemption + WP-A.4 generate pinning + WP-C.2/C.7; R3-F4 →
corrected, command-backed data description; R3-F5 → Downstream dependents
bullet (brief 30) + WP-D.1 edge (e); R3-F6 → WP-D.2 quiesce + recovery path;
R3-F7 → WP-A.3 message text; R3-F8 → honest authority quote below; R3-F9 →
WP-C.2 `root=` recipe + monkeypatch ban; R3-F10 → WP-D.1 edges (a)–(d);
R3-F11 → WP-C.9(d); R3-F12 → `:68` corrected; R3-F13 → WP-A.5; R3-F14 →
standing assumption in Verified current state; R3-F15 → section order kept
deliberately (brief 27 precedent).

**Correction-round (rev-4 review) findings → rev 5:** N-1/N-2 (false
fixture-override premise; WP-B vs WP-C.8/OUT self-contradiction) → WP-B.2
corrected fact + WP-B.3 fixture-helper seeding + WP-C.6 both-paths tests +
OUT-list wording; N-3 (dated filename in shipped source) → WP-A.3 stable
wording; N-4 (one-directional brief-30 coordination) → this brief cannot
edit brief 30 (OUT list); the `--only`-not-plain-`generate` constraint MUST
be surfaced to brief 30's next review round — recorded here and in the
hand-off package so it is not lost.

## Hand-off gate

Authority state, quoted honestly (R3-F8): the owner package records
"**Addendum item 1 is SUPERSEDED** … the HANDED OFF status is **void**.
**Owner decision reopened:** brief 29 needs a rev 3 [now rev 5] against
current main answering the blockers, plus a fresh independent written PASS,
before any hand-off"
(`reports/2026-08-25-codex-audit-verification-owner-package.md:168-181`).
This brief may therefore be handed to Codex only after a fresh independent
adversarial review issues a written PASS receipt under `reports/` and the
Status line above is updated to cite it. No new frozen number is introduced
anywhere in this brief.
