# Brief 39 — independent adversarial review, round 1 (2026-09-06)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; ran the brief's Task 1–3 code verbatim in a scratch package, ruff, pyright, and the three affected test files as a baseline).
**Target:** `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md` rev 1 @ `ea3c5a4`. **Base:** `origin/main` @ `f83428d`. Baseline: layout 27 / dashboard 203 / event-awareness 16 tests OK.

## Verdict: FAIL

Two blockers need an owner decision (1, 6) and one spec inconsistency needs the owner's word (26); the rest are mechanical. The pure module (Task 2) is the strong part: its 15 unit tests ran green exactly as written and every expectation was traced by hand.

## Findings (severity · disposition in rev 2)

1. **BLOCKER (owner)** · acceptance targets impossible: the 14 per-name panels the spec keeps byte-identical are 89% of today's bytes (14 smallest = 497 KB) and carry 333 of 362 `<details>` and 18 of 30 `<h2>`; "< 150 KB / ≤ 8 h2 / ≤ 20 details" cannot pass. → Owner ruling: restate targets as what is VISIBLE with fold-outs closed, or trim the panels (forfeits byte-identity and the chip contract).
2. **BLOCKER** · `evaluation_date` and `status_labels` are loop-locals (`:5554`, `:5594`); the wiring references them at `:5700`. → Hoist `evaluation_date` before the loop; drop `status_labels` from both new signatures (the panel derives it from `sec`).
3. **BLOCKER** · `_symbol_panel_html` extraction omitted `stale_symbols`, `pinned_symbols`, `protected_card_ids` and dropped `symbol_names.append` (`:5633`) → flag-off nav loses every link. → Full signature returning `(panel_html, symbol_name)`; loop cited as `:5548-5664`.
4. **BLOCKER** · `class="drawer"` does not exist (drawer is `<details class="panel diagnostics-drawer" id="diagnostics">`). → `id="diagnostics"` everywhere.
5. **BLOCKER** · Task 6 referenced `self._render_populated()` (does not exist) and `chips()` (nested at `test_event_awareness.py:393` inside the test being replaced). → Lift the fixture + `chips()` to module level in a no-behaviour-change commit, with code.
6. **BLOCKER (owner)** · the event-line union over baseline picks (1 distinct chip on Friday) cannot equal the union over every rendered panel (9 distinct); panels also legitimately differ by symbol/expiry. → Owner ruling on the contract; recommended: line = union over the registered picks' cards; panels keep today's per-card chips; parity asserted only pick-card ↔ its own panel.
7. **BLOCKER** · Task 3 ungated default makes every injected `assemble()` call (65 test sites) run the 3.3 s cached-data experiment build. → Gate on `real_assembly` like `open_positions` (`:1745`); inject in tests.
8. **HIGH** · Task 2 module has 11 pyright errors as written (`str | None` symbols, `object` to int/float, `Mapping` vs `dict`). → Ship the typed version.
9. **HIGH** · blocked record shape is `{"symbol","reason_code","detail","last_known_date","unexpected"}` (`:1866-1870`), no `reason`. → Use `reason_code · detail`; document the shape; fix the fixture.
10. **HIGH** · `_open_slots_notice_html(qualified_picks)` cannot build `_OpenSlot`s without `data`, and today's slot count uses `py_picks` (watch-inclusive, `:4200-4203`). → `_open_slots_notice_html(data, watch_picks)` with the exact body.
11. **HIGH** · status strip mis-stated the WP-G retention rule: `CHAINS_ABSENT` is info, not a failure; uncomputable age keeps the notice loud. → Mirror `:1058-1110`.
12. **HIGH** · closes dot hard-coded green; freshness dict is `{"state": "available"|"unavailable", ...}` with no `max_session`. → State-driven colour.
13. **HIGH** · `render()` emits no HTML comment; the digest is bound in the publish path (`pick_tracker.py:52`, `:5876`). → Parity via `_render_result(...).render_source_row_hashes`.
14. **HIGH** · `event_css` computed at `:5694` before `body_html`; details HTML not a variable. → Hoist `details_html`/`event_line_html`; exact expression given.
15. **HIGH** · `tests/test_attractiveness_dashboard.py` (203 tests) under-scoped: ≥ 14 tests slice on "DATA FRESHNESS" → "Rule-based top 5" or pin order. → Enumerated in rev 2 Task 6.
16. **HIGH** · `_experiments_shelf_html` docstring (`:3775`) forbids importing/running an experiment builder; the brief does so silently. → Cite and amend the docstring.
17. **HIGH** · legacy snapshot captured after the extraction → vacuous. → Capture before any `_render_result` change; extraction asserted against it.
18. **MEDIUM** · cite drift: `load_open_positions :1485`; `_event_chips_html :3065`/`event_chips :3024`; h2 at `:4213`; loop `:5548-5664`; body `:5700-5721`; `assemble` signature `:1562-1571`. → Fixed.
19. **MEDIUM** · baseline pick has no `status` key; has `strike/expiry/dte` at top level (`:357-364`). → Shape + fixture fixed.
20. **MEDIUM** · class is `DiagnosticsDrawerTests` (`:374`). → Named.
21. **MEDIUM** · heading is `DATA FRESHNESS`, not "Data freshness". → Fixed.
22. **MEDIUM** · `mock` not imported in the layout test file. → Import added.
23. **MEDIUM** · appending an import mid-file → ruff E402. → Import placed at top.
24. **MEDIUM** · `pyrightconfig.json` include list omits the new module. → Added.
25. **MEDIUM** · `build_experiment_lanes` returns a fifth `exp_short` lane of dataclasses (not JSON-serialisable); on 09-04 beta is OK for all 18 and tbill ABOVE for all 18. → Documented; only the four dict lanes stored.
26. **MEDIUM (owner)** · spec D4 "keep context lane" vs §2 "remove the context cards"; the brief drops the cards silently. → Owner confirms the lane survives as a column only.
27. **MEDIUM** · API deviates from spec §4 (`context_selection`, `blocked`, `block_reason`, no `event_line`). → Deviation note added.
28. **MEDIUM** · context reasons `BLOCKED`/`DIRECTION_MISMATCH` counted as agreement. → Only `ALIGNED` counts.
29. **MEDIUM** · CSS class list incomplete. → Full list.
30. **MEDIUM** · no WP-* labels (codex-brief skill). → Tasks carry WP labels.
31–36. **LOW** · test counts (15 not 13), helper locations (`:3427`, `:3454`), file-handle leak, unused params, 782,263 bytes, `_board` kwargs collision. → Fixed.
Placeholders (7) flagged by the writing-plans rule (Event ctor, mark-age rule, "today's assembly" ellipsis, class name, `tests/__init__.py`, digest marker, Task 6 delegation). → Each replaced with code or an exact instruction.

## Verified correct by the reviewer

Task 2 module + 15 tests green as written; data shapes for context rows, composite cards, experiment cards/states, `_error_card`, open positions, Schwab failures, `pinned_picks`; `select_qm_top_picks` call valid and `qm_context` non-None at the call site; `_event_chips_html` markup contract; all 16 layout-test and both event-test citations exact; `FEASIBILITY_SOURCE_PATHS` excludes every touched file; ranking/grades/snapshot/source hashes computed outside the flag branch (`:5515-5528`, `:5751-5761`) — structurally untouched; no JS/network/ledger/authority path; `PICK_TOP_N` reused.
