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

The note is the MAIN checkout root's `YYYY-MM-DD.md` (`~/options-validator/`),
gitignored. The Stop hook (`.claude/hooks/session_note_guard.py`, local-only)
anchors there even from a worktree session (fixed 2026-08-14) — never leave
the note only inside a worktree: a gitignored note there is destroyed with the
worktree. If today's note already exists (another session wrote it), append
under a `---` divider instead of overwriting.

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
