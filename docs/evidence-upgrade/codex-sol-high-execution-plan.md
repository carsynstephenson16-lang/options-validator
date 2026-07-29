# Codex Execution Plan — Evidence-Ingestion Architecture (EC-1)

Date: 2026-07-29. Target: **GPT-5.6 Sol, reasoning effort High, Codex IDE
extension inside Cursor.** Start every packet in **/plan** mode; implement
only after the plan step confirms repository reality. One Codex thread and
one pull request per packet. Kalshi packets (6–7) share no files, schemas,
or migrations with equity-research packets (1–5) and may run as a parallel
thread; everything else is sequential as ordered.

Companion documents (attach/open in Cursor alongside each packet):
`docs/evidence-upgrade/final-architecture.md` (the contract),
`docs/evidence-upgrade/source-policy.md`, `docs/evidence-upgrade/decision-log.md`.

## Standing instructions for every packet (Codex must follow)

1. Inspect the repository and its active instruction files (AGENTS.md,
   CLAUDE.md, `.cursorrules` where present) before editing. AGENTS.md
   rules bind you.
2. Confirm baseline behavior first: run the repo's suite before changing
   anything; record the exact result.
3. Adapt file paths/commands to observed reality; if reality differs from
   this packet, update the packet's "repository facts" in your PR notes
   and proceed only if the difference is non-material — otherwise STOP and
   report a blocker.
4. Keep changes strictly inside the packet's scope; no unrelated cleanup,
   no premature abstraction, no drive-by refactors.
5. Preserve existing interfaces unless the packet explicitly changes them.
6. Add a regression test for every confirmed failure mode you touch.
7. Run focused tests first, then the full suite; report exact command
   output (kalshi additionally requires the pytest summary line in the
   commit message — its documented convention).
8. STOP and report a blocker if implementation would violate any
   architecture invariant (each packet lists its own).
9. Never: place orders, add live-brokerage connectivity, touch paper-mode
   flags, write `data/portfolio_state.csv`, alter sealed holdouts or
   pre-committed thresholds, register hypotheses, or freeze numbers —
   those are owner-typed acts in these repos.
10. Tests must run offline. No live network call may enter any test or CI
    path. Network-touching code keeps the repos' dry-run-by-default
    convention.
11. Do not redesign the approved architecture. If repository evidence
    invalidates a documented assumption, report it; the planning records
    get updated first.
12. Durable, cross-task rules belong in the repo's AGENTS.md only when
    genuinely durable; keep AGENTS.md concise — task detail stays here.

Baselines (verified 2026-07-29 — re-verify at packet start):

| Repo | Path | HEAD | Suite command | Baseline |
|---|---|---|---|---|
| equity-research | `/Users/carsynstephenson/equity-research` | `adcb0c9` | `.venv/bin/python -m unittest discover -s tests` | 1544–1546 tests OK (~6s; count drifted +2 between two same-day runs at the same HEAD — record your own baseline at packet start and gate on ≥ that) |
| kalshi-weather-bot | `/Users/carsynstephenson/Claude` (work in `claude/`) | `42d3113` | `cd claude && .venv/bin/python -m pytest tests/ -q` | 2252 passed (~17s) |
| options-validator | `/Users/carsynstephenson/options-validator` | `eb97be9` | `uv run python -m unittest discover -s tests` | 2109 tests OK (~4min); also `uv run ruff check .`, `uv run pyright` clean |

---

## Packet 1 — SEC availability rule module + acceptance-time capture (equity-research)

*(Amended 2026-07-29 after Codex /plan preflight — see decision-log D28.
The original packet wrongly told Codex to write acceptance keys into
"per-filing metadata edgar_fetch.py already persists"; no such object
exists in that script. Verified reality: `edgar_fetch.py` writes only
filing documents, symlinks, an append-only `_fetch_log.txt`, and raw
`_companyfacts.json` — while `data/_sec_submissions/<CIK10>.json` (written
by `scripts/validation_gate.py`, present for 33/57 tickers) already caches
SEC's raw submissions JSON including per-filing `acceptanceDateTime`
arrays, and `market_updates/providers.py:162-183` already parses
`acceptanceDateTime` and uses `acceptance or filing_date` as
`published_at` (test-pinned at `tests/test_market_updates.py:64`). So no
new acceptance capture is needed anywhere; the work is the RULE MODULE
(this packet) and the interval WIRING in the store (moved to Packet 2).)*

**Goal:** A pure, versioned rule module `market_updates/sec_availability.py`
that converts an EDGAR acceptance datetime + submission type into
`filing_date`, `earliest_public_ts_utc` (optimistic lower bound), and
`public_by_ts_utc` (conservative gating bound). No persistence, no
fetcher changes, no schema changes in this packet.

**Context:** `market_updates` SEC events currently carry raw acceptance
time as `published_at` (`providers.py:172`), and options-validator's
bridge gates on `published_at <= as_of`
(`options_researcher/market_context.py:87`) — so as-of reads of SEC
events today gate on raw acceptance time, which invariant 8 prohibits
treating as public availability. This module is the versioned rule that
Packet 2 wires into the provider to fix that going forward. The governing
rule is EDGAR Filer Manual
Vol. II v77 §3.2 (wording identical back through v70): transmission
≤ 17:30 ET on an EDGAR business day → same-day filing date; after 17:30 ET
→ next business day 06:00 ET filing date AND no dissemination until the
next business day; 24 exception submission types — verbatim: 3, 3/A, 4,
4/A, 5, 5/A, 144, 144/A, F-1MEF, F-3MEF, F-4MEF, N-14MEF, N-2MEF, POS
462B, S-11MEF, S-1MEF, S-3MEF, S-4MEF, S-BMEF, SC 13D/A, SCHEDULE 13D,
SCHEDULE 13D/A, SCHEDULE 13G, SCHEDULE 13G/A (24 distinct strings; encode
the list, never a count) — keep same-day filing date and disseminate
until 22:00 ET. EDGAR operates 06:00–22:00 ET Mon–Fri excluding the
official federal-holiday list. The SEC does NOT quantify
acceptance-to-public latency anywhere; the "2 minutes" figure circulating
online is absent from the actual PDS spec and is banned from this
codebase.

**Constraints:** Pure functions only — no network, no I/O, no imports
beyond stdlib. The module lives at `market_updates/sec_availability.py`
(`market_updates/` is a real package with normal dotted imports;
`scripts/` is not a package and uses a `sys.path.insert` idiom — placing
the module in the package keeps the Packet-2 wiring a clean import). All
zone math via `zoneinfo.ZoneInfo("America/New_York")`; never a fixed UTC
offset. `tzdata` pinned in dev requirements. Do NOT touch
`scripts/edgar_fetch.py`, `market_updates/providers.py`, or any storage/
schema code in this packet. No lint config may be added to this repo.

**Done when:** the new module passes the full boundary-test matrix below;
full suite ≥ baseline (record it at start; last observed 1544–1546) OK;
no test touches the network; no file outside the module, its test, and
`requirements-dev.txt` is modified.

- **Repos / working directory:** `/Users/carsynstephenson/equity-research`.
- **Open in Cursor:** `market_updates/providers.py` (read-only context:
  lines 160-185, the acceptance→published_at path this rule will later
  govern), `tests/test_market_updates.py` (test conventions),
  `requirements-dev.txt`, `docs/evidence-upgrade/final-architecture.md`
  §6.1, `docs/evidence-upgrade/decision-log.md` D05/D28.
- **Repository facts to verify before editing:** (a)
  `market_updates/providers.py` parses `acceptanceDateTime` (~line 162)
  and computes `published = _date_or_now(acceptance or filing_date,
  retrieved_at)` (~line 172); (b) `market_updates/` is a package
  (normal imports) and no `market_updates/sec_availability.py` exists
  yet; (c) tests run with `.venv/bin/python -m unittest discover -s
  tests` — record the baseline count you observe.
