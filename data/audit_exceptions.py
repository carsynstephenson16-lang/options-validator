"""data/audit_exceptions.py -- REVIEWED exception registry for the H7
full-window data audit (7b-2 C2, owner decision 2026-07-10).

Every excluded symbol-session must trace to an entry here; the audit never
invents exclusions. Each entry carries provenance. Ranges are inclusive.
"""

from __future__ import annotations

H7_AUDIT_EXCEPTIONS = (
    {
        "symbol": "PLTR",
        "start": "2018-01-02",
        "end": "2020-10-05",
        "kind": "pre_listing",
        "provenance": ("PLTR direct listing 2020-09-30 (closes cache starts "
                       "2020-09-30); listed options begin 2020-10-06 (chain "
                       "cache first day, consistent with normal new-listing "
                       "option-class lead time)"),
    },
    {
        "symbol": "CEG",
        "start": "2018-01-02",
        "end": "2022-02-08",
        "kind": "pre_listing_and_options_inception",
        "provenance": ("CEG spun off from Exelon, first regular-way trade "
                       "2022-01-19 (closes cache starts 2022-01-19); listed "
                       "options begin 2022-02-09 (chain cache first day)"),
    },
    {
        "symbol": "SMCI",
        "start": "2018-08-23",
        "end": "2020-05-04",
        "kind": "suspension",
        "provenance": ("Nasdaq trading suspension / relisting window; ledger "
                       "H7_AMENDMENT_V1_1 2026-07-10: the 263 in-sample gap "
                       "days 2018-08-23..2020-05-04 are the real suspension, "
                       "skip-and-logged at backfill time"),
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
