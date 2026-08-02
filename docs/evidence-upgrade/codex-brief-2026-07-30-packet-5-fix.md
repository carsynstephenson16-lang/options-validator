# Codex brief — Packet 5 fix round 1 (B1 + B2)

**Target model:** Codex-tuned GPT-5.x ("Sol"), API `reasoning.effort = "xhigh"`.
**Authored:** 2026-07-30. **Blocks:** equity-research PR #17.
**Grounding:** OpenAI *Codex prompting guide* and *GPT-5.1 prompting guide*,
`developers.openai.com/cookbook/examples/gpt-5/{codex_prompting_guide,gpt-5-1_prompting_guide}`,
fetched 2026-07-30. Official-source. Deviations from that guidance are marked
**[deviation]** with a reason.

---

## 0. Harness settings (set these before sending the prompt)

| Setting | Value | Official basis |
|---|---|---|
| `reasoning.effort` | `xhigh` | "You can use `high` or `xhigh` reasoning effort for your hardest tasks." This is a correctness-critical multi-file fix in an append-only evidence core — the hardest class this program has. |
| `verbosity` | low, overridden to high for code | "set low global verbosity via API parameter, then override within the prompt to request high verbosity specifically for code output." |
| `parallel_tool_calls` | on | "When multiple tool calls can be parallelized … make these tool calls in parallel instead of sequential." |
| `apply_patch` | named/first-class tool | "We strongly recommend using our exact `apply_patch` implementation as the model has been trained to excel at this diff format." |
| mid-rollout plan prompting | **absent** | "remove all prompting for the model to communicate an upfront plan, preambles, or other status updates during the rollout, as this can cause the model to stop abruptly before the rollout is complete." The brief below therefore contains **no** "tell me your plan first" instruction. A *final* report is still required — that is not mid-rollout narration. |