- **Preconditions:** clean working tree (`data/pick_dashboard/
  timeline_ledger.json` may show a pre-existing local modification —
  leave it untouched); baseline suite green.
- **Exact scope:**
  1. Create `market_updates/sec_availability.py`:
     - `RULE_VERSION = "EDGAR-FilerManual-v77-2026-03-16"`.
     - `EXCEPTION_FORMS: frozenset[str]` with the 24 types above,
       transcribed verbatim (normalize case/whitespace on comparison).
     - `EDGAR_HOLIDAYS_2026: frozenset[date]` (from the official EDGAR
       calendar; structure so future years append).
     - `def availability(acceptance_et: datetime, form_type: str) ->
       SecAvailability` returning a frozen dataclass with
       `acceptance_ts_utc`, `filing_date`, `earliest_public_ts_utc`,
       `public_by_ts_utc`, `rule_version`, `tzdata_version` (from
       `importlib.metadata.version("tzdata")`, with a documented fallback
       string `"system-zoneinfo"` when the package is absent).
     - Rule: tz-aware input required (raise `ValueError` on naive);
       convert to America/New_York; apply the 17:30/22:00/exception/
       business-day/holiday logic exactly as in Context. Availability is
       an INTERVAL: `earliest_public_ts_utc` = acceptance instant for
       in-window/exception cases, else next business day 06:00 ET —
       docstring must label it an optimistic lower bound (PDS
       dissemination lag is nonzero and unquantified);
       `public_by_ts_utc` = 22:00 ET on the dissemination business day
       (same day for in-window/exception; next business day for
       after-hours non-exception) — the conservative bound that
       look-ahead-sensitive consumers gate on (it becomes `available_at`
       for `sec.filing_event` claims).
- **Out of scope:** ANY edit to `scripts/edgar_fetch.py` (it has no
  per-filing metadata object; a sidecar was considered and REJECTED —
  acceptance data is already durably cached in
  `data/_sec_submissions/<CIK10>.json` where present); any edit to
  `market_updates/providers.py`/`models.py`/`normalizer.py`/`storage.py`
  (interval wiring is Packet 2); any schema/database work (packet 2);
  XBRL endpoints (packet 4); registry (packet 3); backfilling old
  filings; touching `scripts/validation_gate.py` (frozen); retroactive
  changes to `published_at` semantics or stored rows (append-only —
  legacy rows get labeled at the consumer in Packet 8, never rewritten).
- **Invariants:** raw acceptance time is never presented as exact public
  availability; no naive datetimes; pure module only.
- **Expected files changed:** `market_updates/sec_availability.py` (new),
  `tests/test_sec_availability.py` (new), `requirements-dev.txt`
  (add pinned `tzdata`). Nothing else.
- **Implementation sequence:** write the failing boundary tests first →
  run them (expect import failure) → implement the module → make tests
  pass → focused tests → full suite.
- **Schema/API effects:** new pure-module API only; no schema, no
  persistence, no behavior change anywhere else.
- **Data migration:** none.
- **Fixtures and tests (the required matrix — implement every row):**
  winter (EST) 17:29 ET → same day; winter 17:31 ET non-exception → next
  business day + earliest_public next day 06:00 ET; summer (EDT) same
  pair (UTC offsets differ — assert the UTC instants, not just dates);
  exception form (e.g. `4`) at 21:59 ET → same-day filing date, earliest
  public = acceptance; exception form at 22:01 ET → next business day;
  Friday 17:31 ET → Monday; day-before-holiday 17:31 ET → skips the
  holiday; DST-transition dates (2026-03-08, 2026-11-01) round-trip
  correctly; naive datetime raises `ValueError`; `SCHEDULE 13G/A`
  (exception) vs `10-K` (not) same instant differ as specified;
  `public_by_ts_utc` cases: in-window filing → same day 22:00 ET (assert
  the UTC instant in both EST and EDT); after-hours non-exception →
  next business day 22:00 ET; exception form 21:59 ET → same day
  22:00 ET; and `earliest_public_ts_utc < public_by_ts_utc` holds in
  every generated case.
- **Validation commands:**
  `.venv/bin/python -m unittest tests.test_sec_availability -v` (all pass)
  then `.venv/bin/python -m unittest discover -s tests` (≥1544, OK) and
  `python3 -m compileall -q scripts` (exit 0).
- **Failure/rollback:** pure additive packet — revert the branch; no data
  effects.
- **Depends on:** nothing.
- **Review checklist:** no fixed UTC offsets anywhere; exception list
  matches the verbatim 24-string list above (check the list, not a
  count); no "2 minutes" or any latency constant; `earliest_public`
  never used as `available_at`; no network in tests; diff touches only
  the three expected files.
- **Evidence references:** `source-ledger.csv` SEC-S1..SEC-S9, SEC-S12;
  decision-log D05, D06 (as amended), D28.

---

## Packet 2 — Alembic baseline + evidence-store expansion (equity-research)

**Goal:** Bring `market_updates/` SQLite storage under Alembic (batch
mode), add the EC-1 bitemporal/admission/freshness/independence columns,
make the raw payload archive content-addressed, and add an append-only
ingestion journal.

**Context:** `market_updates/storage.py` hand-rolls
`CREATE TABLE IF NOT EXISTS` with `SCHEMA_VERSION = 1` in a
`schema_version` table; the `events` table already carries `event_id`
(identity sha256), `source_name`, `trust_level`, `published_at`,
`retrieved_at`, `effective_at`, `content_hash`, `raw_payload_reference`.
`market_updates/service.py` `RawPayloadArchive.write()` stores gzip JSON
at `<provider>_<item_id>.json.gz` with skip-if-exists — a changed payload
for the same id is silently never re-archived (confirmed data-loss bug).
The DB lives under `market_updates/.local/` (gitignored) in WAL mode.
SQLite's WAL-Reset corruption bug affects versions < 3.51.3 under
concurrent multi-writer WAL. Additionally (verified 2026-07-29, D28):
`providers.py:172` sets `published = _date_or_now(acceptance or
filing_date, retrieved_at)` for SEC submissions events — raw acceptance
time flows into `published_at`, which the options-validator bridge gates
on; the local store already holds ~2,557 such rows. This packet wires the
Packet-1 rule module into the SEC provider so `available_at` carries the
conservative bound going forward (legacy rows untouched — append-only).

**Constraints:** Expand-phase only: every column additive and nullable
(or defaulted); no existing reader/writer breaks. Dual-write the raw
archive (old id-keyed path + new content-addressed path) — removal of the
old path is a later contract phase, not this packet. The consumer bridge
(options-validator `market_context.py`) must keep working unchanged
against a migrated DB.

**Done when:** `alembic upgrade head` on a copy of a real DB passes the
reconciliation checks; dual-write verified by tests; new SEC submissions
events carry the availability interval with `available_at =
public_by_ts_utc` while Atom-path and legacy rows are labeled, not
guessed; full suite ≥ recorded baseline OK.

- **Repos / working directory:** `/Users/carsynstephenson/equity-research`.
- **Open in Cursor:** `market_updates/storage.py`,
  `market_updates/service.py`, `market_updates/models.py`,
  `market_updates/normalizer.py`, `market_updates/providers.py`
  (lines 150-290), `market_updates/sec_availability.py` (from Packet 1),
  `docs/market_updates.md`,
  `docs/evidence-upgrade/final-architecture.md` §4, §6.1, §10.
- **Repository facts to verify:** exact current DDL of `events`,
  `source_items`, `provider_state`, `provider_runs`; how
  `schema_version` is written; where `RawPayloadArchive` is constructed;
  that no Alembic config exists anywhere yet; Python/SQLite versions in
  `.venv` (`python -c "import sqlite3;print(sqlite3.sqlite_version)"`).
