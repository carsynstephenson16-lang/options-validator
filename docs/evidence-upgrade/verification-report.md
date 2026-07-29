# Verification Report — Evidence-Ingestion Architecture (EC-1)

Date: 2026-07-29. Verifier: independent, fresh-context Claude Sonnet 5
subagent at high effort, given only the six planning artifacts, the
workstream reports, the saved primary documents, and read-only access to
the three repositories — no access to the lead architect's reasoning.
Disposition of each finding was then decided independently by the lead
(Fable 5); every accepted finding's fix is recorded in decision-log D27.

Verifier's overall result: **PASS_WITH_CORRECTIONS — 0 blocking, 7
correctable findings.** All 7 were evaluated as supported and fixed
before this report was issued.

## Findings and dispositions

| # | Severity | Finding (location) | Lead's evaluation | Fix applied |
|---|---|---|---|---|
| F01 | MAJOR | SEC exception-form list labeled "21 types"; the verbatim Filer Manual v77 sentence (verified in the saved `efmvol2-v77.txt`) lists **24** distinct submission-type strings; Packet 1's checklist "matches the 21 types verbatim" was unsatisfiable | Supported — independently recounted: 24 | Count corrected in `final-architecture.md` §6.1, Packet 1 (context, scope, checklist); rule added: encode the verbatim list, never a count |
| F02 | MAJOR | `earliest_public_ts_utc = acceptance` labeled "conservative" is the *optimistic* extreme for anti-look-ahead purposes; the cited PDS spec itself says dissemination is "as soon as reasonably feasible" (nonzero, unquantified lag) | Supported — "conservative" was direction-inverted for the gating use | Availability re-modeled as an interval: `earliest_public_ts_utc` (labeled optimistic lower bound, never gates look-ahead-sensitive reads) + `public_by_ts_utc` (22:00 ET on the dissemination business day, the `available_at` for decision gating). Architecture §6.1, Packet 1, decision-log D05 amended |
| F03 | MAJOR (borderline) | SQLite ≥3.51.3 WAL gate specified as "warn, not fail" while **both venvs measure 3.50.4** (below every safe version incl. backports) and `market_updates` already runs WAL mode; no remediation path named | Supported — an advisory gate that is already failing is not a gate | Gate made fail-closed: on an unsafe engine, single-writer access is mechanically enforced (non-blocking exclusive write lock; second writer raises `ConcurrentWriterError`); engine version + active control recorded on receipts; engine upgrade documented as an owner decision. Architecture §10/§12, Packet 2 scope 6, D20 amended |
| F04 | MINOR | Two more count errors: ledger row SEC-S8 said "10 holidays" (official 2026 EDGAR calendar lists 11); Packet 3 said "nine providers" (`providers.py` defines ten) | Supported — verifier checked the saved calendar HTML and read `providers.py` | SEC-S8 claim corrected to 11; Packet 3 corrected to ten with the class list enumerated and an instruction to enumerate from `build_providers()` at implementation time |
| F05 | MINOR | Contradiction: architecture §12 "isolation test must pass unmodified" vs Packet 6 "isolation test extended" | Supported — wording conflict, single intent | §12 reworded: the isolation test must continue to pass; extending coverage is expected, narrowing/weakening is not |
| F06 | MINOR | equity-research baseline drifted: documented 1544, verifier measured 1546 at the same HEAD (kalshi's 2252 reproduced exactly) | Supported | Both baseline tables record 1544–1546 with an explicit record-your-own-baseline-at-packet-start instruction (already required by standing instruction #2) |
| F07 | INFO | options-validator tree carries unrelated uncommitted files (modified `live_quotes.py`/test; untracked `schwab_adapter.py`/test) from a concurrent session | Supported — known concurrent-sessions pattern | Packet 8 precondition names the files and forbids staging them |

No finding was rejected. No finding required re-architecting; the fixes
are documentation corrections plus two small enforcement upgrades (F02
interval field, F03 writer lock) folded into the affected packets before
any Codex thread starts.

## Checks that passed (what was actually verified)

The verifier ran all 20 mandated checks and documented per-check evidence
(full text: session scratchpad `adversarial-verification.md`). Highlights
of what was *actually inspected*, not assumed:

- Primary-document cross-checks: NHIGH contract terms PDF (freeze rule
  language verbatim, incl. 7/8 AM ET, +1 week, 11 AM delay conditions);
  WMO-386 Attachment II-12 (only RRx/CCx/AAx defined — no Pxx; GTS
  segmentation retirement dated 2007-11-07 verbatim); NWSI 10-1004 §4.1.2
  (CLI issuance schedule and LST climate-day); EDGAR Filer Manual v77
  (cutoff rules verbatim); 2026 DST dates independently recomputed.
- Repository reality: every file named in the Codex packets confirmed to
  exist (14 modules across three repos, listed per path); the three
  claimed code-level facts re-verified by reading the code —
  `RawPayloadArchive.write()` skip-if-exists at `service.py:94`,
  `edgar_fetch.py` zero acceptance-time handling,
  `exchange_settlements` present-but-unfed (no writer besides the
  migration).
- Commands: kalshi suite re-run (2252 passed, exact reproduction);
  equity-research suite re-run (1546 OK → F06); options-validator
  `ruff check .` and `pyright` re-run clean; the mocked-urlopen offline
  test convention confirmed real by reading `tests/test_macro_refresh.py`.
- Policy integrity: all 53 ledger rows scanned — no discovery-only source
  supports any claim; every rule-bearing policy claim cites a
  governing-primary source; independence groups populated and same-agency
  weather corroboration labeled as such; no composite score exists in any
  schema; coverage-paired reporting present wherever risk is reported;
  lineage bounded (batch inserts + 10k-link test); no lossy migration
  claims a downgrade; no live network in any test path; OOS/holdout and
  shadow/live protections named correctly and untouched; banned result
  vocabulary absent; no live-order/paper-mode scope creep in any packet.

## Residual gaps (recorded, non-blocking)

1. SEC dissemination latency is officially unquantified — handled by the
   interval design; an internally measured SLO may later tighten
   `public_by_ts_utc`, labeled as internal measurement only.
2. WMO `Pxx` remains undefined in the governing sources read — handled by
   quarantine-on-unrecognized-BBB; locate and read the 1994 WMO BBB
   guidelines before ever changing that rule.
3. Murphy (1973) original paper unverified (CloudFront 403) — ECMWF
   official documentation substituted, labeled.
4. The full text of the originally supplied plan documents ("Evidence
   Architecture Corrections, Revision 3" and its predecessor) was never
   located; the commissioning prompt's invariants/corrections served as
   the governing summary (decision-log D01).
5. The equity-research 1544 vs 1546 test-count drift at the same HEAD is
   unexplained (likely environment-dependent discovery); packets gate on
   a freshly recorded baseline, so it cannot mask a regression.

## Final readiness verdict

**READY_FOR_CODEX.** Zero blocking findings; all seven correctable
findings fixed and re-recorded (decision-log D27); every release-blocking
check on the mandated list passed with named evidence. Recommended start:
Thread A Packet 1 (equity-research SEC availability) and Thread B
Packet 6 (kalshi CLI version chain) may begin in parallel.
