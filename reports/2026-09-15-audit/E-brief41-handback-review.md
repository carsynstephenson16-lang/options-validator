# Brief 41 — implementation hand-back review (adversarial)

**Reviewer:** Claude (audit session 2026-09-15) · **Read-only**: no commit, merge, push, checkout, or tracked-file edit.
**Subject:** `codex/brief-41-launchagent-loaded-check`, tip `21d016f` (2026-09-10), 17 files, +1258/−12 vs `main`.

## Hand-back receipt (skill slots)

| # | Slot | Value | Label |
|---|---|---|---|
| 1 | Head SHA | `21d016fd4694d6f9a124ae31f7722777eb6e17d0` — review is of this SHA only | Run-verified |
| 2 | Brief revision pinned | `3537ca7` on `main` (`docs/superpowers/plans/2026-09-09-41-…-codex-brief.md`), header reads **rev 8**; branch copy byte-identical. `3537ca7` is also the branch's merge-base — the executor built from the exact commit that landed rev 8 | Run-verified |
| 3 | CI at that SHA | **NOT VERIFIED** — `gh pr checks` needs network, which this session is barred from. No PR state claim is made here | Unverified |
| 4 | Suite re-run by reviewer | see Task 2 — all green | Run-verified |
| 5 | Artifacts committed | `git log --diff-filter=D main..21d016f` → **no deletions**; all 7 brief-41 receipts present on the branch. No prior FAIL receipt rewritten | Run-verified |
| 6 | Finding-by-finding | Task 1 + Task 3; unanticipated input = real `launchctl print-disabled` output format (Task 3f) | Run-verified |
| 7 | Ops sync plan | after owner merge: `git -C ~/options-validator-ops fetch -q origin main && git -C ~/options-validator-ops merge --ff-only origin/main`, then confirm `rev-parse HEAD == origin/main` before 15:45 ET. Never `reset --hard` ops | Repo-verified |

**Post-landing `diagnostic_source_hash()` (brief R2-B2 obligation):** `f66c436492670d7008e040f22e1f489abcb9e539558dcdee8c23cda930ac052e` (Run-verified on the branch). It **has** rotated, exactly as rev 8 predicted. Every H7 source-health / data-gate receipt cut before landing goes stale and the gates refuse loudly.

## Task 1 — Work package → code map

