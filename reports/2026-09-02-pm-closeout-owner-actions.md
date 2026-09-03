# PM close-out 2026-09-02 — what was finished overnight, what only you can do, what is left

**Provenance:** autonomous orchestration session, night of 2026-09-01 → 02, owner directive
(verbatim): "act as a top project manager and ensure everything thats work in progress is
finished as well as clean up any failures or issues … go through each pull request and close
it out … options validator up and running most optimally by tmwr … look into any deferred
actions … give suggestions for whats left to be done … be completely unbiased and implement
better ideas when needed." Every claim below is labeled Repo-verified, Log-verified,
Test-verified, or Inference. Nothing here appended to any ledger, changed any frozen number,
registered anything, or placed any order.

---

## 1. The one thing only you can do today (before 15:45 ET)

**The Schwab refresh token is dead.** Log-verified: the token file's `creation_timestamp` is
2026-08-23 13:51 ET; Schwab refresh tokens hard-expire 7 days after creation (Official-source,
`reports/2026-08-12-schwab-auth-diagnosis.md` + 2026-08-15 addendum), so it expired
~2026-08-30 13:51 ET. Consequences already on disk:

| Date | 15:45 pre-close chain capture | Intraday quote lane |
|---|---|---|
| 2026-08-31 | FAILED, 15 of 15 names | 0 of 15 |
| 2026-09-01 | FAILED, 15 of 15 names | 0 of 15 |

Per-name receipt note (Log-verified, `reports/schwab_chains/2026-09-01/preclose.json`):
`Refresh token is invalid, expired or revoked`.

**Action:** run the re-auth (needs your Client Secret and a browser; an agent may not do this):

```bash
uv run python tools/setup_schwab.py
```

Do it before 15:45 ET on 2026-09-02 and the scheduled capture resumes the same day. Do NOT
run a same-day manual capture (`docs/h7-forward-operations.md`: same-day retry turns a failed
session into a receipt conflict). The 08-31 and 09-01 chain gaps are permanent by design.

**Why you were not warned:** two defects, both fixed on the ops-fixes branch (§4):
1. The expired-auth classifier (`options_researcher/schwab_auth_failure.py`) required the
   exception's `.error` field to equal `invalid_grant`, but the library raised
   `UnsupportedTokenTypeError` whose `.error` is `unsupported_token_type` — the true cause was
   inside the message text, never inspected. So the log said "PARTIAL FAILURE", not "auth
   EXPIRED — re-auth". (Repo-verified.)
2. No code anywhere computed the token's remaining life; `token_age()` had zero callers.

Downstream, all expected fail-closed behavior from the missing capture (Log-verified):
the 09:09 ritual's pick-tracker recorder raised `SESSION_UNVERIFIED`, H10b/H5 observe lanes
skipped, research refresh reported `UPSTREAM_BLOCKED`. The ritual's persisted receipt correctly
says `OK_STARVED`, but its final console line and exit code said `BROKEN` — a real inconsistency,
also fixed in §4.

---

## 2. Pull requests — 12 open at session start, 6 remaining, every one adjudicated

