# Dividend payer spot-check — 2026-07-23

The six non-zero entries in `data/rates/expected_dividends.csv` were checked against the cited issuer, SEC, or investor-relations source. The annual values below are the stated quarterly cash amount multiplied by four.

| Symbol | CSV annual value | Source amount | Annualized source value | Result |
| --- | ---: | ---: | ---: | --- |
| NVDA | $1.000 | $0.25 quarterly | $1.000 | MATCH |
| MSFT | $3.640 | $0.91 quarterly | $3.640 | MATCH |
| VST | $0.916 | $0.2290 quarterly | $0.916 | MATCH |
| CEG | $1.706 | $0.4265 quarterly | $1.706 | MATCH |
| AVGO | $2.600 | $0.65 quarterly | $2.600 | MATCH |
| ET | $1.350 | $0.3375 quarterly distribution | $1.350 | MATCH |

Sources:

- [NVDA SEC filing](https://www.sec.gov/Archives/edgar/data/1045810/000581026000051/q1fy27pr.htm)
- [MSFT investor news release](https://news.microsoft.com/source/2026/06/10/microsoft-announces-quarterly-dividend-29/)
- [VST issuer release](https://www.prnewswire.com/news-releases/vistra-declares-dividend-on-common-stock-series-b-preferred-stock-and-series-c-preferred-stock-302759203.html)
- [CEG investor-relations dividend table](https://investors.constellationenergy.com/stock-information/dividends-splits/)
- [AVGO issuer release](https://www.prnewswire.com/news-releases/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial-results-and-quarterly-dividend-302790698.html)
- [ET SEC exhibit](https://www.sec.gov/Archives/edgar/data/1276187/000127618726000021/ex991eterq12026.htm)

ET is an MLP distribution per common unit rather than a corporate-stock dividend; the amount is retained because the rates input uses it as the per-unit cash distribution for ex-date option math.

No CSV value changed. This is a source-verification record only.
