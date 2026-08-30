# Task 3 independent review — causal earnings repair and fixed-window feasibility

## Verdict

**PASS.** Specification compliance: PASS. Implementation/evidence quality: PASS. No blocking findings.

This verdict approves the Task 3 evidence repair as a faithful rejection record. It does **not** make `h7-forward-schwab-v1` registration-ready: v1 registration and authority work remain **STOPPED** because the measured `4.0` expected entries are below the required `20`.

## Prioritized findings

None.

## Specification review

- The authoritative production boundary is exactly `97a3e5808b15013e66938345d6b7104b707dc022..e61709c7505a9f44392d4f0de034cd371fd5f527`: one focused commit, five expected files, 166 insertions, and no code, configuration, scorer, cost, ledger, authority, or old-receipt changes.
- Both earnings stores are pure append-only changes. Byte-prefix checks passed; `assertions_v2.csv` adds exactly 15 newline-terminated records and `gating_v3.csv` adds exactly 15, with zero replacement or deletion of prior bytes.
- The amended 15-name schedule specification matches the committed rows exactly: symbol, event ID, fiscal identity, confirmed date, BMO/AMC timing, source type, URL, and conservative `known_as_of_utc` all agree.
- The one-to-one promotion map is exact and field-preserving:

  `A0280/G0026 AMD`, `A0281/G0027 AMZN`, `A0282/G0028 AVGO`, `A0283/G0029 CEG`, `A0284/G0030 CRWV`, `A0285/G0031 ET`, `A0286/G0032 IREN`, `A0287/G0033 MSFT`, `A0288/G0034 NOW`, `A0289/G0035 NVDA`, `A0290/G0036 PLTR`, `A0291/G0037 SMCI`, `A0292/G0038 TEM`, `A0293/G0039 USAR`, `A0294/G0040 VST`.
- Every G row cites its exact A row, uses `actual_quarterly_earnings`, has empty supersession, and preserves all promotion-contract fields. No added row uses or promotes aggregator evidence.
- All 15 local issuer captures matched their recorded SHA-256. Their content supports the recorded fiscal identities, schedule dates, and BMO/AMC classification. AMD and ET retain exact issuer publication times. Each of the 13 date-only releases was independently checked against the XNYS calendar; every stored timestamp is exactly the next regular-session open. This preserves completed-session causality and introduces no lookahead.
- The old feasibility receipt, old H7 ledger, Schwab ledger, v1 code/config/stack/cost/scorer, and authority surfaces are unchanged. Git object identities for the old receipt and ledgers match at base and candidate.
- The v2 artifact is design-only. It keeps earnings and liquidity gates fixed, requires a separately versioned entry stack and preregistration before experiments, and runs no variants or experiments.

## Receipt and result review

- `reports/h7_forward_schwab/2026-08-11-feasibility-primary-earnings.json` passes its canonical receipt-hash verifier.
- Its three current input hashes match the exact candidate bytes: raw assertions, gating assertions, and the primary-evidence packet. Its embedded prior receipt hash matches the unchanged 2026-08-09 receipt.
- The receipt binds the canonical 15-name universe, 70-session window, 1,050 denominator, zero errors, frozen stack version, code SHA, config hash, canonical read-only cache paths, and the result.
- Independent read-only replay against `/Users/carsynstephenson/options-validator/.cache/chains` and `.cache/underlying` reproduced exactly:

  - 70 common sessions, `2026-04-16` through `2026-07-27`
  - 15 names / 1,050 symbol-days
  - 4 passes: `NOW 2026-05-18`, `NOW 2026-07-13`, `MSFT 2026-07-16`, `PLTR 2026-07-16`
  - base rate `0.0038095238095238095`
  - expected entries `4.0`
  - error count `0`

## Commands and evidence

- `git diff --name-only 97a3e580..e61709c` and `git diff --check 97a3e580..e61709c` — expected five-file scope; whitespace check passed.
- Python byte-prefix/CSV audit — both stores pure append; exact 15 A/G IDs; exact one-to-one promotion fields; no aggregators or supersessions.
- `shasum -a 256 /private/tmp/h7-primary/*.md` — all selected capture hashes matched the production packet.
- XNYS-calendar audit of all 13 date-only publications — 13/13 next-session opens matched.
- Receipt audit using `tools.h7_schwab_feasibility.verify_receipt` plus direct SHA-256 recomputation — receipt valid; current input hashes 3/3; prior receipt link valid.
- `git diff --exit-code 97a3e580..e61709c -- reports/h7_forward_schwab/2026-08-09-feasibility.json ledger/h7_forward ledger/h7_forward_schwab config.py options_researcher/h7_watch.py options_researcher/h7_board.py tools/h7_schwab_feasibility.py` — no differences.
- `UV_CACHE_DIR=/private/tmp/h7-review-uv MPLCONFIGDIR=/private/tmp/h7-review-mpl PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_h7*.py' -q` — exit 0.
- Independent fixed-window `measure_cached_history` replay — reproduced 4/1050, expected 4.0, zero errors.

## Remaining risks and unsupported assumptions

- No Task 3 blocking risk found. As with the existing feasibility design, the result is a cached-data measurement, not evidence of edge or authorization to trade.
- No unsupported factual assumption was needed for the verdict; issuer evidence, local hashes, repository bytes, and the independent replay supplied the decision-critical facts.

## Final v1 readiness

**NOT READY / STOPPED for registration and authority.** The repair artifact itself is review-ready and valid, but `4.0 < 20`; the feasibility gate rejects continued v1 registration/authority work. Any future research must proceed only under the separately versioned, still-design-only v2 process.
