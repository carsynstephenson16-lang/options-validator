# repo-reconcile: stale deploy + digest publish denied — Codex brief

- **Date:** 2026-08-24
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** rev 4 — WP-A LANDED on main (PR #75, merge `336ebb6`,
  automerged 2026-08-26 08:54). WP-B (owner-run redeploy + verification) has
  NOT run and remains the single most urgent owner action in this arc — made
  MORE urgent by the rev-4 correction of record below (the deployed
  automerge loop lacks four further guards and auto-merged a `.github/`
  workflow change on 2026-08-26). Rev 4 adds WP-C (SEC-02 strict
  remote-owner verification, owner-routed 2026-08-26) and WP-D (reconciler
  default-draft compliance per `AGENTS.md:98-104`); **WP-C/WP-D: round-2
  (final) independent correction review PASS, 2026-08-26 evening — READY
  FOR HAND-OFF as a prepared DRAFT PR; landing/deploy stay gated on the
  owner's WP-B redeploy. Residuals R3-1/R3-2 applied. Receipt:
  `reports/2026-08-26-briefs-24-29-31-adversarial-review-receipts.md`.**
  Lineage: rev 1
  FAILED round-1 Opus review 2026-08-24 (root cause "the run hangs"
  falsified by the LaunchAgent's own stderr log; rewritten per F1–F13); rev
  2 was the lean landed scope; the rev-3 additions FAILED round-1
  independent review 2026-08-26 evening (findings R24-F1…R24-F18); rev 4
  answers all of them. Rev 2's "no further review round" ruling covered rev
  2's lean scope only.
- **Provenance:** rev 1–2 Repo-verified against origin/main @0ca2601 and the
  live machine on 2026-08-24; rev-4 additions Repo-verified against
  origin/main @4ab1a385c3ee6a5c97285f9bf0a341f5a69feac5 and the live machine
  on 2026-08-26, unless labeled otherwise.

## Why this exists (plain language)

Two independent defects in the daily 08:15 LaunchAgent
`com.carsyn.repo-reconcile`:

**Defect 1 — stale, unreviewed deploy (Repo-verified).** The job executes
`~/bin/repo-reconcile`, whose blob (`git hash-object` = `39af93a5`) matches
NONE of the 11 tracked revisions of `tools/anti-stranding/repo-reconcile` —
it is a hand-modified local variant, 43 added / 135 removed lines vs main
(`git diff --numstat`). It predates two safety features main already has:
the ownership gate (anchor: `# Ownership gate for every side-effect loop`,
~:121-130 — deployed copy acts on ANY discovered repo, including
third-party clones like `~/codex-plugin-cc`) and the pre-push gitleaks gate
(`scan_ok()` defined ~:36-39, called at `if ! scan_ok "$repo" "$range"`,
~:144 — deployed copy re-pushes commits the `~/.githooks/post-commit`
gitleaks hook blocked: a live secret-exposure path on public repos).

**Defect 2 — digest publish is DENIED, silently (Repo-verified).** The run
COMPLETES every morning (no hang: `ps` shows nothing running hours later).
Its final step, `mv "$DIGEST.tmp" "$DIGEST"` onto `~/Desktop`, fails under
launchd with `Operation not permitted` — recorded once per day, 11 times,
in `/tmp/repo-reconcile.err.log` (the plist's `StandardErrorPath`). Cause:
macOS Desktop privacy protection (TCC) — `~/Desktop` is `drwx------@` with
per-file `com.apple.macl` grants and iCloud Desktop sync is on. The
2026-08-15 digest published only because that run was manual from Terminal
(its body is `[dry-run]` lines). With `set +e` and an unconditional
`exit 0`, eight days of failures produced zero operator-visible signal —
the acting-but-not-reporting failure this brief closes.

**Folded-in finding (Repo-verified; was rev-1's WP-B, already answered):**
the four `~/Claude.prod` branches the log claims to push daily have NEVER
been pushed — no `origin/<branch>` exists for any of them, and Claude.prod's
`origin` is a LOCAL PATH (`/Users/carsynstephenson/Claude`), not GitHub.
The deployed copy logs `PUSH` even on failure (`;` where `&&` belongs,
deployed ~:107-108); main already fixes the logging (`PUSH-FAIL` branch).
After redeploy, main's ownership gate makes Claude.prod inventory-only
(local-path origin matches no `$GH_LOGIN` pattern) — that consequence is an
OWNER decision (give it a GitHub origin, or accept report-only), not a
Codex action.

## Scope

IN — the lines below are rev 2's WP-A scope, now LANDED; the base @0ca2601
and "only code change" wording apply to WP-A only. *Amended for WP-C/WP-D —
see the Rev 4 section, which touches `tools/anti-stranding/repo-reconcile` itself
(WP-C item 5, WP-D), the three sibling hooks, a new shared library,
`install.sh` (edit-only, one cp line), and `tests/`, on a branch off
@4ab1a38:*
- Edit `tools/anti-stranding/repo-reconcile` on a branch off origin/main
  @0ca2601: publish the digest to a writable canonical path, make publish
  failure loud, add `export GIT_TERMINAL_PROMPT=0`. Open a PR. Stop.

OUT (do not touch or run) — *amended for WP-C/WP-D; see the Rev 4 section
(install.sh becomes edit-only, never run):*
- `install.sh`, `launchctl`, `brew`, `git config --global` — install and
  verification are OWNER-RUN (see WP-B). Codex must not run any of them.
- The auto-merge policy, flag file, or blackout window (owner directive
  2026-08-15). Note: `install.sh` only writes the automerge flag when the
  file is absent (main install.sh ~:57-58); it never reverses an existing
  value — no contradiction with owner-run install.
- No ledger writes, registrations, authority flips, frozen values,
  live-order paths; ops/research checkouts stay report-only (they are
  usually skipped even earlier by the shared-git-dir dedupe,
  `SEEN_GITDIR`, ~:56-57 — Repo-verified).
- Known bug NOTED, not fixed (record in PR description): `new_prs` is
  incremented inside `| while read` pipeline subshells, so the
  `MAX_NEW_PRS` throttle never accumulates across repos. Separate change.
- No per-repo digest flushing, no gh call wrappers, no SSH/askpass/
  low-speed option bundles, no restructuring. One defect, one fix.

## Work packages

### WP-A — the script change (Codex)

Edit `tools/anti-stranding/repo-reconcile` only:

1. **Writable canonical digest.** Change the publish target to
   `$HOME/.local/state/repo-reconcile/digest.md` (mkdir -p its parent near
   the existing `mkdir -p` for the log). Write the temp file as a sibling
   in the SAME directory and keep the atomic `mv`. Keep the existing
   title-rewrite `sed` before the `mv`.
2. **Best-effort Desktop copy, loud on failure.** After the canonical `mv`
   succeeds, `cp` the digest to `~/Desktop/repo-digest.md`. Check BOTH the
   `mv` and the `cp`: on failure, `logl "PUBLISH-FAIL <path>: <reason>"`
   and make the final `osascript` notification say the digest could not be
   delivered (canonical vs Desktop, whichever failed). A run that cannot
   publish must never exit 0 silently. To make this testable, read the two
   destinations from env vars with the current values as defaults
   (`DIGEST_CANON`, `DIGEST_DESKTOP` or similar) — nothing else becomes
   configurable.
3. **One hang guard.** `export GIT_TERMINAL_PROMPT=0` near the top (after
   the PATH export). Label: Inference — no hang was observed; this closes
   the one cheap git-prompt class. A stall inside the
   `gh auth git-credential` helper is not covered by any git-side guard;
   the loud publish in step 2 is what makes any such failure visible.
4. **PR description must include:** (a) `zsh -n tools/anti-stranding/repo-reconcile`
   output (syntax check — no execution); (b) the red-green proof from the
   Acceptance section; (c) the deployed orphan blob captured verbatim
   (attach current `~/bin/repo-reconcile` contents — reinstalling discards
   an unreviewed local edit and this preserves it for the record); (d) the
   `new_prs` noted-not-fixed bug; (e) the Claude.prod never-pushed finding.

### WP-B — owner-run install + real verification (Codex prints, never runs)

Codex ends its work at the PR and prints this block for the owner:

```bash
cd ~/options-validator && git pull && zsh tools/anti-stranding/install.sh
launchctl kickstart -k gui/$(id -u)/com.carsyn.repo-reconcile
tail -2 /tmp/repo-reconcile.err.log   # must gain NO new "Operation not permitted" line
head -1 ~/.local/state/repo-reconcile/digest.md   # must carry today's date
```

What the installer actually changes (so the owner knows the blast radius —
Repo-verified against main's install.sh): overwrites `~/.githooks/post-commit`
and sets GLOBAL `core.hooksPath`; `brew install gitleaks` if missing; writes
`~/.config/repo-reconcile/gh-login` (currently MISSING — main's post-commit
and claude-session-rescue.sh fail closed without it, so today's deployed
auto-push may be partly disabled anyway); overwrites
`~/bin/claude-session-rescue.sh` and `~/bin/worktree-remove-guard.sh` (both
currently stale vs main); rewrites the plist and re-bootstraps the
LaunchAgent; writes the automerge flag only if absent.

Owner decisions surfaced, not made, by this brief: (1) if Desktop delivery
of the digest matters, grant the job Full Disk Access in System Settings →
Privacy & Security (no script change can bypass TCC); (2) Claude.prod's
local-path origin — add a GitHub remote or accept inventory-only.

A terminal `DRY_RUN=1` run is NOT valid verification — terminal TCC grants
differ from launchd's, which is exactly how this bug hid (Repo-verified:
the 08-15 "success" was a manual run). Only the `launchctl kickstart` proof
counts.

## Acceptance / verification

- `zsh -n tools/anti-stranding/repo-reconcile` exit 0. NOTE (Repo-verified):
  no existing test covers this file — `tests/test_shell_banner_guard.py`
  enumerates `git ls-files '*.sh'` and this file has no extension, so a
  green suite proves nothing about the change.
- `uv run python -m unittest discover -s tests`, `uv run ruff check .`,
  `uv run pyright` all exit 0 (regression gate on the unchanged Python).
- Red-green publish proof (no TCC involvement): run the edited script with
  the Desktop-copy destination overridden to a path inside a read-only
  temp directory → the run must emit `PUBLISH-FAIL` in the log and a
  could-not-deliver notification, and still write the canonical digest;
  then with a writable override → no failure line, both files written.
  Show both outputs in the PR description.
- Owner's WP-B block, after install: no new `Operation not permitted` line
  in `/tmp/repo-reconcile.err.log`, canonical digest dated today, and
  `git show origin/main:tools/anti-stranding/repo-reconcile | diff - ~/bin/repo-reconcile`
  empty.

## Owner ruling appended 2026-08-26 (in-session): SEC-02 folds into this arc

The 2026-08-25 repository audit's SEC-02 finding (the anti-stranding hooks'
remote-ownership check is a raw URL-substring match — spoofable; and the
DEPLOYED copies in `~/.githooks` / `~/bin` currently have NO ownership gate
and NO gitleaks scan at all, worse than the repo copies) is routed INTO this
brief's arc by owner ruling 2026-08-26 ("do not open new workstreams",
"confirm fold into brief 24 sequencing"). Binding sequencing:

1. FIRST land and deploy this brief (redeploying the repo copies is a strict
   improvement — it restores the ownership gate and the gitleaks gate).
2. THEN a small follow-on work package inside this arc replaces the
   substring match with one strict canonical GitHub remote parser/owner
   verifier shared by all hooks (including effective `pushurl`), with fake
   remotes covering HTTPS/SSH/pushurl/spoofed-host forms asserting no push.
   Evidence: audit finding SEC-02,
   `reports/repository-audits/2026-08-25-options-validator/04-candidate-registry.csv`
   (lands with PR #82).

No standalone SEC-02 brief exists or should be created.

## Rev 4 (2026-08-26 evening) — execution state, correction of record, WP-C/WP-D

The rev-3 draft of this section FAILED independent adversarial review with
findings R24-F1…R24-F18; this rev-4 section answers every one. The review
itself independently re-verified every execution-state fact below.

### Execution state (Repo-verified @4ab1a38 + live machine 2026-08-26)

- **WP-A: DONE.** `336ebb6 fix: publish repo reconcile digest safely (#75)`
  is an ancestor of origin/main; the repo copy
  `tools/anti-stranding/repo-reconcile` (blob `40a13c8`) carries
  `DIGEST_CANON`/`DIGEST_DESKTOP` (:15-16), `PUBLISH-FAIL` logging
  (:287,290,293), and `GIT_TERMINAL_PROMPT=0` (:14).
- **WP-B: NOT RUN.** `/Users/carsynstephenson/bin/repo-reconcile` is still
  the orphan blob `39af93a5` (mtime Aug 15);
  `~/.local/state/repo-reconcile/` does not exist; `~/Desktop/repo-digest.md`
  is dated Aug 15. `/tmp/repo-reconcile.err.log` holds 11
  `Operation not permitted` lines; the file was created 2026-08-16 08:15:01
  and its mtime is 2026-08-26 08:54:22 — one failure per daily run,
  2026-08-16 through 2026-08-26 inclusive (R24-F12: this supersedes rev 2's
  "eight days" count, which was stale when restated; R24-F16: the log lines
  carry no timestamps, so the 08-26 attribution is an Inference from file
  mtime + the LaunchAgent schedule, not a direct observation). The
  2026-08-26 daily run used the OLD deployed script. WP-B's owner block is
  unchanged and is the gate for everything below.
- **Unexplained residual (R24-F15):** the same err log also holds four
  `fatal: not a git repository (or any of the parent directories): .git`
  lines interleaved with the Desktop failures. Undiagnosed; recorded here so
  the post-WP-B verification ("no new Operation-not-permitted line") is not
  misread as "log fully clean". Diagnosing them is in scope for the WP-B
  verification session, not for Codex.

### Correction of record (append-only; does not alter the routing)

The 2026-08-26 fold-in ruling above states the deployed copies have "NO
ownership gate and NO gitleaks scan at all." Verified 2026-08-26: that is
true of `~/bin/repo-reconcile` (no `scan_ok`, no `GH_LOGIN`; only a stale
comment mentioning gitleaks at deployed :134), but `~/.githooks/post-commit`
DOES run gitleaks (deployed :28-34) while lacking the ownership gate. The
blanket wording was too strong; the severity ordering is unaffected — and
per R24-F4/R24-F13 the deployed set is in fact WORSE than the ruling knew,
in three further ways:

1. **The deployed automerge loop is missing four guards the repo copy has**
   (Repo-verified, deployed vs `tools/anti-stranding/repo-reconcile`):
   `--author "@me"` (repo :205; deployed :146 has none), `--base main`
   (repo :205; deployed none), the owner-governed-path refusal covering
   `ledger/`, `config.py`, `docs/superpowers/`, `AGENTS.md`, `CLAUDE.md`,
   `.cursorrules`, `.github/` (repo :216-220; deployed none), and
   `--match-head-commit "$sha"` (repo :234; deployed :150 is a bare
   `gh pr merge --squash`). Live consequence: on 2026-08-26 08:54:03 the
   deployed copy auto-merged PR #82, whose diff includes
   `.github/workflows/claude-review.yml` — a path the repo copy's governed
   list would have refused and escalated to the digest. (PR #82 itself was
   owner-un-drafted, so the LANDING was owner-sanctioned; the point is the
   deployed merge path would have applied zero of the repo copy's guards
   either way.)
2. **The deployed post-commit hook's auto-push has never worked** (R24-F13):
   deployed `~/.githooks/post-commit:37` launches the push via `setsid`,
   and `command -v setsid` finds nothing on this machine — macOS ships no
   setsid. The repo copy replaced it for exactly this reason
   (`tools/anti-stranding/post-commit:49`: "nohup, not setsid: setsid is
   not a standard macOS executable"). So the deployed global auto-push is a
   silent no-op; the reconciler remains the only live unscanned-push path.
3. The cached-login file `~/.config/repo-reconcile/gh-login` is MISSING
   (only `automerge` exists there), so the repo copies of the three
   file-reading hooks would currently fail closed if deployed as-is;
   `install.sh:23-25` is the sole writer of that file (R24-F6 context).

All of this strengthens WP-B's urgency: redeploying current main is a strict
improvement on every axis measured.

### WP-C — SEC-02: one strict remote-owner verifier for all hooks (Codex)

Closes audit finding **SEC-02**
(`reports/repository-audits/2026-08-25-options-validator/04-candidate-registry.csv`,
row SEC-02, VERIFIED, score 86): the ownership check in the anti-stranding
scripts is a raw URL-substring `case` match — Repo-verified consumers, and
the complete set (repo-wide grep finds no fifth):
`tools/anti-stranding/repo-reconcile:123-132` (case at :127),
`tools/anti-stranding/post-commit:28-38` (case at :36),
`tools/anti-stranding/claude-session-rescue.sh:29-45` (case at :36),
`tools/anti-stranding/worktree-remove-guard.sh:30-48` (case at :38). A
non-GitHub URL containing `/<login>/` anywhere passes and reaches
`git push`.

Contract:

1. **All push destinations, not one (R24-F1 — review-measured bypass;
   mechanism corrected per correction-round R2-N4):** bare
   `git remote get-url --push origin` returns only the FIRST pushurl, while
   `git push` pushes to EVERY configured pushurl (`set-url --push --add`
   creates seconds). The PRIMARY mechanism is
   `git remote get-url --push --all origin` — correction-round-measured to
   return exactly the true target set in all three attack configurations
   (two pushurls; `pushInsteadOf` rewrite with no pushurl; both combined).
   Require EVERY returned URL to parse to the same accepted owner; any
   non-matching URL, any unparseable URL, or an empty result = fail closed.
   As a cross-check only, also read
   `git config --get-all remote.origin.pushurl` and require consistency
   (Inference, not measured: the raw-config view may differ from the
   rewritten view under `url.*` rewrites; none exist on this machine today —
   verified via `git config --global --get-regexp` on `url.*`, empty). A
   cross-check DISAGREEMENT is a refusal, never an acceptance — and an
   EMPTY pushurl config is the normal no-pushurl case (every GitHub repo on
   this machine today): nothing to cross-check, NOT a disagreement
   (round-2 residual R3-1).
2. **Structural host rule (R24-F7):** parse each URL structurally; the HOST
   (the component after any `userinfo@`, before any `:port` or `/`) must
   equal `github.com` exactly, case-insensitively. Accept optional userinfo
   (`https://OWNER@github.com/OWNER/REPO.git` is a legitimate working form
   and an ACCEPT case); reject any explicit port; the path must be exactly
   `OWNER/REPO[.git]` — no extra segments. Accepted schemes:
   `https://github.com/OWNER/REPO[.git]`,
   `ssh://git@github.com/OWNER/REPO[.git]`,
   `git@github.com:OWNER/REPO[.git]`. NOTE (correction-round R2-N5): in the
   scp-like form the colon is the PATH separator, not a port — the
   reject-any-port rule applies only to URL forms carrying an explicit
   numeric `:port` after the host; applying it to the scp-like colon would
   reject every legitimate scp-like remote. Refusal matrix must include
   `github.com.evil.com`, `https://github.com@evil.com/o/r` (userinfo
   spoof — host is evil.com), local paths, ports, and extra path segments.
3. **One canonical implementation** as a sourced shell library under
   `tools/anti-stranding/`, deployed to an ABSOLUTE `$HOME`-anchored path
   (e.g. `$HOME/bin/anti-stranding-lib.sh`) and sourced by absolute path —
   `~/.githooks/post-commit` executes with cwd inside arbitrary repos, so a
   relative source is wrong by construction (R24-F2).
4. **Login source, stated explicitly (R24-F6; split per correction-round
   R2-N1):** `repo-reconcile` — a once-daily batch job that already calls
   `gh api user` live (:26) — resolves the login as cached file
   `$HOME/.config/repo-reconcile/gh-login` first, else live
   `gh api user -q .login`, else fail closed. The THREE HOOKS
   (`post-commit`, `claude-session-rescue.sh`, `worktree-remove-guard.sh`)
   stay **cached-file-only, fail closed, no network** — `post-commit` runs
   synchronously on EVERY commit in every repo via global `core.hooksPath`,
   and a foreground network call there would stall every commit
   machine-wide whenever the `gh` token is expired (a live recurring
   condition in this project). This preserves `post-commit:32-33`'s
   existing posture exactly. The cached file is currently missing;
   `install.sh:23-25` is its sole writer and WP-B's install run creates it.
   Comparison is case-insensitive — a deliberate WIDENING vs today's
   exact-match `case` patterns (R24-F18; Inference: GitHub logins are
   case-insensitive for routing; recorded as a one-time manual check in the
   PR body, NOT an in-test network call — R24-F8).
5. **Consumers to change:** every one of the four replaces its substring
   `case` with: owners := parse of ALL destination URLs per items 1–2;
   side effects (push, PR create, merge, auto-rescue push) allowed only
   when every owner equals the resolved login. Missing library, missing
   login, or any parse failure = fail CLOSED (inventory/report only),
   matching `tools/anti-stranding/post-commit:32-33`'s existing posture.
6. **install.sh:** add the `cp` line deploying the library (install.sh
   deploys by named `cp` only — :11,:34,:38,:40 — so a new file is
   invisible until added). **Scope OUT amendment (R24-F2):** rev 2's OUT
   line "install.sh … do not touch or run" is amended for this WP to
   "Codex may EDIT `tools/anti-stranding/install.sh` — the ONE new cp line
   deploying the library, nothing else (`install.sh:23-25` already writes
   gh-login correctly; correction-round R2-N6 closed the 'if needed' open
   door); Codex must NOT RUN it — install remains owner-run per WP-B."
7. **Tests (R24-F8, R24-F11, R24-F14):** offline `tests/` unittest style;
   no network, no real `gh` calls, and NO test may execute a real push,
   PR-create, or merge path. Drive the parser against the full accept/refuse
   matrix (including the `--push --add` second-pushurl case asserting
   refusal). Drive `post-commit` and `worktree-remove-guard.sh` end-to-end
   against throwaway repos with crafted remotes — NOT `repo-reconcile`
   (no file extension, guard-gated at :68-69, and its gate falls straight
   into push/PR/merge loops). Non-invocation is asserted via stub `git`/`gh`
   executables earlier on `PATH` that record argv and fail the test if a
   push/create/merge subcommand is ever invoked.

**Sequencing (corrected per R24-F5):** the owner ruling above says "FIRST
land and deploy this brief … THEN a small follow-on work package". That
ordinal is binding on LANDING and DEPLOY unconditionally.
**Agent-proposed (Inference, owner may veto):** Codex may PREPARE the
WP-C/WP-D implementation PR as a GitHub draft before the WP-B redeploy runs,
because a draft PR delays nothing and touches no live path; the PR must not
be made ready or land until the owner confirms WP-B ran. If the owner
prefers the strict reading (no WP-C/WP-D work at all until after redeploy),
that veto stands and Codex waits.

### WP-D — reconciler default-draft compliance (Codex, same PR as WP-C)

`AGENTS.md:98-104` (owner-directed 2026-08-25) requires every worker-created
PR to start as a GitHub draft, and requires automated reconciliation to keep
excluding drafts from merge eligibility. The defect exists in BOTH copies
(R24-F10): repo `tools/anti-stranding/repo-reconcile:178` and deployed
`~/bin/repo-reconcile:121` each read
`draft=""; [[ "$br" == wip/* ]] && draft="--draft"`; the 2026-08-26 log
evidence below was produced by the DEPLOYED copy.

Live proof (corrected per R24-F9): **PR #70** (`codex/attractive-exp-wiring`)
was created BY the reconciler itself (`~/.local/log/repo-reconcile.log`
2026-08-24T08:19:17 PR line, matching the PR's createdAt), non-draft, and
was auto-merged 2026-08-26T12:54:17Z with no human in the loop — a
reconciler-created PR landing on main in direct violation of the draft rule.
(PR #89, created non-draft the same morning, remains OPEN and unmerged — it
is evidence of non-draft creation only, not of an automerge.) The gap was
first recorded in `reports/2026-08-26-brief-29-independent-review-receipt.md`
("Separate open gap — not fixed here"); it is closed HERE, in the
reconciler's own arc.

Changes:

1. `tools/anti-stranding/repo-reconcile`: every `gh pr create` the script
   performs passes `--draft` unconditionally (today the sole creation site
   is :180, reached via the `$draft` variable from :178; the exact code
   shape is Codex's choice).
2. Same edit updates the digest wording at :181 ("opened a PR so you can
   review/merge from anywhere") to say the PR is a DRAFT awaiting the
   owner's make-ready (R24-F17).
3. State the consequence plainly in the PR description: reconciler-created
   PRs stop automerging (drafts are merge-ineligible — Repo-verified:
   deployed automerge filters `select(.isDraft|not)`), so landing them now
   requires the owner to make each one ready. That is the owner's declared
   2026-08-25 policy, stated here so the trade is conscious: a path in
   daily use (PR #70 above) goes away. The automerge loop itself is NOT
   modified (owner directive 2026-08-15 stands for green non-draft PRs the
   owner made ready).
4. **Acceptance is semantic, not textual (R24-F11):** a test runs the
   script under `DRY_RUN=1` with stub `gh`/`git` executables earlier on
   `PATH` that record argv; it asserts every recorded `pr create` argv
   contains `--draft` (and that no merge/push argv occurs in the test at
   all). No grep-on-source acceptance — a correct `$draft`-variable
   implementation must pass.

### Rev-4 acceptance (in addition to rev 2's)

- `zsh -n` on every touched script exits 0.
- New WP-C/WP-D tests RED against unmodified code (recorded in the PR
  body), then GREEN; full offline suite, `uv run ruff check .`,
  `uv run pyright` exit 0.
- The implementation PR is created with `gh pr create --draft`, proven
  `isDraft=true` via `gh pr view --json isDraft`, and stops there (no
  make-ready, no merge, no deploy, no ops sync) pending the WP-B
  confirmation gate.
- **Make-ready preconditions (owner checks, Codex prints them):**
  (a) WP-B has run — `git show origin/main:tools/anti-stranding/repo-reconcile
  | diff - ~/bin/repo-reconcile` is empty; (b)
  `~/.config/repo-reconcile/gh-login` exists and is non-empty (the three
  hooks are cached-file-only and fail closed without it — WP-C item 4,
  consistent per correction-round R2-N2).
- **Second redeploy required (R24-F3):** WP-C/WP-D landing on main changes
  NOTHING live until the owner re-runs the WP-B install block once more
  (`git pull && zsh tools/anti-stranding/install.sh` +
  `launchctl kickstart -k gui/$(id -u)/com.carsyn.repo-reconcile`) and
  re-verifies the diff-empty equality proof. Until that second redeploy, the
  daily 08:15 job keeps running the old logic — say so in the PR body in
  exactly these terms.