Direct `gh pr merge` was blocked by the permission classifier for this autonomous session
(same as 2026-08-30). The sanctioned landing path is the daily reconciler (~08:15), which
auto-squash-merges non-draft PRs with all-green checks EXCEPT those touching owner-governed
paths (`ledger/`, `config.py`, `docs/superpowers/`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`,
`.github/`). Those need your click.

### Closed tonight with byte-level evidence (comments on each PR)

| PR | Branch | Why closed |
|---|---|---|
| #140 | codex/handoff | Identical head SHA to #88 (closed 08-30); every file a strict predecessor of main |
| #135 | codex/qm-dashboard-integration-20260717 | 07-17 snapshot; all 16 facts.log lines already on main verbatim (union driver) |
| #127 | claude/pr93-review-round2-2026-08-27 | All 12 files diff 0 lines vs main — PR #93 carried everything |
| #139 | claude/schwab-api-setup-cleanup-79f827 | 08-04 snapshot; merging would revert 5 newer doctrine sections; rule now enforced by the reconciler |
| #125 | spec-3a-invocation-source | A REVERSION: strips the import-time invocation-source anti-forgery snapshot and the Brief 32 sidecar call |
| #143 | codex/a2-outcome-battery | Superseded by #138 (merged 08-31). Tip tagged `archive/codex-a2-outcome-battery` (cited SHAs stay reachable) |
| #144 | claude/options-validator-research-review-e27946 | Superseded by #136 (owner-approved reapply 08-30) |

Local branch copies for all seven were removed with plain `git branch -d` (never `-D`) after
`irreplaceable_data_guard.py verify` → OK; every tip remains on origin.

### Ready to land — will automerge at ~08:15 if checks stay green

| PR | Content | Governed path? |
|---|---|---|
| #141 | 5-line `wiki/log.md` append (RAG-health ingest record) | No → automerges |
| #101 | H7 bar-7 registration packet, row 6 flipped to **MET** citing your 08-31 ruling 1 (commit b748a36) | No (`reports/`) → automerges |

### Ready to land — **need your click** (governed paths)

| PR | Content | Why it needs you |
|---|---|---|
| #136 | The two 2026-08-13 instrument-only specs you approved 08-30 ("114 yes approve and reapply") | `docs/superpowers/` |
| #142 | Brief 36 text + 4-round review receipt (docs only) | `docs/superpowers/` |
| #145 | Your O2/O4 rulings: ratification receipt, corrected addendum, ONE new ledger fact `A2_ENTRY_CONVENTION_RATIFIED_V1` | `ledger/` + `config.py` (comment only) |

#145 was CONFLICTING because GitHub ignores the `merge=union` driver for `facts.log`; resolved
by a local union merge (head f63c7e5: main's facts.log + exactly one added line, zero removed;
Test-verified: a2_runner 47 OK, research_facts 4 OK, ledger_diagnostics 21 OK). Land #145
promptly — an unmerged ledger-touching branch is the chain-fork failure mode.

### Suggested click order
1. #145 (ledger — first, so nothing else appends ahead of it)
2. #136, #142
3. #146 (ops fixes; review PASS, ready). #147 (Brief 36 door) is NOT ready — draft, round-2 FAIL vs
   the moved brief; see §3a.

After the merges, sync production BEFORE 15:45 ET (the capture wrapper refuses to run if ops
is behind origin/main):

```bash
git -C ~/options-validator-ops merge --ff-only origin/main
```

---

## 3. Brief 36 — the H7 Schwab activation door (the critical path to the first real verdict)

Codex DID implement Brief 36 (branch `codex/brief-36-h7-activation-door`, 8 commits, 26 files,
+1710/−68) but never pushed or opened a PR; the branch existed on this laptop only. Pushed
tonight as backup. A fresh Opus adversarial review (Test-verified: 3658 tests OK, ruff 0,
pyright 0; zero `ledger/` lines touched) returned **FAIL** with two blockers:

- **F1 (WP-E):** the quote-age "blocking gate" exists as a library function with zero callers in
  the arming path — exactly the finding-F2 failure mode one level up.
- **F2 (WP-G):** the owner-fields guard refuses every store not in a frozen map, and five test
  files monkeypatch that map — functionally the rejected PR #71 `owner_fields` pattern relocated.

Plus F3–F10 (config fallback for the loss bar, `events[0]` assumption, single-number error, an
un-rederived occupancy figure, missing end-to-end feasibility test, missing bar==7 assertion,
undocumented tightenings, hardcoded cohort). Full receipt: `reports/2026-09-02-brief-36-implementation-review-round1.md`
on the branch. A fix round was dispatched the same night; its result and the round-2 review
are recorded in §3a below.

WP-D (the live `bool("false")` → true durability defect on main), WP-A (input-hash binding),
WP-C (owner-confirmed CLI), WP-I core, and WP-H all held up under attack.

### 3a. Fix-round and round-2 outcome

Fix round completed the same night (12 commits, HEAD e3bf887; Test-verified: 3680 tests OK,
ruff 0, pyright 0; `ledger/` diff 0 lines). Per finding: F1 — `evaluate_schwab_quote_age` is
now called from `open_real_session`, the single arming door every real session and
`h7_entry_preflight` pass through, keyed on the data-gate receipt's Schwab evidence mode
(legacy lane test-enforced untouched; missing sidecar → board refuses; over-threshold →
per-name ban). F2 — `OWNER_FIELDS_BY_STORE` deleted; `resolve_owner_fields(base,
data_gate_result)` is a pure function of store path + evidence mode, each real store refuses
the other lane's evidence, containment restored, all five monkeypatch sites removed. F3 bar
required (named error, no fallback). F4 registration selected by event type, refuses ≠1. F5
both numbers in the error. F6 occupancy expectation re-derived and lockout bound to config
(`H7_SCHWAB_REGISTERED_OCCUPANCY_LOCKOUT_SESSIONS = 42`, schedule-derived, NOT owner-typed,
test-bound to the variant menu's constant). F7 single identity definition + end-to-end
tool-receipt→validator test. F8 two bar==7-under-config-10 assertions. F9 documented, not
reverted. F10 cohort + per-name exclusion reasons in `config.py` with seq-0/packet provenance.

Opened as **draft PR #147**. The fresh round-2 review returned **FAIL** (4 blockers, 6 majors;
receipt `reports/2026-09-02-brief-36-implementation-review-round2.md` on the branch) — and the
reason matters more than the list: **the brief itself moved from rev 3 to rev 8 during this
session** (01:29–02:08 ET, commits 2dbac49…d4fc1c4 on the PR #142 branch, made by a concurrent
session applying the GitHub review-bot waves that fired when #142 was marked ready). Round 1 and
the fix round were against rev 3; round 2 was against rev 7. Rev 7/8 forbid several things the
fixed branch now does: a blocking 60-minute gate (rev 7 WP-E.1 says the 60 is display-only
"Mode A" with an `AWAITING_OWNER_THRESHOLD` verdict until you re-rule and type an ABSOLUTE
threshold); the `count × window / len(sessions)` occupancy scaling (must refuse lookback ≠
window instead); the cohort as a `config.py` constant (must be owner-typed at use time, pinned
to the seq-0 ledger set); no activation-spec file or CLI pin; whole-universe GO instead of
per-included-name GO (WP-J). Round-1's F1 finding ("gate has no callers") was a mis-finding
against rev 7, which explicitly ships the gate with no production caller.

**Decision taken:** no third round tonight against a moving target. PR #147 stays DRAFT with
both receipts committed and both PRs cross-linked. **Next:** one fix round against the FINAL
brief revision (confirm #142's head first), explicitly reverting the F1 wiring in
`options_researcher/h7_session.py`, then round-3 review, then your click.

**Process lesson (recorded, not blamed):** two autonomous sessions worked the same lane in the
same hour without a shared lock. The 08-31 note already warned about this. Suggested rule: a
session that intends to revise a brief or implement it posts a one-line "claim" comment on the
brief's PR first; the other session checks the PR thread before dispatching.

**Consequence to carry forward (unchanged from the brief):** the new `config.py` constants
move `config_hash()`, so every pre-merge feasibility / source-health / data-gate receipt is
invalid by design; regenerate them at the merged config before the activation CLI. No
validator was weakened to accept old receipts.

---

## 4. Ops fixes shipped tonight (PR #146, branch `claude/ops-fixes-2026-09-02` — independent review PASS, receipt committed)

All four are small, test-driven, and reviewed; none changes a frozen number or a verdict path.

| # | Defect | Fix |
|---|---|---|
| F1a | Expired-token classifier gated on the wrong exception field | Classify on the message text; test with the exact 09-01 exception |
| F1b | No token-age warning anywhere | New `options_researcher/schwab_token_age.py` (offline arithmetic on `creation_timestamp` + 7 days); one advisory line in the 09:09 ritual and the 15:45 capture log; `SCHWAB_REFRESH_TOKEN_HARD_EXPIRY_DAYS = 7` in `config.py` labeled Official-source |
| F3 | CI Secret Scan false positive on main @6e08cf8 (gitleaks fingerprint pinned to old line 44; the constant moved to line 49; the ignore-file comment itself reproduced the string) | New fingerprint + reworded comment. Not a real secret: it is the plain-text ledger label `PIN_FACT_TOKEN` |
| F5 | Ritual prints `RITUAL STATUS: BROKEN` / exit 1 on days its own receipt says `OK_STARVED` | Final echo/exit reuses the same carve-out the receipt and notification already use |

---

## 5. Deferred / open items — recommendations (unbiased, with the counter-argument)

1. **Research-refresh lane has never passed its preflight since the 08-27 retime** (Log-verified:
   7 consecutive runs, three different causes; the 09-01 cause is the stale board from §1).
   The guard derives its "as-of" from the attractiveness board's freshness, which lags whenever
   Schwab captures fail. **Recommendation:** decide whether this LLM refresh should key on the
   ritual's own `run_status_*.json` (runs daily regardless of chain health) instead of the
   board. Counter-argument: refreshing research context against a stale board may be exactly
   what the guard should refuse. Owner call; medium change; not done tonight.
2. **The scorer-reads-config-at-verdict-time defect** (Brief 36 round-3 N1) exists for every
   registered window, not only Schwab. The 08-31 note flagged H10b/H5. Recommendation: one
   read-only audit that lists, per live window, where its loss bar comes from (event vs config).
3. **`.tmp/worktrees/a2-governance-facts`** holds an unpushed reconciler rescue commit and an
   uncommitted working-tree change that are exact duplicates of the #145 ledger line. Cleanup
   was classifier-blocked tonight. After #145 merges: `git worktree remove` will refuse
   (modified file); this needs your manual `--force` or a decision to leave it.
4. **`.claude/worktrees/gracious-neumann-d938c9`** hosts the nested H7-packet worktree and 1,105
   `.remember` log files — keep until #101 lands, then it is a candidate.
5. **Live dashboard** shows exit −15 in `launchctl list`; that is five-week-old bookkeeping. The
   server on 127.0.0.1:8765 has been up since 08-26 and answers 200. No action.
6. **Pioneer `FwUpdateManagerd` zombie leak** (PROJECT_STATE 08-25) — permanent fix still open.
7. **Schwab weekend re-auth is a standing manual chore** with a 7-day fuse. The new token-age line
   makes the fuse visible daily; the honest next step is a Friday reminder in the digest, not
   automation of the re-auth (it needs your secret).

---

## 6. Plain-English status after tonight

- **Done:** every stale PR adjudicated and closed with evidence; six PRs green and ready; H7
  packet records your GO; A2 ratification queued; Brief 36 implementation pushed, reviewed twice
  (draft PR #147, not mergeable yet); four operational blind spots fixed with tests (PR #146); 20 dead local branches and one dead
  worktree removed; everything that existed only on this laptop is now on GitHub.
- **Open, yours:** Schwab re-auth (today), three governed-path clicks, ops sync before 15:45.
- **Next:** land Brief 36 door → regenerate cohort-9 feasibility + source-health + data-gate
  receipts at the post-merge config → you run the activation CLI typing bar 7, the OD-3 line,
  and the pre-acceptance → H7 forward window registered → the first real verdict clock starts.
