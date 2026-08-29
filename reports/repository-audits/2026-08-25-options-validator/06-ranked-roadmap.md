# Ranked Roadmap

## Now — Lane A

1. **SEC-01: authorize comment-triggered Claude review callers (score 90).** Add a failing offline workflow-contract test; require the comment author's association to be exactly `OWNER`, `MEMBER`, or `COLLABORATOR` on both comment event branches; deny `NONE` and unlisted values; preserve automatic `pull_request` review; run targeted/static verification; and obtain fresh independent spec and quality review. One local candidate commit only; no push or PR. If the trusted-comment policy causes an unexpected workflow regression, disable both comment triggers and their condition branches while retaining automatic `pull_request` review; do not restore public untrusted triggering.

## Next — owner-reviewed plans

2. **DATA-01: bind existing Schwab evidence into the irreplaceable-data inventory.** First preserve and inventory canonical ops bytes, define exact namespace/deep-hash expectations, review the generated tracked diff, and prove the absent-populated-removed regression. This is operational data authority, not Lane A.
3. **SEC-02: replace spoofable Git-remote ownership matching.** Design one strict canonical GitHub remote parser/owner verifier shared by all hooks, including effective `pushurl`, and test every supported URL form. Because this changes global push authority and overlaps protected WIP, it requires separate owner review.
4. **WIKI-01: refresh derived current-status notes.** Correct H5 observer-only, paused/no-namespace H7, closed H10a, narrowed H10b, disabled ThetaData acquisition, and authority-tier/dashboard drift; add commit/date stamps and append the required wiki lint log only under explicit vault-update authority.
5. **DATA-02/DATA-03: define quote-age and close-lineage contracts.** Obtain an owner-approved, source-supported quote-age policy and a raw-to-derived close receipt design before changing any decision-bearing gate or provider workflow.

## Later / evidence first

- Add macOS zsh CI only after runner, cost, and secret boundaries are chosen.
- Add repo-rag CI only after it is declared a supported release surface.
- Reproduce the localhost Host/origin scenario in the actual browser/deployment before changing the preview protocol.
- Measure dashboard I/O on a declared cache snapshot before any performance edit.
- Collect admissible realized fills before calibrating execution; do not infer capacity, assignment, or broker behavior from quotes alone.

## Do not build now

- No CSCV/PBO on the heterogeneous, underpowered current trial set.
- No broad config refactor, H6/H8 watcher merge, dashboard rewrite, ritual rewrite, mass format, new strategy variant, provider acquisition, cache refresh, backtest, or production promotion.

## Rollback and authority

Every future item keeps existing fail-closed behavior and append-only evidence. No roadmap item authorizes live orders, paper-book mutation, provider calls, ledger changes, cache mutation, vault edits, deployment, push, merge, or PR creation. Only SEC-01 is currently implementation-authorized by the master prompt's Lane A gate.