| WP | Requirement | Evidence (file:line, branch) | Status |
|---|---|---|---|
| A.1 | `classify()` pure, 14 tuples + 2 raises, listed sort order | `options_researcher/launchagent_state.py:51-65`. I hand-enumerated all 16 tuples: the chain maps each correctly; `DISABLED` beats `LOADED` (R3-4) via the `not disabled` guard on branch 1 | MET |
| A.1 | `compare()` universe = tracked ∪ prefixed installed ∪ prefixed loaded; `disabled` contributes no label | `:68-98` — universe at `:76-80` matches the brief verbatim; sort by `(enum order, label)` at `:97-98` | MET |
| A.2 | `tracked_labels()`, 4 roots, plistlib → regex fallback, `ValueError` naming file + match count | `:101-130`; catches `(ExpatError, plistlib.InvalidFileException)` at `:113`; non-mapping / missing / empty `Label` → identical `"match count 0"` raise at `:126` (R5-M4) | MET |
| A.3 | `/bin/launchctl` absolute; only `list`/`print`/`print-disabled`; injectable `run`; `gui/<os.getuid()>` | `:156-190`; argv at `:157,169,179`; `uid=os.getuid()` at `:270` | MET |
| A.3 | `observe()` assembler, `Observation` dataclass, `FileNotFoundError` → `unavailable_inputs=('list','print','print-disabled')`, `compare()` never sees `None` | `:193-223`; `disabled or frozenset()` at `:218` (R6-m2) | MET |
| A.4 | Receipt schema v1, six counts, `atomic_text_write`, keyed by `run_date` | `:226-243`, write at `:281`; path `reports/ritual/launchagent_state_{run_date}.json` at `:279`. Arg order `(text, path)` matches `data/atomic_io.py:66` and the `ritual_status.py:120-121` idiom | MET |
| A.5 | CLI flags, `--run-date` required unless `--no-receipt`, empty `--as-of` permitted with the exact message, summary line, **always exit 0** | `:246-315`; message `:266-269` verbatim; `receipt=none (--no-receipt)` `:277`; argparse `SystemExit` swallowed at `:255-258` so even a bad flag exits 0 | MET |
| A.5 | Print order INSTALLED_NOT_LOADED → DISABLED → UNTRACKED | `:288-301` iterates sorted states, so `LOADED_NOT_INSTALLED` prints *before* `UNTRACKED`, and it prints a line for `LOADED_NOT_INSTALLED` the brief never listed | EXCEEDS SCOPE (cosmetic, harmless) |
| A.2 | duplicate-`Label` guard | `:127-128` — defensive, not requested by the brief | EXCEEDS SCOPE (benign) |
| A.5 | receipt-write `OSError` → advisory line, incident lines still printed, exit 0 | `:282-285`, pinned by `tests/test_launchagent_state.py:314` | EXCEEDS SCOPE (good) |
| B.1/B.2/B.3 | 11 lines after `:385`, region-marked, comment block, no `note`, no substitution | `tools/daily_ritual.sh:386-396` — see Task 3c | MET |
| C.1 | `_launchagent_state(root, as_of)`, receipt-based, full status mapping | `tools/job_health_digest.py:716-871`; `NOT_INSTRUMENTED` only when no receipt exists at all; stale/`as_of: null` suppress `OK`; `INSTALLED_NOT_LOADED`/`DISABLED` → `FAILED`; `UNTRACKED`/`LOADED_NOT_INSTALLED` → `DEGRADED` | MET |
| C.2 | appended after `_alignment_check`, `NO_SESSION` short-circuit preserved, `render_digest` untouched | `:897` (`*_launchagent_state(root, as_of)`), short-circuit at `:884-889` returns before it | MET |
| D.1 | 16 tests incl. all-16-tuple `classify()`, real-tree 12-label test, `.bak` exclusion, print-beats-list, absent binary | `tests/test_launchagent_state.py:69-357` (16 methods) | MET |
| D.2 | 8 digest fixtures + 4 tests | `tests/fixtures/job_health/launchagent_*.json` (8 files), tests at `tests/test_job_health_digest.py` (+97) | MET |
| D.3 | `DATA_TIER_MODULES` entry; **recomputed** line registries; zsh region test | `tests/test_daily_ritual_provenance.py:61-63`; `406→417`, `449→460`, and all 7 `MUTATION_VERB_SITES` values `+11`; `LaunchagentAdvisoryTests:219-271` | MET |
| D.4 | `test_launchagent_state` added to macOS CI list | `.github/workflows/ci.yml:107` | MET |
| E.1/E.2 | README paragraph + dated classifier correction | `tools/launchagents/README.md:53-60` and `:97-103` | MET |
| OUT | no `config.py`, no `options_researcher/__init__.py`, no `ledger/`, no `data/`, no plist install | `git diff --name-only` (Task 4) confirms all absent | MET |

**Nothing is PARTIAL or NOT MET.**

## Task 2 — Verification I ran myself (no stated count trusted)

All in `/Users/carsynstephenson/options-validator/.tmp/worktrees/brief41` at `21d016f`. `.venv` was already present; no `uv sync` needed.

