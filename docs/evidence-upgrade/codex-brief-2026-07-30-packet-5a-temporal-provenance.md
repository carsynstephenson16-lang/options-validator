# Codex brief — Packet 5A: temporal provenance at the parser layer

**Revision 2, 2026-07-30.** Revision 1 was REQUEST_CHANGES'd for four factual
defects and one sequencing contradiction; all five are corrected below and the
verification that drove each is cited. Do not use revision 1.

**Target model:** Codex-tuned GPT-5.x ("Sol"), `reasoning.effort = "xhigh"`.
**Grounding:** OpenAI *Codex prompting guide* / *GPT-5.1 prompting guide*
(Official-source, fetched 2026-07-30). Harness: low global verbosity overridden
high for code, `parallel_tool_calls` on, first-class `apply_patch`, **no
prompting for an upfront plan or mid-rollout status**. `AGENTS.md` auto-injects;
this brief does not restate repo guardrails.

---

## What changed from revision 1, and why

**1. Scope cut: 5A is parser-layer only.** Revision 1 demanded a production
admission matrix over every route while also preserving the rule that
non-immutable policies raise. Those are contradictory. Measured:

```
sec_edgar    (immutable)    -> QUARANTINED / temporal-missing-availability
fred         (slow)         -> RAISES ValueError: no freshness_window
twelve_data  (fast)         -> RAISES ValueError: no freshness_window
gdelt        (event_driven) -> RAISES ValueError: no freshness_window
```

Six of seven routes cannot reach the temporal gate at all until 5C supplies
windows. **The full admission matrix is therefore 5C's deliverable, not 5A's.**
5A owns provider/parser → provenance. (My earlier reproduction only reached the
temporal gate because it injected windows via `replace()` — an artifact of the
harness, not something the production path can do.)

**2. The SEC inventory was wrong.** Only the structured `sec_edgar`
submissions parser populates the interval (`providers.py:206-207`).
`sec_edgar_atom` and `sec_companyfacts` populate **neither** field —
verified by reading both construction sites. Revision 1 called all three
"already implemented."

**3. FRED is not a free win.** The provider requests
`series_id, api_key, file_type=json, sort_order=desc, limit=2`
(`providers.py:457-458`) — **no `output_type`, no real-time period**. FRED
defaults real-time periods to today, so the returned `realtime_start`
describes the *query's* information set, not the observation's original
release. The no-API-key CSV fallback (`fredgraph.csv?id=`) carries **no
real-time field at all**. Initial-release data needs a vintage/ALFRED-style
query (`output_type=4`). **Official-source: FRED real-time period docs.**

**4. Twelve Data is not a free win.** `/quote` is called with no `interval`
(`providers.py:678`), so it defaults to a daily bar, and the parser reads
`row["close"]` — a bar close, not a tick. `datetime` is the bar's *opening*
time. The rule needs the timestamp corresponding to the actual quoted price
(`timestamp` / `last_quote_at`, market state) plus the exchange timezone.
**Official-source: Twelve Data /quote docs.**

**5. The blanket ban on retrieval time was wrong, and conflated two clocks.**
Retrieval time is a legitimate *conservative* anti-lookahead bound: a replay
before first capture demonstrably could not see the record, so capture time
never overstates availability. What retrieval must never do is reset
*freshness*. Revision 1's absolute ban would have stranded routes that have a
sound bound available. Corrected model below.

---

## The two clocks — the core of this packet

These are different questions and must be different fields.

| Field | Question it answers | May retrieval time supply it? |
|---|---|---|
| `available_at` | "When can we *prove* the system could have seen this?" | **Yes**, as a conservative upper bound, labeled `observed-at-retrieval` |
| `freshness_anchor` | "When was this fact actually observed/released/quoted at source?" | **Never.** Re-fetching an old record must not make it fresh. |

Collapsing them is what makes a repeatedly-fetched stale quote look current
while a genuinely fresh release looks stale.

---

## 1. The prompt

````text
Give every registered ingestion route typed temporal provenance at the
provider/parser layer. Do not touch admission-gate sequencing or freshness
policy; those are 5C. Work on branch `feature/evidence-upgrade-packet-5`.

<solution_persistence>
- Autonomous senior engineer: gather context, implement, test, refine
  end-to-end in this turn.
- Do not stop at analysis or a partial route. Every route gets a typed
  outcome, including the routes whose honest outcome is "unresolved".
