# repo-reconcile: stale deploy + digest publish denied — Codex brief

- **Date:** 2026-08-24
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** rev 2 — round-1 Opus adversarial review (2026-08-24) FAILED
  rev 1: its root cause ("the run hangs") was falsified by the LaunchAgent's
  own stderr log; rev 2 is rewritten around the measured cause per findings
  F1–F13. Pending no further review round (owner-directed lean scope).
- **Provenance:** Repo-verified against origin/main @0ca2601 and the live
  machine on 2026-08-24 unless labeled otherwise.

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

IN (the only code change):
- Edit `tools/anti-stranding/repo-reconcile` on a branch off origin/main
  @0ca2601: publish the digest to a writable canonical path, make publish
  failure loud, add `export GIT_TERMINAL_PROMPT=0`. Open a PR. Stop.

OUT (do not touch or run):
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