- **Preconditions:** packet 1 merged (not a code dependency — ordering
  keeps one PR in flight per repo); baseline suite green; copy an
  existing `.local` DB (or synthesize one via the store's own API) for
  migration rehearsal.
- **Exact scope:**
  1. Add `alembic` to `requirements-dev.txt` (pinned); create
     `market_updates/migrations/` with `alembic.ini` + `env.py`
     configured `render_as_batch=True`, DB URL supplied at runtime (the
     store owns the path — no hardcoded absolute paths).
  2. Migration 0001 "baseline": captures the CURRENT observed schema
     exactly; stamps existing DBs (`alembic stamp` semantics — detect the
     legacy `schema_version` row and record it as superseded, do not
     delete it).
  3. Migration 0002 "ec1-expand" (classification: additive-expand,
     reversible): on `events` add nullable columns `observed_at`,
     `available_at`, `recorded_at`, `freshness_class`, `stale_after`,
     `admission_state` (default `'PENDING'` for new rows; backfill
     existing rows to `'ADMITTED'` with journal note — they were already
     consumed), `admission_reason`, `independence_group`,
     `purpose_authority` (default `'decision'` — matches current use),
     `verify_support_status` (default `'not_checked'`),
     `confidence_level`, `superseded_by`, `raw_sha256`,
     `selector_version`, `registry_version`, `run_id`. New tables:
     `ingestion_journal` (append-only: `journal_id` PK autoincrement,
     `recorded_at` system-assigned, `event_kind`, `payload_json`) and
     `run_evidence` (`run_id`, `event_id`, composite PK) with an index
     each direction.
  4. `storage.py`: writers populate `recorded_at` (system UTC now, not
     caller-supplied) and the new fields when provided; a guard method
     refuses UPDATEs to admitted rows' payload fields (supersede
     instead); every insert appends one `ingestion_journal` row in the
     same transaction.
  5. `service.py`: `RawPayloadArchive.write()` computes sha256 of the
     canonical payload bytes, writes `blobs/<sha[:2]>/<sha>.json.gz`
     (atomic tempfile+fsync+rename, skip-if-exists — mirror the kalshi
     `capture_raw_payload` layout), AND keeps writing the legacy id-keyed
     path when absent (dual-write); returns the sha; `events.raw_sha256`
     stores it. Shadow-read helper compares legacy vs new for the same
     item and logs mismatches (this is where the changed-payload-same-id
     bug becomes visible instead of silent).
  6. SQLite safety enforcement (measured 2026-07-29: this venv's SQLite
     is 3.50.4 — BELOW the safe floor of ≥3.51.3 / backports
     3.44.6/3.50.7 — and `storage.py` already sets
     `PRAGMA journal_mode = WAL`, the mode the documented WAL-Reset
     corruption bug affects under concurrent writers):
     `_sqlite_wal_safe() -> bool` checks
     `sqlite3.sqlite_version_info >= (3, 51, 3)` or exact backport
     versions (3, 44, 6) / (3, 50, 7). When UNSAFE, single-writer access
     is mechanically enforced: an exclusive, non-blocking `flock` on a
     lock file beside the DB, acquired at write-session open; a second
     concurrent writer raises a typed `ConcurrentWriterError`
     (fail-closed — never a warning). Record the engine version and
     which control was active on `provider_runs` receipts. Note in
     `docs/market_updates.md`: reaching a safe engine requires a newer
     Python build or a bundled-SQLite package — an owner decision;
     `requirements-dev.txt` pins cannot change the stdlib engine.
     Tests: version-gate unit test (monkeypatched version tuples incl.
     both backports); lock-contention test (two write sessions, second
     raises).
  7. SEC availability-interval wiring (uses Packet 1's
     `market_updates/sec_availability.py`): `models.py` gains optional
     fields `acceptance_ts_utc`, `earliest_public_ts_utc`,
     `public_by_ts_utc`, `availability_rule_version` on
     `RawSourceItem`/`MarketEvent` (+ `event_to_dict`);
     `providers.py::parse_sec_submissions` computes the interval from
     `acceptanceDateTime` + form type and sets them; `normalizer.py`
     passes them through; `storage.py` persists them (columns are part of
     migration 0002) and sets `available_at = public_by_ts_utc` for
     submissions-path SEC events going forward. `published_at` semantics
     are UNCHANGED (provider-asserted timestamp; append-only history —
     existing rows are never rewritten; consumers label legacy rows per
     Packet 8). The Atom-feed path (`_feed_entries`) has no
     acceptanceDateTime: leave its `available_at` null with reason
     `availability_basis="feed-timestamp-unruled"` recorded in the
     payload — never guess an interval for it. Tests: submissions-path
     event carries the interval and `available_at == public_by_ts_utc`
     (both an in-window and an after-hours fixture); Atom-path event has
     null `available_at` + the reason; existing pinned tests
     (`tests/test_market_updates.py:56,72,151,236`) stay green unmodified.
- **Out of scope:** registry (3), XBRL (4), admission gates (5), any
  consumer changes, removing the legacy archive path, kalshi/
  options-validator files, retroactive edits to existing rows'
  `published_at`/`available_at`, and ANY edit to `scripts/edgar_fetch.py`.
- **Invariants:** append-only discipline (no in-place payload rewrites);
  naive datetimes refused; consumer bridge untouched and still green.
- **Expected files changed:** `market_updates/migrations/*` (new),
  `market_updates/storage.py`, `market_updates/service.py`,
  `market_updates/models.py`, `market_updates/providers.py`,
  `market_updates/normalizer.py`, `requirements-dev.txt`,
  `docs/market_updates.md` (schema section), new tests
  `tests/test_market_updates_migrations.py`,
  `tests/test_raw_archive_content_addressing.py`,
  `tests/test_sec_availability_wiring.py`.
- **Implementation sequence:** failing tests for the changed-payload bug
  and for `recorded_at` system-assignment → baseline migration → expand
  migration → storage/service changes → migration rehearsal on the copied
  DB with reconciliation → full suite.
- **Schema/API effects:** as in scope; `SCHEMA_VERSION` constant retired
  in favor of Alembic revision (legacy row preserved).
- **Data migration behavior:** expand-phase; reversible downgrade for
  0002 (drops added columns/tables — allowed because nothing depends on
  them yet); rehearsal required: run upgrade on a copy, then verify
  (a) row counts per table unchanged, (b) sum of `content_hash` values
  unchanged, (c) bridge query (`published_at <= as_of`) returns identical
  results pre/post. Keep the rehearsal transcript in the PR.
- **Fixtures/tests:** migration up+down on temp DB; dual-write both paths
  exist and hashes match; changed-payload-same-id now archives a second
  blob and logs; journal rows appended per insert and never deleted;
  UPDATE-refusal guard; SQLite version gate + writer-lock contention
  behavior (as specified in scope item 6).
- **Validation commands:**
  `.venv/bin/python -m unittest tests.test_market_updates_migrations tests.test_raw_archive_content_addressing -v`,
  then full suite, then `python3 -m compileall -q scripts`.
- **Failure/rollback:** migrations rehearsed on copies; production `.local`
  DB migrates only after suite green; rollback = `alembic downgrade -1`
  (0002 only) or restore the copied DB file. Never claim downgrade for
  any future lossy migration.
- **Depends on:** packet 1 merged (ordering only).
- **Review checklist:** batch mode actually used for any constraint
  change; no absolute paths; journal is append-only (no delete/update
  API); dual-write keeps legacy readers working; WAL safety enforced
  (version gate + writer lock, fail-closed — not a warning).
- **Evidence references:** decision-log D03, D04, D15, D20, D22;
  FRM-S7 group; equity-research audit §§4, 8–10, 12.

---

## Packet 3 — Source registry v1 + claim-type authority rules (equity-research)

**Goal:** A declarative, versioned source registry file + loader that
encodes the source hierarchy, claim-type authority rules, purposes, and
bans, and stamps `registry_version` onto capture receipts.

**Context:** Authority rules currently live in prose (AGENTS.md SOURCE
HIERARCHY lines ~124–134 and PLUGIN OUTPUT INTEGRATION ~136–173) and in
scattered code. `integrations/repo_rag/policy.json` shows the repo's
existing minimal-policy-file shape. `market_updates/providers.py` defines
nine typed providers whose identities seed the registry.