| Command | Result | Label |
|---|---|---|
| `PYTHONPATH=tests uv run python -m unittest test_launchagent_state test_job_health_digest test_daily_ritual_provenance` | **Ran 117 tests · OK · exit 0** (81.2 s) | Run-verified |
| `uv run python -m unittest discover -s tests` | **Ran 3925 tests · OK (skipped=5) · exit 0** (359.1 s) | Run-verified |
| `uv run ruff check .` | `All checks passed!` · **exit 0** | Run-verified |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations` · **exit 0** | Run-verified |
| Acceptance 3a (`tracked_labels`) | prints `12`, assert passes · exit 0 | Run-verified |
| Acceptance 5 (closure proof) | closure = 50 paths; **`closure∩diff = []`** | Run-verified |
| Acceptance 6 (live, `--no-receipt`) | prints `INSTALLED_NOT_LOADED com.carsyn.options-validator.research-refresh`, summary `12 tracked, 9 loaded, 1 installed-not-loaded, 0 disabled, 2 not-installed`, **exit 0**, **no receipt written** | Run-verified |
| Cross-check `launchctl print gui/501/…research-refresh` | **exit 113** — independently confirms unloaded | Run-verified |

21 new test methods (16 + 4 + 1). The brief's "3,905" baseline was measured on `645365b`, a different SHA, so the delta is not directly comparable; the 3925 figure above is mine. Worktree left clean: `git status --porcelain` shows **no tracked-file modifications** after my runs.

## Task 3 — Adversarial pass

| # | Attack | Finding | Label |
|---|---|---|---|
| a | Does observation mutate launchd? | **No.** The only argv vectors are `list`, `print`, `print-disabled` (`launchagent_state.py:157,169,179`). `bootstrap`/`enable` appear *only* inside printed advice f-strings (`:292,297-298`), README prose, and test assertions — never in a list passed to `run`. No `bootout`/`kickstart`/`disable`/`unload` anywhere in the diff | Run-verified |
| b | Network / provider / ledger writes? | **None.** No `requests`/`urllib`/`httpx`/`socket`/`schwab`/`thetadata` import; grep of added lines in `options_researcher/` + `tools/` finds no `ledger`, `facts.log`, `paper_trades`, or order path. The single write site is `atomic_text_write` → `reports/ritual/` (`:281`) | Run-verified |
| c | Does the ritual hunk move a gate? | **No.** Exactly **one** hunk, `@@ -384,6 +384,17 @@`. Gate lines are byte-identical in position on both refs: `ritual_authority status` **:46**, `require-data` **:60**, `CRIT_COUNT=0` **:82**, `crit()` **:85**, branch guard **:95-101**, origin/main alignment gate **:102-107**, `require-full` **:151**, token advisory **:385**. Only lines *below* 386 shift (+11). Inserted lines verbatim: `# ---- launchagent state ----` / `echo ">>> launchagents:"` / `"$UV" run python -m options_researcher.launchagent_state \` / `  --root "$REPO" --as-of "$AS_OF" --run-date "$RUN_DATE" || true` / `# ---- end launchagent state ----`, preceded by a 5-line comment block, sitting after `:385` and before the Schwab preclose lane at `:398` — so it is not the lane's first executable statement (R1-13) | Run-verified |
| d | Fail-soft, and is it pinned? | **Yes, and yes.** The block touches no `CRITICAL`/`CRIT_COUNT`/`DATA_STARVED`/`RITUAL_TERMINAL_STATUS`; `|| true` plus a CLI that returns 0 on every path. Pinned by `tests/test_daily_ritual_provenance.py:219-271`: it slices the region, runs it under real `zsh` with a `$UV` stub that **exits 3**, and asserts the subprocess exits 0, argv carries `--root/--as-of/--run-date`, and the log contains **no `CRITICAL:`** — for both `AS_OF=2026-09-08` and `AS_OF=""` | Run-verified |
| e | Digest row semantics changed? | **No.** Two hunks only: a new `_launchagent_state` function and one splice line in `collect_health`. No existing row builder, `HealthStatus`, `HealthRow`, or `render_digest` touched; `NO_SESSION` short-circuit intact. It reuses the existing `_contained_path` / `_read_object` helpers | Run-verified |
| f | *Unanticipated input:* is the `print-disabled` parser real-world correct? | **Yes.** I ran the real `/bin/launchctl print-disabled gui/501` (25 lines) and replayed the module's `re.fullmatch` against it: **4 matches**, all `com.apple.*`, zero `=> true/false`-style lines. Had macOS used the boolean form, the module would silently report 0 disabled — a false negative. It does not | Run-verified |
| g | **Risk — no `subprocess` timeout** | `run(...)` is called with `capture_output/text/check` only (`:157,168-173,178-183`); **no `timeout=`**. The 09:09 unattended ritual makes 14 launchctl spawns; a wedged `launchctl print` hangs the ritual, and `|| true` cannot rescue a hang. This is *brief-conformant* (rev 8 A.3 specifies exactly those kwargs), so it is not an executor defect — but it is a real unattended-job exposure | Run-verified / Inference |
| h | Daily-committed artifact | `reports/ritual` is first on `DATA_TIER_PATHS` (`tools/daily_ritual.sh:573-574`), so the receipt is auto-staged and committed every session. No allow-list change needed — intended by A.4, but it is a new daily commit artifact | Run-verified |
| i | Provenance oddity | Of the 2 commits on the branch, `faf5d27 "wip(auto): daily rescue 2026-09-10"` — a `repo-reconcile` auto-rescue authored as **Carsyn**, not Codex — carries 6 of the 17 files (ritual, digest, CI, README, 2 test files). The message describes nothing. Code is fine; the history is misleading | Run-verified |
| j | Test hermeticity | CLI tests `patch.object(self.m, "observe", …)` (`:271,293,325,355`) and adapter tests inject `run`; the real-tree test reads files only. **No test spawns real launchctl** | Run-verified |

## Task 4 — Merge readiness

