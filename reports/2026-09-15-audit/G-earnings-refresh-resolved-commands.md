# G. Earnings-refresh packet — `--known-as-of` / `--timing` resolution attempt

**Status: BLOCKED. None of the 15 rows could be resolved.** Every SEC EDGAR
request made under the mandated fixed, non-personal User-Agent was rejected
by sec.gov with HTTP 403 and the page title `SEC.gov | Your Request
Originates from an Undeclared Automated Tool`. This is a retrieval task, not
an analysis task, so no values are fabricated or estimated to fill the gap —
the two placeholders in every command below are exactly as they were in
`reports/2026-09-15-audit-edge-verdict-and-loose-ends.md` section 6.

## What was tried

- Tool argument parser checked first, per instructions:
  `uv run python tools/h7_refresh_earnings.py append-raw --help` and a grep
  of `tools/h7_refresh_earnings.py` / `options_researcher/h7_earnings.py` /
  `options_researcher/a2_runner.py` confirm: `--timing` only accepts
  `{bmo, amc, unknown}`; `--known-as-of` must be a timezone-aware ISO-8601
  timestamp (the code parses it with
  `datetime.fromisoformat(value.replace("Z","+00:00"))` and then requires
  `tzinfo is not None`). The docstring's own example is
  `--known-as-of 2026-10-10T12:00:00+00:00`. Eastern is EDT (UTC-4) on all
  15 dates in question, so the intended conversion is ET time + 4h, rendered
  with a `+00:00` offset.
- Per the mandated method, for each row the `.txt` filing header
  (`https://www.sec.gov/Archives/edgar/data/<CIK>/<ACCESSION18>/<ACCESSION-WITH-DASHES>.txt`)
  was fetched first (preferred source for `ACCEPTANCE-DATETIME:`), one
  request per filing (well under the 2-request/filing cap; the index-page
  fallback was not attempted for the other 14 once the pattern was
  confirmed on the first).
- Every request used `curl -A "options-validator-research/1.0
  (+https://github.com/carsynstephenson16-lang/options-validator)"`, sec.gov
  host only, 1 request per filing, ≥1 second apart. No email address or
  personal name was included in any request, per the non-negotiable rule.
- A diagnostic request to the CRWV **index** page (`.../0001769628-26-000362-index.htm`)
  with the same UA returned the identical 403/"Undeclared Automated Tool"
  page, confirming the block is not specific to the `.txt` endpoint.

