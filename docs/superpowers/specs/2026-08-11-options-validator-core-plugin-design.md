# Options Validator Core private plugin design

**Date:** 2026-08-11

**Status:** Draft — pending owner review.

> **Provenance correction (2026-08-11).** First committed (`9713dfc`) carrying
> `Status: Owner-approved design`. That label was never true — no owner
> approval had been given or requested. Corrected to the accurate state.

**Parent:** `2026-08-11-options-validator-plugin-program-design.md`

## 1. Context

The repository currently has 13 canonical Codex skills under `.agents/skills/`
and a tracked ledger hook under `.agents/hooks/`. Claude discovers most of the
same skills through `.claude/skills/` links. The standalone `ov/` compatibility
bundle contains nine skills: six byte-identical mirrors, two intentional
variants, and one bundle-only Advisor Tool. There is no current
`.codex-plugin/plugin.json` package.

The roadmap requires consolidation without deleting the standalone bundle or
overwriting intentional variants. It also requires moving the local-only live
trading hook into the tracked hook surface and testing it.

## 2. Decision

Create `plugins/options-validator-core/` as the canonical installable package,
while keeping `.agents/skills/` and `.agents/hooks/` as the editable repository
sources of truth. Generated package copies are verified through an explicit
source manifest and deterministic checker.

The package version begins at `0.1.0`. It has no connector, MCP server,
authentication, network access, or external dependency.

### 2.1 Deliverable ranking (added 2026-08-11 by review)

*Reviewer-drafted; not an owner decision.*

Section 8 states the package is deliberately **not enabled** in this checkout.
That is correct, and it means the specification must be honest about which
parts deliver value now and which are speculative. Ranked:

1. **Move `block_live_trading.py` into `.agents/hooks/` with tests.** This is
   an existing roadmap item, not new scope: `PROJECT_STATE.md:196` lists
   "P3 hook | Move live-trading hook to tracked `.agents/hooks` with tests" as
   **READY NOW after P0 docs**, and `PROJECT_STATE.md:73` records P0.3-P0.6 and
   P0.8 closed, so the precondition reads as satisfied. Verified current state:
   the hook is untracked and gitignored (`.gitignore:22` matches `.claude/*`;
   `git ls-files .claude/hooks/block_live_trading.py` returns nothing), and
   `.agents/hooks/` contains only `block_ledger_edits.py` and `README.md`.
   The repository's single no-live-orders tripwire is therefore backed up
   nowhere and covered by no test. This is worth doing on its own merits and
   should not be made contingent on the plugin decision.
2. **`ov/` drift classification and checker.** Independently useful: it pins a
   divergence that is currently undocumented. Verified by hashing all nine
   `ov/` skills against `.agents/skills/` — six are byte-identical, exactly two
   diverge (`repo-health-review`, `results-red-team`), one is bundle-only
   (`advisor-tool`), matching §6. Each skill is a single `SKILL.md` except
   `advisor-tool`, so that comparison is complete rather than partial.
3. **Fix the dangling critic rule reference.** Verified real:
   `.agents/skills/independent-research-critic/SKILL.md:144` points at
   `.agents/rules/independent-research-critic.md`, which exists (779 bytes) but
   sits outside the skill folder and would not travel with a packaged skill.
4. **The plugin package itself.** Speculative. It is built, smoke-installed in
   a throwaway clone, proved to work, and then not used by anything. Its value
   is optionality, which is real but should not be presented as equal to
   items 1-3.

If the owner approves only item 1, that is a coherent and useful outcome and
this specification should not be read as requiring the rest.

## 3. Canonical content

The Core package includes these 13 skills:

1. `backtest-realism-audit`
2. `daily-ritual`
3. `grilling`
4. `independent-research-critic`
5. `ledger-discipline`
6. `obsidian-vault`
7. `options-beginner-explainer`
8. `options-data-audit`
9. `repo-health-review`
10. `results-red-team`
11. `session-synthesis`
12. `verdict-interpreter`
13. `web-fetch-order`

The package includes two guard hooks:

- `block_ledger_edits.py`
- `block_live_trading.py`

Any canonical skill resource currently stored outside its skill folder must be
made package-local or referenced through an explicitly validated repository
path. In particular, the independent critic's condensed rule file must ship as
a resource of that skill rather than becoming a dangling `.agents/rules/`
reference after installation.

