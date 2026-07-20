# OpenBB adapter handoff for `equity-research`

The adapter source is the MIT-licensed
`OpenBB-finance/backends-for-openbb` repository pinned in
`../third_party/repos.toml`. It is the intended starting point for an
`equity-research`-owned enrichment backend.

The adapter may expose convenient market or company-context fields for analyst
workflow and UI use. It must not become the citation-of-record. The existing
`equity-research` pipeline remains canonical for:

- SEC filings and `tickers/*/filings/_companyfacts.json`;
- existing captured web pages, URLs, and access timestamps;
- filing-grade `[SOURCED: ...]` claims;
- DCF/reverse-DCF outputs and calibration records.

The adapter should therefore write only explicitly non-canonical enrichment
artifacts, with provider, as-of time, and raw response provenance. A later
implementation in the separate `equity-research` checkout should add its own
optional environment and tests; this options-validator repository does not
import the adapter or share configuration across repos.

For the complete file layout, provenance envelope, and test gates, use
`docs/superpowers/plans/2026-07-18-cross-repo-external-quant-integration-map.md`.
