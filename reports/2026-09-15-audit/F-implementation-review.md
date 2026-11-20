# F — Adversarial implementation review, `claude/audit-2026-09-15`

Worktree `/Users/carsynstephenson/options-validator/.tmp/worktrees/audit-0915`.
**Run** = I executed it; **Repo** = read in-tree; **Inf** = inference.

## VERDICT: PASS WITH FIXES

The gate is sound. I could not construct any case where it pushes unreviewed
**executable** code to `origin/main`; every serious attack fails closed. The
fixes are documentation/contract defects and cheap hardening. One (G1) is a
FAIL-class finding under the strict rule I was given, with a one-sentence fix.

**Two framing facts (Run):**

1. **The branch has ZERO commits.** `HEAD == main == origin/main == 6873263`.
   The entire change is uncommitted working-tree state in one removable
   worktree. If it is removed, the work is gone. Highest-priority item here.
2. **The tree changed during the review** — 14 files at start, 17 now
   (`+391/−4926`): `PROJECT_STATE.md` plus deletion of `crawler.js`,
   `package.json`, `package-lock.json` appeared mid-audit. Another writer is
   active. All findings re-verified against the current state.

---

## A. Tests and lint (Run) — re-run against the current tree

| Command | Result | Exit |
|---|---|---|
| `PYTHONPATH=tests uv run python -m unittest <7 modules>` | **Ran 163 tests, OK** | **0** |
| `uv run ruff check .` | **All checks passed!** | **0** |

Identical counts on the earlier 14-file state. No failures, no skips reported.

---

## B. Can the gate push unreviewed CODE? — 22-case attack matrix (Run)

Gate region (`tools/daily_ritual.sh:124-158`) cut out and sourced under zsh
against real scratch repos with bare origins in `/tmp`.

| Attack | Result |
|---|---|
| Plain code commit ahead | REFUSE |
| `git mv` code **into** `reports/pick_tracker/` | REFUSE — `--no-renames` reports both sides |
| Evil merge (resolution edits code) | REFUSE — tree diff catches it; `log --name-only` showed only evidence |
| `reports/ritualX/x.py`; `reports/h5../x.py`; case variants | REFUSE |
| Ahead commit **deletes** code | REFUSE |
| Newline in filename under an allowed prefix | REFUSE — git C-quotes it **under `core.quotePath` default, false, and true**; the leading `"` defeats the match |
| Non-ASCII filename in evidence dir | REFUSE (quoted) |
| Evidence + one code file | REFUSE |
| Origin moves between fetch and push (non-ff) | Predicate passes, **push FAILS**, `&&` chain breaks → REFUSE |
| Stale ref (fetch failed) + real origin ahead with code | Predicate passes, **push FAILS** → REFUSE |
| `return 1` inside `while … done <<< …` | rc=1 — `return` **does** escape the loop in zsh |

**Four cases PASS the predicate. None lets unreviewed code execute:**

| Case | Assessment |
|---|---|
| **Symlink** `reports/pick_tracker/link.sh → ../../tools/code.sh` | **Strongest finding.** `git diff --raw` reports mode **120000**; the predicate matches **path text only, never mode**. The target's content is unchanged and nothing executes the link — but an attacker-chosen symlink lands on `origin/main`, and any later writer to that evidence path gets write-through to a code file. |
| Gitlink (mode 160000) at an evidence path, no `.gitmodules` | PASS. Git will not init or run it. Theoretical. |
| Commit whose **tree is identical** to `origin/main` (empty commit; code commit + clean revert → 2 commits ahead, empty tree diff) | PASS, pushes. Tip tree == reviewed tree, so nothing unreviewed *runs*; unreviewed **history** reaches `origin/main`. Provenance, not execution. |
| A **file** literally named `reports/ritual` (the exact-match arm) | PASS. Requires deleting the directory; nothing executes it. |

`EVIDENCE_ALLOW` and the predicate are **byte-identical** across all four
scripts — the comment's claim holds (Run, string compare).

---

## C. Does the fetch-failure fallback weaken safety? — **No**

The old gate **never fetched**, so "stale ref" was its permanent condition.

