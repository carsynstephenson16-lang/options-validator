---
name: obsidian-vault
description: Use when the user wants to find, create, ingest, organize, query, or lint notes in the options-validator Obsidian LLM wiki, or asks whether its vault, links, indexes, or sync are configured correctly.
---

# Options Validator Obsidian LLM Wiki

## Contract

The Git repository root is the Obsidian vault. Andrej Karpathy's LLM-wiki
pattern is instantiated under `wiki/`:

- `wiki/raw/`: immutable source material; never edit or delete it.
- `wiki/*.md`: LLM-maintained, derived operator memory.
- `wiki/index.md`: content catalog; read first and update with every new page.
- `wiki/log.md`: append-only operations history.
- `wiki/CLAUDE.md`: path-scoped authority for wiki work; read before editing.

The wiki is not project truth. Verify claims against `ledger/`, `data/`,
`reports/`, `docs/superpowers/`, tests, and source files. If they disagree,
correct the derived wiki.

## Resolve the Vault

Work in the current Git checkout unless the user explicitly asks to change the
vault currently open in Obsidian:

```bash
git rev-parse --show-toplevel
sed -n '1,200p' wiki/CLAUDE.md
sed -n '1,240p' wiki/index.md
git status --short
```

On macOS, Obsidian's registered vaults are recorded in
`~/Library/Application Support/obsidian/obsidian.json`. A linked worktree may
not have `.obsidian/` and may not be registered; that is not a wiki defect.
Never copy edits into another checkout silently. Land the branch, or get the
user's explicit direction, before changing a second checkout.

## Workflows

### Search or query

Use `rg` against `wiki/` first, then inspect canonical evidence. File a durable
synthesis only when it adds reusable operator knowledge. A filed query result
must update `wiki/index.md` and append a `query` entry to `wiki/log.md`.

### Ingest

1. Preserve the source unchanged under `wiki/raw/`.
2. Create or revise lowercase kebab-case derived pages under `wiki/`.
3. Cite canonical repo paths and distinguish fact, inference, and open gaps.
4. Use `[[wikilinks]]` between derived pages.
5. Add a relative Markdown link and one-line summary to `wiki/index.md`.
6. Append `## [YYYY-MM-DD] ingest | Summary` to `wiki/log.md`.

### Lint

Check stale claims, contradictions, missing index entries, broken links, and
orphan pages. Fix derived pages only and append a `lint` log entry.

## Validation

```bash
git diff --check -- .agents/skills/obsidian-vault/SKILL.md wiki
git status --short -- wiki/raw
test "$(readlink .claude/skills/obsidian-vault)" = "../../.agents/skills/obsidian-vault"
rg -n '/mnt''/d|Mostly'' flat|No'' folders' .agents/skills/obsidian-vault/SKILL.md
```

The final `rg` must return no matches. Before claiming Obsidian visibility,
confirm the registered vault path is the checkout containing the edits; a
worktree-only change becomes visible in the primary vault after it is landed.
Exception: gitignored root daily notes (`YYYY-MM-DD.md`) never land with any
branch — copy them to the main checkout per `session-synthesis`.
