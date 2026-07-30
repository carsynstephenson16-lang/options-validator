# Codex brief — Packet 5B: typed earnings claims and evidence-backed corroboration

**Authored:** 2026-07-30, after 5A merged (PR #17). **Depends on:** 5A's
temporal provenance. **Does not depend on:** 5C.
**Target model:** Codex-tuned GPT-5.x ("Sol"), `reasoning.effort = "xhigh"`.
**Grounding:** OpenAI *Codex prompting guide* / *GPT-5.1 prompting guide*
(Official-source, fetched 2026-07-30). Harness: low global verbosity overridden
high for code, `parallel_tool_calls` on, first-class `apply_patch`, **no
prompting for an upfront plan or mid-rollout status**. `AGENTS.md` auto-injects.

---

## Reachability check, run before this brief was written

Carry-forward lesson 1 from the 5A round: verify the thing you are about to
ask for, not the thing you are looking at. Measured just now:

```
earnings.date policy: slow | window: None | min groups: 2
admit() -> UNREACHABLE at record construction
   ValueError: claim type 'earnings.date' has freshness class 'slow'
               but no freshness_window
```

So `earnings.date` cannot reach the admission gates at all until 5C sets
windows — the same trap that made 5A revision 1 unbuildable.

**Therefore 5B's proof obligation is at the producer/store layer, not the
admission layer.** Do not add a window to make an admission test runnable.
The end-to-end admission matrix belongs to 5C.

## Why this packet exists

There is no `earnings.date` route. The claim types actually produced are
`sec.filing_event`, `sec.numeric_fact`, `company.publication`,
`central_bank.publication`, `macro.series`, `market.quote`, `news.discovery`.
SEC filings become `sec.filing_event`; IR records become
`company.publication`. Nothing extracts, types, or stores an earnings date.
Separately, `claim_type` is written to the ingestion journal but not to the
event row, and no typed date, fiscal period, status, or corroborating evidence
IDs are persisted — so even a nominally admitted earnings row could not feed
the H7 gate. **Repo-verified, D37.**

---

## The prompt

````text
Produce typed, evidence-backed earnings-date claims: extraction, identity,
status transitions, supersession, and corroboration that proves matching
evidence rather than counting channels. Do not set freshness windows and do
not move any board authority; those are 5C and the packet 8 integration.

<solution_persistence>
- Autonomous senior engineer: gather context, implement, test, refine
  end-to-end in this turn.
- Every claim type you introduce gets a typed outcome including its failure
  states; do not ship a nullable date with implicit meaning.
- Bias to action, with the exception in <independence_must_be_proven>.
</solution_persistence>

<context_gathering>
- One parallel batch: `market_updates/providers.py`, `service.py`,
  `storage.py`, `models.py`, `normalizer.py`, `admission.py`,
  `data/source_registry.json`, and 5A's temporal-provenance module.
- Early stop: you can name the extraction sites and the store shape.
- Do not re-derive D37/D38.
</context_gathering>

## Deliverable 1 — a typed earnings claim, not a date column

Model the claim explicitly. Minimum shape:

  symbol, fiscal_period, expected_date, status, known_as_of,
  supersedes, evidence_ids, temporal_provenance

- **Identity is `(symbol, fiscal_period)`** — not the date, and not the
  source record. A date that moves is the *same claim* in a new state, not a
  new claim. Keep identity separate from metadata: a retrieval date, a source
  record id, and a rule version are none of them the claim's identity.
- **`status` is a state machine**, not a boolean or a nullable date:
  expected / confirmed / revised / superseded / conflicted / passed.
  Transitions are explicit and recorded; an unknown transition raises rather
  than silently overwriting.
- **`known_as_of`** is the claim's own as-of, distinct from 5A's
  `available_at` and `freshness_anchor`. Reuse 5A's provenance type; do not
  duplicate or reinvent it.
- **Expiry is event-driven, not durational.** The claim transitions when the
  event passes, the date changes, evidence conflicts, or a newer claim
  supersedes it — never "after N days". This is why a `slow` window is the
  wrong instrument for it, and why 5C should not be asked to paper over it.

## Deliverable 2 — extraction, and where it comes from

Extract the earnings date from the sources that actually carry it. SEC
filings and issuer IR publications are the two candidates already in the
registry with `earnings.date` in scope (`sec_edgar` → group `sec-edgar`,
`company_ir` → group `issuer`).

Persist `claim_type` and the typed values **on the event row**, not only in
the ingestion journal. That is a schema change: additive-expand migration
`0008`, following `0007`'s pattern — stamp any legacy rows before installing
constraints, journal the row count, and make `downgrade()` reverse exactly
what it did and nothing more.

<independence_must_be_proven>
`corroboration_groups` is currently an unvalidated list of strings
(`storage.py:348`), so passing "issuer" satisfies the count without proving
that matching issuer evidence exists. That is the defect to fix, not a
mechanism to use.

Corroboration must carry **evidence IDs** and be validated against the
registry: each group must be backed by a real stored evidence row whose
extracted date matches, within a stated tolerance, for the same
`(symbol, fiscal_period)`.

And it must not be satisfied by transport. An 8-K under Item 2.02 frequently
republishes the issuer's own press release, so "SEC said it and IR said it"
can be one source arriving down two pipes. Where the SEC record is a
republication of the issuer release, that is ONE independent group, not two.
Detect it — shared release text, matching timestamps, the filing exhibiting
the issuer's release — and record the determination.

If genuine independence cannot be established, the correct outcome is a claim
that stays uncorroborated with a named reason. An uncorroborated claim is a
successful, truthful outcome. Manufacturing a second group to reach the count
is a failure that would pass every test.
</independence_must_be_proven>

## Deliverable 3 — proof at the producer/store layer

Add offline tests, driven by **real parser fixtures** rather than
hand-constructed records (hand-built records encode the author's belief about
the data instead of the data — the mechanism by which B1 and B4 both hid):

1. Extraction: each source fixture yields the expected typed claim.
2. State machine: every transition, including the refusals. Prove a date
   change produces a `revised` transition on the *same* identity rather than a
   duplicate claim.
3. Corroboration: (a) two genuinely independent sources corroborate;
   (b) an 8-K republishing the issuer release does NOT corroborate;
   (c) a bare group-name string with no backing evidence does NOT corroborate.
4. Supersession and conflict: a conflicting date is recorded as `conflicted`,
   not silently resolved by recency.

Out of scope, explicitly: any admission-level matrix for `earnings.date`
(unreachable — see the reachability check), any freshness window, and any
change to `tests/test_admission.py`'s expectation that non-immutable policies
raise. If your work makes that test fail, stop and report.

## Scope note — do not overreach

The market-updates watchlist is 4 names (MSFT, AMZN, VST, CEG); H7's frozen
scope is 15 (`h7-forward-15-v1`). This packet does not expand either. It
produces claims for the names already configured; becoming H7's earnings
source requires an explicit scope expansion and a parity proof against the
existing `gating_v3` store, which is the packet 8 integration, not this.

## Definition of done — evidence, not assertions

1. Guard red/green for every guard added: neutralize, show RED, restore, show
   GREEN; name the failing test and counts. (D35)
2. Print the extraction/corroboration matrix in the final report: source,
   claim identity, status, corroboration outcome and reason.
3. `python -m pytest tests` against the 1871 + 630-subtest baseline on merged
   `main`.
4. `compileall -q scripts`; `integrity_check.py --checks dead-citations`
   0 FAIL/0 WARN (`CITATION_PATH_RE` is unanchored — a `docs/...` path for a
   file outside this repo reddens it; do not loosen the guard);
   `git diff --check`; lock hashes unchanged or explained; alembic single head
   after `0008`.
5. Any official source cited for filing or disclosure behaviour gets its URL
   and capture date in `docs/evidence-upgrade/source-ledger.csv`. Official
   sources only.

## Editing constraints

- ASCII default; `apply_patch` for single-file edits.
- Shared worktree: NEVER revert changes you did not make; ignore unrelated
  modified files (an unrelated `uv.lock` change is currently uncommitted and
  must stay that way); if files change under you mid-task, stop and report.
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

## Instruction conflicts resolved on purpose

| Conflict | Resolution |
|---|---|
| Official "bias to action / complete a working version" vs corroboration that cannot honestly be satisfied | `<independence_must_be_proven>` names the shortcut (fabricating a second group to reach the count), forbids it, and defines an uncorroborated claim as a successful outcome — so "complete" never requires a manufactured group. Same shape as 5A's `UNRESOLVED`. |
| Official "cover the root cause, not a narrow slice" vs packet boundaries | The admission matrix, the freshness window, and the H7 scope expansion are each named as belonging elsewhere, with the measured reachability proof for the first — comprehensiveness cannot silently absorb 5C or the packet 8 integration. |
| Official "make reasonable assumptions" vs claim discipline | Assumptions permitted for code shape; forbidden for disclosure behaviour, where an official source or an honest refusal is required. |

## Carry-forward lessons from 5A, applied here

1. **Reachability checked first** — run at the top of this brief, and it moved
   the proof obligation off the admission layer before a round was spent.
2. **No field called a free win without reading what produced it** — hence
   "extract from the sources that carry it", with the 8-K republication hazard
   named rather than assumed away.
3. **Identity separate from metadata** — `(symbol, fiscal_period)` is the
   claim; dates, rule versions and record ids are not.
4. **Typed states over booleans** — an explicit status machine with recorded
   transitions, and refusals that raise rather than overwrite.
