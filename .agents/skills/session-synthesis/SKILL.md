---
name: session-synthesis
description: Turn a work session into a short, human Obsidian note that captures decisions and reasoning, not output. Use at the end of a meaningful session, when Carsyn says "wrap up," "make the note," "obsidian," or before context is about to be lost. 
---

# Session Synthesis

The vault is for Future Carsyn, six weeks from now, who remembers nothing. She doesn't need what the code prints — the repo has that. She needs why things are the way they are, what was rejected, and what she was worried about. Write like a person leaving a note for a friend, not like a machine dumping a log.

## Rules

- Hard cap: 250 words for the body. If it doesn't fit, it isn't synthesized yet.
- Every decision gets its REASON, in one sentence, in plain English. "Chose stationary bootstrap because trades overlap in time, so shuffling them independently would fake more certainty than we have" — not "implemented stationary bootstrap."
- Rejected ideas are first-class content. What was considered and why it lost is the most expensive knowledge to regenerate.
- No pasted logs, no pasted code. File paths and commit hashes only.
- Write "Open worries" honestly, including doubts about whether the day's work was the right work.
- Use [[wikilinks]] for tickers, strategies, and concepts so the vault connects (e.g. [[put credit spread]], [[VST]], [[stationary bootstrap]]).

## Where the note goes

The note is `<checkout root>/YYYY-MM-DD.md`, gitignored. The Stop hook
(`.claude/hooks/session_note_guard.py`) checks the CURRENT checkout's root. In
a worktree session that is the WORKTREE root — and a gitignored note there is
silently destroyed when the worktree is removed. So from a worktree: write the
note at the worktree root (satisfies the hook), then immediately copy it to
the main checkout root (`~/options-validator/`). If today's note already
exists there (another session), append under a `---` divider instead of
overwriting.

## Format

# {{YYYY-MM-DD}} — {{one-line what this session was about}}

**In one sentence:** what changed and why it matters.

**Decisions and why:**
- decision → reason (max 4)

**Rejected:**
- idea → why it lost (include "none rejected" if true — that itself is a flag that we may not be considering alternatives)

**Where things stand:** ledger version, phase, verdict status. One or two lines.

**Open worries:** the honest ones.

**Next session, start here:** one concrete action, with file path.

## Anti-patterns (do not do these)

- Bullet-pointing every command that was run
- Recording results without the decision they triggered
- Optimistic tone drift ("great progress!") — the note is a record, not a pep talk
