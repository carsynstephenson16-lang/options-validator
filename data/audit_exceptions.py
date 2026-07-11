"""data/audit_exceptions.py -- REVIEWED exception registry for the H7
full-window data audit (7b-2 C2; corrected 7b-2R finding 2, 2026-07-11).

Every excluded symbol-session must trace to an entry here; the audit never
invents exclusions. Each entry carries provenance with a `basis`:

  * basis="official"      the exclusion is established by primary sources
                          (SEC filings, exchange notices), cited by URL;
  * basis="data_coverage" the period is NOT proven untradable -- the
                          archive simply cannot prove listed-options
                          availability. These entries require an
                          owner-ratified scope amendment before any
                          diagnostic may launch; the audit BLOCKS on them
                          (unratified_coverage_entries) until `ratified_by`
                          names the ledger amendment.

7b-2R corrections baked in:
  * SMCI is three segments, not one "suspension": the Nasdaq suspension
    (2018-08-23, company 8-K item 3.01), the delisted period (Form 25-NSE
    effective 2019-03-22 through relisting 2020-01-13), and a relisted
    period with NO established options-resumption date (2020-01-14 through
    2020-05-04, the day before the chain cache resumes).
  * Underlying listing status is separated from verified listed-options
    availability; option inception is never inferred from the first cached
    file (PLTR/CEG each get an explicit data_coverage segment between the
    equity's official first trade and the cache's first chain day).

Ranges are inclusive. The union of segments per symbol equals the pre-7b-2R
exclusion intervals exactly, so manifest counts are unchanged.
"""

from __future__ import annotations

H7_AUDIT_EXCEPTIONS = (
    {
        "symbol": "PLTR",
        "start": "2018-01-02",
        "end": "2020-09-29",
        "kind": "pre_listing",
        "basis": "official",
        "source_urls": (
            "https://www.sec.gov/Archives/edgar/data/1321655/000119312520258493/d904406d424b4.htm",
        ),
        "provenance": ("PLTR NYSE direct listing 2020-09-30 (424B4 "
                       "prospectus filed 2020-09-30); listed options cannot "
                       "predate the underlying's first trade"),
    },
    {
        "symbol": "PLTR",
        "start": "2020-09-30",
        "end": "2020-10-05",
        "kind": "options_inception_unverified",
        "basis": "data_coverage",
        "source_urls": (
            "https://www.miaxglobal.com/alerts/2020/10/12/miax-exchange-group-options-markets-listing-palantir-technologies-inc-pltr",
        ),
        "provenance": ("equity listed 2020-09-30 but no official "
                       "option-listing notice covers these sessions; the "
                       "earliest official evidence of listed PLTR options "
                       "is the MIAX listing alert effective 2020-10-13; "
                       "chain cache has no data before 2020-10-06. NOT "
                       "proven pre-listing -- data-coverage limitation "
                       "requiring an owner-ratified scope amendment"),
    },
    {
        "symbol": "CEG",
        "start": "2018-01-02",
        "end": "2022-02-01",
        "kind": "pre_listing",
        "basis": "official",
        "source_urls": (
            "https://www.sec.gov/Archives/edgar/data/1868275/000110465922010603/tm224960d4_ex99-1.htm",
            "https://boxoptions.com/assets/BOXOnnMemo205387.pdf",
        ),
        "provenance": ("CEG regular-way trading on Nasdaq began 2022-02-02 "
                       "(company PR, 8-K exhibit 99.1); when-issued CEGVV "
                       "traded from 2022-01-19 with no listed options (BOX/"
                       "OCC spinoff memo covers only the EXC adjustment)"),
    },
    {
        "symbol": "CEG",
        "start": "2022-02-02",
        "end": "2022-02-08",
        "kind": "options_inception_unverified",
        "basis": "data_coverage",
        "source_urls": (),
        "provenance": ("no official option-listing notice found for CEG "
                       "options inception (MIAX per-class alerts had ceased "
                       "by 2022; no OCC/Cboe/Nasdaq/BOX notice located); "
                       "chain cache begins 2022-02-09. Data-coverage "
                       "limitation requiring an owner-ratified scope "
                       "amendment"),
    },
    {
        "symbol": "SMCI",
        "start": "2018-08-23",
        "end": "2019-03-21",
        "kind": "underlying_suspended",
        "basis": "official",
        "source_urls": (
            "https://www.sec.gov/Archives/edgar/data/1375365/000162828018011320/form8-k_20180822.htm",
            "https://www.miaxglobal.com/alerts/2018/08/23/miax-options-and-miax-pearl-delisting-alert-super-micro-computer-inc-smci",
        ),
        "provenance": ("Nasdaq trading suspension effective the open of "
                       "2018-08-23 (company 8-K item 3.01, filed "
                       "2018-08-23); MIAX delisted SMCI options the same "
                       "day. Legacy option series kept trading on other "
                       "venues -- the chain cache holds files through "
                       "2019-04-18 inside this and the next segment; they "
                       "are quarantined (present_but_excluded), never "
                       "consumed, because the underlying was not "
                       "regular-way tradable"),
    },
    {
        "symbol": "SMCI",
        "start": "2019-03-22",
        "end": "2020-01-13",
        "kind": "delisted",
        "basis": "official",
        "source_urls": (
            "https://www.sec.gov/Archives/edgar/data/1375365/000135445719000123/primary_doc.xml",
            "https://www.sec.gov/Archives/edgar/data/1375365/000137536519000010/form8-k_20190311x301.htm",
            "https://www.sec.gov/litigation/admin/2020/33-10822.pdf",
        ),
        "provenance": ("Form 25-NSE filed by Nasdaq 2019-03-12; effective "
                       "ten days after filing per 17 CFR 240.12d2-2(b) -> "
                       "2019-03-22 (Inference from the two cited filings; "
                       "the rule, not a dated notice, fixes the day). SEC "
                       "settled order 33-10822: 'delisted from March 2019 "
                       "through January 2020'. Relisting approved "
                       "2020-01-08, trading recommenced 2020-01-14"),
    },
    {
        "symbol": "SMCI",
        "start": "2020-01-14",
        "end": "2020-05-04",
        "kind": "options_coverage_gap",
        "basis": "data_coverage",
        "source_urls": (
            "https://www.sec.gov/Archives/edgar/data/1375365/000137536520000004/form8-k20200109.htm",
        ),
        "provenance": ("equity relisted on Nasdaq 2020-01-14 (company 8-K) "
                       "but NO official notice establishes when listed "
                       "options resumed (every 2020 MIAX per-class listing "
                       "alert enumerated: no SMCI; OCC/Cboe 2020 archives "
                       "not reachable); chain cache resumes 2020-05-05. "
                       "Data-coverage limitation requiring an "
                       "owner-ratified scope amendment"),
    },
)


def excluded(symbol: str, iso_day: str,
             registry=H7_AUDIT_EXCEPTIONS) -> dict | None:
    """The registry entry covering (symbol, day), or None."""
    for entry in registry:
        if (entry["symbol"] == symbol
                and entry["start"] <= iso_day <= entry["end"]):
            return entry
    return None


def unratified_coverage_entries(registry=H7_AUDIT_EXCEPTIONS) -> tuple:
    """data_coverage entries with no owner-ratified amendment yet. The
    audit BLOCKS while this is non-empty: an exclusion the archive cannot
    prove is a scope question only the owner may settle (7b-2R finding 2)."""
    return tuple(e for e in registry
                 if e["basis"] == "data_coverage" and not e.get("ratified_by"))
