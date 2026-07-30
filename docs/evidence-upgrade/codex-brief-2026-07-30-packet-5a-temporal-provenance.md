# Codex brief — Packet 5A: temporal provenance for every registered route

**Target model:** Codex-tuned GPT-5.x ("Sol"), API `reasoning.effort = "xhigh"`.
**Authored:** 2026-07-30. **Blocks:** everything downstream — 5B, 5C, PR #17.
**Grounding:** OpenAI *Codex prompting guide* and *GPT-5.1 prompting guide*,
fetched 2026-07-30 (Official-source). Same harness settings as the packet 5
fix brief: `xhigh`, low global verbosity overridden high for code,
`parallel_tool_calls` on, first-class `apply_patch`, and **no prompting for an
upfront plan or mid-rollout status** (the migration note warns it causes early
termination). `AGENTS.md` is auto-injected root-to-leaf, so this brief does not
restate the repo guardrails.

---

## Why this packet exists

D37: with the proposed freshness windows applied, all seven affected routes
still fail at `temporal-missing-availability` — the windows unblock zero
routes. `public_by_ts_utc` and `availability_rule_version` are populated in
exactly one place, `providers.py:206-207`, inside the SEC submissions parser.
Every other provider leaves them `None` (`models.py:105-106`), and that gate
fires before the staleness gate. **Repo-verified.**

---

## 1. The prompt

````text
Give every registered ingestion route a versioned availability rule, so that
admission can evaluate temporal safety instead of refusing for lack of inputs.
Work on branch `feature/evidence-upgrade-packet-5` in its existing worktree.

<solution_persistence>
- You are an autonomous senior engineer: gather context, implement, test, and
  refine end-to-end in this turn.
- Do not stop at analysis or a partial route. Carry every route through
  implementation, the matrix test, and verification.
- Bias to action, with ONE exception defined in <do_not_invent_availability>.
</solution_persistence>

<context_gathering>
The defect and its location are established. Do not re-derive D37.
- One parallel batch: `market_updates/providers.py`,
  `market_updates/sec_availability.py`, `market_updates/models.py`,
  `market_updates/storage.py`, `market_updates/service.py`,
  `market_updates/normalizer.py`.
- Early stop: you can name each route's temporal signal from the inventory
  below. Confirm it against the code; do not go looking for more.
- Escalate once if a cited line has drifted: re-locate by symbol with `rg`.
</context_gathering>

## The reference implementation to generalize

`market_updates/sec_availability.py` already does this correctly for SEC. It
returns a `SecAvailability` carrying `acceptance_ts_utc`, `filing_date`,
`earliest_public_ts_utc`, `public_by_ts_utc`, `rule_version`, and
`tzdata_version`, with `RULE_VERSION = "EDGAR-FilerManual-v77-2026-03-16"` —
a version string naming the governing document and its date. Its docstring
records the discipline to preserve: `earliest_public_ts_utc` is an optimistic
lower bound, and look-ahead-sensitive consumers must gate on the conservative
`public_by_ts_utc`.

Generalize that shape. Every route gets a rule that returns a bounded interval
plus a `rule_version` naming the governing source and its date. Do not
special-case SEC out of the new abstraction; it should become one
implementation of it.

## Measured per-route inventory — what each source actually gives you

All Repo-verified today. `published_at` is what the provider currently sets.

| Route | `published_at` today | Real availability signal | Where it is |
|---|---|---|---|
| `sec_edgar`, `sec_edgar_atom` | filing timestamp | acceptance + form rule | already implemented |
| `sec_companyfacts` | — | same SEC rule | already implemented |
| `fred` | **observation date** (`providers.py:431`) | `realtime_start` | **already captured in payload** (`providers.py:435`) |
| `twelve_data` | **fetch time `now`** (`providers.py:699`) | exchange `datetime` on the row | **already captured in payload** (`payload=row`) |
| `bls` | **observation date** (`providers.py:528`) | official release timestamp | NOT captured — needs new capture or release calendar |
| `bea` | **observation period** (`providers.py:573`) | official release timestamp | NOT captured |
| `eia` | **observation period** (`providers.py:617`) | official release timestamp | NOT captured |
| `treasury_fiscal_data` | **record date** (`providers.py:654`) | publication/business-day rule | NOT captured |
| `gdelt` | article date | GDELT `seendate` | check `parse_gdelt_articles` |
| `company_ir` | feed entry date | feed `published`/`updated` | check `providers.py:353` |
| `federal_reserve` | feed entry date | feed `published`/`updated` | check `providers.py:427` |

Two of these are free wins: FRED and Twelve Data already carry the correct
signal in the payload and simply do not use it. FRED's `realtime_start` is the
vintage — the moment the observation first became available — which is the
whole reason a quarterly observation dated April 1 can arrive in July.

<do_not_invent_availability>
The naive way to make the matrix pass is to default `available_at` to
`retrieved_at` or `utc_now()` when a source has no availability signal. DO NOT
DO THIS under any circumstance. It fabricates temporal provenance, and because
`recorded_at >= available_at` would then always hold, it would silently defeat
the look-ahead gate this entire architecture exists to enforce. NO LOOK-AHEAD
is a non-negotiable repo guardrail.

