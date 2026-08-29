# Adversarial Verification — Ranked Roadmap

**Audit target:** frozen `main` snapshot `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`
**Review mode:** independent, read-only source review followed by a comparison
with `06-ranked-roadmap.md`. No provider, strategy, order, paper-book, cache,
ledger, or operational command was run.

## Initial verdict: PASS WITH CORRECTIONS

The roadmap correctly keeps authority-bearing data, provider, H7, strategy,
and operational work out of Lane A. It makes no profitability claim and does
not authorize a live order, paper-book write, provider call, cache mutation,
ledger change, push, merge, deployment, or vault update.

Its single Lane-A assertion, however, is not ready to be represented as a
numeric threshold decision. `05-diminishing-returns-analysis.md` declares
that the CSV's 0--5 fields are not score inputs, but supplies neither the six
criterion allocations nor applied penalties for SEC-01. The stated score of
92, and therefore the claim that it clears an 85-point gate, cannot be
independently recomputed from the current audit artifacts.

## SEC-01 adjudication

**Finding status: supported.** The public repository's comment-triggered
workflow permits either a PR issue comment or review comment containing
`@claude` without an `author_association` predicate
(`.github/workflows/claude-review.yml:60-65`). If
`CLAUDE_CODE_OAUTH_TOKEN` is configured, that path reaches the Claude action
with the secret (`:77-87`, `:112-127`). The defect is untrusted authorization
of metered credential use; this review found no evidence of secret disclosure
or arbitrary shell execution by a commenter.

**Hard-gate status: none identified.** The affected workflow is not in the
136-path protected inventory, and the narrow repair does not alter research,
strategy, provider, data, H7, or push authority. The automatic
`pull_request` branch should remain unchanged unless a separate policy change
is approved. A temporary removal of comment triggers is a simpler emergency
rollback, but is not preferable to a scoped caller check for the normal fix.

**Lane-A eligibility once a reproducible table is supplied: conditionally
approved.** SEC-01 may be admitted to Lane A if, and only if, the table:

1. Lists all six stated criteria with a numeric allocation and total out of
   100, plus every applied penalty (including an explicit zero where none
   applies).
2. Ties the evidence score to the public-repository check and the exact two
   predicates above, and states the configured-secret condition.
3. Shows a final score of at least 85 after penalties, with `protected WIP`,
   `dependency`, `authority`, `data mutation`, and unsafe-mutation gates all
   explicitly recorded as absent.
4. Uses a test/rollback contract that is actually executable without
   credentials: reject untrusted associations on *both* comment branches;
   allow exactly the documented trusted set; preserve automatic PR review;
   and safely disable both comment triggers while retaining automatic PR
   review if rollback is needed.

With that table and contract, this is a narrow, reversible, dependency-free
access-control repair and is eligible for Lane A. Until then, the correct
roadmap state is **"Lane-A eligible; score pending"**, not "currently
implementation-authorized by the Lane-A score gate."

## Required corrections

1. **Make scoring reproducible.** Add the SEC-01 component/penalty table to
   the diminishing-returns artifact or candidate registry and replace the
   unexplained `92`/`>=85` assertion. Do not manufacture a score from the CSV
   comparative 0--5 columns.
2. **Correct the threat wording.** Replace “any public PR comment reaches the
   token-bearing action” with “a comment on a PR containing `@claude`, from
   any association, can invoke the credentialed action when the OAuth secret
   is configured.” The no-secret path visibly skips the optional reviewer.
3. **Specify the implementation contract.** Apply the association condition
   to `github.event.comment.author_association` in each comment branch. Name
   the allowed associations (`OWNER`, `MEMBER`, `COLLABORATOR`) and explicitly
   deny `NONE` and unlisted values. A condition on the PR author would not fix
   the caller-authorization defect.
4. **Make validation concrete.** The proposed workflow-contract test must
   assert both comment branches and the retained automatic-PR branch; a YAML
   parse alone does not test GitHub-expression semantics. Keep it offline and
   credential-free, and add static workflow validation only when available
   without adding a production dependency.
5. **Correct TST-03 wording.** `tools/repo_rag` is offline and stdlib-only,
   but has no `uv.lock`. Its future CI plan must not call the suite “locked”
   unless a separately reviewed lock is introduced; use its documented
   `python3 -m unittest discover -s tests` contract instead.

## Other roadmap checks

| Check | Result | Evidence and ruling |
|---|---|---|
| Duplicate candidates / simpler alternatives | Pass | The roadmap consolidates DATA-02/DATA-03 and does not re-propose already-landed chain-consistency or fill-adversity work. Emergency disabling of comment triggers is noted above as rollback, not a competing feature. |
| Hidden protected-WIP overlap | Pass | SEC-02 still overlaps protected `tools/anti-stranding/repo-reconcile`; architecture/dashboard/H7/config paths remain plan-only. SEC-01 and CI workflow paths are absent from the recorded protected inventory. |
| Data/provider authority | Pass | DATA-01 remains an operational data-authority mutation; DATA-02/03 require an owner-approved data contract. ThetaData remains disabled (`data/provider_policy.py:1-25`). |
| H7/strategy authority | Pass | The roadmap does not restart or register H7. Current authority has `h7_active=False`, and full ritual evaluation reports no active namespace (`data/ritual_authority.py:38-49,69-84`). |
| Statistical overfitting / false profitability | Pass | The roadmap correctly rejects CSCV/PBO for the heterogeneous underpowered set and requires admissible realized fills before calibration. It makes no positive strategy or execution claim. |
| Test and rollback sufficiency | Correction required only for SEC-01 and TST-03 | SEC-01 needs the explicit test matrix above. DATA-01, SEC-02, and data-lineage items retain appropriately named evidence, rollback, and authority gates. |
| Unsupported localhost finding | Pass | The roadmap preserves SEC-03 as evidence-first pending actual browser/deployment reproduction; loopback and CORS counterevidence are not overstated. |

## Initial ready decision

**Not ready to execute SEC-01 under a score-gated Lane-A authorization until
the score table and workflow-contract test specification are added.** After
those corrections, SEC-01 is the only supported candidate that can enter Lane
A without a separate owner authority decision. All other roadmap sequencing
remains supported and appropriately fail-closed.

## Parent adjudication

All five required corrections were accepted. `04-candidate-registry.csv`
now states the configured-secret condition, names the exact caller policy and
offline test contract, and corrects TST-03's command. The SEC-01 score was
recomputed rather than preserved: `05-diminishing-returns-analysis.md` now
allocates all six positive components (94 subtotal), applies a named
four-point complexity penalty, records every zero penalty and hard gate, and
produces a final score of 90. `06-ranked-roadmap.md` now carries that score,
the exact trusted and denied associations, the retained automatic PR branch,
and the safe trigger-disabling rollback. The parent therefore adjudicates SEC-01 as Lane A:
90, no protected overlap, no dependency, no data mutation, no authority hard
gate, and no unsafe-action reject gate.

## Final verdict after adjudication: PASS

The initial corrections are satisfied. SEC-01 is ready for the prompt's
Lane-A implementation phase at a reproducible score of 90, subject to the
required test-first writer and independent post-change review. No other
candidate is implementation-authorized by this audit.
