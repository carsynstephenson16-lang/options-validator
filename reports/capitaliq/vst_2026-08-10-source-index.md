# Capital IQ VST source index — 2026-08-10

## Purpose and boundary

This is a durable provenance index for a private Capital IQ capture of Vistra Corp. It improves event-research traceability without adding licensed PDFs or unreviewed vendor data to Git.

- Company: Vistra Corp
- Ticker / exchange: VST / NYSE
- Capital IQ company key: `4085953`
- S&P Capital IQ ID: `7959935`
- LEI: `549300KP43CPCUJOOG15`
- Profile: <https://www.capitaliq.spglobal.com/web/client?auth=inherit#company/profile?id=4085953>
- Retrieved: `2026-08-10`
- Raw-document policy: private and outside Git; this index is self-contained and does not depend on a machine-local bundle.

This material is display-only research evidence. It is not verdict-eligible and must not enter option-chain truth, quote or Greek validation, H7 forward evidence, backtests, candidate ranking, sizing, or trade activation.

## Source map

1. **10-Q** — page date `2026-08-10`; quarter ended `2026-06-30`; document ID `264760018`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=264760018&KeyProductLinkType=2); SHA-256 `baa3e1d489c6244cd70cb07e21b97806f00cfaa59f65fd411f4c9bd4c0f5e3ba`.
2. **Audio Transcript** — page date `2026-08-07`; document ID `264714280`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=264714280&KeyProductLinkType=2); SHA-256 `8fda0034988d1a68a5138d2e9cea4f653c23cf5166d6e9de3cf132b0364a87cb`.
3. **Earnings Call Transcript** — page date `2026-08-07`; document ID `264711362`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=264711362&KeyProductLinkType=2); SHA-256 `8fda0034988d1a68a5138d2e9cea4f653c23cf5166d6e9de3cf132b0364a87cb`.
4. **Investor Presentation** — page date `2026-08-07`; document ID `264707558`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=264707558&KeyProductLinkType=2); SHA-256 `2e115f07b695efdf53ed6e4caca0ced186efd8e313c83eb3e6e89b490e9149cd`.
5. **Earnings Release** — page date `2026-08-07`; document ID `264696864`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=264696864&KeyProductLinkType=2); SHA-256 `94be748d2b50ebc35280b29a5b66c872355de09d3d09ad5fa4cc717737ccdcf0`.
6. **Sustainability Report** — page date `2026-07-09`; document ID `263256969`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=263256969&KeyProductLinkType=2); SHA-256 `b29378439e71363a1c736096653f447e281b1d553d79ffa4c6c5348867a13875`.
7. **Annual Report (AR)** — page date `2026-03-18`; document ID `257009805`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=257009805&KeyProductLinkType=2); SHA-256 `e7f89738428c8f22c2f17a5561c620e130e674f8576a483c146cee8461abe174`.
8. **Annual Report (ARS)** — page date `2026-03-18`; document ID `256990518`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=256990518&KeyProductLinkType=2); SHA-256 `e7d1dbe56c98883e9131b303ee89331c17e8440c91ad571ad7751a1928a2b85c`.
9. **DEF 14A** — page date `2026-03-18`; document ID `256990566`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=256990566&KeyProductLinkType=2); SHA-256 `aeb18cbf9a0944f42d6c0cdb7459334a316cf0d49b1fdb20ffe41c9dfef05636`.
10. **DEFA 14A** — page date `2026-03-18`; document ID `256990602`; [Capital IQ viewer](https://www.capitaliq.spglobal.com/apisv3/spg-webplatform-core/docviewer?mid=256990602&KeyProductLinkType=2); SHA-256 `efa5f2d560f72e30aa08aa3506f91697a47b7d87f20a10ca178e007ae78c5e36`.

## What this improves

- Establishes a reproducible evidence map for VST's `2026-08-07` earnings event and the subsequent 10-Q.
- Prevents double counting: the Audio Transcript and Earnings Call Transcript have different Capital IQ IDs but identical SHA-256 hashes.
- Records source-quality exceptions: the ARS export is a one-page placeholder, and the DEF 14A viewer filename reports `2026-04-29` while the Capital IQ page reports `2026-03-18`.
- Makes missing options evidence explicit: this packet contains no contracts, expirations, strikes, bid/ask quotes, implied volatility, Greeks, open interest, volume, timestamps, or quote provenance.

## Safe use

Allowed uses are event chronology, catalyst context, transcript review, and source discovery. Before any event-calendar or earnings-timing append, confirm the date against a direct SEC filing or Vistra investor-relations source and retain that primary-source URL.

Do not treat provider profile fields, estimates, transcript text, or document metadata as a substitute for canonical market data or as evidence of an options edge.