- Bias to action, with the exception in <unresolved_is_a_valid_outcome>.
</solution_persistence>

<context_gathering>
The defect and its location are established; do not re-derive D37.
- One parallel batch: `market_updates/providers.py`, `sec_availability.py`,
  `models.py`, `normalizer.py`, `storage.py`, `service.py`.
- Early stop: you can name each route's temporal signal from the contracts
  below. Confirm against code; do not go looking for more.
</context_gathering>

## Deliverable 1 — a provenance result type

Introduce one typed result that every route's rule returns. It must be able to
express all three real outcomes, not just success:

- EXACT       — a source-supplied time for the actual event (release, quote,
                acceptance). Carries `freshness_anchor`.
- BOUNDED     — no source time available, but first immutable capture time is
                a provable conservative bound. Sets `available_at` only,
                with `availability_basis = "observed-at-retrieval"`, and
                leaves `freshness_anchor` unset. MUST NOT be treated as
                freshness.
- UNRESOLVED  — neither available. Carries a specific machine-readable reason.

<unresolved_is_a_valid_outcome>
A route that cannot prove when its data became public SHOULD end UNRESOLVED
with a precise reason. That is the system working. Do not manufacture an
EXACT time from a retrieval timestamp, and do not use BOUNDED to populate
`freshness_anchor`. A partial matrix with truthful statuses is a complete
deliverable; a fully-resolved matrix built on retrieval time is a failure that
would pass every test.
</unresolved_is_a_valid_outcome>

Persist the outcome in a structured field — `availability_basis`, status, and
reason on the record (or an explicit journal payload), not as prose inside the
rule. `availability_basis` already exists as a payload convention in the SEC
parser (`providers.py:185-191`); extend that pattern rather than inventing a
parallel one.

## Deliverable 2 — rule identity, separate from evidence metadata

Every rule carries, as its own typed object:

  rule_id, rule_version, governing_source_url, governing_effective_date,
  captured_at, source_snapshot_hash, coverage_horizon

A document *retrieval date* must not become the rule version.
`sec_availability.RULE_VERSION = "EDGAR-FilerManual-v77-2026-03-16"` names the
governing document and its effective date — follow that shape, and add the
remaining fields around it.

`coverage_horizon` is fail-closed: a rule asked about a period its governing
calendar does not cover must raise, exactly as
`EdgarHolidayCalendarCoverageError` already does. Silent extrapolation past a
published calendar is the same defect class as a missing window.

## Deliverable 3 — per-route contracts (corrected)

| Route | Contract |
|---|---|
| `sec_edgar` | Already correct. Preserve `sec_availability.py`'s internals **behind the shared interface**; do not refactor its working logic. |
| `sec_edgar_atom` | Inherit provenance by accession from the canonical submissions record. If the accession is absent, remain **discovery-only** — not EXACT. |
| `sec_companyfacts` | Cannot use the submissions acceptance rule: the aggregate record has no accession and no acceptance timestamp. Use Packet 4's conservative XBRL filing-date rule, or UNRESOLVED. |
| `fred` | Default query returns the *current vintage*; `realtime_start` is the query's information set, not first publication. EXACT requires a vintage/ALFRED-style query (`output_type=4`). The CSV fallback has no real-time field → UNRESOLVED or BOUNDED. |
| `twelve_data` | `/quote` defaults to a daily bar; `datetime` is the bar open, and the parsed price is `close`. Use the timestamp corresponding to the quoted price (`timestamp` / `last_quote_at`), plus exchange timezone and market state. |
| `bls`, `bea`, `eia`, `treasury_fiscal_data` | Official release calendars, revision-aware (below). Fail-closed on coverage. |
| `gdelt` | `seendate` from `parse_gdelt_articles`. Discovery purpose only. |
| `company_ir`, `federal_reserve` | Feed `published`/`updated`; a feed timestamp is issuer-controlled, so BOUNDED may be the honest answer. |

## Deliverable 4 — revision-aware macro treatment

A release calendar alone cannot timestamp a *revised* value. Each macro
observation must distinguish:

- initial release — first publication of that observation
- revision — a later restatement of the same period
- current-vintage retrieval — what the source says today

An observation's `freshness_anchor` is the release that produced *that value*,
not the series' most recent release. Model this explicitly; do not let a
revision inherit the initial release time or vice versa.

## Deliverable 5 — the matrix, at the parser layer

