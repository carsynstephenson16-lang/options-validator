# Options Validator Core private plugin design

**Date:** 2026-08-11

**Status:** Owner-approved design

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

`ov/SOURCE_MANIFEST.json` preserves the current three classes:

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