**Constraints:** The registry must not weaken any existing ban
(Daloopa/Capital IQ/Kensho/LSEG citation bans; TipRanks exclusion) — they
are encoded, and a test locks them. Registry edits are supersessions: the
file carries `registry_version` (content hash of entries) and a
`supersedes` field; the loader refuses an entry-edit that reuses a prior
version id.

**Done when:** loader validates the schema; providers resolve their
registry entries; `provider_runs` receipts include `registry_version`;
ban tests pass; full suite green.

- **Working directory:** `/Users/carsynstephenson/equity-research`.
- **Open in Cursor:** `AGENTS.md` (both sections above),
  `integrations/repo_rag/policy.json`, `market_updates/providers.py`,
  `market_updates/service.py`, `source-policy.md` §1–2,
  `final-architecture.md` §5.
- **Repository facts to verify:** provider names as implemented; where
  `provider_runs` receipts are written; that no `source_registry` file
  exists yet.
- **Preconditions:** packet 2 merged (receipts carry `registry_version`
  column-side via `provider_runs` — verify the column exists or add it in
  a tiny additive migration 0003 in THIS packet).
- **Exact scope:** create `data/source_registry.json` (schema
  `ec1-source-registry/v1` per final-architecture §5) with entries for:
  the ten market_updates providers (verified in `providers.py`:
  SecEdgar, CompanyIr, Gdelt, FederalReserveRss, Fred, Bls, Bea, Eia,
  TreasuryFiscalData, TwelveData — enumerate from `build_providers()`
  at implementation time, not from this count), sec-edgar-companyfacts (for packet
  4), sec-edgar-archives-html (fallback, `display_only`), the banned
  plugin families (`allowed_purposes: []`), and stockanalysis.com
  (tier-2, `display_only` for numerics per D07). Create
  `market_updates/registry.py`: `load_registry(path) -> Registry` with
  full schema validation (unknown keys rejected; every entry requires
  authority_class ∈ the six classes, scope_claim_types non-empty,
  allowed_purposes ⊆ {decision, display_only, discovery});
  `Registry.entry_for(source_id)`, `Registry.authority_ok(source_id,
  claim_type, purpose) -> bool` (scope-beats-rank: out-of-scope always
  False regardless of class); `registry_version` = sha256 over canonical
  JSON of entries. Wire `service.py` runs to load the registry once and
  stamp `registry_version` on run receipts.
- **Out of scope:** enforcement at admission time (packet 5); registries
  in the other two repos (their packets); AGENTS.md rewrites (add only a
  two-line pointer to the registry file under SOURCE HIERARCHY).
- **Invariants:** bans preserved verbatim; registry supersession only.
- **Expected files:** `data/source_registry.json` (new),
  `market_updates/registry.py` (new), `market_updates/service.py`
  (stamping), possible migration 0003 (additive `registry_version` on
  `provider_runs`), `tests/test_source_registry.py` (new), `AGENTS.md`
  (two-line pointer).
- **Implementation sequence:** failing tests (schema validation; ban
  lock; scope-beats-rank; version stamping) → registry file → loader →
  wiring → suites.
- **Schema/API effects:** new file + module; one additive column at most.
- **Data migration:** none beyond the optional additive column.
- **Fixtures/tests:** malformed registry rejected (unknown key, empty
  scope, bad class); `authority_ok` truth table incl. out-of-scope
  high-authority → False; banned source + any purpose → False; version
  changes when entries change; stable when whitespace changes.
- **Validation:** focused test module, then full suite.
- **Failure/rollback:** additive; revert branch.
- **Depends on:** packet 2.
- **Review checklist:** no ban weakened; loader refuses silently-edited
  versions; canonical JSON hashing matches `research/hashing.py`-style
  sorted-keys convention (document the exact canonicalization in the
  module docstring).
- **Evidence references:** decision-log D07 (rule), D12, D26;
  equity-research audit §11; source-policy §2.

---

## Packet 4 — XBRL structured-facts fetcher + as-first-reported queries (equity-research)

**Goal:** Fetch numeric financial facts from `data.sec.gov` structured
endpoints with `accn`/`form`/`filed` recorded per fact, stored under EC-1
fields, with an as-of query API that never returns facts unavailable at
the queried instant.

**Context:** The repo already caches `companyfacts` JSON per ticker (via
`edgar_fetch.py`) but numeric extraction for analyses is scrape/LLM-read
based. The `companyconcept` API returns each fact with `accn`, `form`,
`filed`, `fy`, `fp`, `start`/`end` (verified by a live call this cycle).
SEC staff guidance flags custom XBRL tags as comparability risks.

**Constraints:** SEC fair-access pattern copied from `edgar_fetch.py`
(descriptive UA from `SEC_EDGAR_USER_EMAIL`, ≥0.15s spacing, retry only
on 408/429/5xx). All network behind the existing fetch-then-cache
convention; tests run on recorded fixtures only. Facts store is
append-only: a later filing restating a period appends a new row
(`supersedes` link), never overwrites.

**Done when:** for a fixture ticker, `fact_asof("Revenues", period_end,
as_of)` returns the value first available on/before `as_of` with its
accession number, and returns the restated value only for `as_of` ≥ the
restating filing's availability; suite green.

- **Working directory:** `/Users/carsynstephenson/equity-research`.
- **Open in Cursor:** `scripts/edgar_fetch.py` (fair-access + caching
  conventions), `market_updates/sec_availability.py` (packet 1; scripts/
  is not a package — import it by adding the repo root to `sys.path`,
  matching the existing scripts idiom),
  `market_updates/storage.py` + `registry.py` (packets 2–3),
  `final-architecture.md` §4, §6.1; `source-policy.md` §2.
- **Repository facts to verify:** where companyfacts JSON is cached today
  and its exact shape; whether any existing code parses XBRL units.
- **Preconditions:** packets 1–3 merged.
- **Exact scope:** new module `scripts/xbrl_facts.py`:
  `fetch_companyconcept(cik, taxonomy, tag)` (network, cached to
  `data/_sec_xbrl/<CIK10>_<taxonomy>_<tag>.json`, fair-access);
  `ingest_concept(json_blob) -> list[FactRow]` (pure) mapping each unit
  entry to a row: value, unit, period start/end, `accn`, `form`,
  `filed`, `frame` if present, `is_custom_tag` (taxonomy not in
  {us-gaap, dei, srt, ifrs-full} ⇒ True ⇒ `confidence_level` downgraded
  one step with logged reason `custom-xbrl-tag`), `observed_at` =
  period end, `available_at` = availability rule applied to the filing
  (packet 1 module; when only `filed` date is known use next business
  day 06:00 ET conservative bound and record
  `availability_basis="filed-date-conservative"`), `claim_type` =
  `sec.numeric_fact`, `source_id` = `sec-edgar-companyfacts`;
  storage into the packet-2 store (or a dedicated `xbrl_facts` table via
  additive migration 0004 if the events table shape fits poorly — Codex
  decides in /plan and justifies); `fact_asof(tag, period_end, as_of)`
  pure query implementing as-first-reported semantics.
- **Out of scope:** rewriting analyses to consume this (a later
  owner-driven change); frames bulk endpoints; non-numeric facts.
- **Invariants:** append-only; availability computed only by the
  versioned rule; scraped numerics remain `display_only` (registry).
- **Expected files:** `scripts/xbrl_facts.py`, migration 0004 if chosen,
  `tests/test_xbrl_facts.py` + fixture JSON (recorded once, committed),
  registry already contains the source (packet 3).
- **Implementation sequence:** commit a real recorded `companyconcept`
  fixture → failing tests for `ingest_concept` and `fact_asof`
  (restatement case: two accessions, same period, different values) →
  implement pure parts → network fetcher last → suites.
