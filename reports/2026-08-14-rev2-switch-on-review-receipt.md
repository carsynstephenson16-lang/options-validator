# Adversarial review receipt — brief 11 rev-2 (ritual switch-on)

**Date:** 2026-08-14
**Subject:** `docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md`
at rev-2
**Reviewer:** independent adversarial review agent, commissioned by the
orchestrating session under the house rule that no spec is implemented without
one (brief 10 failed exactly here — see
`reports/2026-08-14-brief-10-adversarial-review-receipt.md`).
**Code truth for verification:** `~/options-validator-ops` at
`origin/main` = `c96ed4b` (merge of PR #36, 2026-08-14 10:28 ET). Every line
number in this receipt is a `c96ed4b` line number and was re-verified against
that tree while applying the fixes.

---

## Verdict

**PASS WITH FIXES.**

The spec's core judgment survived review: Option B (re-scope the data phase to
the frozen cache with explicit starvation labeling) is the right call, the
three-flag authority design is sound, and `ritual_data_phase_active` correctly
removes the dishonest source claim that sank brief 10. Nothing in the review
overturns a design decision.

What failed review was **implementability and factual accuracy in the
details**: seven findings would have caused an implementer following the spec
literally to ship something broken, and eleven more were unsafe-but-survivable
gaps. Most consequential: rev-2's §6.2 wrap instruction would have fenced off
the only steps that actually do anything under the data tier, producing a
"switch-on" that switches nothing on.

**Disposition summary: 7 blockers applied, 11 cautions applied, 1 owner-decision
demotion applied. Zero declined.** Every finding was verified true against
`c96ed4b` before being applied. Result is rev-2.1 of the same document.

---

## Blockers B-1 … B-7

