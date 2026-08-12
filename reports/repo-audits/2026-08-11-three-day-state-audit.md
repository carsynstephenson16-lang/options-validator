# Three-day repository state audit — 2026-08-11

**Auditor:** Claude (Fable) lead session, orchestrating five Sonnet workstream agents plus two fresh Sonnet verifiers (adversarial + completeness), per the audit mission of 2026-08-11.
**Mode:** read-only. The only repository write is this report. Not committed, not pushed, per mission boundaries.

---

## 1. Executive verdict

**SOUND WITH RESIDUALS.**

Everything that landed on `main` in the last 72 hours was inspected at the code level, re-tested, and checked against the repo's governance rules, and the landed work itself holds up: the H7 Schwab restart machinery is genuinely build-only and owner-gated (registration store VALID-EMPTY, authority flags `False`, the prepared authority-flip patch unapplied, the one-door AST test a real enforcement mechanism); the four attractiveness experiments comply with the 2026-08-09 authorization (display-only, causal, config-frozen constants, and the production attractiveness dashboard plus its ranking code are **byte-for-byte identical** across the whole 49-commit window); the ledger stayed append-only; the OOS seal is intact; provider boundaries held; and the full test suite at HEAD is green — 2645 tests, 0 failures, 11 environment skips — reproduced in three independent runs (54 errors appear only when the documented `.env` variable `LIVE_MARKET_DATA_PROVIDER=schwab` is absent, a pre-window hermeticity gap, not a regression).

The residuals are state debt, not broken code. Zero BLOCKER findings. One HIGH finding: an owner-ruled, adversarially-reviewed, cryptographically chain-valid RQ2 amendment (K=2→K=3, would-be ledger seq 25, provenance label `owner-delegated standing 2026-07-25` present) is stranded on unmerged branches `claude/rq2-k3-and-dashboard-split` / `claude/rq2-k3-stale-docs`, while three documents on `main` still tell readers the K discrepancy is unresolved and awaiting owner adjudication. Main's ledger stops at seq 24; the branch entry's `prev_hash` matches main's seq-24 hash and verifies with the real `research.ledger.verify()`. Nothing indicates a deliberate hold — this looks simply unlanded.

Six MEDIUM findings: (1) the new expired-Schwab-auth classification in `intraday_capture.py` is silent in the common steady-state (fresh probe) because pre-existing per-batch/per-symbol `except Exception` handlers swallow the `OAuthError` first — empirically reproduced both ways: the banner fires only when the schema probe is stale/missing; the sibling preclose lane's fix works fully; (2) the new `evaluate_exact_session_package` / `external_exact_session` gate branch in `h7_data_gate.py` has zero direct test coverage, though its own implementation plan listed `tests/test_h7_data_gate.py` as "Modify"; (3) `PROJECT_STATE.md` — the designated canonical status — was last updated 2026-08-04, predates the entire window, and its H7 section no longer reflects the prepared (not activated) restart; `README.md` Scope status is similarly stale; (4) the `evidence/ops-august-2026-08-09` branch is by-design, documented archival of the Aug 5–7 capture receipts (session note on main names it), but there is no fold-back plan, `ledger/facts.log` has diverged (mergeable cleanly — verified with `git merge-tree`), and whether the underlying Aug 5–7 intraday parquet bytes exist anywhere beyond the production disk is an open owner question; (5) `feat/h7-forward-schwab-v1` merged without the independent adversarial review its own owner-gate packet lists as a prerequisite for the authority flip — the flip must not be typed until that review exists; (6) commit `d77f995` is labeled `docs(h7)` but removed a real validation check (`code_sha` equality) from registration-event building — reasoned and still hash-verified, but invisible to changelog-level audits.

Two candidate findings were **killed** by the adversarial verifier: there is no "competing dashboard-split architecture" (unmerged brief 06 specifies exactly the standalone `experiments_dashboard.py` design that shipped; only the brief file itself is missing from main), and `codex/qm-dashboard-integration-20260717` is an ordinary stale branch, not a disjoint history (the "no common ancestor" result was a shallow-clone artifact, disproven after deepening).

**Single highest-priority next action:** land (or have the owner explicitly veto) the RQ2 seq-25 amendment stack, then refresh `PROJECT_STATE.md`/`README.md` to match reality — the code is in better shape than the record of it.

---

## 2. Audit boundary