- **Schema/API effects:** possible `xbrl_facts` table; new module API.
- **Data migration:** additive only.
- **Fixtures/tests:** ingest maps `accn`/`form`/`filed` correctly;
  custom-tag downgrade fires with logged reason; `fact_asof` before/after
  restatement availability; naive `as_of` refused; no-network-in-tests
  guard (mock/injected opener like `test_macro_refresh.py`).
- **Validation:** focused module, full suite, compileall.
- **Failure/rollback:** additive; revert branch.
- **Depends on:** packets 1, 2, 3.
- **Review checklist:** conservative availability basis recorded when
  acceptance time unknown; no silent replacement of restated values;
  rate limiting present; fixture is a genuine recorded response.
- **Evidence references:** decision-log D07, D08; IMP-S05..S08; SEC-S1.

---

## Packet 5 — Admission gates, verify-support, lineage junctions (equity-research)

**Goal:** Enforce EC-1 admission at write time: hard per-dimension gates,
typed quarantine/rejection reasons, conflict edges, the double-order
verify-support step for LLM-extracted claims, run↔evidence lineage, and
per-artifact reproducibility manifests.

**Context:** After packets 2–4 the store has the fields; nothing yet
*enforces* them. The admission design is final-architecture §8; judge
bias evidence mandates double-order agreement for any LLM verdict.
`scripts/validation_gate.py` is frozen (no new checks there) — admission
lives in `market_updates/`, not in the analysis validator.

**Constraints:** Admission is code-rule-based; the ONLY LLM involvement
is the verify-support check, which runs as a manual/scheduled research
utility — never inside unittest/CI (CI uses recorded verdict fixtures).
An extractor's own call can never set `verify_support_status=supported`
for itself (separate invocation, recorded prompts/outputs).

**Done when:** every insert lands `ADMITTED` only by passing gates 1–3
(+4 where required, from recorded verdicts; +5–6 where the claim type
requires), otherwise `QUARANTINED`/`REJECTED` with a typed reason;
lineage junction populated; high-volume test passes; suite green.

- **Working directory:** `/Users/carsynstephenson/equity-research`.
- **Open in Cursor:** `market_updates/storage.py`, `registry.py`,
  `normalizer.py`, `service.py`, `final-architecture.md` §8–9,
  `source-policy.md` §8.
- **Repository facts to verify:** insert paths all flow through one
  storage chokepoint (if not, list them all in /plan before coding).
- **Preconditions:** packets 2–4 merged.
- **Exact scope:** new module `market_updates/admission.py`:
  `admit(record, registry, now) -> AdmissionResult` applying, in order:
  authority-in-scope (registry), temporal safety (`available_at` present
  & rule-versioned; quarantine `recorded_at < available_at` reason
  `lookahead-violation`), extraction integrity (selector/layered hashes
  present for typed claims), verify-support requirement routing
  (claim types configured `requires_support=True` must carry a
  `supported` recorded verdict; `display_only` may be `not_checked`),
  freshness (`stale_after` in future), corroboration where configured
  (distinct `independence_group` count). Typed reason enum (one string
  namespace, e.g. `authority-out-of-scope`, `temporal-missing-availability`,
  `lookahead-violation`, `drift-selector-mismatch`, `support-failed`,
  `support-disagreement`, `stale-at-admission`,
  `corroboration-insufficient`). Conflict edges: `conflicts_with` table +
  both records quarantined reason `conflict-unresolved`.
  **Legacy grandfathering (D32, added 2026-07-29):** migration 0002 executed
  `UPDATE events SET admission_state='ADMITTED'` across every pre-existing
  row while leaving `admission_reason` NULL, and journalled the rationale
  ("rows predate admission-state enforcement and were already consumable")
  only in `ingestion_journal` — so nothing *on the row* distinguishes
  evidence that passed gates from evidence that predates them, and the
  packet-8 consumer would read both as fully gated. Migration 0006 must
  stamp `admission_reason='legacy-grandfathered'` on exactly the rows that
  are `ADMITTED` with a NULL `admission_reason` at migration time (the 0003
  trigger permits this: `admission_reason` is one of its three allowed
  lifecycle columns). Do NOT re-run gates retroactively, do not change any
  other column, and do not alter `admission_state`. Add a test asserting a
  legacy row ends up ADMITTED + `legacy-grandfathered` while a
  gate-admitted row carries its real reason.
  `market_updates/verify_support.py`: takes (claim text, source span),
  runs TWO judged calls with swapped presentation order via an injected
  judge callable (the real judge binding is a thin CLI for manual runs;
  tests inject fakes), verdict `supported` only on agreement,
  `support-disagreement` otherwise; stores both raw verdicts.
  Lineage: populate `run_evidence` in bounded batches (≤500/executemany)
  from the ingestion path; run receipts extended with aggregate counts
  {seen, admitted, quarantined, rejected}. Reproducibility manifest
  helper `market_updates/manifest.py`: `write_manifest(artifact_path,
  command, extra)` records git commit, requirements-dev hash, timestamp,
  raw-data pointers → `<artifact>.manifest.json`.
- **Out of scope:** consumer-side read filtering (packet 8 pattern is
  options-validator's; equity-research consumers adopt in a later
  owner-scheduled pass); any change to `validation_gate.py`; golden
  benchmark (packet 9).
- **Invariants:** no composite score anywhere — gates + ordinal level
  with logged movement reasons only; LLM never fetches+validates+promotes
  in one step.
- **Expected files:** `market_updates/admission.py`,
  `market_updates/verify_support.py`, `market_updates/manifest.py` (all
  new), `market_updates/storage.py` + `service.py` (wiring), migration
  **0006** (additive: `conflicts_with` table; run-receipt count columns;
  legacy-grandfathered stamp per D32) — renumbered 2026-07-29 (D31): the
  chain in `market_updates/migrations/versions/` now reads 0001 legacy
  baseline, 0002 EC-1 expand, 0003 admitted immutability, 0004 provider-run
  registry version (packet 3), 0005 xbrl_facts (packet 4); confirm the head
  revision before authoring,
  tests `tests/test_admission.py`, `tests/test_verify_support.py`,
  `tests/test_lineage_volume.py`.
- **Implementation sequence:** failing tests per gate (one test per
  reason code) → admission module → conflict edges → verify-support with
  injected fake judges (agree/disagree/order-sensitivity cases) → lineage
  batches + high-volume test (10,000 links; assert both directions query
  under a bounded time/row budget and memory stays flat via iterator) →
  manifest helper → wiring → suites.
- **Schema/API effects:** migration 0006 additive.
- **Data migration:** additive only, plus the D32 legacy stamp (an UPDATE of
  `admission_reason` only, on rows where it is currently NULL — permitted by
  the 0003 trigger, which allows lifecycle updates to `admission_state`,
  `admission_reason`, and `superseded_by` on ADMITTED rows).
- **Fixtures/tests:** as enumerated; plus: ordinal `confidence_level`
  reproduces from its logged reasons (property-style test over the reason
  set); an extractor-supplied `supported` without recorded double-order
  verdicts is refused.
- **Validation:** focused modules → full suite → compileall.
- **Failure/rollback:** additive; revert branch. Admission can be
  feature-flagged default-on with an env kill-switch documented in
  `docs/market_updates.md` (flag removed at contract stabilization).
- **Depends on:** packets 2, 3, 4.
- **Review checklist:** every reason code has a test; no LLM call in any
  test; junction inserts bounded; receipts carry aggregates; both
  conflict sides quarantined.
- **Evidence references:** decision-log D12, D13, D14, D16, D17, D25;
  FRM-S3/S4/S6; IMP-S01/S02/S04.

---

## Packet 6 — CLI version chain, BBB parsing, quarantine, determination freeze, exchange settlement capture (kalshi)

**Goal:** Version-chain NWS CLI products (issuance-time + BBB ordered),
quarantine contradictory chains, freeze settlement labels on Kalshi's own
contract-terms schedule, and record the exchange's actual settlement
values.