| ID | Finding (condensed) | Disposition |
| --- | --- | --- |
| **B-1** | The H7 fence matcher (P2) was never specified. A substring matcher would see `options_researcher.h7_watch` at `daily_ritual.sh:98` — the `python -c` AS_OF resolution — conclude an H7 surface precedes the `require-full` gate, and **fail P2 on a correct script**. | **APPLIED** (§8 P2, §8.1). Rule fixed: provenance tests match **`python -m <module>` invocation sites only**; a `python -c` site is never an H7 surface for P2. `:98` is classified `DATA_TIER_PERMITTED` with its justification recorded — it reads a session calendar and mutates nothing, and `AS_OF` gates the entire data phase, so fencing it would blank the data tier. Mutation test **M9** proves the matcher is specified rather than accidental. |
| **B-2** | The closure invariant (P4) was broken six ways and could not have passed on the unmodified script. (a) P4 said two registries, §8.1 declared three. (b) The seven `python -c` sites were unclassified. (c) `options_researcher.features` was registered as a `python -m` site — it is invoked via `python -c` at `:249`/`:252`. (d) `data.ritual_authority` (`:37`, `:47`) was unclassified. (e) Only one of four `mkdir` sites was listed; `git fetch` (`:402`) and `git merge --no-edit` (`:403`) were omitted from the verb list. (f) The test compared module names and shell-verb strings as one merged set. | **APPLIED** (§8 P4, §8.1). Rewritten as **three registries with three matchers and three separate comparisons**. All seven `python -c` sites enumerated by line number and classified (`98`, `99` DATA_TIER_PERMITTED; `156` FULL_TIER; `249`, `252` DATA_TIER; `323`, `334` FULL_TIER_PROBE). `features` moved to registry 2. `data.ritual_authority` exempted as the gate itself, with a note that it is invoked as `"$PYTHON" -m`, not `"$UV" run python -m`, so the exclusion and the matcher agree. All four `mkdir` sites plus `git fetch`/`git merge` added to the verb registry. Mutation tests **M3**, **M10** added. |
| **B-3** | §3 deliverable 5's rider — research refresh "resumes *automatically*, with no further code change" — is false. | **APPLIED** (§3). Rider deleted, replaced with the honest statement: refresh stays blocked until **both** (i) fresh evidence exists **and** (ii) `require-full` is satisfied. Verified: `attractiveness_research_v2.py:366-367` raises `UpstreamBlocked` unless run status is exactly `"OK"`; (ii) needs `h7_active=True` and `exact_session_source_active=True`, i.e. registration day plus owner flips — **and each flip is itself an edit to `data/ritual_authority.py`, a file inside `diagnostic_source_hash`**. There is no configuration in which refresh resumes without a hashed-file edit. |
| **B-4** | §6.2's instruction to "wrap the entire region from step 3 through the end of the `GATE_GO` block" in `require-full` would fence the **data-tier island** that sits inside that literal range — `qm_dashboard --refresh-ohlcv` (`:235`) and both `features.build_all` calls (`:249`, `:252`). Following the spec produces a switch-on that switches nothing on. | **APPLIED** (§6.2). Replaced with **two explicit full-tier regions**, `:113-:216` (A) and `:260-:340` (B), with the unfenced data-tier island `:218-:258` between them; single gate evaluation, return code reused by both `if` blocks; `GATE_GO=0` / `H7_EXIT_READY=0` set explicitly in region A's `else`. Added the clause that the **frozen operator order** (`daily_ritual.sh:2-10`, H7 amendment v1.4 + the 2026-07-24 `H10_RITUAL_ORDER_FIX`) is preserved byte-for-byte in relative order — the fence adds `if`/`fi` and moves no step. New tests `test_data_tier_island_is_outside_the_full_fence` and `test_frozen_operator_order_is_preserved`; mutation test **M8**; the smoke test now checks the island actually ran. |
| **B-5** | The hash-binding claim was wrong in both directions. rev-2 named `h7_schwab_window_registration`, `intraday_capture` and `intraday_preview` as `diagnostic_source_hash` refusal sites — **all four of those refusals bind `config_hash`**, which this change set does not touch. rev-2's hashed-paths list also omitted six entries. The resulting "must land outside the trading session" rule was an invented constraint. | **APPLIED** (§2, §11). Corrected binding table: `diagnostic_source_hash` binds `h7_exit_session.py:247,267`, `h7_watch.py:197`, `h7_data_gate.py:748`, `h7_activation_guard.py:177`, `tools/h7_data_audit.py:668`; `config_hash` binds `intraday_capture.py:495`, `intraday_preview.py:81`, `h7_schwab_window_registration.py:175,263`. Hashed-paths list completed from `research/hashing.py:17-26` — adds `pyproject.toml`, `uv.lock`, `metrics.py`, `analysis/`, `harness/`, `strategies/`, with the note that the first two are **file** entries, so a dependency bump changes the hash even though no `.py` changed. Landing window restated as two regimes: today, only "not during a 07:10 run"; after `h7_active` flips, the strict out-of-session rule binds. |
| **B-6** | §10.7 said `config.INTRADAY_CAPTURE_TIMES` has four keys. It has **five**. | **APPLIED** (§10.8). Verified at `config.py:755-761`: `open_auction` 09:31, `open` 09:35, `midmorning` 11:00, `midday` 13:00, `preclose` 15:45. Test now asserts the **key set**, not the count, so a rename is caught too. Noted why this mattered: a spec saying `len(...) == 4` ships a test that fails on the unmodified repo, and the likely "fix" is deleting `preclose` — the 15:45 key the entire Schwab capture lane runs on. |
| **B-7** | §8.1 forbade any test from reading `CURRENT_AUTHORITY` and asserting a flip state; §10.5 asserted CLI exit codes "at the pre-flip defaults", which is exactly that. Today's `main()` hardcodes the live object (`ritual_authority.py:48`), so the CLI is untestable without depending on live flags. Separately, the existing `assertEqual(required, status)` (`tests/test_ritual_authority.py:47`) becomes meaningless under three modes and had no specified replacement. | **APPLIED** (§5, §8.1, §10). `main()` gains `*, authority: RitualAuthority = CURRENT_AUTHORITY`; both evaluators run on the injected object; the shell call sites stay byte-identical. Per-mode stdout contract specified in a table. Replacement assertions defined: `require-data` stdout equals `status["data_phase"]`, `require-full` stdout equals `status["full_ritual"]`. §10.5 rewritten to assert three explicit flag combinations rather than "the pre-flip defaults". |

---

## Cautions C-a … C-k

