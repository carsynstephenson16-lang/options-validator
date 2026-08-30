# Briefs 24 / 29 / 31 — independent adversarial review receipts (2026-08-26 evening)

**Orchestrator:** Claude Fable 5 session on `claude/codex-handoff-plan-2026-08-22`
**Reviewers:** three independent Opus adversarial reviewer agents, one per brief,
each retained across rounds so the correction rounds were judged by the author
of the original findings. Every round was read-only against
`origin/main@4ab1a385c3ee6a5c97285f9bf0a341f5a69feac5` plus the working-tree
revision under review; reviewers re-derived claims from primary artifacts
(files, logs, `gh` timelines, and — for the brief-24 parser contract — `git`
behavior measured in throwaway repos).

Process shape per brief: round-1 full adversarial review → orchestrator
repairs → bounded correction round(s), maximum two, by the same reviewer.
The reviewers' full texts are the reviews of record; this receipt records the
verdicts, the round structure, and the dispositions that bind hand-off.

---

## Brief 29 — Schwab inventory binding (DATA-01)

`docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md`

| Round | Revision | Verdict | Substance |
|---|---|---|---|
| (prior) | rev 2 source proposal | FAIL | `reports/2026-08-26-brief-29-independent-review-receipt.md`, blockers 1–8 |
| 1 | rev 3 | **FAIL** | 4 blocking (WP-B broke `RepoRootAnchoringTests`; acceptance `verify` could not pass as written; `TRACKED_NAMESPACES` comment promised more than the specced code delivered; false Repo-verified data description) + 7 important + 4 minor (R3-F1…R3-F15) |
| 2 (correction 1) | rev 4 | **FAIL** | 14/15 answered; R3-F1's repair rested on a false premise (the CLI fixtures do NOT override `--inventory`; they isolate by cwd) — residuals N-1…N-4 |
| 3 (correction 2, final) | rev 5 | **PASS** | Reviewer hand-traced the seeded fixture through all five `RepoRootAnchoringTests` methods under the new WP-A/WP-B code — every one passes on its original assertions, including the `present: false`-coupling case. Five minor, non-gating residuals — ALL APPLIED in the committed revision. |

Reviewer's final verdict line: "**PASS** … No new defect that can produce
wrong behavior, data mutation, or an un-implementable step."

**Carried forward, binding on brief 30's next review round:** brief 30's
inventory regeneration for `.cache/schwab_chains_midday` must use
`generate --only` (which creates a missing key additively), never a plain
whole-list `generate`. Brief 29 cannot edit brief 30 (its own OUT list);
this receipt is the durable pointer.

**Hand-off state:** the owner package's reopened-decision condition
("a rev against current main answering the blockers, plus a fresh
independent written PASS, before hand-off",
`reports/2026-08-25-codex-audit-verification-owner-package.md:168-181`) is
now satisfied. Hand-off proceeds under the owner's 2026-08-26 evening
in-session directive to produce and execute the Codex handoffs that finish
the audit arc (provenance: owner message in-session; no frozen number
involved).

---

## Brief 24 — repo-reconcile arc, rev-4 additions (SEC-02 fold + default-draft)

`docs/superpowers/plans/2026-08-24-24-repo-reconcile-redeploy-codex-brief.md`

| Round | Revision | Verdict | Substance |
|---|---|---|---|
| 1 | rev 3 additions | **FAIL** | 5 high (live multi-pushurl bypass in the parser contract, measured in throwaway repos; WP-C contradicted the brief's own OUT list; nothing ever redeployed the new code; the correction of record understated the deployed automerge loop by four guards; sequencing over-reach labeled owner-binding) + medium/low (R24-F1…R24-F18) |
| 2 (correction 1, final) | rev 4 | **PASS** | All six mandatory fixes verified line-by-line; reviewer also re-verified its own round-1 refutation targets (PR #82 owner-un-draft timeline TRUE; PR #70 reconciler-created→non-draft→automerged chain TRUE). Three residuals; the one with teeth (empty-pushurl cross-check would refuse every repo) — APPLIED; the IN-list enumeration — APPLIED; Status update — this receipt. |

Reviewer's final verdict line: "**PASS** … Rev 4 is ready for Codex."

Material new findings of record from this arc (now in the brief's
correction-of-record section): the DEPLOYED automerge loop lacks
`--author "@me"`, `--base main`, the governed-path refusal, and
`--match-head-commit`, and auto-merged a `.github/` workflow change on
2026-08-26 (landing itself owner-sanctioned); the deployed post-commit
auto-push has NEVER worked (`setsid` absent on macOS); PR #70 was created
non-draft by the reconciler and automerged with no human in the loop —
the live violation WP-D closes.

**Hand-off state:** WP-C/WP-D ready for Codex as a PREPARED DRAFT PR;
landing/deploy remain gated on the owner's WP-B redeploy (binding
sequencing), and the prepare-early clause stays Agent-proposed
(Inference, owner may veto). WP-B itself is the single most urgent OWNER
action in the arc.

---

## Brief 31 — audit close-out follow-ups (SEC-01 test pinning + digest wiring)

`docs/superpowers/plans/2026-08-26-31-audit-closeout-followups-codex-brief.md`

| Round | Revision | Verdict | Substance |
|---|---|---|---|
| 1 | rev 1 | **FAIL** | 3 blocking (threat statement claimed a non-existent live exploit — the workflow's `if:` keys off `event_name`; WP-B omitted the REQUIRED `--as-of` argument; checkout/out-dir placement unresolved and self-contradicting) + F4-F16 |
| 2 (correction 1, final) | rev 2 | **PASS WITH FIXES → applied** | All 16 round-1 findings + 4 round-2 defects verified answered; F9 registry-tidy condition satisfied (row 30 added with the renumbering backed by commit `3659bd4`'s own message; 28/29 status notes match `origin/main`); six cosmetic residuals — ALL APPLIED in the committed revision. |

Reviewer's final verdict line: "**Verdict: PASS.** … this brief is ready:
WP-A to hand off now, WP-B parked behind the owner's yes or no."

**Hand-off state:** WP-A ready for Codex immediately (separate PR). WP-B is
OWNER-GATED — brief 21 assigned invocation wiring to the owner; the
build/install split needs an explicit owner yes before Codex may start it.

---

## Registry

`docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md` gained: row 30 (closing
the registry gap; renumbering evidenced by commit `3659bd4`), dated factual
status notes on rows 28/29, the intake collision marked resolved-in-fact,
and row 31 (reserved and tracked together with its brief). Reviewed within
the brief-31 arc (F9/F16 closed by the round-2 reviewer against the
working tree).