**Context:** `data/nws_cli_client.py` already parses CLI text fail-closed
on morning partials. `storage/research_provenance.py` provides
content-addressed blobs + immutable typed tables incl.
`weather_verifications` and `exchange_settlements`;
`engine/settlement_parity.observed_max_so_far()` combines CLI max with
live station max. No CLI version ordering or quarantine exists; the bot
computes its own settled view and (verified in audit) has no adapter
polling Kalshi's actual market `result`/`settlement_value`. Governing
facts: WMO-386 §2.3.2.2 + Attachment II-12 (BBB = RRx/CCx/AAx, x=A..X,
Y lost-sequence, Z >24h-late; no Pxx defined); NWSI 10-1004 §4.1 (CLI ≥
twice daily; morning issuance = complete prior LST day; afternoon =
current-day partial; corrections "as needed"); NHIGH contract terms
(freeze at first 7/8 AM ET after release or +1 week; delay to 11 AM ET on
METAR inconsistency or later-lower-high; post-expiration revisions
ignored); Kalshi market status lifecycle `determined → disputed/amended →
finalized`.

**Constraints:** Work in `claude/`; respect the PreToolUse guard (touch
none of `config.py`, `strategy_config.py`, `engine/ev_engine.py`,
`engine/validator.py`). Research-provenance write paths only — the live
decision path must not gain new imports from this packet (mirror the
shadow-isolation discipline). All UTC tz-aware; commit message carries
the pytest summary line. Tests offline (mock urlopen per repo
convention).

**Done when:** for fixture chains, ordering/quarantine/freeze behave per
the matrix below; exchange settlements persist idempotently; 2252 + new
tests pass.

- **Repos / working directory:** `/Users/carsynstephenson/Claude`, work
  in `claude/`.
- **Open in Cursor:** `data/nws_cli_client.py`,
  `storage/research_provenance.py`, `storage/database.py`,
  `engine/settlement_parity.py`, `market_metadata.py`,
  `data/stations.py`, `docs/forecast-run-provenance.md`, AGENTS.md
  (Naming Conventions, Settlement Stations), `final-architecture.md`
  §6.2, decision-log D09–D11.
- **Repository facts to verify:** exact `cli_reports` schema and writers;
  whether the raw WMO heading line is currently retained by the CLI
  fetch; current writers (if any) of `exchange_settlements`; the exact
  public API base already used by `market_metadata.py` (reuse it — do not
  hardcode a new host); station/city ticker mapping.
- **Preconditions:** baseline suite green (2252).
- **Exact scope:**
  1. `data/wmo_heading.py` (new, pure): parse
     `T1T2A1A2ii CCCC YYGGgg [BBB]` → dataclass {ttaaii, cccc,
     day, hour, minute, bbb_type ∈ {RR, CC, AA, None},
     bbb_seq ∈ A..Z, raw}; unknown/malformed BBB (incl. any `P..` form)
     → `bbb_type="UNRECOGNIZED"` (never guess).
  2. Research-provenance table `cli_product_versions` (immutable-insert
     pattern): city_code, climate_date (LST day), issuance dhm (UTC),
     bbb fields, observed_max_f (nullable), is_partial,
     raw_blob_sha256 (content-addressed full product text),
     received_at, chain ordering key = (issuance, bbb category order
     initial<RR<CC/AA sequence), receipt-time fallback ONLY when two
     headings tie — logged with reason `bbb-fallback-receipt-order`.
  3. Quarantine evaluation `storage/cli_chain.py`:
     `evaluate_chain(rows, station_obs_max) -> ChainStatus` with typed
     reasons: `later-lower-high`, `parity-mismatch` (vs
     `observed_max_so_far`), `bbb-sequence-gap`, `bbb-unrecognized`;
     quarantined chains are excluded from label eligibility.
  4. Determination freeze `storage/settlement_label.py`: compute
     label lifecycle {PENDING, DETERMINED, DELAYED_REVIEW, AMENDED,
     FINALIZED} mirroring the contract terms: freeze at the first
     7:00/8:00 AM ET after a complete (non-partial) CLI for the climate
     day exists, outer bound climate_date + 7 days; enter DELAYED_REVIEW
     (11:00 AM ET) on either quarantine reason (1)/(2) analogues;
     versions arriving after freeze recorded but marked
     `post_expiration=True` and never change the frozen label; keep
     accepting versions through Settlement Date (+1 day).
  5. Exchange settlement capture: extend the existing Kalshi client
     surface (verified in /plan) with a research-only poll of settled
     markets for tracked tickers → `exchange_settlements` immutable
     insert {ticker, market_id, result, settlement_value, determined_at,
     finalized_at, raw_blob_sha256}; a comparison helper flags
     label-vs-exchange divergence (typed reason `label-exchange-mismatch`
     → human-review artifact, not an auto-correction).
- **Out of scope:** any change to live trading/halt logic, EV, fusion,
  probability; unhalt decisions; METAR as a NEW feed (parity uses
  existing `station_observations`); backfilling history.
- **Invariants:** shadow/live one-way isolation preserved (no live-path
  imports of new modules); fail-closed everywhere; append-only.
- **Expected files changed:** `data/wmo_heading.py`,
  `storage/cli_chain.py`, `storage/settlement_label.py` (new);
  `storage/research_provenance.py` (new table + inserts);
  `data/nws_cli_client.py` (retain/parse the heading line — additive);
  the Kalshi client module found in /plan (research-only poll); tests
  `tests/test_wmo_heading.py`, `tests/test_cli_chain.py`,
  `tests/test_settlement_label.py`, `tests/test_exchange_settlements.py`.
- **Implementation sequence:** failing heading-parser tests (RRA/CCA/AAB/
  missing/`PAA`→UNRECOGNIZED/malformed) → parser → chain-order tests
  (initial<RRA; CCA supersedes; receipt-fallback logged) → chain module →
  quarantine matrix (later-lower-high; parity mismatch; CCB-before-CCA
  gap; unrecognized) → freeze lifecycle tests (7/8 AM freeze; 11 AM
  delay; post-expiration version ignored for label; DST/LST window via
  `data/stations.py` zones, winter+summer cases) → exchange capture with
  mocked API fixtures (idempotent re-insert no-op; changed payload same
  key → ProvenanceConflict) → full suite.
- **Schema/API effects:** one new research table (+
  `exchange_settlements` usage); no live-path schema changes.
- **Data migration behavior:** additive `CREATE TABLE IF NOT EXISTS` via
  the store's existing idempotent pattern (repo convention; Alembic not
  introduced here — decision D03).
- **Validation commands:**
  `cd claude && .venv/bin/python -m pytest tests/test_wmo_heading.py tests/test_cli_chain.py tests/test_settlement_label.py tests/test_exchange_settlements.py -q`
  then `.venv/bin/python -m pytest tests/ -q` (≥2252 passed + new);
  commit message includes the summary line.
- **Failure/rollback:** research-store additive; revert branch; no
  live-path exposure by construction (isolation test extended to the new
  modules).
- **Depends on:** none of packets 1–5 (parallel thread allowed).
- **Review checklist:** UNRECOGNIZED BBB quarantines (no Pxx guessing);
  freeze rule matches contract-terms text quoted in decision-log D10;
  divergence produces a review artifact, never an auto-fix; isolation
  test updated; naming conventions (lowercase source labels, city codes)
  respected.
- **Evidence references:** WMO-S1..S8; decision-log D09, D10, D11;
  kalshi audit §§4–5, 12, 14, 17.

---

## Packet 7 — Lineage gating for legacy calibration artifacts + legacy timestamps (kalshi)

**Goal:** Close independent-review findings F05/F06: the legacy
calibration-artifact loader must validate lineage (code tag, regime,
training cutoff, feature schema, config hash) before an artifact is used,
and the legacy runtime path must persist provider issue/valid timestamps.

**Context:** `storage/research_capture.py` already derives `cohort_id`
from run_id+regime_id+code_sha+config_hash; the 2026-07-27 review
(docs/findings/2026-07-27-independent-quant-architecture-review.md)
documents that the ACTIVE calibration artifact is loaded by
sample-count/BSS only. The fix is extending the existing lineage pattern
to the legacy loader — not new invention.