| ID | Finding (condensed) | Disposition |
| --- | --- | --- |
| **C-a** | §8.1's rewrite inventory covered only two test modules; other modules bind `daily_ritual.sh` text and will break on the restructure. | **APPLIED** (§8.1, delta row D4b). Enumerated **four**: `tests/test_h7_daily_exit_order.py` (`:12` reads the script; `:16-24`, `:56-70`, `:98-111`), `tests/test_qm_dashboard.py:451-455`, `tests/test_shell_banner_guard.py:107-127`, and **`tests/test_h8_watch.py:635-636`** — the fourth, which the review named in its count but omitted from its list; found by grepping `tests/` for `daily_ritual` and checking which modules read and assert on the script text. Each row records why the test exists, and the instruction is "correct, never weaken". |
| **C-b** | §11's rollback presented flipping `ritual_data_phase_active=False` as a cheap one-liner without stating what it costs post-registration. | **APPLIED** (§11). Added a warning block: the three-flag design is deliberately **monotone**, so the flag is a **master switch**. Post-registration, flipping it also stops the live H7 window's daily evidence (source-health, data-gate, watcher, exit fill/monitor), and each missed session is an irreplaceable gap in a verdict-bearing record. Post-registration this is incident-response-grade, not a convenience. |
| **C-c** | The PREPARED authority-flip patch is invalidated, and rev-2's "regenerate once in this landing" is insufficient. | **APPLIED** (§5, delta row D4c). Verified the patch has **two hunks and both break**: hunk 1's context is the two-field `CURRENT_AUTHORITY` constructor; hunk 2 rewrites exactly the two tests rev-2.1 replaces, including the `assertEqual(required, status)` line B-7 retires. Because content depends on registration-day tests, the requirement is **regenerate AT registration day** plus a `STALE — DO NOT APPLY; REGENERATE AT REGISTRATION` marker now. Also flagged `reports/h7_forward_schwab/2026-08-09-owner-gate-packet.md:55`, which states the flip is "only `exact_session_source_active=True`, `h7_active=True`, and matching tests" — a two-flag assumption now incomplete. |
| **C-d** | The `[DATA-STARVED]` label had no mechanism. `crit()` (`:63`) only sets a boolean, so "the only CRITICAL is the capture-receipt line" would be implemented by grepping `$SUMMARY` — and any future CRITICAL containing that text would silently downgrade a genuinely broken run. | **APPLIED** (§6.4). Specified a dedicated `STARVED_CRIT` flag set only at the capture-receipt call site (`:350-353`) plus a `CRIT_COUNT` counter in `crit()`. Title rule is a pure counter comparison with no text matching. Invariant stated for review: *the summary line logic must never relabel a genuinely CRITICAL run as merely starved* — enforced by `CRIT_COUNT -eq 1`. Test `test_starved_label_requires_single_capture_critical` and mutation test **M7** added. |
| **C-e** | Nothing detects ops being **behind** `origin/main` intra-day. §9.2 covers ops being ahead; R2 is an unenforced human rule. | **APPLIED as new owner decision D-6** (§12), with §9.1's R2 cross-referenced and §13's C4 disposition made conditional. Cited today's real incident, measured: PR #36 merged **10:28:03 ET**, ops realigned **14:28:10 ET** — a four-hour undetected refusal window, closed only because a human happened to act. Options: D-6a scheduled pre-15:45 check (new plist = new standing config = owner `launchctl bootstrap`), D-6b documented manual check, D-6c accept and write it down. Recommendation D-6a, flagged as owner's call because it creates a standing scheduled job. |
| **C-f** | S1's conditions were not artifact-measurable — "unattended LaunchAgent fires, not manual wrapper runs" and "no re-auth in the span" are recorded nowhere, so the bar could only be asserted from memory. | **APPLIED** (§7, and surfaced in D-4). Restated per condition: conditions 1, 2, 5 are measurable from named artifacts. Condition 3 (unattended-vs-manual) gets an explicit fork — **3a** add an `invocation_source` field to the capture receipt, with the landing constraint noted (`options_researcher/` is inside `diagnostic_source_hash`), or **3b** drop it. rev-2's re-auth condition is **dropped as written**, with the note that a token expiry already shows up as a missed session and is therefore caught by condition 1. |
| **C-g** | §2 claimed the Schwab gate is unreachable from `h7_data_gate`. It is already partly wired. | **APPLIED** (§2, §4). Corrected: `h7_data_gate.evaluate()` already takes `evidence_mode` (`:513`), and the module already imports `h7_schwab_data_gate` and branches on its `EVIDENCE_MODE` (`:522`, `:601-604`). Only the **CLI flag** is missing (`:813-829` has `--close-dir`, `--chain-dir`, `--reports-dir`, `--source-health-receipt`, `--write-receipt`, no `--evidence-mode`). Option A's stated cost reduced accordingly; **recommendation unchanged**, with the reason made explicit — reasons 1-4 for rejecting Option A are about evidence and registration, not plumbing cost. |
| **C-h** | "Underlying OHLCV refreshes to the current session" overclaims. | **APPLIED** (§3 deliverable 2, §11, §12 D-5, smoke test). Verified: `qm_dashboard` main calls `refresh_qm_ohlcv(watch_universe(), …)` (`:440`), so only **`.cache/underlying_ohlcv` for the 9-name watch universe** refreshes, further restricted to frozen QM-sidecar members (`:350-364`). The closes store **`.cache/underlying` stays frozen at 2026-08-05**; its only refresher, `data/recent_topup.py`, is deliberately never called by the ritual — `tests/test_daily_ritual_provenance.py:47` asserts exactly that. Consequence stated plainly: every closes-store consumer stays as stale after switch-on as before, and no artifact may say otherwise. |
| **C-i** | `git merge -q --no-edit origin/main` (`:403`) was omitted from §6.1's mutation-surface table. | **APPLIED** (§6.1 row 18b). Classified as a data-tier mutation surface, with the note that it is the most consequential verb in that block: it can rewrite tracked files and create a commit, runs unattended and fail-soft, and unlike `git add` is not allow-list scoped. Also added to the closure test's verb registry (B-2e). |
| **C-j** | C7 ("tests pass vacuously") was closed prematurely — rev-2's own closure spec could not have passed. | **APPLIED** (§13). C7 reopened in the disposition table with the specific reasons it was not fixed, then closed via B-2's corrected spec: three registries, three matchers, three comparisons, full `python -c` and verb enumeration, and mutation tests M3/M9/M10 proving the closure test bites. Noted the failure mode: a closure test that fails on the unmodified script gets "fixed" by deleting assertions, which is vacuity arriving by the front door. |
| **C-k** | The `OPTIONS_VALIDATOR_CACHE_ROLE=publisher` export (`:89`) was unclassified. | **APPLIED** (§6.1 row 1b). Classified data tier — the honest reading, since `data/thetadata_adapter.py` re-verifies role, repo root, branch and `origin/main` identity at the point of use, so the export alone writes nothing. Added a least-privilege note: under Option B **no data-tier step needs publisher authority**, so narrowing the export to the `require-full` region would be strictly tighter. **Deliberately not changed in this landing** — reasoning recorded — because moving a process-wide env export inside the same change set that restructures both gates multiplies hiding places for a mistake. Parked in `ideas-parking-lot.md`; the table now makes the grant visible. |

