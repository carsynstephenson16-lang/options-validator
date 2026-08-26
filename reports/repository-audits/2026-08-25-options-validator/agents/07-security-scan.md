# Standard Codex Security Scan

**Status:** COMPLETE
**Scan ID:** `07f7e340-decc-460e-a642-abc93000d0a7`
**Frozen target:** `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`
**Mode:** Standard single-pass; no Deep Scan
**Generated report:** `/private/var/folders/zt/zktvcc0n0z1cq0kdt3mvg5lh0000gn/T/codex-security-scans-042DI2/2026-08-25-1403-options-validator-audit/c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771_20260825T181702Z_wiv3sj8e/report.md`

## Verdict

The scan reported **two Medium and one Low** finding. The public-comment authorization defect is the only security candidate that is narrow, unprotected, and plausibly Lane A. The global auto-push defect is plan-only because its root control spans protected operational push authority. The localhost finding remains lower-confidence and needs a runtime/browser threat-boundary decision before implementation.

## Findings

1. **Medium / high confidence — credentialed Claude review can be invoked by any PR commenter.** The `issue_comment` and `pull_request_review_comment` paths check only for an `@claude` substring (`.github/workflows/claude-review.yml:60-65`), then expose the configured Claude OAuth token to the pinned reviewer (`:77-87,112-127`). The repository was verified public. Two independent Terra source reviews reached the same finding. Existing SHA pins, base-branch `REVIEW.md`, and per-PR concurrency prevent broader claims about code substitution or token disclosure, but they do not authorize the caller or prevent sequential/cross-PR quota consumption. Candidate: require `OWNER`, `MEMBER`, or `COLLABORATOR` author association on both comment paths.
2. **Medium / high confidence — global auto-push ownership uses a spoofable URL substring.** `tools/anti-stranding/post-commit:26-52`, `claude-session-rescue.sh:29-45`, and `worktree-remove-guard.sh:30-48` treat a remote as owner-controlled when the raw URL merely contains the cached login. The installer makes the hook global (`install.sh:9-14`). A crafted push-capable non-GitHub remote can satisfy that pattern. Gitleaks and protected-branch exclusions reduce impact but do not verify remote identity. Plan-only: the shared operational root overlaps protected WIP and changes push authority.
3. **Low / medium confidence — localhost dashboard lacks Host validation.** `options_researcher/live_dashboard.py:453-477` routes only by path; `/live.json` can reach the cached refresh path (`:493-525`). Loopback binding, absent permissive CORS, TTL single-flight, session/probe gates, and the lack of any order/mutation endpoint materially reduce severity. A remote disclosure path needs DNS rebinding or an equivalent browser bypass. Park pending a deployment/browser reproduction and an explicit decision on local capability protection.

## Reviewed controls and non-findings

- Schwab secret/token storage uses Keychain, strict private-path and mode checks, and a market-data-only method allowlist; no account/order authority was found.
- H7 Restic backup/restore uses structured argv, fixed backup paths, exact snapshot binding, a temporary restore root, and inventory/receipt verification; no attacker boundary survived validation.
- No production `eval`, `exec`, `pickle`, unsafe YAML, `shell=True`, or `os.system` use was found by the offline search.
- Repo-RAG SQLite user inputs were parameterized in reviewed paths.
- Current provider policy disables ThetaData acquisition before legacy approval-token paths execute.

## Coverage and limitations

- Two Terra auditors fully reviewed 29 security-relevant files and the parent independently validated the three retained findings. Coverage is **partial** across the 1,111-file repository.
- No exploit, provider/network call, secret read, or operational mutation was performed.
- The security preflight was ready with a non-blocking warning: three usable worker slots versus the scanner's preferred six.
- Advisory TAC status could not be retrieved because the optional connector was not authenticated; this did not gate the scan.
- The workbench warned that report artifacts changed the worktree during the scan; results remained sealed to the original frozen snapshot.

## Stop condition

Reached: one Standard scan was completed and sealed, every retained finding has a source path, attack prerequisites, counterevidence, remediation, and candidate decision, and no Deep Scan was started.