**Constraints:** The bot is halted and must stay halted; nothing here
may change decision outputs — gating may only REFUSE artifacts, never
substitute values. `strategy_config.py`/`ev_engine.py`/`validator.py`
are guard-protected; if the loader lives inside one of them, STOP in
/plan and report the exact location so the owner can approve the guarded
edit path.

**Done when:** an artifact missing/mismatching lineage fields is refused
fail-closed with a typed reason (and the current artifact's status is
reported honestly); legacy forecast rows persist issue/valid timestamps;
suite green.

- **Working directory:** `/Users/carsynstephenson/Claude`, in `claude/`.
- **Open in Cursor:** the review doc F05/F06 sections,
  `storage/research_capture.py`, `storage/research_provenance.py`
  (`evaluate_freshness`), the calibration loader (locate in /plan —
  search for the artifact id load path), `docs/forecast-run-provenance.md`.
- **Repository facts to verify:** where the calibration artifact is
  loaded and what metadata it carries today; which legacy tables lack
  `provider_issue_at`/valid-window fields; whether the active artifact
  (id noted in the review) even HAS lineage metadata to validate.
- **Preconditions:** packet 6 merged (shared conventions), suite green.
- **Exact scope:** (1) `storage/artifact_lineage.py`: required-fields
  spec {code_sha, regime_id, training_cutoff, feature_schema_version,
  config_hash}; `validate_artifact(meta, current_context) ->
  LineageVerdict` (typed refusal reasons; missing metadata ⇒ refuse with
  `lineage-metadata-absent`); wire into the loader so refusal
  fail-closes to "no calibration artifact" (the code's existing
  no-artifact behavior — verify what that is in /plan and preserve it).
  (2) Additive columns (idempotent ADD COLUMN helper, repo convention)
  for `provider_issue_at`/`valid_until` on the legacy forecast-log path
  identified in /plan, populated going forward (no backfill), threading
  `evaluate_freshness` where the review's F06 indicates.
- **Out of scope:** regenerating/retraining calibration artifacts;
  changing thresholds; unhalt logic; anything in guarded files without
  explicit owner approval.
- **Invariants:** refuse-never-substitute; halted stays halted;
  append-only.
- **Expected files:** `storage/artifact_lineage.py` (new), loader wiring
  (located in /plan), `storage/database.py` (additive columns),
  `tests/test_artifact_lineage.py` (+ a test that the legacy path writes
  the new timestamps).
- **Implementation sequence:** /plan locates loader + legacy tables →
  failing tests (mismatched config_hash refused; absent metadata
  refused; matching passes; loader integration refusal path) → module →
  wiring → columns → suites.
- **Schema/API effects:** additive columns; new module.
- **Data migration:** additive, idempotent, no backfill.
- **Validation:** focused tests then `pytest tests/ -q` full; summary
  line in commit.
- **Failure/rollback:** additive; revert branch.
- **Depends on:** packet 6 (ordering/conventions only).
- **Review checklist:** refusal is fail-closed and typed; no guarded
  file edited without approval; honest PR note about whether the ACTIVE
  artifact passes or fails the new gate (it may fail — that is a finding,
  not a bug to hide).
- **Evidence references:** kalshi audit §4 (F05/F06), §8, §16;
  decision-log D03, D26.

---

## Packet 8 — Consumer upgrade: availability/admission filtering in market_context (options-validator)

**Goal:** The cross-repo consumer bridge filters on EC-1 fields:
ADMITTED-only, `available_at <= as_of` (falling back to `published_at`
where `available_at` is null), purpose=decision, freshness checked —
with conformance fixtures proving producer/consumer agreement.

**Context:** `options_researcher/market_context.py` is a read-only
sqlite3 consumer that already refuses naive `as_of` and filters
`published_at <= as_of`. Packet 2 added nullable EC-1 columns, so the
bridge must handle both old rows (nulls → legacy behavior, labeled) and
new rows (full gating).

**Constraints:** Bridge stays read-only and network-free. options-validator
conventions bind: ruff + pyright must stay clean; tests offline; changes
here are mechanical consumer logic, within the standing division of labor
(Codex implements). Do not touch `config.py` or any registered-spec file.

**Done when:** fixture DBs (one legacy-shape, one EC-1-shape) produce the
specified inclusions/exclusions; ruff/pyright/unittest all green.

- **Working directory:** `/Users/carsynstephenson/options-validator`.
- **Open in Cursor:** `options_researcher/market_context.py`, its tests
  (locate via `grep -r market_context tests/`), `docs/market_updates.md`
  (in equity-research — the bridge contract), `final-architecture.md`
  §4.3.
- **Repository facts to verify:** exact current query and column list in
  `market_context.py`; existing test fixture construction.
- **Preconditions (amended 2026-07-29, D33):** packet 2 merged in
  equity-research — that is the real gate, and it is already met. Every
  column this consumer reads exists and is populated on `main` today:
  `available_at` is written as the conservative `public_by_ts_utc` bound on
  SEC submissions-path rows and is deliberately NULL on Atom-feed rows
  (`tests/test_sec_availability_wiring.py:104-153` asserts both);
  `admission_state`, `admission_reason`, `stale_after`, and
  `purpose_authority` all exist (migration 0002). Packet 5 adds *writers and
  reason codes*, not columns this consumer reads, so packet 8 no longer
  blocks on it and may run in parallel — with one carve-out: the
  `legacy-grandfathered` label from D32 lands in packet 5's migration 0006,
  so packet 8 must treat a NULL `admission_reason` on an ADMITTED row as
  grandfathered-legacy and label it accordingly, which stays correct both
  before and after that stamp exists.
- **Working-tree hazard (refreshed 2026-07-29 — the F07 list is stale and
  understated):** concurrent sessions have left a much larger uncommitted
  surface. Modified: `.env.example`, `.gitignore`, `README.md`,
  `options_researcher/intraday_capture.py`, `options_researcher/live_quotes.py`,
  `pyproject.toml`, `tests/test_intraday_capture.py`,
  `tests/test_live_quotes.py`, `uv.lock`. Untracked: `data/schwab_adapter.py`,
  `data/schwab_credentials.py`, `docs/schwab-market-data-setup.md`,
  `tools/setup_schwab.py`, `tests/test_schwab_adapter.py`, and two files
  under `reports/`. Never stage, commit, revert, or "clean up" any of them;
  scope every `git add` to this packet's own files by explicit path (never
  `git add -A`/`.`). **`pyproject.toml` and `uv.lock` are both modified**, so
  record the baseline suite result and the resolved environment at packet
  start and re-check at the end — an environment shift from someone else's
  session must not be misread as a regression from this packet. Re-measure
  the baseline yourself; do not assume the previously recorded 2109.