- `git merge-base --is-ancestor main codex/…` → **exit 1: `main` is NOT an ancestor.** Merge-base `3537ca7`; `main` is **2 ahead**, branch **2 ahead**. (Run-verified)
- `main`'s 2 commits (`5ff7001`, `6873263`) are pure data: `reports/**` and `ledger/facts.log`. The branch touches **none** of them → **a rebase onto `main` is needed but will not conflict.** (Run-verified)
- `git diff --name-only main...codex/…` → the 17 files listed in Task 1. Contains **no** `config.py`, `ledger/`, `options_researcher/__init__.py`; the only `data/`-adjacent paths are `tests/fixtures/job_health/*.json`. **Acceptance 4 satisfied.** (Run-verified)
- Branch **is pushed** (`origin/codex/brief-41-launchagent-loaded-check` = `21d016f` locally). (Run-verified)

**Concurrent-session overlap (`claude/audit-2026-09-15`) — this is the real hazard.** That branch has *no committed diff*; its work is uncommitted in `.tmp/worktrees/audit-0915`. Its `tools/daily_ritual.sh` hunks are `@@ -99,12 +99,79 @@` and `@@ -571,7 +638,8 @@`, net **+68 lines** (73/−5). (Run-verified)

- **`tools/daily_ritual.sh`: no textual overlap.** Brief 41's only hunk is at 384–396; the alignment-gate rewrite is at 99–110. ~275 lines apart — git merges both cleanly. (Run-verified)
- **`tests/test_daily_ritual_provenance.py`: direct conflict.** Both branches rewrite the *same* registry entries. Brief 41: `406→417`, `592→603`, `615→626`, `632→643`. Concurrent: `406→473`, `592→660`, `615→(164, 683)`, `632→700`. Whichever lands second will conflict, and even a clean auto-merge would be **semantically wrong** — the correct post-both value is baseline **+11+68** (e.g. `git add` → 671, not 603 or 660). `test_every_script_surface_is_classified` will fail closed, which is the design working. (Run-verified)
- Brief 41 touches **none** of `tools/ops_alignment_check.sh`, `tools/schwab_chain_capture.sh`, `tools/schwab_chain_intraday_capture.sh`, `tools/h7_activation_day.sh`. No allow-list overlap. (Run-verified)

## Task 5 — Verdict

### PASS WITH FIXES

The implementation is faithful to rev 8, observation-only, fail-soft, and independently green on my own runs. Nothing is PARTIAL or NOT MET, and no scope-OUT boundary is crossed. The fixes are procedural, not code defects:

1. **Rebase onto current `main` before opening/refreshing the PR** — `main` is not an ancestor. Conflict-free (main's 2 commits are data-only).
2. **Sequence against `claude/audit-2026-09-15`.** Whichever lands second must recompute `PYTHON_DASH_C_CLASSIFICATION` and `MUTATION_VERB_SITES` in `tests/test_daily_ritual_provenance.py` against the *merged* script (combined shift +79 above line 386) and re-run `test_every_script_surface_is_classified`. Do not hand-resolve that conflict by picking one side.
3. **Squash `faf5d27` into `21d016f`** at merge so the history is one authored commit, not an auto-rescue with an empty message.
4. **CI at `21d016f` is unverified here** (no network). The owner must run `gh pr checks` and record the run ID before landing.
5. **Recommended, owner's call:** add `timeout=` to the three `run(...)` calls. This needs a brief amendment (rev 8 pins the kwargs), so it is a follow-up, not a merge blocker.
6. Record in the merge notes: `diagnostic_source_hash()` rotates to `f66c4364…`; every pre-landing H7 source-health / data-gate receipt goes stale and those gates will refuse loudly until regenerated.

Out of scope for me and unchanged: merge timing, `crit` promotion (D-1), reloading `research-refresh` (D-2), installing the digest agent (D-3). Green checks are review evidence, not landing authority.

### Draft-PR commands (for the owner — NOT run by me)

```bash
cd /Users/carsynstephenson/options-validator
git fetch origin
git worktree add .tmp/worktrees/brief41-rebase codex/brief-41-launchagent-loaded-check
git -C .tmp/worktrees/brief41-rebase rebase origin/main
git -C .tmp/worktrees/brief41-rebase push --force-with-lease origin codex/brief-41-launchagent-loaded-check

gh pr create --draft \
  --base main \
  --head codex/brief-41-launchagent-loaded-check \
  --title "feat(ops): installed-vs-loaded LaunchAgent advisory in the daily ritual (brief 41)" \
  --body-file .tmp/audit-2026-09-15/brief41-pr-body.md

gh pr checks codex/brief-41-launchagent-loaded-check
gh pr view codex/brief-41-launchagent-loaded-check --json headRefOid,isDraft
```

The PR body must carry the acceptance output above — `exit 0` for steps 1/2/3, the `12` from 3a, `closure∩diff = []` from step 5, the step-6 live line — plus the brief SHA implemented (`3537ca7`) and the post-landing `diagnostic_source_hash()`.
