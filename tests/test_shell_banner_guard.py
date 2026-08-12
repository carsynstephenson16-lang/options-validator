"""tests/test_shell_banner_guard.py

Static contract test for the "banner-pollution" bug class that has bitten
this repo twice in two days:

  1. H8's ritual artifact (fixed 2026-07-23, ef4b3f5) -- fixed by making the
     program write its own JSON artifact via `--out` instead of a shell
     capturing its stdout.
  2. tools/intraday_capture.sh's session-tag derivation (fixed 2026-07-24,
     42ae8c8) -- fixed with a strict `grep -Eo '^...$' | tail -1` filter plus
     an explicit "NONE" sentinel for the legitimate-empty case.

Root cause (repo-verified 2026-07-24: `uv run python -c "import lumibot"`
alone prints `... | INFO | LumiBot v4.5.63 starting` to STDOUT with exit 0,
confirmed via separate stdout/stderr redirection): LumiBot v4.5.63 and
python-dotenv print import-time INFO banner lines to stdout. Any shell code
that captures `uv run python`/`python` stdout into a variable or file and
then parses a specific value out of it risks silently reading a banner line
instead of (or mixed in with) the real answer.

PATTERN RULES enforced by this test
------------------------------------
1. Enumerate every git-tracked `*.sh` file (`git ls-files '*.sh'`) -- these
   are the only shell scripts that ship with the repo (vendored `.venv`
   scripts are out of scope).
2. Find every command substitution -- POSIX `$(...)` or legacy backtick
   `` `...` `` -- whose command text invokes a python process (`uv run
   python`, bare `python`, or `python3`). Nesting and multi-line `-c '...'`
   blocks are handled by a small paren-depth scanner that treats `'...'`/
   `"..."` spans as opaque (their parens don't count toward shell-level
   depth, matching real shell quoting semantics for THIS purpose).
3. Also find every `| tee <path>` pipeline stage that follows a python
   invocation earlier in the same logical line (backslash-continued
   physical lines are joined first) -- `tee` writes the raw stream to a
   FILE, which is the same capture-into-an-artifact risk as a variable
   capture, and in zsh (no `setopt PIPE_FAIL` anywhere in this repo,
   verified below) `if cmd | tee file; then` even checks tee's exit status,
   not cmd's.
4. A capture is INLINE-PROTECTED if the same substitution/pipeline text
   contains a strict anchored filter -- `grep -Eo '^...'`/`grep -E
   '^...'` (single- or double-quoted) or `sed -n 's/^...` -- BEFORE the
   value is used further. This matches the repo's established defenses
   (daily_ritual.sh AS_OF/SCOPE_ID, tools/intraday_capture.sh TAG).
5. A capture that is NOT inline-protected must appear in the ALLOWLIST
   below with a non-empty one-line justification, matched by a distinctive
   substring that must appear inside the offending span's own text. Two
   legitimate reasons show up in this repo, and ONLY these two:
     a. The raw capture exists purely so `$?` can reflect the python
        process's own exit code (zsh has no pipefail, so exit-code capture
        must happen on an un-piped substitution, separate from any
        filtering pipe) -- and the real VALUE is extracted from the same
        variable a few lines later via its own anchored `grep -Eo`/`sed -n
        's/^.../.../ p'` filter (visible near the allowlisted line).
     b. The raw capture is echoed to a human-facing log ONLY -- no value is
        ever parsed out of it.
   A capture allowlisted for reason (a) is verified by this test to
   actually have a nearby anchored-filter derivation of the SAME variable
   in the same file, so a justification can't be used as an escape hatch on
   its own -- see `_assert_reason_a_has_a_downstream_filter`.
6. Anything neither inline-protected nor allowlisted is a NEW unfiltered
   capture -- the test fails loudly, by design, so the class cannot return
   silently. Prefer fixing it (strict filter, sentinel, or --out
   program-written-file) over adding an allowlist entry; the allowlist is
   for the two narrow, already-audited exceptions above, not a general
   escape hatch.

This scanner is deliberately biased toward false positives (forced into the
allowlist / requiring a fix) over false negatives (a new unfiltered capture
slipping through unnoticed).
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PYTHON_INVOCATION_RE = re.compile(r"\buv\s+run\s+python\b|\bpython3?\b")

# A strict anchored filter: `grep` (any flag combination -- -Eo, -E, -m1,
# -q, ... -- the flags don't matter, the anchor does) with a quoted pattern
# containing '^', or a `sed -n 's/^...` substitution. This is the
# established "survives banner pollution" shape used throughout the repo
# (a banner line cannot match a pattern anchored to the start of a line
# unless it happens to collide with the exact expected shape).
ANCHORED_FILTER_RE = re.compile(
    r"grep\s+(?:-[A-Za-z0-9]+\s+)*'[^']*\^[^']*'"
    r"|grep\s+(?:-[A-Za-z0-9]+\s+)*\"[^\"]*\^[^\"]*\""
    r"|sed\s+-n\s+'s/\^"
)

# Matches a variable-assignment prefix ("VAR=" or 'VAR="') immediately
# preceding a capture, so failure messages and allowlist matching see the
# assigned-to variable name, not just the bare "$(...)"/"`...`" text.
_ASSIGN_PREFIX_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\")?\Z")

# (relative file path, distinctive substring that must appear inside the
#  offending span's own text, one-line justification). Every entry must be
#  reason (a) or (b) from the module docstring; reason (a) entries are
#  cross-checked below to have a real downstream anchored-filter derivation
#  of the same variable in the same file.
ALLOWLIST: list[tuple[str, str, str]] = [
    (
        "tools/daily_ritual.sh",
        'SH_OUT="$("$UV" run python -m options_researcher.h7_source_health',
        "reason (a): raw combined stdout+stderr capture exists only so "
        "SH_RC=$? can reflect the python process's own exit code (zsh has "
        "no pipefail here); the real VALUE (SH_RECEIPT) is extracted two "
        "lines later via an anchored `grep -Eo 'receipt=[^ ;]+' | tail -1`, "
        "and SH_OUT itself is otherwise only echoed to the log for human "
        "context.",
    ),
    (
        "tools/daily_ritual.sh",
        'DG_OUT="$("$UV" run python -m options_researcher.h7_data_gate',
        "reason (a): raw combined stdout+stderr capture exists only so "
        "DG_RC=$? can reflect the python process's own exit code; the real "
        "VALUE (DG_RECEIPT) is extracted two lines later via an anchored "
        "`sed -n 's/^immutable receipt //p' | tail -1`, and DG_OUT itself "
        "is otherwise only echoed to the log for human context.",
    ),
    (
        "tools/daily_ritual.sh",
        "DG_VERDICT_OUT=",
        "reason (a): raw capture exists only so DG_VERDICT_RC=$? can "
        "reflect the python process's own exit code (distinguishing 'the "
        "receipt could not be read' from a parsed verdict); the real VALUE "
        "(DG_VERDICT) is extracted on the next line via an anchored "
        "`grep -E '^(GO|NO_GO)$' | tail -1`. DG_VERDICT_OUT is never "
        "echoed anywhere.",
    ),
    (
        "tools/intraday_capture.sh",
        "TAG_RAW=",
        "reason (a)+(b): raw capture exists so TAG_RC=$? can reflect the "
        "python process's own exit code; the real VALUE (TAG) is derived "
        "on the next line via an anchored `grep -Eo "
        "'^(open_auction|open|midmorning|midday|preclose|NONE)$' | tail "
        "-1`. TAG_RAW is also dumped verbatim on a refusal (`echo "
        '"$TAG_RAW"` under the unparseable-output branch) so the operator '
        "can see exactly what banner/output confused the parse -- that's "
        "diagnostic display, not a second parse path.",
    ),
    (
        "tools/intraday_capture.sh",
        "CAP_OUT=",
        "reason (a): raw combined stdout+stderr capture exists only so "
        "CAP_RC=$? can reflect the python process's own exit code; every "
        "downstream read of CAP_OUT (the coverage line, the 'refused'/"
        "'CONFLICT' branches) goes through its own anchored `grep "
        "'^...'`/`grep -m1 '^...'` pattern, and the raw var is otherwise "
        "only echoed to the log for human context.",
    ),
    (
        "tools/schwab_chain_capture.sh",
        "CAP_OUT=",
        "reason (a): raw combined stdout+stderr capture exists only so "
        "CAP_RC=$? can preserve the capture CLI's exit code; every "
        "downstream classification reads CAP_OUT through an anchored "
        "`grep '^schwab_chain_capture ...'` filter, and the raw value is "
        "also echoed to the human-facing log.",
    ),
]


def _tracked_shell_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "*.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]


def _mask_comments(text: str) -> str:
    """Replace shell comment text (an unquoted '#' through end of line) with
    spaces, preserving every character offset so line numbers and downstream
    span-finding stay correct. Quote state (single/double) is tracked across
    the whole file, so a literal '#' inside a quoted string (e.g. inside a
    `python -c '...'` source blob) is correctly NOT treated as a comment
    starter, and -- the actual motivation for this function -- backticks
    used as markdown-style code-span notation inside a `#` comment (this
    module's own docstring does that; tools/intraday_capture.sh's comments
    do too) are never mistaken for a real backtick command substitution."""
    out = list(text)
    quote: str | None = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#":
            end = text.find("\n", i)
            if end == -1:
                end = n
            for k in range(i, end):
                out[k] = " "
            i = end
            continue
        i += 1
    return "".join(out)


def _matching_paren(text: str, open_idx: int) -> int:
    """Index of the ')' matching the '(' at text[open_idx]. Content inside
    '...'/"..." spans is treated as opaque (its parens don't count), which
    matches real shell quoting semantics for this purpose."""
    assert text[open_idx] == "("
    depth = 0
    i = open_idx
    n = len(text)
    quote: str | None = None
    while i < n:
        ch = text[i]
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"unbalanced '(' at index {open_idx}")


def _find_dollar_paren_and_backtick_spans(masked_text: str) -> list[tuple[int, int, str]]:
    """Find `$(...)`/`` `...` `` spans in COMMENT-MASKED text (see
    `_mask_comments`), extending each span's start leftward over a directly
    adjacent `VAR="` / `VAR=` assignment prefix so callers/allowlist entries
    can identify captures by the variable they're assigned to."""
    spans: list[tuple[int, int, str]] = []
    n = len(masked_text)
    i = 0
    while i < n:
        if masked_text[i] == "$" and i + 1 < n and masked_text[i + 1] == "(":
            end = _matching_paren(masked_text, i + 1) + 1
            start = i
            m = _ASSIGN_PREFIX_RE.search(masked_text[:start])
            if m:
                start = m.start()
            spans.append((start, end, "$(...)"))
            i = end
        elif masked_text[i] == "`":
            j = masked_text.find("`", i + 1)
            if j == -1:
                break
            start = i
            m = _ASSIGN_PREFIX_RE.search(masked_text[:start])
            if m:
                start = m.start()
            spans.append((start, j + 1, "`...`"))
            i = j + 1
        else:
            i += 1
    return spans


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Join backslash-line-continued physical lines into logical lines,
    each paired with the character offset where it starts in `text`."""
    out: list[tuple[int, str]] = []
    offset = 0
    buf = ""
    buf_start: int | None = None
    for line in text.split("\n"):
        if buf_start is None:
            buf_start = offset
        if line.endswith("\\"):
            buf += line[:-1] + " "
        else:
            buf += line
            out.append((buf_start, buf))
            buf = ""
            buf_start = None
        offset += len(line) + 1
    if buf:
        assert buf_start is not None
        out.append((buf_start, buf))
    return out


def _find_tee_spans(masked_text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for start, line in _logical_lines(masked_text):
        tee_idx = line.find("| tee")
        if tee_idx == -1:
            tee_idx = line.find("|tee")
        if tee_idx == -1:
            continue
        before = line[:tee_idx]
        if PYTHON_INVOCATION_RE.search(before):
            spans.append((start, start + len(line), "|tee"))
    return spans


def _find_capture_spans(text: str) -> list[tuple[int, int, str]]:
    """Find every python-stdout-capture candidate span in `text`. Detection
    runs on a comment-masked copy (so backticks/`$(` inside `#` comments
    can't be mistaken for real shell syntax); returned (start, end) offsets
    are valid against the ORIGINAL `text` too, since masking preserves
    length and position exactly."""
    masked = _mask_comments(text)
    spans = _find_dollar_paren_and_backtick_spans(masked)
    spans.extend(_find_tee_spans(masked))
    return spans


def _is_allowlisted(rel_path: str, span_text: str) -> bool:
    for file_path, substring, reason in ALLOWLIST:
        if file_path == rel_path and substring in span_text and reason.strip():
            return True
    return False


class ShellBannerGuardTests(unittest.TestCase):
    def test_no_pipe_fail_relied_on_anywhere(self) -> None:
        """Sanity-check a load-bearing assumption of this test's reason-(a)
        allowlist entries and of the fixes in tools/daily_ritual.sh /
        tools/intraday_capture.sh: these are zsh scripts and none of them
        opt into `setopt PIPE_FAIL`, so `$?` after a piped command always
        reflects the LAST stage of the pipe, never an earlier stage. If this
        ever flips, several "capture raw so $? is honest" allowlist
        justifications above stop being true and need re-auditing."""
        pipefail_re = re.compile(r"setopt\s+[A-Za-z_]*pipe_?fail|set\s+-o\s+pipefail", re.I)
        for path in _tracked_shell_files():
            if path.suffix != ".sh":
                continue
            text = _mask_comments(path.read_text(encoding="utf-8"))
            self.assertIsNone(
                pipefail_re.search(text),
                f"{path.relative_to(REPO_ROOT)} sets PIPE_FAIL/pipefail -- "
                "re-audit the reason-(a) allowlist entries in "
                "tests/test_shell_banner_guard.py, they assume it is unset "
                "(without it, $? after `cmd | othercmd` reflects othercmd, "
                "not cmd, which is exactly why several captures here split "
                "'capture raw for $?' from 'filter for the value' into two "
                "separate statements).",
            )

    def test_every_python_capture_is_filtered_or_allowlisted(self) -> None:
        failures: list[str] = []
        for path in _tracked_shell_files():
            if path.suffix != ".sh":
                continue
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(REPO_ROOT).as_posix()
            for start, end, kind in _find_capture_spans(text):
                span_text = text[start:end]
                if not PYTHON_INVOCATION_RE.search(span_text):
                    continue
                if ANCHORED_FILTER_RE.search(span_text):
                    continue  # inline-protected
                if _is_allowlisted(rel, span_text):
                    continue
                line_no = text.count("\n", 0, start) + 1
                snippet = span_text.strip().replace("\n", "\\n")[:300]
                failures.append(f"{rel}:{line_no} ({kind}) {snippet}")
        self.assertEqual(
            [],
            failures,
            "Unfiltered python-stdout capture(s) found -- this is exactly "
            "the banner-pollution bug class (LumiBot v4.5.63 / python-dotenv "
            "print import-time INFO lines to stdout; see tools/"
            "daily_ritual.sh's 2026-07-23 ef4b3f5 and 2026-07-24 42ae8c8 "
            "fixes). Fix it with a strict anchored `grep -Eo '^...$' | "
            "tail -1` filter (with an explicit sentinel if empty is a "
            "legitimate outcome), or better, a program-written --out file "
            "(see options_researcher.h8_watch / entry_watch / "
            "h7_entry_preflight). Only add a justified ALLOWLIST entry in "
            "this test file if the capture is provably safe per the "
            "module docstring's reason (a)/(b).\n\n" + "\n".join(failures),
        )

    def test_allowlist_reason_a_entries_have_a_downstream_anchored_filter(
        self,
    ) -> None:
        """An allowlist justification claiming 'the real value is filtered
        two lines later' has to be true, not just asserted -- otherwise the
        allowlist is a silent escape hatch for exactly the bug this test
        exists to prevent. For each allowlisted raw-capture variable, assert
        the file contains at least one anchored-filter line that reads that
        SAME variable name."""
        var_name_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
        for file_path, substring, reason in ALLOWLIST:
            if "reason (a)" not in reason:
                continue
            match = var_name_re.match(substring)
            self.assertIsNotNone(
                match,
                f"allowlist entry {substring!r} claims reason (a) but its "
                "substring doesn't start with a recognizable VAR= prefix -- "
                "can't verify a downstream filter reads it.",
            )
            assert match is not None
            var_name = match.group(1)
            text = (REPO_ROOT / file_path).read_text(encoding="utf-8")
            downstream_filter_re = re.compile(
                rf'\$\{{?{re.escape(var_name)}\}}?["\']?\s*\|\s*'
                r"(grep|sed|printf).*"
            )
            self.assertTrue(
                any(
                    downstream_filter_re.search(line) and ANCHORED_FILTER_RE.search(line)
                    for line in text.split("\n")
                ),
                f"{file_path}: allowlisted {var_name} claims a downstream "
                "anchored filter derives the real value from it, but no "
                f"line in the file pipes ${var_name} through an anchored "
                "grep -Eo/-E or sed -n 's/^... filter.",
            )


if __name__ == "__main__":
    unittest.main()