**Root cause:** SEC's own posted fair-access policy for automated EDGAR
requests requires a User-Agent that identifies a company/individual *and*
includes a contact **email address** (SEC's documented example format is
`Sample Company Name AdminContact@sample.com`). The mandated fixed UA for
this task deliberately excludes any email or personal name (to avoid
repeating a prior leak), and SEC's edge classifies that UA as an
"undeclared automated tool" and blocks it outright — before any rate
limiting even comes into play. This is a genuine conflict between two of
this task's own constraints (SEC's server-side requirement vs. the
no-email/no-personal-name rule), not a transient error. No workaround was
attempted (no UA was tried that would have satisfied SEC's format), because
the rules said the UA must be fixed for every request.

## 1. Table of 15 rows

All 15 rows show the same outcome. Accession numbers are given
dash-formatted (10-2-6) as used in the request URL.

| # | Symbol | Accession | Acceptance datetime (as fetched) | Converted `--known-as-of` value | Derived `--timing` + reason | Form-type check | Fetch time (UTC) | Source URL used |
|---|---|---|---|---|---|---|---|---|
| 1 | CRWV | 0001769628-26-000362 | **BLOCKED — HTTP 403 "Undeclared Automated Tool"**, no acceptance timestamp returned | UNRESOLVED (placeholder retained) | unknown — cannot derive without acceptance time | Not verified — page blocked before content could be read | 2026-09-15T15:27:25Z | https://www.sec.gov/Archives/edgar/data/1769628/000176962826000362/0001769628-26-000362.txt |
| 2 | TEM | 0001193125-26-326083 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:26Z | https://www.sec.gov/Archives/edgar/data/1717115/000119312526326083/0001193125-26-326083.txt |
| 3 | PLTR | 0001321655-26-000039 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:27Z | https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/0001321655-26-000039.txt |
| 4 | NOW | 0001373715-26-000072 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:28Z | https://www.sec.gov/Archives/edgar/data/1373715/000137371526000072/0001373715-26-000072.txt |
| 5 | SMCI | 0001375365-26-000021 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:29Z | https://www.sec.gov/Archives/edgar/data/1375365/000137536526000021/0001375365-26-000021.txt |
| 6 | NVDA | 0001045810-26-000073 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:31Z | https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/0001045810-26-000073.txt |
| 7 | AMD | 0000002488-26-000121 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:32Z | https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/0000002488-26-000121.txt |
| 8 | AVGO | 0001730168-26-000076 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:33Z | https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/0001730168-26-000076.txt |
| 9 | IREN | 0001878848-26-000051 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:34Z | https://www.sec.gov/Archives/edgar/data/1878848/000187884826000051/0001878848-26-000051.txt |
| 10 | USAR | 0001970622-26-000056 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:35Z | https://www.sec.gov/Archives/edgar/data/1970622/000197062226000056/0001970622-26-000056.txt |
| 11 | ET | 0001276187-26-000033 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:36Z | https://www.sec.gov/Archives/edgar/data/1276187/000127618726000033/0001276187-26-000033.txt |
| 12 | VST | 0001692819-26-000017 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:37Z | https://www.sec.gov/Archives/edgar/data/1692819/000169281926000017/0001692819-26-000017.txt |
| 13 | CEG | 0001868275-26-000097 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:39Z | https://www.sec.gov/Archives/edgar/data/1868275/000186827526000097/0001868275-26-000097.txt |
| 14 | MSFT | 0001193125-26-323632 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:40Z | https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/0001193125-26-323632.txt |
| 15 | AMZN | 0001018724-26-000024 | BLOCKED — same 403 | UNRESOLVED | unknown — cannot derive | Not verified — blocked | 2026-09-15T15:27:41Z | https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/0001018724-26-000024.txt |

Diagnostic index-page check (extra, not counted toward the 2-per-filing cap
above since it was against the same CRWV filing): `GET
https://www.sec.gov/Archives/edgar/data/1769628/000176962826000362/0001769628-26-000362-index.htm`
→ also HTTP 403, same block page, fetched 2026-09-15T15:27:53Z UTC.

## 2. `append-raw` commands — placeholders NOT filled

Because no acceptance timestamp could be retrieved for any of the 15
filings, the commands below are unchanged from
`reports/2026-09-15-audit-edge-verdict-and-loose-ends.md` section 6. Filling
`<acceptanceDateTime>` with anything other than a value actually read off
SEC EDGAR would violate the no-fabrication / Official-source-only rule this
task and the project's integrity guardrails both require.

```bash
R="uv run python tools/h7_refresh_earnings.py append-raw --status occurred --source-type sec_filing --record-type assertion"
$R --symbol CRWV --event-id CRWV-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-08-11 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1769628/000176962826000362/crwv-20260811.htm --known-as-of <acceptanceDateTime>
$R --symbol TEM  --event-id TEM-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-07-30 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1717115/000119312526326083/tem-20260730.htm --known-as-of <acceptanceDateTime>
$R --symbol PLTR --event-id PLTR-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-08-03 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/pltr-20260803.htm --known-as-of <acceptanceDateTime>
$R --symbol NOW  --event-id NOW-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-07-22 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1373715/000137371526000072/now-20260722.htm --known-as-of <acceptanceDateTime>
$R --symbol SMCI --event-id SMCI-FY26Q4  --fiscal-period FY26Q4  --occurred-date 2026-08-11 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1375365/000137536526000021/smci-20260811.htm --known-as-of <acceptanceDateTime> --notes "full report; the 2026-07-21 Item 2.02 was PRELIMINARY (do not promote as actual)"
$R --symbol NVDA --event-id NVDA-FY27Q2  --fiscal-period FY27Q2  --occurred-date 2026-08-26 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm --known-as-of <acceptanceDateTime>
$R --symbol AMD  --event-id AMD-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-08-04 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/amd-20260804.htm --known-as-of <acceptanceDateTime>
$R --symbol AVGO --event-id AVGO-FY26Q3  --fiscal-period FY26Q3  --occurred-date 2026-09-02 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-20260902.htm --known-as-of <acceptanceDateTime>
$R --symbol IREN --event-id IREN-FY26Q4  --fiscal-period FY26Q4  --occurred-date 2026-08-27 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1878848/000187884826000051/iren-20260827.htm --known-as-of <acceptanceDateTime> --notes "the 2026-07-20 Item 2.02 was a business update, not a quarterly report"
$R --symbol USAR --event-id USAR-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-08-10 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1970622/000197062226000056/usar-20260810.htm --known-as-of <acceptanceDateTime>
$R --symbol ET   --event-id ET-2026Q2    --fiscal-period 2026Q2  --occurred-date 2026-08-04 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1276187/000127618726000033/et-20260804.htm --known-as-of <acceptanceDateTime>
$R --symbol VST  --event-id VST-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-08-07 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1692819/000169281926000017/vistra-20260807.htm --known-as-of <acceptanceDateTime>
$R --symbol CEG  --event-id CEG-2026Q2   --fiscal-period 2026Q2  --occurred-date 2026-08-06 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1868275/000186827526000097/ceg-20260806.htm --known-as-of <acceptanceDateTime>
$R --symbol MSFT --event-id MSFT-FY26Q4  --fiscal-period FY26Q4  --occurred-date 2026-07-29 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-20260729.htm --known-as-of <acceptanceDateTime>
$R --symbol AMZN --event-id AMZN-2026Q2  --fiscal-period 2026Q2  --occurred-date 2026-07-30 --timing unknown --source-url https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/amzn-20260730.htm --known-as-of <acceptanceDateTime>
# then, for each printed raw id A0xxx:
# uv run python tools/h7_refresh_earnings.py promote --raw-id A0xxx --event-class actual_quarterly_earnings
# uv run python -m options_researcher.h7_source_health
```

## 3. Provenance

Every fetch attempt above is **Official-source (attempted)** — sec.gov only,
User-Agent `options-validator-research/1.0
(+https://github.com/carsynstephenson16-lang/options-validator)` on every
request, no email or personal name in any request, 1 request per second
minimum spacing, ≤2 requests per filing. No value in the table or the
commands above is LLM-asserted, estimated, or carried over from any other
source (e.g., memo C, which itself does not contain acceptance timestamps)
— every `<acceptanceDateTime>` placeholder that could not be verified
directly against an SEC response was left as a placeholder rather than
filled with a guess.

## Rows not resolved

**All 15 rows are unresolved**: CRWV, TEM, PLTR, NOW, SMCI, NVDA, AMD, AVGO,
IREN, USAR, ET, VST, CEG, MSFT, AMZN. The blocker is structural (SEC's UA
policy vs. this task's no-email/no-personal-name rule), not per-filing, so
resolving even one row requires either (a) the owner supplying a
SEC-compliant User-Agent (an email address SEC will accept is unavoidable
under their published policy), or (b) the owner fetching the 15
acceptance timestamps manually and pasting them back for conversion. Once a
compliant UA or manually-supplied timestamps are available, the conversion
step itself (ET+4h → `...+00:00`, bmo/amc/unknown derivation) is mechanical
and can be completed in minutes.