Add an **offline** test that runs every registered route's real parser against
a committed provider fixture and asserts the resulting provenance status,
basis, and reason.

- Use actual parser fixtures, NOT hand-constructed `RawSourceItem` objects.
  Hand-built records are how B1 and B4 both hid: they encode the author's
  belief about the data instead of the data.
- Assert the honest outcome per route, including UNRESOLVED ones.
- No network. Offline is a hard repo constraint.

Explicitly out of scope: the production admission matrix. Six of seven
non-SEC routes raise before reaching the temporal gate until 5C sets windows.
Do not add windows to make a matrix runnable, and do not modify
`tests/test_admission.py:240-248`'s expectation that non-immutable policies
raise. If your work makes it fail, stop and report.

## Definition of done — evidence, not assertions

1. Guard red/green per rule: neutralize, show RED, restore, show GREEN. Name
   the failing test and counts. (D35)
2. Print the full parser-layer matrix in the final report: route, status,
   basis, reason, and whether the rule is EXACT, BOUNDED, or UNRESOLVED.
3. `python -m pytest tests` against the 1858 + 586-subtest baseline. That
   worktree's `.venv` is stale and has no `pip`; repair from
   `requirements-dev.txt` or use a venv satisfying `requirements.txt`, and say
   which.
4. `compileall -q scripts`; `integrity_check.py --checks dead-citations`
   0 FAIL/0 WARN (note: `CITATION_PATH_RE` is unanchored — a `docs/...` path
   for a file outside this repo will redden it; do not loosen the guard);
   `git diff --check`; lock hashes unchanged or explained; alembic single head.
5. Every governing calendar or doc cited gets its URL and capture date
   recorded in `docs/evidence-upgrade/source-ledger.csv`. Official sources
   only — no aggregators, no model recall.

## Editing constraints

- ASCII default; `apply_patch` for single-file edits.
- Shared worktree: NEVER revert changes you did not make; ignore unrelated
  modified files; if files change under you mid-task, stop and report.
- Never `git reset --hard` or `git checkout --`. Do not amend a commit.
- Do not touch `ledger/` or any append-only artifact.

<final_answer_formatting>
- Lead with what changed and why, then the matrix, then red/green. No
  "Summary:" preamble.
- `path:line` references; no large diffs or before/after pairs; at most two
  short snippets.
- Reconcile every intention as Done, Blocked (one sentence + exact question),
  or Cancelled. Nothing left in progress.
- High verbosity in code; low verbosity in the final message.
</final_answer_formatting>
````

---

## 2. Instruction conflicts resolved on purpose

| Conflict | Resolution |
|---|---|
| Official "bias to action / complete a working version" vs NO LOOK-AHEAD | Revision 1 banned retrieval time outright, which was too blunt. Now the licence is precise: retrieval time is permitted as `BOUNDED`/`observed-at-retrieval` for `available_at`, forbidden for `freshness_anchor`, and `UNRESOLVED` is defined as a successful outcome so "complete" never requires fabrication. |
| Official "cover the root cause, not a narrow slice" vs packet boundaries | The admission matrix and the non-immutable-raises test are named as 5C's, with the measured proof that they cannot run here — so comprehensiveness cannot silently absorb the next packet. |
| Official "make reasonable assumptions" vs claim discipline | Assumptions permitted for code shape; forbidden for release timing and vintage semantics, where the fallback is `UNRESOLVED`. |

## 3. Carry-forward to 5B (typed earnings claims)

Four lessons this round produced, to apply before 5B is written:

1. **Check reachability before specifying any matrix.** Run the thing end-to-end
   and read the first failure. Revision 1 specified a matrix that could not
   execute; one command would have caught it.
2. **Never call a payload field a "free win" without reading the request that
   produced it.** Both FRED and Twelve Data had the right *field name* and the
   wrong *semantics*, decided by query parameters the brief never examined.
3. **Separate identity from metadata.** 5B's earnings claim needs the same
   discipline: `(symbol, fiscal_period)` identity distinct from status,
   evidence IDs, and supersession — and a retrieval date is never a version.
4. **Typed states beat booleans.** EXACT/BOUNDED/UNRESOLVED here; for 5B,
   an explicit status machine (expected / confirmed / revised / superseded /
   conflicted / passed) rather than a nullable date.

## 4. If the round underperforms

Official metaprompt at end of turn; generate the revision two or three times
and keep only what recurs; eval any surviving change before adopting it.