| Shape | OLD | NEW | Change |
|---|---|---|---|
| fetch ok, aligned | proceed (possibly stale) | proceed (fresh) | **stronger** |
| fetch ok, behind | often missed | refuse | **stronger** |
| fetch ok, ahead-evidence | refuse | push + proceed | **intended loosening** |
| fetch ok, ahead-code | refuse | refuse | same |
| fetch fail, aligned vs stale ref | proceed | proceed + note | same + diagnostic |
| fetch fail, real origin ahead (stale ref matches HEAD) | proceed, undetected | proceed, undetected | same |
| fetch fail, ahead-evidence | refuse | push fails → refuse (Run) | same |
| fetch fail, ahead-code | refuse | refuse | same |

In **every** fetch-fail shape the new gate equals the old one. A stale ref is an
*older* base → *larger* diff → only extra refusals; the push is the real
serializer. The fallback is strictly a diagnostic improvement.

Caveat: `http.lowSpeed*` bounds the fetch **only because origin is HTTPS**
(confirmed in `~/options-validator-ops`, the checkout the 07:10 LaunchAgent
runs). Switch origin to SSH and the "bounded" claim silently evaporates.

---

## D. Can `pick_tracker` / `closes_receipts` contain code? — true today, unenforced

Producers write **only** hardcoded literal filenames:
`options_researcher/pick_tracker.py:1643-1646`, `:1709`, `:1775`;
`data/recent_topup.py:186` (`f"{payload['scope']}.json"`, `scope` is
argparse-`choices`-restricted). No ticker, API field, or CLI arg ever supplies
an **extension**. On disk: 42/52 files, `json|md|jsonl|gitkeep` only, **zero**
`.py`/`.sh`. No consumer executes — repo-wide zero hits for `pickle`, `joblib`,
`dill`, `marshal`, `yaml.load`, `runpy`. (Repo)

**But the invariant is conventional, not enforced.** `daily_ritual.sh:652` runs
`git add -- reports/pick_tracker` **recursively and extension-blind**, under a
message asserting `"this commit never contains code."` (`:637`, `:650`), and the
widened gate now auto-pushes it. A `.py` arriving by any other route (human,
agent, `git mv`) is auto-committed and auto-pushed with a message denying it is
code. Secondary: `data/recent_topup.py:186` has no `_is_below` containment on
`run_date`, unlike `pick_tracker.py:270-291`.

---

## E. Line registries and the P1 fence — hold (Run)

**All 19 registered line numbers compared old-vs-new individually: 19/19 point
at byte-identical line text, zero drift.** Shift boundaries are exactly as
described — gate grew 6 → 73 lines (**+67**), `FULL_TIER_PATHS` split one array
line (**+68** thereafter); sites ≤101 unshifted. Gate `fetch` **159** / `push`
**164** are new sites, correctly registered (`:150`, `:152`).

**P1 fence holds.** `test_require_data_precedes_every_mutation_surface`
(`:410-423`) compares **byte offsets** and takes the *first* regex match, so the
gate's fetch/push are now first — and still pass:

```
line  60  … "$PYTHON" -m data.ritual_authority require-data
line  71  exec > "$LOG" 2>&1
line 159  … git … fetch -q origin main   (gate)
line 164  … git … push  -q origin main   (gate)
```

`require-data` (60) precedes the push (164) by 104 lines. The widened `git
fetch` matcher is not command-anchored, but comments are excluded and an
unregistered match fails the test — fail-closed. The `git push` matcher stays
anchored so it does not match the realign prose at `:690`.

**Stale artifact:** `tests/test_daily_ritual_provenance.py:94` says "Line 115" —
the site is now **187** (was 120 on main, so already wrong; +67 widened it).
Prose only. Also pre-existing: `:1096` opens the script via relative
`Path("tools/daily_ritual.sh")`, making that test cwd-dependent.

---

## F. Activation-day change — no owner decision contradicted, but the remedy is now vacuous

The old `test_routine_refuses_closes_receipts_and_staged_code` was **not**
pinning an owner ruling. Brief-40 round-2 finding 3
(`reports/2026-09-08-brief-40-adversarial-review-round2.md:17`) frames the
omission as a mechanical hazard, and its remedy is a **derived set** — "the
intersection of `DATA_TIER_PATHS` and `EVIDENCE_ALLOW`".
`tests/test_h7_activation_day.py:299-311` pins `ROUTINE_ALLOW == DATA_TIER_PATHS
∩ EVIDENCE_ALLOW` by equality, so the `ROUTINE_ALLOW` edit is **mechanically
compelled** by the `EVIDENCE_ALLOW` edit, not a second decision. Prior approved
briefs call these paths "evidence" explicitly.