Where a source genuinely has no availability signal, the correct outcome is
that the route stays refused — but with a precise, per-route reason recorded
in the rule, not the generic `temporal-missing-availability`. A route that
cannot yet prove when its data became public SHOULD be quarantined. That is
the system working.

Report which routes you gave real rules and which remain honestly unresolved.
A partial matrix with truthful reasons is a success; a full matrix built on
`retrieved_at` is a failure that would pass every test.
</do_not_invent_availability>

## Where official timing is needed

For `bls`, `bea`, `eia`, and `treasury_fiscal_data`, the availability rule
depends on official release timing. Use the agency's own published release
calendar or documentation as the governing source, cite the URL and capture
date in the `rule_version` string exactly as the SEC rule does, and record it
in `docs/evidence-upgrade/source-ledger.csv`. Do not cite blogs, aggregators,
or model recall. If an official calendar cannot be obtained for a source,
that source falls under <do_not_invent_availability> — leave it refused with a
named reason and say so.

## Required: the end-to-end route matrix

This is the deliverable that would have caught the defect, and it matters more
than any individual rule.

Add a test that walks **every** entry in `_INGESTION_ROUTES`
(`service.py:50`), drives a representative record through the production
admission path, and asserts the resulting `(state, reason)` per route. It must
read the FIRST gate that refuses, not the gate under study. Include routes you
expect to be refused, with their expected reason — the matrix records reality,
it does not assert success.

Existing tests build a synthetic `claim.basic` policy and a fixture registry
(`tests/test_admission.py:38-45`); that is exactly how B1 and B4 both hid.
This matrix must use the registered routes, the registered policies, and the
real registry.

## Definition of done — evidence, not assertions

1. Guard red/green for every rule you add: neutralize it, show the suite goes
   RED, restore, show GREEN. Name the failing test and the counts. (D35)
2. Print the full route matrix in your final report — route, state, reason,
   and whether the rule is real or honestly unresolved.
3. Full suite `python -m pytest tests`; report the count against the 1858 +
   586 subtests baseline. That worktree's `.venv` is stale and has no `pip`;
   repair it from `requirements-dev.txt` or use a venv satisfying
   `requirements.txt`, and say which.
4. `python -m compileall -q scripts`.
5. `python scripts/integrity_check.py --checks dead-citations` → 0 FAIL, 0
   WARN. `CITATION_PATH_RE` is unanchored, so prose containing a `docs/...`
   path for a file outside this repo will redden it. Do not loosen the guard.
6. `git diff --check`; `pyproject.toml` and `uv.lock` hashes unchanged or
   explained; alembic single head.
7. Do not change `tests/test_admission.py:240-248`'s expectation that
   non-immutable policies raise. That belongs to 5C, not here. If your work
   makes it fail, stop and report rather than editing it.

## Editing constraints

- ASCII by default; `apply_patch` for single-file edits.
- The worktree is shared with concurrent sessions. NEVER revert changes you
  did not make; ignore unrelated modified files; if files change under you
  mid-task, stop and report.
- Never `git reset --hard` or `git checkout --`. Do not amend a commit.
- Do not touch `ledger/` or any append-only artifact.

<final_answer_formatting>
- Lead with what changed and why, then the route matrix, then the red/green
  table. No "Summary:" preamble.
- Reference files as `path:line`. No large diffs or before/after pairs.
- At most two short snippets, only where a path reference is ambiguous.
- Reconcile every intention as Done, Blocked (one sentence + the exact
  question), or Cancelled. Nothing left in progress.
- High verbosity inside the code; low verbosity in the final message.
</final_answer_formatting>
````

---

## 2. Instruction conflicts resolved on purpose

| Conflict | Resolution |
|---|---|
| Official: "bias to action … complete a working version." Repo: NO LOOK-AHEAD. | `<do_not_invent_availability>` names the specific completion the model would otherwise reach for (`retrieved_at`) and forbids it, then redefines success so a partial matrix with truthful reasons *is* a complete deliverable. Without this, "make the matrix pass" and "never fabricate provenance" point in opposite directions. |
| Official: "cover the root cause, not a narrow slice." Repo: packet boundaries. | The brief names what belongs to 5C (the non-immutable-raises test) and instructs the model to stop and report rather than fix it, so comprehensiveness does not silently absorb the next packet. |
| Official: "make reasonable assumptions." Repo: claim discipline — official sources only for timing. | Assumptions are permitted for code shape, forbidden for release timing; the fallback is an honest refusal, not a guess. |

The official "tight error handling — no broad catches, no success-shaped
fallbacks" is again the exact shape of the fix, so the brief uses that
vocabulary deliberately.

## 3. If the round underperforms

Use the official metaprompt (end of turn), generate the revision two or three
times, and keep only what recurs across runs — single-run suggestions overfit
to the one situation. Any surviving change gets an eval before adoption.
