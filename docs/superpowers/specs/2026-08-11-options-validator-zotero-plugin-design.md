# Options Validator Zotero private plugin design

**Date:** 2026-08-11

**Status:** Draft — pending owner review. **Blocked on §10 below.**

> **Provenance correction (2026-08-11).** First committed (`9713dfc`) carrying
> `Status: Owner-approved design`. That label was never true — no owner
> approval had been given or requested. Corrected to the accurate state.

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

## 10. Corpus and question — REQUIRED, currently unanswered

*Added 2026-08-11 by review. Reviewer-drafted; not an owner decision. This
section blocks approval of the rest of this specification.*

Sections 1-9 specify a careful read-only ingestion pipeline — content-addressed
storage, duplicate detection, prompt-injection fixtures, an eleven-field
provenance schema — without ever naming what is in the library or which
decision it changes. Section 5 simultaneously concedes the output is
non-canonical, not verdict-eligible, not market data, and insufficient for the
repository's primary-source requirements. A capability that is none of those
things must state what it *is* for.

The reviewer cannot answer this: the contents of the owner's Zotero library are
not visible from the repository. What follows is two candidate corpora found in
the repository, offered so the owner can confirm, replace, or reject them.

### 10.1 Candidate A — the academic bibliography already in use

`.cursorrules` requires experiment and composite-lane constants to be
"standard-from-literature or official-source conventions frozen in `config.py`
with LLM-proposed provenance labels." The repository already carries a
substantial working bibliography, currently held only as prose inside a report:

- forecast combination — Clemen 1989; Timmermann 2006; DeMiguel, Garlappi &
  Uppal 2009 (`reports/2026-08-04-composite-signal-lane-decision.md:147-148`);
- time-series momentum — Moskowitz, Ooi & Pedersen 2012, *JFE* 104(2), with
  Lo, Mamaysky & Wang 2000 and Sullivan, Timmermann & White 1999 as displayed
  caveats (`:159-163`);
- causal regime labeling — Shu & Mulvey 2024, arXiv:2410.14841; Cederburg,
  O'Doherty, Wang & Yan 2020, *JFE* 138(1) (`:189-193`);
- open-interest change — Fodor, Krieger & Doran 2011, *FMPM* 25(3) (`:198-202`).

**The question this corpus answers:** when a frozen constant is challenged
months later, can its literature provenance be re-verified from a stable
locator rather than from an LLM-written sentence in a report? Today the answer
is no — there is no DOI, no stored PDF, and no retrieval date behind any of
these citations.

### 10.2 Candidate B — the licensed source packages

`docs/superpowers/specs/2026-08-10-vst-post-earnings-analyst-review-design.md`
§3.2 stores a licensed CapitalIQ package outside Git at a private absolute
path, and already tracks the exact concerns this plugin implements by hand:
SHA-256 identity, a two-PDF duplicate collapsed to one underlying source, an
inadmissible placeholder document, and a hard "must not copy licensed PDFs or
long proprietary excerpts into Git" rule.

That is §4-§6 of this specification performed manually. If more such packages
are coming, mechanizing it is defensible.

**Caution:** licensed vendor documents raise a rights question this
specification's "rights or availability notes" field records but does not
resolve. Whether such documents may be held in a personal reference manager is
an owner determination, not an agent one.

### 10.3 Owner questions that gate approval

1. **Which corpus, if either?** If Candidate A, the deliverable is much smaller
   than §1-§9 imply — metadata, DOIs and retrieval dates for perhaps a few
   dozen papers, with attachment handling optional. If Candidate B, the full
   attachment-safety machinery is warranted but the rights question must be
   settled first. If neither, this plugin should be parked in
   `ideas-parking-lot.md` rather than built.
2. **Does the library already exist and roughly how large is it?** The
   specification's cost is dominated by the attachment pipeline. A library of
   forty metadata records and no attachments does not need it.

Until both are answered in writing, sections 1-9 are not approved.
