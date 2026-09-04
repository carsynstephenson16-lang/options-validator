# Brief 37 — independent adversarial review, round 3 (2026-09-04)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; no file edited).
**Target:** brief rev 3 as committed at `03c42b1`.
**Baseline:** branch `claude/post-147-2026-09-03`, tree = `origin/main` @`039d76e` + docs-only commits `12b4404`, `03c42b1`.
**Method (reviewer's words):** every rev-3 file:line opened; the three structural changes traced through the real call graphs; the ops build re-counted with `grep -o | wc -l`; `np.busday_count` and the closes-index dtype measured; every test named or implicated by a work package opened.

## Verdict: FAIL

Two blockers; 16 of the 18 round-2 dispositions confirmed applied (14 and 15 re-applied with numbers still wrong; 7 closed only for the empty-list case).

## Findings (severity · disposition in rev 4)

1. **BLOCKER** · WP-G(b) breaks `tests/test_event_awareness.py:311` (`test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list`, comment `:312` "Catches a consumer drifting from the single event-chip join contract"; market-wide events `:176-183`, empty `complex_map` `:376`, assertions `:441-449`; second exposure `:258`). The file is outside Scope IN and the invariant was authored on purpose by brief 28. → **Rev 4 removes WP-G(b).** DR-8b is held for the visual-redesign brief with the contract test cited; the orchestrator's reason: a cosmetic dedupe must not silently retire a deliberately pinned parity contract.
2. **BLOCKER** · WP-H never retired the check that produces DR-9 (`tools/job_health_digest.py:525-532` returns FAILED before the loop) and left `chain_dir` — the third positional argument to `schwab_chain_manifest.verify_session` at `:550` — undefined. → Reviewer's exact wording adopted: delete `:525-532`, compute `cache_root`/`chain_dir`, directory guard, per-symbol containment against `cache_root`, `:550` otherwise unchanged.
3. **HIGH** · WP-E's whole-page assertion was assigned to `tests/test_schwab_freshness_gather.py`, which never renders a page. → Moved to `tests/test_attractiveness_dashboard.py`.
4. **HIGH** · WP-B's exception tuple omitted `TypeError` (`portfolio.py:90`, `:93` receive `None` from `csv.DictReader` on a short row). → `(OSError, TypeError, ValueError)`.
5. **MEDIUM** · WP-C guarded only the empty-blocker case. → Sentinel when the list does not contain exactly one entry; test covers empty and two-entry cases. Dataclass construction, sole-blocker reachability and import purity all confirmed by the reviewer.
6. **MEDIUM** · WP-E's replacement sentence embedded "pending owner ruling", which becomes false if the ruling is "leave NaN". → Non-temporal wording.
7. **MEDIUM** · WP-A admitted a `date` object as the END bound; `load_closes` slices a string index (`data/underlying_closes.py:57-59`; measured dtype `object`). → ISO string of the NY build date.
8. **MEDIUM** · the held DR-5b paragraph read as a work package. → Fenced with "Codex must NOT implement any part of this bullet".
9. **MEDIUM** · WP-B named no injection seam (house pattern `dashboard.py:155-157`). → `holdings=` keyword on `assemble()`.
10. **LOW** · DR-6 count split: 26 across the 13 "Unavailable" lines (reason carried twice, `:1974` and `:1975`, joined at `:5073`) + 148 in `bbb_absent`. → Fixed.
11. **LOW** · DR-8b: all 295 chips are FOMC (180 for 2026-09-16, 65 for 2026-10-28, 32 for 2026-12-09, 18 across six 2027 dates) over 180 containers. → Fixed in the held bullet.
12. **LOW** · WP-F block structure omitted the inner `if :495` / `else :498`. → Fixed.
13. **LOW** · end-of-range cites: `_h7_window_panel:398-424`; `_hero_pick_html:3877-3926`; digest chain-dir block `:524-532`, loop `:533-542`, misleading string built at `:560`. → Fixed.
14. **LOW** · WP-D wording on `render()`; WP-B omitted `_PARTY`'s consumer `dashboard.py:450`. → Fixed.
15. **LOW** · `session(s)` pluralization unspecified (house style `:1128`). → Pluralize properly.
16. **LOW** · `trading_sessions_between` import is function-local (`:1246` inside `_page_chain_age_sessions`). → Import locally inside `_gather_symbol`, mirroring `:1938`.
17. **LOW** · WP-G(a) age predicate sign unstated. → `age > CHAIN_STALE_BLOCK_SESSIONS` collapses; everything else, including a negative count, stays red.
18. **LOW** · "the module's only import" imprecise; registry row 37 still described rv21 work. → "only first-party import"; registry row updated.

## Verified correct by the reviewer (attacked and survived)

WP-C authority construction (frozen dataclass `data/ritual_authority.py:31-35`; `:83` the sole producible blocker with the two flags True; `THETADATA_ACQUISITION_DISABLED` nested under `:78-81`; import graph pure; neither file in the closure). WP-G(a) data access (`_schwab_state_html` called once at `:1122` with the whole page mapping; `evaluation_date` at `:1739`; drawer list `:5660-5669` has six members pinned by `tests/test_attractiveness_layout.py:375-382`, `:405`; loud test `:3571-3584` stays red at age 0). WP-E truth conditions (`closes_as_of` is an ISO string at `:1945`; `closes_as_of > day` impossible because `raw_closes` loads with `end=day` at `:1942`; NaN unconditional at `:1965-1966`; `bbb_absent` `:1619-1625` reuses the same string; fixture `DAY = "2026-08-14"`, closes end `2026-08-04`, `busday_count == 8`; `:188`, `:197-199` untouched). WP-F in full (`python -c` sites and `MUTATION_VERB_SITES` all outside `481-507`; `--status RUNNING` at `:143`; `STARVED_CRIT=0` at `:83`, `=1` at `:502` moves with the block; region markers outside; `ritual_receipt.py` has no dashboard/pick-tracker reference). Every DR measurement reproduces on the ops build. Shape vs skill compliant. No ledger/registration/authority/live-order/config/launchd change anywhere in rev 3.
