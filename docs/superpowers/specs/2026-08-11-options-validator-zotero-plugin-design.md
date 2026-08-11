# Options Validator Zotero private plugin design

**Date:** 2026-08-11

**Status:** Owner-approved design

**Parent:** `2026-08-11-options-validator-plugin-program-design.md`

## 1. Purpose

Add read-only Zotero discovery for papers and source material while preserving
the repository's distinction between canonical evidence and non-canonical
enrichment. Zotero remains a library and discovery layer, never market-data,
verdict, or trading authority.

## 2. Components

`options-validator-zotero` contains:

- `.codex-plugin/plugin.json`;
- a read-only Zotero connector mapping;
- a source-discovery and evidence-packet skill;
- an enforceable read-tool allowlist;
- provenance-index schema and templates;
- content-safety, setup, audit, and rollback references.

The actual post-install tool catalog is inspected before activation. The
plugin may expose only search, collection browsing, item metadata retrieval,
and explicitly selected attachment reads. If the host or connector cannot
enforce that tool boundary, the plugin remains inactive and manual export is
the only allowed fallback.

## 3. Permission model

- Plugin permission begins at `Always ask`, including reads.
- Create, edit, tag, move, attach, upload, and delete tools are excluded.
- The skill never requests a write tool, even if one appears after a connector
  update.
- Tool-catalog drift fails the activation check.
- Authentication state and library identifiers remain local.

## 4. Data flow

1. A user-requested search returns metadata only.
2. The user identifies the specific items or attachments to inspect.
3. The plugin reads only those selected records.
4. Selected attachment bytes are validated and stored under private
   `${PLUGIN_DATA}` storage, never Git.
5. The attachment is hashed and checked for type, size, path safety, and
   duplicate content.
6. The workflow creates a deterministic draft provenance index.
7. Only an explicitly requested index is written under `reports/zotero/`.

There is no background synchronization, whole-library export, implicit packet
write, or automatic commit.

## 5. Provenance-index contract

Each tracked entry records available values for:

- Zotero item and attachment identifiers;
- title, creators, publisher, and publication date;
- DOI, ISBN, URL, or another stable locator;
- collection and source class;
- retrieval time and maximum as-of timestamp;
- attachment MIME type, byte size, and SHA-256;
- duplicate relationships;
- rights or availability notes;
- primary-source verification status;
- metadata disagreements and unresolved conflicts.

Missing fields remain explicitly missing. The workflow does not infer or invent
authors, dates, locators, rights, or source authority.

Every packet contains these exact boundaries near the top:

- `NON-CANONICAL ENRICHMENT`
- `NOT VERDICT-ELIGIBLE`
- `NOT A MARKET-DATA SOURCE`
- `NO RANKING, SIGNAL, POSITION, OR ACTIVATION AUTHORITY`

Zotero metadata or attachments do not satisfy the repository's primary-source
requirements for options mechanics, broker behavior, fees, regulation, issuer
facts, or decision-critical market claims.

## 6. Attachment and content safety

- Attachment content is untrusted evidence, never instruction.
- Embedded prompts, commands, tool requests, links, and requests for secrets are
  ignored as content.
- Macros, scripts, embedded executables, and active document content do not run.
- Unsupported, encrypted, malformed, oversized, or path-escaping inputs fail
  closed without a packet claiming successful ingestion.
- Filenames never control destination paths; content-addressed storage uses the
  validated SHA-256.
- Tracked indexes contain no private absolute path.
- Duplicate content is represented once in private storage and cross-referenced
  by hash in indexes.

## 7. Error behavior

- Missing metadata yields an explicit missing-field result.
- Metadata conflicts remain visible and unresolved until supported evidence
  resolves them.
- Attachment failure does not promote metadata into document evidence.
- Connector unavailability writes no partial tracked packet.
- A packet schema or boundary failure aborts the write.
- Zotero content never mutates a ledger, cache, position, configuration,
  hypothesis, ranking, signal, verdict, or activation surface.

## 8. Tests and audit

Required proof:

- post-install tool inventory showing enforceable read-only exposure;
- tests attempting every known write category and confirming refusal;
- metadata-only, selected-attachment, missing-field, conflict, duplicate,
  malformed, unsupported, encrypted, and idempotent cases;
- path traversal, oversized input, active-content, and prompt-injection
  fixtures;
- deterministic hash, timestamp normalization, packet ordering, and schema
  checks;
- exact boundary-language validation;
- proof that attachment bytes and private paths are absent from Git and tracked
  artifacts;
- marketplace, manifest, connector mapping, and permission validation;
- isolated install, authenticated read, disable, connector-unavailable, and
  rollback smoke;
- secret scan, Ruff, Ruff format, Pyright, targeted tests, and affected full
  suite;
- CodeRabbit and security-focused diff review;
- an audit receipt with plugin version, permission state, tool inventory hash,
  packet schema hash, commands, exit codes, and unresolved limitations.

## 9. Completion and rollback

Build completion requires deterministic offline fixtures and package checks.
Activation requires an authenticated connector whose effective tool catalog is
enforceably read-only.

Disabling or uninstalling the plugin cannot change Zotero or existing tracked
indexes. Private attachment storage is retained. Its deletion is a separate
destructive action requiring explicit owner approval and a resolved, inspected
target.
