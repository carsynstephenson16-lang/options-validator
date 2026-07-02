# `git checkout <commit> -- <paths>` pre-stages; inspect the index before every commit

**Lesson:** Restoring files from another commit stages them immediately. Any
later `git commit` sweeps them in even if your `git add` named fewer files.
Always run `git diff --cached --name-only` (or `--stat`) and read the list
before committing — counting is not reading.

**What happened (2026-07-01):** While untangling the Codex hardening patch out
of `data-layer`'s `3fa4cb6`, 16 files were brought over via
`git checkout 3fa4cb6 -- <paths>` (silently staged), then 14 code/test paths
were `git add`ed and committed. The intended code-only commit (`f6186e3`)
therefore also carried the 4 spec/plan/audit/handoff doc updates. Harmless
here — all 18 files were part of the same hardening consolidation — but the
commit message under-describes the docs, and the planned code/docs split
didn't happen.

**Why it mattered:** The execution handoff's implementer rules exist because a
staged-sweep already corrupted a commit on this project once (`0ef6a85`), and
rule (c) is literally "re-check staged set before commit." A `wc -l` of the
staged list was run and showed 18 vs 14, but the commit was issued in the same
compound command, so the discrepancy was seen only after the fact. Check
BEFORE, in a separate step, and never chain "inspect" and "commit" in one
command line.