**However**, `ROUTINE_ALLOW` (`h7_activation_day.sh:65-66`) is now
**byte-for-byte `DATA_TIER_PATHS`** (`daily_ritual.sh:629-630`) — same 11
entries. The R2-3 intersection subtracts **nothing**; the new test's example
`reports/not_evidence/` is a path the pipeline cannot generate. Two artifacts
now disagree with the code and were **not** updated:

- **`docs/h7-forward-operations.md:189-190` is now FALSE**: "`reports/pick_tracker`, `reports/closes_receipts`, code, and any other dirty path outside that intersection still refuse." They no longer refuse. File unmodified.
- Brief-40 acceptance criterion `…2026-09-08-40-…:295` ("refuses a dirty `reports/closes_receipts` path (R2-3)") is **violated**; rationale at `:204-211` is stale.

`ROUTINE_ALLOW` is the script's only *automatic mutation* authority (`:87`,
`:188-190` — sweeps dirty **and untracked** matching paths into a commit on one
CLI flag), so it warrants the amendment even though the edit is forced.

---

## G. Docs loss audit

**G1 — one binding sentence LOST (FAIL-class).** On `main`, three files carried
a **conflict-precedence tie-break**: `CLAUDE.md@main:25-26` ("PROJECT_STATE.md
governs sequencing, **and its P0 gate wins over any doc that implies building
now**") and `.cursorrules@main:80-81` / `AGENTS.md@main:185-186` ("**its P0 gate
binds**"). All three now stop at "governs sequencing." / "(the canonical
roadmap)". Regex `P0` → **zero hits** in all three branch files *and* in branch
`PROJECT_STATE.md`. Retiring the stale **"P0" label** is correct; the deletion
took the non-stale **precedence obligation** with it. Mitigation exists only
inside the pointed-to file (`PROJECT_STATE.md:6-7`), not in the instruction layer.

**G2** — `AGENTS.md:185` collapses three headings under one saying "keep
identical" but drops **"(non-negotiable)"** (present at `.cursorrules:15`).
Codex reads AGENTS.md standalone.

**G3** — `README.md:54` enumerates five CSVs but omits
`data/positions/h7_positions.csv`, which exists (header-only today).

Everything else checks out. All three claimed verbatim ports (Draft-PR authority
hold, Catalyst-calendar rule, Hard-guardrails/Engineering/Verdict bullets) are
**character-identical** — no MUST→should, no dropped exception. All 15 skill
directories the old CLAUDE.md enumerated exist. The four README holdings facts
resolve in `data/positions/*.csv`. Both removed restatements (hypothesis list,
holdings) were **stale on main** — net accuracy gain.

---

## H. Hooks

**Byte-identity confirmed** (`shasum -a 256` + `cmp`, Run), matching the
prefixes `.agents/hooks/README.md:22` claims: `f52c6f32…` (block_live_trading),
`075088a5…` (session_note_guard).

**H1 (material) — the tracked bodies are NOT the code being executed.**
`.claude/settings.local.json` still registers the **untracked laptop-only**
copies: `:23` `.claude/hooks/block_live_trading.py`, `:46`
`.claude/hooks/session_note_guard.py`; only `:34` (block_ledger_edits) uses
`.agents/hooks/`. CLAUDE.md's "hard enforcement" still depends on untracked
files on one machine. Disclosed deferral
(`reports/2026-09-15-audit-edge-verdict-and-loose-ends.md:67`), but "now
tracked" overstates the effect.

**H2 — zero test coverage for both new hooks.** Two approved plans specified
them: `…2026-07-23-integrity-hardening-batch-v1-codex-brief.md:65-66` and
`…2026-08-11-options-validator-core-plugin-design.md:43,122` ("with tests"). The
move landed; the tests did not.

**H3** — `block_ledger_edits.py` is currently unmodified vs main (its earlier
` M`-with-empty-diff was a transient mode flip by the concurrent writer). It is
`644` while the new two are `755`; irrelevant, all are run as `python3 "<path>"`.
The README honestly **drops** main's "tested"/"covered by `tests/`" wording.

---

## I. Other

**I1 — a refusing gate sends NO desktop notification.** The branch guard at
`:99` fires `osascript`; the gate's refusal (`:168-171`) exits **before** the
notification at `:723`. `printf "%b" "$SUMMARY"` **does** print the CRITICAL
line, but only into the log (`exec > "$LOG"` at `:71` precedes the gate).
Pre-existing — and exactly why 09-14 was invisible. The change does not fix it
and *widens* the paths that reach this silent exit.

**I2 — `note` cannot corrupt the STARVED/BROKEN title.** Title (`:715-722`) and
exit (`:734-741`) logic are **pure counter comparisons**; `note` touches neither
`CRITICAL` nor `CRIT_COUNT`. No text matching on `$SUMMARY`. Safe.

**I3 — missing `-C "$REPO"`** on lines 159 and 164; every other gate call has
it. Correct today only via `cd "$REPO" || exit 2` at line 37. Latent.

**I4 — zsh semantics verified** (Run): `<<<`, `[ ]`, `&&` continuations, and
`return` from inside `while … done <<<` all behave. No `set -e`, so
`[ "$BEHIND_COUNT" -ne 0 ] && return 1` falling through is safe.

**I5 — `FULL_TIER_PATHS`** gained two Schwab namespaces (`:642`), already in
`EVIDENCE_ALLOW` on main — low risk, but un-briefed scope with no finding behind it.

**I6 — commit `6873263` is clean**: 19 files, **all** under `reports/`/`ledger/`.
The incident narrative holds.

**I7 — environment defect (not this branch).** Mid-session every Bash/Write call
was refused because `$CLAUDE_PROJECT_DIR` resolved to a Claude scratch
workspace, so all three hooks fail-closed on a missing file — exactly the
lockout documented at `.agents/hooks/README.md:65-71`. Make hook command paths
absolute.

---

## Exact minimal fixes

1. **(Process, first)** **Commit and push.** Zero commits exist; the work lives in one removable worktree.
2. **(G1, required)** Restore the precedence clause in `.cursorrules` Scope guard, mirrored to `AGENTS.md`/`CLAUDE.md`, without the stale label: *"PROJECT_STATE.md §2 Live blockers and §4 Standing gates bind and outrank any doc that implies building now."*
3. **(F, required)** Rewrite `docs/h7-forward-operations.md:189-190` (now false); amend brief-40 acceptance criterion `:295`; record that the R2-3 intersection is a no-op for data-tier paths.
4. **(H1, required)** Switch `.claude/settings.local.json:23,46` to `.agents/hooks/`, or stop calling the hooks "tracked enforcement".
5. **(B/symlink, recommended)** Reject non-regular modes: after the path loop, refuse if `git diff --raw --no-renames origin/main HEAD` reports a destination mode other than `100644`/`100755`/`000000`. Closes symlink **and** gitlink in one line.
6. **(D, recommended)** Add a suffix reject (`*.py|*.sh|*.bash|*.zsh|*.pl|*.rb`) to the predicate and `path_allowed`, plus a test asserting the two dirs hold only `{json,jsonl,md,gitkeep}`.
7. **(I1, recommended)** Add the `osascript` notification to the gate's refusal branch, matching line 99.
8. **(H2, recommended)** Add `tests/test_block_live_trading.py` and `tests/test_session_note_guard.py`.
9. **(Trivial)** `-C "$REPO"` on lines 159/164; `(non-negotiable)` back into `AGENTS.md:185`; `h7_positions.csv` into `README.md:54`; fix the "Line 115" comment at `test_daily_ritual_provenance.py:94` → 187.

Not required: the empty-tree/revert push is provenance-only, and fixing it
(rejecting ahead-count > 0 with an empty tree diff) would break the legitimate
self-heal path. Document it instead.

**Method note.** My harness initially produced two false PASSes — a malformed
newline filename whose setup silently failed, leaving an empty diff, and **an
empty diff always passes this predicate**. Both were re-run corrected and both
REFUSE. Every PASS above was confirmed to have a non-empty tree diff, except the
identical-tree cases where the empty diff *is* the finding. Anyone reusing this
technique should assert the attack actually committed before trusting a PASS.