- **Exact scope:** extend the bridge query/filters: rows with
  `admission_state` present must be `ADMITTED`; `available_at` used when
  non-null else `published_at` (each returned record labeled
  **`gating_basis`**: `available_at` | `published_at-legacy` — renamed from
  `availability_basis` on 2026-07-29 per D34, because the producer already
  writes a field of that exact name into the raw payload with a *different*
  vocabulary (`submissions-acceptance-interval`,
  `submissions-acceptance-missing`, `submissions-acceptance-invalid`,
  `feed-timestamp-unruled` — `providers.py:125,185-191`), and two same-named
  fields carrying different value sets across a repo boundary is a misread
  waiting to happen. `gating_basis` is consumer-derived: it records which
  column this bridge actually gated on, and must never be copied from the
  producer's payload string);
  plus `admission_basis`: `gated` where `admission_reason` is non-null, else
  `grandfathered-legacy` (D32 — a NULL reason on an ADMITTED row means the
  row predates gate enforcement and was blanket-admitted by migration 0002);
  `purpose_authority` in (null→legacy-decision, `decision`);
  `stale_after` in the past ⇒ excluded unless caller passes
  `include_stale=True` (then labeled). Add conformance fixture vectors:
  a small JSON fixture (copied verbatim from the equity-research packet-5
  test fixtures — same bytes, committed here) driving both a
  fixture-built legacy DB and an EC-1 DB. If packet 5 has not merged when
  this packet starts, author the fixture here from the packet-2 column
  semantics and record that packet 5 must adopt the identical bytes.
- **Out of scope:** any producer change; new data sources; dashboards.
- **Invariants:** read-only; naive-`as_of` refusal preserved; no network.
- **Expected files:** `options_researcher/market_context.py`,
  `tests/test_market_context.py` (extend), conformance fixture JSON under
  `tests/fixtures/` (follow existing fixture layout).
- **Implementation sequence:** failing tests per filter case (admitted /
  quarantined excluded / stale excluded / stale included-labeled / legacy
  nulls / availability basis labeling) → implementation → `uv run ruff
  check .` → `uv run pyright` → full suite.
- **Schema/API effects:** bridge return records gain `gating_basis` and
  `admission_basis` (additive).
- **Data migration:** none.
- **Validation:** `uv run python -m unittest tests.test_market_context -v`
  (adjust to the located test path), then full suite + ruff + pyright.
- **Failure/rollback:** revert branch; consumer-side only.
- **Depends on:** packets 2, 5.
- **Review checklist:** legacy rows keep working (labeled); no silent
  stale acceptance; fixtures byte-identical to producer-side vectors.
- **Evidence references:** decision-log D02, D04, D15; equity-research
  audit §10; options-validator audit §17.

---

## Packet 9 — Golden-question retrieval benchmark + provider health metrics (equity-research)

**Goal:** A committed, offline benchmark (filings domain first) scoring
retrieval precision/recall/abstention against primary-source answers,
plus provider health metrics (null rate, freshness, conflict rate,
quarantine rate, golden-set scores) computed from receipts.

**Context:** No regression signal for retrieval quality exists anywhere.
Method per `research-method.md` §4: 10–15 questions keyed to accession
numbers/exact values, including deliberate correctly-abstain items;
coverage always reported beside risk.

**Constraints:** Runs entirely offline in CI against committed fixtures
and the local store; question/answer authorship must be owner-reviewable
(one YAML file, plain language, primary-source citation per item). LLM
judging is NOT used for scoring — exact-match/`accn`-match only.

**Done when:** `python -m market_updates.benchmark run` prints per-domain
precision/recall/abstention WITH coverage, exits non-zero below
registered floors; health metrics land on run receipts; suite green.

- **Working directory:** `/Users/carsynstephenson/equity-research`.
- **Open in Cursor:** packet 4/5 modules, `research-method.md` §4,
  `source-policy.md` §8.
- **Repository facts to verify:** available fixture data (which tickers
  have committed companyfacts/filings to key questions against). Inventory
  taken 2026-07-29: `tests/fixtures/market_updates/` holds
  `company_facts.json`, `sec_submissions.json`, `sec_atom.xml`,
  `company_rss.xml` plus macro-provider blobs, and packet 4 adds
  `tests/fixtures/xbrl/0001543151_us-gaap_Revenues.json` (Uber) with a
  provenance sidecar. `company_facts.json` is a full companyfacts blob and
  is the realistic source of most answerable items. **If fewer than 8
  questions are genuinely answerable from committed fixtures, ship fewer and
  say so in the PR — do not invent an answer, do not add a fixture solely to
  hit the count, and do not key a question to data the repo does not hold.**
  A benchmark padded to a target number is worse than a short honest one.
- **Preconditions:** packets 4–5 merged.
- **Exact scope:** `data/golden_questions/filings.yaml` (12 items: 8
  answerable keyed to committed fixtures with `accn` + expected value;
  4 abstain items — plausible questions whose answers are absent from
  fixtures); `market_updates/benchmark.py` (load, run against the store,
  score, report; floors read from the YAML header — floors are
  owner-typed numbers, so the initial header values ship as
  `floor_precision: null` = report-only until the owner types them);
  `market_updates/health.py` computing the metric set per provider from
  `provider_runs` + admission counts; wire health output onto run
  receipts.
- **Out of scope:** other domains' question sets (follow-on packets);
  any retriever changes; LLM judges.
- **Invariants:** offline; coverage-paired reporting; floors owner-typed
  (report-only until then).
- **Expected files:** the YAML, `market_updates/benchmark.py`,
  `market_updates/health.py`, `tests/test_benchmark.py`,
  `tests/test_health_metrics.py`.
- **Implementation sequence:** YAML with real fixture-keyed answers →
  failing scorer tests (perfect set; one-wrong; abstain-hit;
  abstain-miss = answered-when-shouldn't; coverage arithmetic) →
  benchmark module → health module tests (synthetic receipts) → wiring →
  suites.
- **Schema/API effects:** receipts gain health fields (additive).
- **Data migration:** none.
- **Validation:** focused tests, full suite, then one real run:
  `.venv/bin/python -m market_updates.benchmark run` (report-only).
- **Failure/rollback:** additive; revert branch.
- **Depends on:** packets 4, 5.
- **Review checklist:** abstain items genuinely unanswerable from
  fixtures; no floor numbers invented (null until owner types them);
  metrics computed from our receipts, never provider self-report.
- **Evidence references:** decision-log D16, D21; IMP-S15..S17.

---

## Packet 10 — Shared-package extraction checkpoint (cross-repo; NOT a build packet)

**Goal:** A go/no-go review, not code. After packets 1–9 have run in
production use for a full cycle (≥1 month of daily rituals), assess
whether ≥2 repos consume a stable EC-1 interface and whether extraction
of a shared package is justified.

**Inputs:** conformance fixture drift report (are the copied vectors
still byte-identical?), list of contract deviations logged in
decision-log updates, migration/journal health, benchmark trends.
**Output:** a dated recommendation memo in `docs/evidence-upgrade/`
(extract / defer / never), owner-decided. No code is written under this
packet. **Depends on:** all prior packets + a cycle of real use.

---

## Recommended thread layout

- Original layout — Thread A (sequential): packets 1 → 2 → 3 → 4 → 5 → 8 → 9.
  Thread B (parallel): packets 6 → 7.
- **Revised 2026-07-29 (D33), after packets 1–4 and 6–7 shipped:** thread B
  is out of kalshi work, and packet 8's real dependency is packet 2 (met),
  not packet 5. Remaining layout — **Thread A: 5 → 9** (both equity-research,
  and 9 genuinely needs 5). **Thread B: 8** (options-validator, a different
  repo, so no shared working tree and no merge contention with thread A).
  The two threads share one contract seam — the conformance fixture bytes —
  handled by the carve-outs written into packets 5 and 8. Packet 10 is a
  calendar checkpoint, not a Codex thread.
- **Never run two Codex threads against the same repository checkout.** Both
  threads previously worked in different repos by accident of ordering; from
  here it is a rule. Concurrent work in one tree makes every measured test
  count unreliable, which is the one thing this program cannot tolerate.

## AGENTS.md durable additions (keep minimal)

Only after the relevant packet merges, add to the repo's AGENTS.md:
- equity-research: two lines — "Evidence admission: see
  `market_updates/admission.py`; source authority: `data/source_registry.json`
  (edits are supersessions, never in-place)." and "All evidence
  timestamps tz-aware UTC; `recorded_at` is system-assigned."
- kalshi: one line under Naming Conventions — "CLI product versions are
  chain-ordered by issuance+BBB; unrecognized BBB forms quarantine
  (`storage/cli_chain.py`)." Plus, after packet 7 (added 2026-07-29): one
  line — "Calibration artifacts are selected by lineage identity (code tag,
  evaluation regime, training cutoff, feature schema, config hash), not by
  sample count or BSS; a lineage mismatch REFUSES the artifact and never
  substitutes one." Both packets are merged, so both lines are due now.
- options-validator: none (bridge behavior documented in the module).
