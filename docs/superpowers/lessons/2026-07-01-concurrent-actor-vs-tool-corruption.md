# When observations contradict, suspect a concurrent actor before suspecting tools

**Lesson:** If two reads of the same repo disagree mid-session, check whether
another agent or the owner moved the tree (reflog + content hashes) before
blaming output filtering, caching, or the harness.

**What happened (2026-07-01):** This session's first read of the implementation
audit returned 462 lines including a "Final Branch Review Pass"; a `git status`
moments later showed a clean tree whose audit was 233 lines without it. It
looked like the rtk output-filter hook was corrupting piped git output. Blob
hashes (`git hash-object <disk file>` vs `git rev-parse HEAD:<path>`) plus the
reflog proved the real cause: at 23:41 the working tree — Codex's post-review
hardening patch plus a new DoltHub/AlphaVantage data layer — was committed to a
new `data-layer` branch (`3fa4cb6`) and the checkout switched back to
`phase-1a-research-integrity`, racing this session's first tool calls. Every
"contradiction" was two honest snapshots of two different states; rtk was
innocent throughout.

**Why it mattered:** The wrong diagnosis (broken tooling) would have meant
distrusting all shell output for the rest of the session. The right one exposed
a real coordination breach: the single-writer rule from
`handoff-2026-07-01-phase1a-execution.md` §2 was violated again, and `3fa4cb6`'s
message ("Add offline-testable data layer...") hides ~20 integrity fixes it
also contains. Standing rules reaffirmed: before editing, confirm no other
agent is mid-flight; settle "which bytes are real" questions with content
hashes, which cannot be filtered or stale.