`AGENTS.md` is auto-enumerated root→leaf and injected as its own user-role
message, so this brief deliberately does **not** restate the repo guardrails
that already live in `AGENTS.md` and `scripts/AGENTS.md`. Duplicating them
would create exactly the instruction conflicts the GPT-5.1 guide warns about
("you should be able to shape the behavior significantly by checking for
conflicting instructions and being clear").

---

## 1. Prompt to send

````text
Fix two defects in Packet 5 of the EC-1 evidence-ingestion program, found by
adversarial review of PR #17 and reproduced by execution. Work in the existing
worktree for branch `feature/evidence-upgrade-packet-5`; it is already merged
up to `main` at `aca8114`.

<solution_persistence>
- Treat yourself as an autonomous senior engineer: gather context, plan,
  implement, test, and refine without waiting for additional prompts at each
  step.
- Persist until the task is fully handled end-to-end within this turn: do not
  stop at analysis or a partial fix; carry changes through implementation,
  verification, and a clear explanation of outcomes.
- Bias to action. Implement with reasonable assumptions rather than ending the
  turn on clarifications — with ONE exception, defined in
  <owner_typed_numbers> below. That exception is narrow and explicit; do not
  generalize it into permission to stop anywhere else.
</solution_persistence>

<context_gathering>
Goal: get enough context fast. The defect locations are named below, so
discovery is cheap — do not re-derive the review.
- One parallel batch first: read `market_updates/admission.py`,
  `market_updates/storage.py`, `market_updates/config.py`,
  `market_updates/service.py`, `tests/test_admission.py`.
- Early stop: you can name the exact lines to change (they are cited below —
  confirm them, do not rediscover them).
- Escalate once: if the cited line numbers have drifted, re-locate by symbol
  with `rg`, then proceed. Do not widen scope beyond the files above plus the
  tests you add.
</context_gathering>

## B1 (blocking) — non-immutable claim classes are unconditionally quarantined

Measured facts, all reproduced by execution — treat them as given:

- `ClaimTypePolicy.freshness_window` (`market_updates/admission.py:87`) is
  never set anywhere in the repository: not in any of the eight entries of
  `CLAIM_TYPE_POLICIES` (`admission.py:99-112`), not in tests.
- `ClaimTypePolicy.stale_after()` (`admission.py:92-96`) therefore returns
  `None` for every class whose `freshness_class` is not `"immutable"`.
- `admit()` (`admission.py:297-308`) treats `stale_after is None` as stale and
  returns `QUARANTINED / stale-at-admission`.
- `storage.py:410-412` is the production path: it passes
  `policy.stale_after(...)` straight into the `AdmissionRecord`.
- `admission_enabled` defaults to **True** (`config.py:215-219`; the generated
  config template writes `admission_enabled = true`). This defect is live on
  merge, not latent.

Measured blast radius over `_INGESTION_ROUTES` (`service.py:50`): 7 of 12 live
routes become permanently un-admittable — `bea`, `bls`, `eia`, `fred`,
`treasury_fiscal_data` (all `macro.series`), `twelve_data` (`market.quote`),
`gdelt` (`news.discovery`). Only the four `immutable` classes admit.

Root cause is a semantic collision, not a typo: `stale_after()` returns `None`
to mean "no horizon defined"; `admit()` reads `None` as "expired".

Required:

1. Make the missing-horizon case **fail loud, not fail-silent-quarantine**.
   A non-`immutable` `ClaimTypePolicy` with no `freshness_window` must be
   refused at construction or at settings load — a raised error naming the
   offending claim type — never silently converted into quarantined data.
   Do not add a broad `except`, and do not add a success-shaped fallback.
2. Add a table-driven test that drives `admit()` over **every** entry in
   `CLAIM_TYPE_POLICIES` with the *registered* claim types and asserts each
   expected terminal state. This test must fail on the current code.
3. Populate `freshness_window` for the non-`immutable` classes — see
   <owner_typed_numbers>.

Why the existing 1858-test suite is green: every gate test builds
`BASIC_POLICY` with `freshness_class="immutable"` and a synthetic
`claim_type="claim.basic"` that is not in `CLAIM_TYPE_POLICIES`
(`tests/test_admission.py:38-45`). The eight registered policies are never run
through `admit()` by any test. Guard-removal proves a gate fires when reached;
it cannot prove the gate is reachable with real inputs. Your new test closes
that specific hole, so write it to cover the registered table, not a fixture
that resembles it.

<owner_typed_numbers>
The freshness windows are frozen decision-eligibility parameters. Under this
project's standing rule the owner types them; an implementing agent must not
choose them.

- If the windows were supplied to you as `fast=<...>`, `slow=<...>`,
  `event_driven=<...>`, use exactly those values and quote them back in your
  final report.
- If they were NOT supplied: implement items 1 and 2 in full, leave
  `freshness_window` unset, and make the fail-loud refusal the shipped
  behavior. Do not pick placeholder windows, not even ones you mark TODO. End
  by naming the three values you need. This is the only sanctioned stopping
  point in this task, and it still requires items 1 and 2 complete and green.
</owner_typed_numbers>

## B2 (blocking, process) — the verify-support stage is wired to nothing

`requires_support=True` occurs exactly once in the repository, at
`tests/test_admission.py:44`. All eight registered policies set it `False`, so
the support gate (`admission.py:269-295`) and all of
`market_updates/verify_support.py` can never execute against a real claim
type. `verify_support.py`'s own CLI is documented "not called by ingestion or
CI".

This is the third consecutive round of the same pattern in this program:
something recorded as enforced, exercised by nothing real.

Required — pick exactly one and say which you picked and why:

- (a) Enable `requires_support` on the claim types the architecture intended,
  and add tests proving admission changes as a result; or
- (b) Leave it off and write, in `docs/market_updates.md`, an explicit
  statement that verify-support ships in this packet as a manual operator tool,
  naming the packet that wires it into ingestion.

(a) changes what gets admitted, so if you judge (a) correct, implement it and
flag the behavior change prominently rather than burying it.

## Definition of done — evidence, not assertions

Every item below must be *shown*, not claimed. "N tests passed" is never
evidence that a specific guard works.

1. For each guard you add or change: delete or neutralize it, show the suite
   goes RED, restore it, show GREEN. Report the specific test that failed and
   the counts. This is a standing requirement in this program (D35).
2. Full suite: `python -m pytest tests` from the worktree root. Report the
   count. Baseline on this branch before your change is 1858 passed + 586
   subtests. Measured environment note: that worktree's own `.venv` is stale
   and lacks `bs4`, and has no `pip`; either repair it from
   `requirements-dev.txt` or run with a venv that already satisfies
   `requirements.txt` — and say which you did.
3. `python -m compileall -q scripts`.
4. `python scripts/integrity_check.py --checks dead-citations` — must be
   0 FAIL, 0 WARN. Note: `CITATION_PATH_RE` is unanchored, so any prose you
   write containing a `docs/...`-shaped path for a file outside this repo will
   redden this gate. Do not loosen the guard to get past it.
5. `git diff --check`.
6. `pyproject.toml` and `uv.lock` SHA-256 unchanged start to end, or an
   explicit statement of what changed and why.
7. Alembic chain still resolves to a single head at `0007_admission_gates`.

## Editing constraints

- Default to ASCII. Use `apply_patch` for single-file edits.
- You may be in a dirty worktree shared with concurrent sessions. NEVER revert
  changes you did not make. If unrelated files are modified, ignore them; do
  not stage them. If you notice files changing under you mid-task, stop and
  report.
- Never use `git reset --hard` or `git checkout --`. Do not amend a commit.
- Every number in strategy logic comes from config, not a literal.
- Do not touch `ledger/` or any append-only artifact.

<final_answer_formatting>
- Lead with what changed and why, then the evidence table. No "Summary:"
  preamble.
- Report each red/green experiment as one line: guard → mutation → failing
  test → restored result.
- Reference files by path, optionally `path:line`. Do not paste large diffs or
  before/after pairs; the reviewer reads the diff separately.
- At most two short snippets total, and only where a path reference is
  genuinely ambiguous.
- Reconcile every intention you formed during the task as Done, Blocked (one
  sentence plus the exact question), or Cancelled. Do not end with anything
  in progress.
- Use high verbosity inside the code you write — clear names, straightforward
  control flow, comments only where a block is not self-explanatory. Use low
  verbosity in the final message.
</final_answer_formatting>
````

---

## 2. Instruction conflicts resolved on purpose

The GPT-5.1 guide's migration advice is that behavior problems usually trace to
conflicting instructions. Three conflicts exist between the official Codex
starter prompt and this repo's rules. Each is resolved explicitly above rather
than left for the model to arbitrate:

| Conflict | Resolution in the brief |
|---|---|
| Official: "do not end your turn with clarifications unless truly blocked." Repo: frozen numbers are owner-typed. | `<owner_typed_numbers>` defines one sanctioned stopping point, scoped so items 1–2 must still ship complete and green. Persistence is preserved everywhere else. |
| Official: "Bias to action … make reasonable assumptions and complete a working version." Repo: an implementing agent must not choose decision-eligibility thresholds. | The assumption-making licence is explicitly withdrawn for three named values only, and the fail-loud path is defined as the shipped behavior in their absence — so "complete a working version" stays achievable without them. |
| Official: preambles/plan updates are promptable on current Codex. Migration note: prompting for upfront plans "can cause the model to stop abruptly before the rollout is complete." | No plan-first or mid-rollout narration is requested. The required reporting is a *terminal* evidence report, which the guide's own final-answer section endorses. |

Two places where the official guidance and this repo agree, and the brief
leans on the overlap rather than restating it twice:

- "Tight error handling — no broad catches or silent defaults: do not add
  broad try/catch blocks or success-shaped fallbacks" is *exactly* the shape of
  the B1 fix. The brief names the defect in the guide's own vocabulary so the
  model recognizes it as a first-class instruction, not a local preference.
- "Behavior-safe defaults: gate or flag intentional changes and add tests when
  behavior shifts" is what makes B2 option (a) reportable rather than silent.

---

## 3. Optional pre-flight: self-reflection rubric

If this fix round underperforms, prepend the official self-reflection block —
it is the guide's recommended lever for one-shot quality:

```markdown
<self_reflection>
- First, spend time thinking of a rubric until you are confident.
- Then think deeply about what makes a world-class fix for a fail-silent
  data-admission defect. Use that to create a rubric with 5-7 categories. Do
  not show the rubric to the user; it is for your purposes only.
- Finally, use the rubric to internally iterate on the best possible solution.
  If your response is not hitting top marks across all categories, start again.
</self_reflection>
```

## 4. If the round underperforms: metaprompt, don't rewrite

Official remedy is metaprompting at the end of the turn, not hand-tuning.
Send, verbatim, adapted from the guide:

```text
That was a high quality response, thanks. It seemed like it took you a while
to finish though. Read through your instructions and look for anything that
might have made you take longer to formulate a high quality response than you
needed. Write out targeted (but generalized) additions/changes/deletions to
your instructions to make a request like this one faster next time at the same
level of quality.
```

Then the surgical-revision metaprompt: propose a revision that reduces the
observed issues while preserving good behaviors; do not redesign from scratch;
prefer small explicit edits that clarify conflicting rules and tighten vague
guidance; keep structure and length roughly similar; output `patch_notes` then
`revised_system_prompt`.

Generate the revision two or three times and keep only what recurs across
runs — the guide's caution is that single-run suggestions are often overfit to
that one situation. Any change worth keeping gets an eval before it is adopted.