The existing local live-trading hook is first moved into `.agents/hooks/` with
tests. Plugin and Claude registrations point at tracked or packaged copies only
after those copies pass their tests.

## 4. Planned file layout

```text
.agents/plugins/marketplace.json
.agents/hooks/block_live_trading.py
plugins/options-validator-core/
├── .codex-plugin/plugin.json
├── skills/<13 skill folders>/
└── hooks/
    ├── hooks.json
    ├── block_ledger_edits.py
    └── block_live_trading.py
tools/plugins/
├── core_sync_manifest.json
└── sync_core_plugin.py
tests/
├── test_core_plugin_package.py
└── test_block_live_trading.py
ov/SOURCE_MANIFEST.json
```

Only `plugin.json` lives inside `.codex-plugin/`. Every manifest path is
relative, begins with `./`, resolves inside the plugin root, and is rejected if
it escapes through `..` or a symlink.

## 5. Synchronization contract

`core_sync_manifest.json` records, for every generated package file:

- canonical source path;
- package destination path;
- synchronization class;
- expected SHA-256 after synchronization;
- whether executable mode is required.

`sync_core_plugin.py --check` is read-only. It exits nonzero for missing,
extra, stale, path-escaping, mode-mismatched, or unexpectedly divergent files.

`sync_core_plugin.py --sync` changes only files classified as approved mirrors.
It stages output in a temporary directory, validates the complete package, and
then performs bounded atomic replacements. It refuses unknown destinations and
does not run automatically during validator, research, dashboard, or ritual
workflows.

The tool never reads or writes ledgers, cache data, positions, experiment
configuration, reports, or private source material.

## 6. `ov/` compatibility classification

`ov/SOURCE_MANIFEST.json` does not exist yet; this specification creates it (see
§4). It records the three classes that are already true on disk today:

- **Mirror:** the six byte-identical skills must match their canonical
  `.agents/skills/` sources.
- **Intentional variant:** `repo-health-review` and `results-red-team` retain
  independent hashes and a written rationale; automated synchronization never
  overwrites them.
- **Bundle-only:** `advisor-tool` remains independently versioned and is not
  silently added to Core.

Any new divergence, missing classification, or extra skill fails the checker.
The implementation must not delete `ov/`, flatten its variants, or copy its
Advisor Tool into Core.

## 7. Hook contract

Both hooks accept the host event JSON on stdin and preserve their documented
exit contract. Malformed input fails closed. Tests cover direct file tools,
shell writes, known order-placement patterns, benign reads and test commands,
false positives, missing fields, Unicode, and path normalization.

Hook documentation must state that hooks are tripwires rather than security
boundaries. Hash-chain verification, typed ledger APIs, sandboxing, code review,
and owner authorization remain authoritative.

Plugin installation does not automatically trust bundled hooks. Activation
requires review of the exact packaged `hooks.json` and script hashes.

## 8. Source-repository activation rule

The Core package is listed in the repo marketplace and installed in an isolated
temporary clone or fixture containing the required Options Validator paths for
acceptance testing. It is not enabled in the source checkout because the source
checkout already exposes the canonical 13 skills directly. This avoids
duplicate workflow routing and context.

The source checkout still benefits from the tracked hook repair, package drift
checker, `ov/` classification, and installation proof.

## 9. Testing and audit

Required tests and checks:

- manifest and marketplace JSON validation;
- exact inventory and SHA reconciliation;
- source/package path containment and symlink-escape rejection;
- unknown, missing, extra, stale, and intentional-variant cases;
- hook malicious, benign, malformed, and false-positive fixtures;
- checker read-only proof and bounded `--sync` mutation proof;
- isolated installation, skill discovery, hook trust review, invocation,
  disable, and uninstall smoke;
- Ruff, Ruff format, Pyright, targeted unittests, and affected full suite;
- secret scan and final diff review;
- CodeRabbit and security-focused diff review;
- an audit receipt containing plugin version, source hashes, package hashes,
  commands, exit codes, and known limitations.

## 10. Completion and rollback

Core is build-ready only after every check passes and the temporary install
shows exactly 13 namespaced skills and the two expected hooks. It is not
activated in the source repository.

Rollback disables or uninstalls the marketplace package and restores local hook
registration to the last reviewed tracked version. Rollback does not delete
canonical skills, `ov/`, ledgers, data, reports, or tests.