| Item | Value |
|---|---|
| Session start (WINDOW_END) | 2026-08-11 20:26:59 EDT / 2026-08-12 00:26:59 UTC |
| WINDOW_START | 2026-08-08 20:26:59 EDT / 2026-08-09 00:26:59 UTC |
| Repository path | `/home/user/options-validator` (fresh cloud clone, single worktree) |
| Checked-out branch | `claude/options-validator-audit-izf37s` |
| LOCAL_HEAD == LOCAL_MAIN == AUDIT_HEAD (origin/main via GitHub API + fetch, re-confirmed twice) | `f9aad05cf70f76971f87b2be45b13033e0a87bfa` |
| WINDOW_BASE (last main commit before window) | `c875839` (Merge PR #28, 2026-08-05) |
| Commits reachable on main since WINDOW_BASE | 50 (49 authored in-window + `66500c9`, authored 2026-08-05, legitimately introduced by in-window merge `71e0526`) |
| Merges landed on main in window | exactly 10: `1866f59`, `ea83d48`, `2779569`, `9640b92`, `d6ed665`, `c39d5b6`, `f9aad05`, `d2ae2e5` (PR #30), `5d98895` (PR #29), `71e0526` — each first-parent diff byte-identical to its feature branch (no smuggled content) |
| Files changed in window | 83 |
| Working tree | clean at baseline and at completion; no stashes; no extra worktrees |
| PRs | #29, #30 merged in-window; #31 open draft (`claude/ai-engineering-portfolio-project-a08276`, single standalone portfolio doc, read in full — no repo-governance content) |
| Tags | one, pre-window (`archive/2026-08-03/docs/replan-2026-07-22`); none created in window |
| Limitations | (a) clone was **shallow** at session start (boundary ≈2026-07-31); deepened during verification (additive objects only, no ref changes). (b) No `.env`, no gitignored caches, no `~/options-validator-ops` / `~/options-validator-research`, hooks in `settings.local.json` not registered here — production-host state not inspectable. (c) A `tests` package inside site-packages shadows dotted test invocation; `unittest discover -s tests` (the documented command) is unaffected. |

---

## 3. Three-day change inventory

| # | Workstream | Commits | Files (core) | Purpose | Status | Evidence |
|---|---|---|---|---|---|---|
| 1 | H7 Schwab forward lane | merge `1866f59` (13 commits `d6b771d`…`c1563ec`) + `2d68a8c`, `64635c2`, `6a38040` | `data/schwab_adapter.py`, `options_researcher/schwab_chain_capture.py`, `tools/schwab_chain_manifest.py`, `options_researcher/h7_schwab_data_gate.py`, `h7_schwab_window_registration.py`, `tools/h7_schwab_feasibility.py`, `tools/h7_forward_backup.py`, `ledger/h7_forward_schwab/README.md`, plist template, gate packet + feasibility receipt | Build (not activate) a Schwab-based H7 restart lane: preclose capture → hash-verified manifest → exact-session gate → owner-gated registration namespace + feasibility measurement | VERIFIED (inert by design; owner-gated) with findings M2, M5, M6 | Test-verified (all 9 targeted modules green); Repo-verified (`ritual_authority.py` flags False; registration store empty; `register_window_real` has zero callers) |
| 2 | Attractiveness experiment program | `5942eb2` + merges `ea83d48`, `2779569`, `9640b92` (EXP modules, wiring `1fe8169`, hardening `6c41585`, receipts) | `options_researcher/exp_{beta_qqq,tail_shape,spread_stability,tbill_carry}.py` + tests, `config.py` EXP block, specs/briefs, review receipts | 4 display-only scanner experiments under the 2026-08-09 owner authorization | VERIFIED; finding L1 (2 constants outside config.py) | Test-verified (49 experiment tests + 4 baseline-isolation tests green); Repo-verified (causal truncation at `asof` in each module; no ledger/positions imports) |
| 3 | Experiments dashboard split | `09d2344`, `e67a895`, `e5ab2eb` via merges `c39d5b6`, `f9aad05` | `options_researcher/experiments_dashboard.py` (new), `attractiveness_dashboard.py` (restored), `tests/test_experiments_baseline.py` | Physically remove experiment code from the production dashboard into a standalone manual-only module | VERIFIED — `git diff c875839..f9aad05 -- options_researcher/attractiveness_dashboard.py` is empty; AST import-boundary + subprocess byte-check tests enforce it | Test-verified + Repo-verified; both CLIs run clean here |
| 4 | Ops failure classification | `0964e81` via merge `d6ed665` | `options_researcher/schwab_auth_failure.py` (new), `intraday_capture.py`, `schwab_chain_capture.py`, both `.sh` wrappers, design doc + receipt | Classify expired Schwab OAuth (invalid_grant / refresh token) as a distinct operator-actionable failure in both capture lanes | PARTIAL — preclose lane VERIFIED end-to-end (empirical, unmocked); intraday lane conditional (finding M1) | Test-verified + two empirical unmocked reproductions (adversarial verifier scratch drivers preserved in session scratchpad) |
| 5 | Data-guard cwd anchoring fix | `427f3b2` via PR #29 (`5d98895`) | `tools/irreplaceable_data_guard.py`, its test, CLAUDE.md note | Anchor the guard on the main checkout from any cwd; exit 2 = LOCATION, never data loss | VERIFIED | Test-verified (18/18); live run here exits 1 (fresh-clone cache absence — expected, and correctly *not* exit 2) |
| 6 | Chain-policy refactor | `50af90f` | `data/chain_policy.py` (new), `thetadata_adapter.py` re-exports, `live_quotes.py` import | Move provider-neutral helpers verbatim out of the retired ThetaData adapter | VERIFIED (identity-pinned by `test_chain_policy.py`; 27 importers resolve unchanged) | Test-verified |
| 7 | Docs / evidence / skills / wiki | `71e0526`, `d2ae2e5` (`3d5266e`), `7395e82`, `a2ad377`, `32afcc8`, `0abf9cb`, `66500c9`, `fae63a9`, `d77f995` (doc part), receipts `61a061a`/`9281a52`/`aae0e9c` | source-standard docs, Bright Data DECLINED, skill fail-closed `[NO_INPUT]` sentinel, architecture-review decision, wiki log, owner gate packet | Record decisions and reviews | VERIFIED (docs match behavior where checkable); wiki RAG stats duplicate flagged (L-INFO) | Repo-verified |
| 8 | Unmerged in-window work | PR #31 (`59a0071`); `codex/options-validator-plugins-design` (3 commits, 4 spec docs, 2026-08-11); `claude/rq2-k3-and-dashboard-split` + `claude/rq2-k3-stale-docs` (`f230813`, `d91a8e9`, `f1e7dec`); `evidence/ops-august-2026-08-09` (`863175a`) | — | See findings H1, M4; PR #31 and plugins branch are standalone spec/docs work with no dangling references from main | CLASSIFIED (see §7) | Repo-verified |
| 9 | Superseded / stale branches | `codex/attractive-exp-{beta-qqq,spread-stability,tail-shape,tbill-carry}` (patch-id-equivalent content landed), `docs/h7-schwab-restart-codex-brief-2026-08-09`, `port/qm-frozen-study-guard`, `sfix`, `claude/schwab-api-setup-cleanup-79f827` (pre-window; unadopted CLAUDE.md "branch hygiene" rule), `codex/qm-dashboard-integration-20260717` (ordinary stale branch; merge-base `38a6b57` 2026-07-17 — "disjoint history" disproven after unshallowing) | — | — | SUPERSEDED / STALE | Repo-verified (`git cherry`, patch-id, deepened merge-base) |

---

## 4. Findings (severity-ordered)

### BLOCKER — none.

### H1 [HIGH] Owner-ruled RQ2 K=3 ledger amendment (seq 25) stranded off-main; main's docs still call the question open
- **Facts (all Repo-verified, adversarially confirmed):** `ledger/experiments.jsonl` on main ends at seq 24. Branch commit `f230813` appends seq 25 (`RQ2_AMENDMENT_V1_1`): `prev_hash` matches main's seq-24 `record_hash`; the chain **verifies with the real `research.ledger.verify()`** run against the branch blobs; the entry carries the required provenance label `owner-delegated standing 2026-07-25`, records an independent adversarial review (PASS-WITH-EDITS, edits adopted), and quotes the owner ruling ("it was 3 i want it to be 3 not 2", in-session 2026-08-10). Sibling commit `f1e7dec` fixes the stale K=2 references in `config.py`, the robustness addendum, and two 2026-08-09 reports. Neither commit is an ancestor of HEAD. Three main docs still describe the discrepancy as unresolved/owner-needed: `reports/2026-08-09-parking-lot-471-selection-report.md:214`, `reports/2026-08-09-attractiveness-experiment-authorization.md:107-110`, `docs/superpowers/specs/2026-08-09-attractiveness-experiment-program-design.md:239` (the third is not fixed even on the branch). No hold/veto/abandonment evidence exists anywhere (wiki, session notes, commit messages searched).
- **Impact:** main misinforms on a registered hypothesis's frozen parameter (RQ2-v1 opens 2026-09-01); any session bootstrapping from main would re-open a question the owner already ruled on, or worse, build RQ2 badges to K=2.
- **Adversarial verdict:** CONFIRMED (verifier severity MEDIUM-HIGH: no chain-fork risk, no RQ2 badge code exists yet, branch is pushed). Lead ruling: HIGH on governance-currency grounds.
- **Repair:** merge the `claude/rq2-k3-stale-docs` stack (superset of both commits) — the adversarial verifier confirmed it is a clean append; also fix the third stale doc. Owner confirmation of the merge is prudent since it lands a ledger entry.

### M1 [MEDIUM] Intraday expired-auth classification is silent in the common steady-state path
- **Facts (Test-verified + empirical):** `intraday_capture.py:817`'s new `except OAuthError` fires only when the schema probe is stale/missing (then `run_probe()`'s unguarded `regular_session_state` call at `live_quotes.py:341` lets the error propagate — proven unmocked: banner + exit 1). With a **fresh probe** (the common case; probes are valid 7 days per `LIVE_PROBE_MAX_AGE_DAYS`), the per-batch/per-symbol `except Exception` handlers (`intraday_capture.py:741-744, 748-761`) swallow the same `OAuthError`: result is exit 0, `coverage: 0/N`, no banner — proven unmocked. The only test of the catch mocks `capture()` wholesale; the working stale-probe path has no test either. Sibling preclose lane (`schwab_chain_capture.py:193-195`) re-raises correctly and is fully verified. Design doc claims the goal for "both unattended capture lanes."
- **Impact:** operator actionability only (lane is display-only, zero verdict authority): a real expired-token day in steady state looks like a generic zero-coverage outage instead of `SCHWAB REAUTH REQUIRED`.
- **Repair:** Codex brief 1 (§10).

### M2 [MEDIUM] New H7 exact-session gate branch has zero direct test coverage
- **Facts (Repo-verified):** the window added `schema_policy="external_exact_session"`, the `CacheAuditReceiptError → CHAIN_V2_AUDIT_RECEIPT_INVALID` NO_GO branch, and `evaluate_exact_session_package()` (with a reserved-evidence-mode `ValueError` guard) to `options_researcher/h7_data_gate.py`. `grep -rln "evaluate_exact_session_package\|external_exact_session\|CHAIN_V2_AUDIT_RECEIPT_INVALID" tests/` → no hits; `tests/test_h7_schwab_data_gate.py`'s refusal tests all raise in `verify_session` before reaching these paths; `tests/test_h7_data_gate.py` — which the implementation plan (`docs/superpowers/plans/2026-08-09-h7-schwab-restart-implementation.md`) listed as "Modify" — was untouched.
- **Impact:** untested NO_GO and mode-confusion guards in the entry-authority gate the owner will rely on at OD-3 time. Dormant today (no CLI wiring).
- **Repair:** Codex brief 2 (§10). Must be closed before the authority flip.

### M3 [MEDIUM] Canonical status documents predate the window
- **Facts (Repo-verified, two independent paths):** `PROJECT_STATE.md` last touched `b62e1df` 2026-08-04 (audit stamp 2026-08-02, audited checkout an `sfix` HEAD); silent on all four in-window workstreams; its H7 §Q11 ("DO NOT RESTART NOW … any later attempt must use a new registration and namespace") is honored in the letter by the window's build (new namespace, nothing activated) but no longer describes current preparedness. `README.md` Scope status last touched 2026-08-04; no mention of the H7 Schwab restart machinery or the experiments (position/holdings figures were verified byte-accurate). Its P0 gate is **not** violated: P0.1–P0.6, P0.8 were already VERIFIED COMPLETE pre-window, and the in-window authorization doc reconciled this explicitly. Current state exists but is fragmented across dated reports (H7 session note, split receipt, ops receipt, selection report).
- **Impact:** any agent following CLAUDE.md's index bootstraps 8 days behind, and the fragmentation defeats the "single-source index" design.
- **Repair:** owner-typed or delegated PROJECT_STATE.md + README Scope-status refresh; add the H7 Schwab PREPARED/NOT ACTIVATED row.

### M4 [MEDIUM] August ops evidence lives only on an archival branch, with open questions
- **Facts:** `evidence/ops-august-2026-08-09` (`863175a`) holds the sole copies of `reports/intraday_capture/2026-08-{05,06,07}/*` receipts, `reports/live_probe/2026-08-05.json`, an inventory update, and 20 `ledger/facts.log` lines. **By-design and documented** — main's `reports/h7_forward_schwab/2026-08-09-session-note.md` names the branch and SHA ("Preserved August ops evidence on pushed branch…"); it is pushed to origin. Residuals: (a) receipts of this class normally live on main (Jul 24/27/28 do); (b) `reports/` paths are outside `irreplaceable_data_guard.py`'s namespace list, so the guard would never notice this branch's loss; (c) `facts.log` has since diverged (main +1 line, branch +20; `git merge-tree` shows a clean, conflict-free union — no chain risk, it is a plain flock-append log); (d) **unknown:** whether the raw `.cache/intraday` parquet bytes for Aug 5–7 (inventory count 180→360 on the branch) exist anywhere beyond the production disk — only JSON receipts were committed.
- **Repair:** merge the branch (clean per merge-tree) or record an explicit archival policy + deadline; owner to confirm the parquet bytes are on the production machine and covered by backup.

### M5 [MEDIUM] H7 Schwab lane merged without its gate-packet-required adversarial review
- **Facts (Repo-verified):** the owner gate packet (`fae63a9`) lists "Independent adversarial review is resolved" as prerequisite #4 of 6 before any authority flip, "pending orchestrating Claude/Opus." No adversarial-review receipt for `feat/h7-forward-schwab-v1` exists anywhere in the repo (contrast: the experiment program got two receipted review rounds pre-merge). Merged code is inert (empty ledger namespace, flags False, one-door test), so present risk is low.
- **Repair:** commission and receipt the review before the owner types OD-3. This audit's WS2/WS3 code inspection is evidence but is not the commissioned review the packet describes.

### M6 [MEDIUM] Commit `d77f995` mislabeled: "docs(h7)" removed a validation check
- **Facts (Repo-verified):** the commit deletes the `feasibility["code_sha"] != evidence["code_commit"]` equality check from `h7_schwab_window_registration.build_window_registration_event`, with a new test asserting the looser (reasonable — receipts may legitimately predate doc-only commits) behavior; the feasibility receipt remains hash-verified (`_validate_feasibility`; hash independently recomputed True this session). Not a security bypass; a changelog-level audit would miss a functional change to registration validation.
- **Repair:** one-line correction note in the H7 session note or gate packet; message discipline going forward.

### M7 [MEDIUM] Preclose capture lane ops gaps (latent until the plist is installed)
- **Facts (Repo-verified):** `tools/schwab_chain_capture.sh` (a) collapses REFUSED / receipt-CONFLICT (exit 2) / partial-failure into one generic BROKEN bucket where the intraday sibling has four distinct branches; (b) has no `osascript` operator notification (log-file only); (c) same-day retry after any partial capture is unsalvageable by design (whole-universe refetch + `_write_parquet_once` hash-match-or-refuse) — consistent with the "Monday canary is 15/15" all-or-nothing bar but undocumented as an operational constraint. Plist is a TEMPLATE ONLY, not installed.
- **Repair:** Codex brief 3 (§10), before the canary.

### LOW findings
- **L1:** `exp_tail_shape.py:40,43` — `_JUMP_MIN_PERIODS=126`, `_FAT_TAIL_EXCESS_KURTOSIS=1.0` live outside `config.py` (siblings route all constants through config); both provenance-labeled and test-covered. Move or document the carve-out.
- **L2:** Brief 06 (`docs/superpowers/plans/2026-08-10-06-experiments-dashboard-split-codex-brief.md`, `d91a8e9`) never landed on main although its implementation did. Adversarial verifier **refuted** the "competing architecture" theory: the brief specifies exactly the shipped standalone design (verified detail-for-detail incl. `EXPERIMENTS_OUTPUT_PATH`). Paper-trail gap only; landing `f1e7dec`'s stack would also bring this file.
- **L3:** `ideas-parking-lot.md:1214` still says the four experiments are "NOT yet implemented — Codex unavailable at selection time" — false at HEAD (all four shipped same day).
- **L4:** CLAUDE.md points to `reports/strategy-evaluations/12_review_of_the_two_landed_commits.md` as "Open engine defects (read before touching backtest code)" while PROJECT_STATE P0.2–P0.6 (more recent) record those defects as closed; nothing marks the report historical.
- **L5:** Test hermeticity: 54 tests (31 `test_intraday_capture`, 23 `test_live_quotes`) error without `.env`'s `LIVE_MARKET_DATA_PROVIDER=schwab` because `live_quotes.py:348` evaluates the `getattr` default eagerly (`_configured_provider()` runs even when the fake client supplies `provider_name`). Pre-window (≤2026-07-31/2026-08-01). CLAUDE.md's "OFFLINE" test framing doesn't mention the `.env` dependency.
- **L6:** Test-isolation leak: running the suite **without** the env var writes a stray `reports/live_probe/2026-07-15.json` into the real repo tree (observed and removed twice this session; candidate origin among the five test modules using that fixture date). Cosmetic but pollutes working trees.
- **L7:** `h7_schwab_data_gate.evaluate()` fails package-tamper cases via uncaught `SchwabChainManifestError` rather than the module's NO_GO-code contract — intentional and crash-visible, but inconsistent; normalize before CLI wiring.
- **L8:** Data guard `--allow-absent` still alarms on an exists-but-empty `.cache/chains` (auto-mkdir'd by an import); working as documented, worth a doc note.
- **L9:** H7 Schwab lane code commits carry no implementer attribution (no Co-Authored-By / "Implemented by" trailers), unlike `50af90f` and the Codex experiment commits; the brief names Codex as implementer but git cannot corroborate — a division-of-labor auditability gap, not a demonstrated violation.
- **L10 (pre-window, informational):** `claude/schwab-api-setup-cleanup-79f827` holds an unadopted 2026-08-04 CLAUDE.md "branch hygiene" rule absent from main; `wiki/log.md`'s 2026-08-05 and 2026-08-09 RAG-health entries report byte-identical stats (594 sources / 14879 chunks) — plausible, unverifiable here.

---

## 5. Changes verified as correct

- **Experiment program isolation** — strongest evidence in the audit: `attractiveness_dashboard.py`, `attractiveness.py`, and `test_attractiveness_dashboard.py` are byte-identical from `c875839` to `f9aad05`; the frozen GREEN-fraction recipe cannot have moved. Isolation additionally enforced by an AST import-boundary test and a subprocess byte-check of the no-args CLI. All 4 experiment modules verified causal (truncation at `asof`, `shift(1)` sigma, `known_as_of_utc` filters), fail-closed (`DATA_BLOCKED` cards, no escaping exceptions), display-only (no ledger/positions imports), stamped with `max_asof`. Two in-window self-corrections (`9c04f6d`, `1070073` — the latter fixed a genuine causality bug, `valid_through` → `source_date`) confirmed present at HEAD and test-locked.
- **H7 Schwab lane inertness** — registration store VALID-EMPTY; `register_window_real` has zero callers; authority-flip patch unapplied (`ritual_authority.py` flags False, file untouched all window); one-door AST test re-run green and proven non-tautological (catches a reconstructed evasion); ledger-edit hook extended to the new namespace (33/33 tests); capture writes atomic + hash-refuse-on-overwrite; manifest verification validates hashes/sizes/row-counts/receipt binding, not existence; plist TEMPLATE ONLY with `RunAtLoad=false`; wrapper enforces branch==main==origin/main fail-closed; read-only client allowlist contains no order/account methods; `SCHWAB_TRADING_ENABLED=false` hardcoded in both wrappers.
- **Feasibility governance** — the recorded feasibility **fails** the 2026-07-24 2× gate (3.0 expected entries vs 20 needed from 3/1050 base rate) and is correctly routed to the owner fail-path with nothing typed; receipt hash independently recomputed True.
- **Preclose auth classification** (`schwab_chain_capture.py`) — expired-token OAuthError propagates through the real `capture()` to a single `auth EXPIRED` banner + exit 1; shell escalation branch verified.
- **Data-guard fix** — 18/18 tests incl. worktree/subdir/outside-repo/genuine-loss fixtures; live run here correctly identifies this clone as its own main checkout (exit 1, not a false LOCATION error).
- **Chain-policy refactor** — verbatim move pinned by an object-identity test; all importers resolve.
- **Ledger/OOS/provider boundaries** — window's only ledger change is an added README; no appends, no edits; `allow_oos` usage all under the disclosed PIVOT_4NAME_SCOPE policy, legacy holdout untouched, reveal budget still 0/3; no network-client imports in any experiment/dashboard code; `.cursorrules`↔`AGENTS.md` authorization text word-identical; no dependency, CI, or lint-config changes in-window; test delta reconciles (+110 methods, ~2536→2645, no weakened assertions, no broadened excepts).
- **Receipts** — substantive, not rubber stamps: Stage B review found a real vacuous-test bug; Stage C has red-then-green tracebacks whose current equivalents re-run green; the split receipt's byte-hash and grep claims verified at HEAD; the Fable PASS receipt's deferred blast-radius item (F4/R6) was later resolved architecturally by the split. All receipt-referenced SHAs are ancestors of HEAD except the evidence branch, which is correctly described as unmerged.

---

## 6. Current project state (fresh-evidence matrix)

| Domain | State at `f9aad05` | Evidence |
|---|---|---|
| Engineering / CI | Full suite green: 2645 tests, 0 failures, 11 skips (env skips for absent real caches) given documented `.env`; ruff clean; pyright clean; no CI workflows changed in-window | 3 independent full runs this session |
| Research — live hypotheses | H5 alert-only · H6 seq 6 INSUFFICIENT_SAMPLE, one open NVDA call · H7 seq 7-10 PAUSED (OD-3), new `h7-forward-schwab-v1` namespace PREPARED/NOT REGISTERED/NOT ACTIVATED · H8 seq 11 zero positions · H10a seq 15 (ends 2026-10-06) · H10b seq 16 (ends 2027-01-06) · RQ1 seq 17 SPENT · RQ2-v1 seq 18 opens 2026-09-01 — **K=2 on main, owner-ruled K=3 amendment unlanded (H1)** · A2-v1 seq 19 not built · REGIME-AMI seq 23-24 display-only | ledger parsed directly; README registry cross-checked |
| Experiments lane | EXP-BETA/TAIL/SPREAD/TBILL shipped display-only in standalone `experiments_dashboard.py`; nothing autoruns it; promotion owner-gated | code + grep + tests |
| Data / providers | ThetaData acquisition permanently disabled (OD-4); v1 cache frozen 2026-07-27; Schwab read-only lane authorized; `.cache/schwab_chains` machinery built, zero live bytes captured; `data/rates/` committed and causal | `docs/provider-transition.md` (updated in-window — the one core doc that is current) |
| Operations | 15:45 ET preclose capture job exists as an uninstalled template; intraday capture live on production host (not inspectable here); expired-auth classification: preclose lane working, intraday lane conditional (M1); Aug 5–7 receipts on archival branch (M4) | code + session note |
| Ledger / OOS | `experiments.jsonl` chain VALID to seq 24; `facts.log` intact (+1 line in window via merge); `h7_forward` event ledger VALID (1 record); `h7_forward_schwab` VALID-EMPTY; legacy holdout sealed, 0/3 reveals spent | verify CLIs exit 0 |
| Governance | Ship-blocker retired (2026-08-03) stands; 2026-08-09 experiment authorization honored; all owner gates listed in §7 untriggered; hooks and guardrail twins in sync | WS3 + completeness verifier |
| Roadmap | **No current canonical statement** — PROJECT_STATE.md stale since 2026-08-04 (M3); truth fragmented across dated reports | git log on the file |

---

## 7. Remaining-work queue

**Repair now** (order = dependency + urgency; none touch prohibited surfaces beyond their stated scope):
1. **Land or veto the RQ2 seq-25 stack** (`claude/rq2-k3-stale-docs` ⊇ `f230813`+`d91a8e9`+`f1e7dec`) — owner confirms, orchestrator merges; then fix the third stale doc (`…experiment-program-design.md:239`). Proof: ledger seq 25 on main, `research.cli verify` OK, zero K=2 references outside history. *(H1, L2, part of M3's doc set)*
2. **Fix intraday expired-auth propagation** — Codex brief 1. Proof: new red-first tests green; both probe states produce the banner + exit 1. *(M1)*
3. **Refresh PROJECT_STATE.md + README Scope status** to cover the window (H7 Schwab PREPARED row, experiments lane, ops classification, dashboard split, RQ2 resolution once landed). Owner types any frozen numbers; drafting delegable. Proof: both files dated ≥ this audit, consistent with `docs/provider-transition.md`. *(M3)*
4. **Decide the evidence-branch fold-back** — merge `evidence/ops-august-2026-08-09` (merge-tree clean) or record archival policy; owner confirms the Aug 5–7 parquet bytes exist on the production disk. *(M4)*

**Next after repairs:**
5. Exact-session gate test coverage — Codex brief 2. *(M2)*
6. Commission + receipt the H7 Schwab adversarial review (gate-packet prerequisite #4). *(M5)*
7. Preclose ops parity (taxonomy, notification, retry-constraint doc) — Codex brief 3, before the canary. *(M7)*
8. Doc corrections batch: `d77f995` note (M6), parking-lot line 1214 (L3), CLAUDE.md report-12 pointer (L4), guard `--allow-absent` note (L8).

**Later:** test hermeticity (default/inject provider label in tests; fix the eager `getattr` at `live_quotes.py:348`) (L5); test-isolation leak (L6); `h7_schwab_data_gate` error-contract normalization before CLI wiring (L7); move tail-shape constants into config.py or document the carve-out (L1); commit-attribution discipline (L9); adopt-or-reject the parked branch-hygiene CLAUDE.md rule (L10).

**Owner-gated (untriggered; do not act without typed owner input):** OD-3 typing for `h7-forward-schwab-v1` incl. starvation accept (quoting 3.0 vs 20) or redesign; authority flip (only after Monday canary 15/15 + backup drill + M5 review + registration); any experiment promotion (2026-07-24 gate applies); RQ2 V1 statistic pinning (post-seq-25 amendment, pre-result); T-bill ex-div forward calendar sourcing; rates CSV refresh; H10 wiki skew-badge mislabel decision.

**Parked:** per `ideas-parking-lot.md` (32 sections; 2026-08-09 dispositions recorded; parked ≠ rejected).

**Closed / superseded:** the four `codex/attractive-exp-*` branches, `docs/h7-schwab-restart-codex-brief-2026-08-09`, `port/qm-frozen-study-guard(-v2)`, `sfix`, `codex/qm-dashboard-integration-20260717` (ordinary stale, content superseded), PR #24–#30 lineage; the "competing dashboard design" and "orphan history" theories (refuted this audit).

---

## 8. Documentation and truth drift

| Record | Drift | Ref |
|---|---|---|
| `PROJECT_STATE.md` | STALE — canonical status 8 days behind; silent on entire window | M3 |
| `README.md` Scope status | STALE — no H7 Schwab restart row, no experiments lane | M3 |
| 3 docs claiming RQ2 K unresolved | FALSELY OPEN — owner ruled 2026-08-10; fix unlanded | H1 |
| `ideas-parking-lot.md:1214` | FALSE at HEAD ("NOT yet implemented") | L3 |
| CLAUDE.md → report 12 pointer | STALE framing ("open engine defects" vs P0-recorded closure) | L4 |
| CLAUDE.md test command framing | INCOMPLETE — "OFFLINE" suite silently requires `.env` provider label | L5 |
| Commit `d77f995` message | MISLABELED — "docs" commit with functional validation change | M6 |
| Brief 06 | MISSING from main though implemented | L2 |
| Stage B review (`61a061a`) | Historically accurate but describes a superseded enforcement mechanism (flag dict, later replaced by physical split) — read with the split receipt | INFO |
| `wiki/log.md` RAG entries | Byte-identical stats 4 days apart — unverified | L10 |
| `docs/provider-transition.md` | **CURRENT** — the positive control; updated in-window, all claims verified | §5 |

---

## 9. Verification ledger

Environment: fresh Linux cloud container, Python 3.12 via `uv sync --frozen` (exit 0). No `.env`; gitignored caches absent; production ops dirs absent; repo hooks unregistered here; clone shallow at start, deepened during verification (additive only).

| Command | Exit | Result |
|---|---|---|
| `uv run python -m unittest discover -s tests` (bare env) | 1 | 2645 tests, **54 errors** (31 `test_intraday_capture`, 23 `test_live_quotes` — all `LIVE_MARKET_DATA_PROVIDER` RuntimeError), 11 skips |
| `LIVE_MARKET_DATA_PROVIDER=schwab uv run python -m unittest discover -s tests` | 0 | **2645 tests, OK, 11 skips** — lead run; independently reproduced by WS2 (192s), WS4 (188.5s), completeness verifier; adversarial verifier got 10 skips post-unshallow (`test_source_hash_reproducibility` shallow-guard skip now runs and passes — mechanism proven) |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run pyright` | 0 | 0 errors, 0 warnings |
| `git diff --check` | 0 | clean |
| `uv run python -m research.cli verify` | 0 | `ledger OK` |
| `uv run python -m options_researcher.h7_event_ledger verify` | 0 | `VALID records=1 head=a1ea228c2abb` |
| `uv run python tools/irreplaceable_data_guard.py verify` | 1 | All cache namespaces missing/lost — **expected fresh-clone state** (correctly not exit-2 LOCATION); not evidence of production data loss |
| `uv run python -m tools.research_context_assemble --verify` | 3 | `UPSTREAM_BLOCKED: RESEARCH_RITUAL_ROOT is required` — correct fail-closed behavior in this container |
| `uv run python -m options_researcher.attractiveness_dashboard` | 0 | renders; all names `BLOCKED: NO_CACHED_CHAINS` (expected, no cache) |
| `uv run python -m options_researcher.experiments_dashboard` | 0 | renders standalone experiments page |
| `uv run python -m options_researcher.h7_entry_preflight` | 1 | refuses (no data-gate receipt here); writes nothing |
| Targeted modules (each `unittest discover -p`) | 0 | `test_chain_policy` 1 · `test_core` 37 · `test_exp_beta_qqq` 11(1s) · `test_exp_tail_shape` 11(1s) · `test_exp_spread_stability` 13(2s) · `test_exp_tbill_carry` 14(1s) · `test_experiments_baseline` 4 · `test_experiments_dashboard` 4 · `test_attractiveness_dashboard` 110 · `test_live_quotes` 70 · `test_intraday_capture` 80 · `test_schwab_chain_capture` 8 · `test_schwab_chain_schedule` 3 · `test_shell_banner_guard` 3 · `test_schwab_chain_manifest` 6 · `test_h7_backup` 4 · `test_h7_one_door` 7 · `test_h7_schwab_data_gate` 7 · `test_h7_schwab_feasibility` 5 · `test_h7_schwab_window_registration` 10 · `test_schwab_adapter` 15 · `test_block_ledger_edits` 33 · `test_irreplaceable_data_guard` 18 — all OK |
| Empirical reproductions | — | M1 both paths (unmocked fake-client drivers); seq-25 chain verify via real `research.ledger.verify()`; `git merge-tree` clean union for facts.log; feasibility `receipt_hash` recomputes True; brief-06 == shipped design; deepened merge-base `38a6b57` |
| **Skipped deliberately** | — | `h7_data_gate` / `h7_schwab_feasibility` real runs (write governance receipts); `h7_source_health`, `live_quotes --probe`, `live_dashboard`, `daily_ritual` (live/provider-adjacent lanes); RAG ingest re-run |

Side effects of this audit, all reverted or inert: one leaked test artifact (`reports/live_probe/2026-07-15.json`) created by the bare-env suite run and removed; verifier scratch artifacts created under `reports/` during empirical drivers and removed; local clone unshallowed (objects only, no refs); `git status --porcelain` empty at completion; HEAD unchanged at `f9aad05`.

---

## 10. Codex handoff briefs

### Brief 1 — Propagate expired-Schwab-auth through `intraday_capture.capture()` (M1)
- **Defect:** with a fresh schema probe, an authlib `OAuthError` (`invalid_grant`, "Refresh token is invalid, expired or revoked") raised by any client call inside `capture()` is swallowed by the per-batch handler (`options_researcher/intraday_capture.py:741-744`) and per-symbol handler (`:748-761`), yielding exit 0 / zero coverage / no banner. `main()`'s `except OAuthError` (`:817`) is reached only via the stale-probe path (`live_quotes.py:341` unguarded).
- **Fix shape:** in both handlers, check `schwab_auth_failure.is_expired_refresh_token_error(exc)` and re-raise — mirror `schwab_chain_capture.py:193-195`. Do not change non-auth per-symbol fail-open semantics.
- **Tests (red-first):** drive the real `capture()` (fake client only, no `capture()` mock) in (a) fresh-probe and (b) stale-probe states with every client method raising the exact authlib error; assert `main()` exits 1 with the `intraday_capture auth EXPIRED:` banner in both. Keep the existing wrapper-string contract (`tools/intraday_capture.sh:118-119`) unchanged.
- **Acceptance:** new tests fail on current HEAD, pass after; full suite green; ruff/pyright clean. **Prohibited:** network, ledger writes, changes to receipt schema.

### Brief 2 — Direct tests for the exact-session gate branch (M2)
- **Gap:** `options_researcher/h7_data_gate.py` — `evaluate_exact_session_package()`, `schema_policy="external_exact_session"`, `CacheAuditReceiptError → CHAIN_V2_AUDIT_RECEIPT_INVALID` NO_GO, and the reserved-evidence-mode `ValueError` guard have zero direct tests; the implementation plan listed `tests/test_h7_data_gate.py` "Modify" but it was untouched.
- **Scope (test-only):** synthetic fixtures exercising (a) receipt-validator-raises → NO_GO with `CHAIN_V2_AUDIT_RECEIPT_INVALID` in the reasons; (b) `REAL_H7_EVIDENCE_MODE` / `SYNTHETIC_EVIDENCE_MODE` rejected with `ValueError`; (c) a happy-path evaluation of a manifest-verified synthetic package. No production-code change expected — if a defect surfaces, stop and report rather than fix.
- **Acceptance:** new tests green; no change to any non-test file; full suite green.

### Brief 3 — Preclose capture ops parity (M7)
- **Scope:** `tools/schwab_chain_capture.sh`: split the generic BROKEN bucket into REFUSED / RECEIPT CONFLICT (exit 2) / partial-failure / generic, mirroring `tools/intraday_capture.sh:114-121`; add the `osascript` notification the sibling has; document the same-day-retry constraint (whole-universe refetch + hash-match-refusal ⇒ a session completes only in one atomic run; stale partials need explicit operator handling) in `docs/h7-forward-operations.md` and the wrapper's failure text.
- **Acceptance:** `tests/test_schwab_chain_schedule.py` + `test_shell_banner_guard.py` extended and green; no behavior change to `schwab_chain_capture.py` itself. Land before the Monday canary.

*(No briefs for M3/M4/M5/H1 — those are owner/orchestrator decisions and doc work, not implementation defects. M6 needs a one-line receipt note, not a brief.)*

---

## 11. Unknowns

1. Whether the raw Aug 5–7 `.cache/intraday` parquet bytes exist on the production disk and in backup — only receipts are in git (owner/ops question). *(M4)*
2. Schwab's live OAuth error wire format vs the hard-coded match string — untestable offline; classified **Inference**; control flow around it is Test-verified. 
3. Production-host state: installed LaunchAgents, `.env`, `~/options-validator-ops` receipts, cache integrity — not inspectable from this container; the guard's alarming output here is environmental.
4. `wiki/log.md` RAG ingest stats — not re-runnable here.
5. Receipts' claimed suite runs in their authoring environments — accepted via independent reproduction at HEAD, not via replay at each historical SHA.
6. Who actually implemented the unattributed H7 Schwab code commits — brief says Codex; git is silent. *(L9)*

---

*Evidence chain: five workstream evidence packets (git/integration, code/regression, research integrity, data/ops, project-state/docs) + adversarial and completeness verifier packets, all produced 2026-08-11/12 within this session; scratch drivers for the empirical reproductions preserved in the session scratchpad. Prohibited-action check: no branch/ref mutations, no ledger writes, no provider calls, no OOS reads, no receipt-writing CLIs invoked; the two receipt-writing tools were explicitly not run.*