---

## Owner-decision change

| ID | Finding | Disposition |
| --- | --- | --- |
| **D-5** | rev-2 raised the ritual's network call as an owner decision. It is not one — the Yahoo lane is **already ratified** in `docs/2026-08-04-underlying-closes-source-decision.md` ("Yahoo stays primary. Schwab is NOT adopted for this lane"). Re-asking a settled question invites accidental reversal. The claim was also overbroad: "the ritual's one network surface" ignores `git fetch`/`merge`/`push` (`:402-404`), `restic backup` (`:417`), and cold-cache `uv` resolution. | **APPLIED** (§12 D-5, §13 C5). Demoted from an owner decision to a **disclosure**. Claim narrowed to: `qm_dashboard --refresh-ohlcv` is the ritual's only **market-data / provider** call (`data/underlying_ohlcv.py:185-200`). It stays on; owner veto remains available by amendment. |

---

## Notes on the application pass

* **Nothing was declined.** Every blocker and caution was checked against
  `~/options-validator-ops` @ `c96ed4b` before being written into rev-2.1, and
  all eighteen were factually correct as stated.
* **One finding was extended.** C-a said "four other" test modules and listed
  three; the fourth (`tests/test_h8_watch.py:635-636`) was located by grepping
  `tests/` for `daily_ritual` and checking which modules read the script text
  and assert on it. rev-2.1 lists all four.
* **One finding is only partly dischargeable by a spec edit.** C-f's condition 3
  needs either a new receipt field (a hashed-file change under
  `options_researcher/`) or the condition dropped. rev-2.1 does not choose —
  it makes the fork explicit and attaches it to owner decision D-4, because
  choosing would be inventing a bar the owner has not ratified.
* **One recommendation was deliberately not implemented.** C-k's least-privilege
  narrowing of the publisher export is recorded with reasoning and parked
  rather than folded into this landing. This is a disposition, not an omission.
* **rev-2.1 changes no code.** It is a specification document. Every finding is
  discharged as a corrected instruction to the future implementer, plus named
  tests and mutation tests (M1-M10) that make the corrections checkable rather
  than merely written down.
