# Brief 41 — review round 6 (confirmation of the round-5 fixes)

**Target:** brief rev 7 (uncommitted on `claude/brief-41-launchagent-loaded-check-2026-09-09`).
**Reviewer:** fresh Opus subagent, read-only, dispatched 2026-09-09 ~15:00 ET; scope = the thirteen round-5 replacements and any contradiction they could introduce.
**Verdict:** **PASS WITH FIXES** — all thirteen round-5 findings CLOSED at named lines; 2 minors + 1 nit, exact wording, applied in rev 8.
**Disposition:** rev 8 committed with this receipt so the dispatch self-check (`rev 8`, eight files) can succeed at a pinned SHA.

## Findings
- **R6-m1 (MINOR)** D.1 still asserted `FileNotFoundError → UNAVAILABLE` after R5-B2 made `UNAVAILABLE` observation-level. Fix: assert the `Observation(states=(), unavailable_reason=<non-None>, unavailable_inputs=('list','print','print-disabled'))` shape.
- **R6-m2 (MINOR)** `observe()` could pass `None` into `compare(disabled: Collection[str])` on a degraded `print-disabled`. Fix: `disabled_labels(...) or frozenset()`.
- **R6-n3 (NIT)** Status line read as if the latest review was a pass. Fix: name rounds 1–3 and 5 FAIL, 4 and 6 PASS WITH FIXES.

## Consistency sweep (clean)
Schema coherence (`Observation` → `build_receipt` → A.4 keys → C.1 reads → D.1/D.2 assertions; six count keys = six `State` members); CLI synopsis ⊇ WP-B invocation ⊇ acceptance 6; Scope OUT no longer contradicts A.4; `classify()`/`compare()`/`observe()`/`tracked_labels()` signatures consistent with D.1; Status READY FOR HAND-OFF; PR-starts-draft at acceptance 7 and the dispatch prompt; D-1/D-2/D-3 recorded not made; the only new constant is `OWN_PREFIX` (LLM-proposed); no `config.py` change. Operational note: the dispatch self-check is fail-closed, so a dispatch against a SHA that predates rev 8 stops rather than mis-implements.
