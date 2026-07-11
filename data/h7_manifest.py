"""data/h7_manifest.py -- THE canonical eligible-session manifest for the
H7 diagnostic (7b-2R, review finding 2).

Before 7b-2R the audit and the runner enumerated sessions independently:
the audit excluded 426 SMCI sessions while the runner's cache scan could
still load the 163 chain parquets that exist inside that interval (legacy
option series kept trading until the April 2019 expiration after the
2018-08-23 equity suspension), so unaudited data could have produced
trades. This module is now the ONE enumeration both sides consume:

  * tools/h7_data_audit.py audits exactly these (symbol, session) pairs and
    binds the manifest into the receipt;
  * harness/run_h7_backtest.py loads ONLY chain files eligible here;
    present-but-excluded and unexpected files are reported and quarantined,
    never consumed.

Nothing here reads what happens to be on disk to DECIDE eligibility; disk
contents are only CLASSIFIED against the manifest (classify_cache).
"""

from __future__ import annotations

import re
from pathlib import Path

import config
from data.audit_exceptions import excluded

# tolerant on case so a case-variant file collides into one identity and is
# reported as a duplicate instead of silently coexisting
_FILE_RE = re.compile(
    r"^(?P<sym>[A-Za-z0-9.\-]+)_(?P<day>\d{4}-\d{2}-\d{2})\.parquet$")


def eligible_manifest(symbols=None, start=None, end=None, *,
                      sessions=None, registry=None) -> dict:
    """{symbol: {"eligible": [...], "excluded": {day: kind}}}, enumerated
    from the XNYS calendar and the reviewed exception registry."""
    from data.cache_runner import trading_days
    symbols = list(symbols or config.H7_BACKTEST_SYMBOLS)
    start = start or config.H7_BACKTEST_START
    end = end or config.H7_BACKTEST_END
    sessions = (list(sessions) if sessions is not None
                else trading_days(start, end))
    out: dict = {}
    for sym in symbols:
        elig: list[str] = []
        exc: dict[str, str] = {}
        for day in sessions:
            entry = (excluded(sym, day) if registry is None
                     else excluded(sym, day, registry=registry))
            if entry is None:
                elig.append(day)
            else:
                exc[day] = entry["kind"]
        out[sym] = {"eligible": elig, "excluded": exc}
    return out


def eligible_days(manifest: dict, symbol: str) -> set[str]:
    return set(manifest[symbol]["eligible"])


def classify_cache(manifest: dict, chain_dir, *, names=None) -> dict:
    """Account for EVERY chain-cache file belonging to a manifested symbol.

    Returns sorted identity lists (never bare counts -- the receipt binds
    identities):
      present               eligible session, file on disk
      missing               eligible session, no file
      present_but_excluded  excluded session, file on disk (QUARANTINED:
                            reported here, refused by the runner)
      unexpected            file for a manifested symbol on a day outside
                            the manifest domain (out-of-window or
                            non-session date)
      duplicates            distinct filenames normalizing to one
                            (symbol, day) identity
    """
    if names is None:  # `names` is injectable for filesystem-free tests
        names = [p.name for p in Path(chain_dir).iterdir()]
    on_disk: dict[tuple[str, str], list[str]] = {}
    for name in names:
        m = _FILE_RE.match(name)
        if m is None:
            continue
        sym = m.group("sym").upper()
        if sym in manifest:
            on_disk.setdefault((sym, m.group("day")), []).append(name)

    out: dict[str, list[str]] = {"present": [], "missing": [],
                                 "present_but_excluded": [],
                                 "unexpected": [], "duplicates": []}
    for sym, m in manifest.items():
        for day in m["eligible"]:
            key = "present" if (sym, day) in on_disk else "missing"
            out[key].append(f"{sym}_{day}")
    for (sym, day), names in on_disk.items():
        if len(names) > 1:
            out["duplicates"].append(f"{sym}_{day}")
        if day in manifest[sym]["excluded"]:
            out["present_but_excluded"].append(f"{sym}_{day}")
        elif day not in set(manifest[sym]["eligible"]):
            out["unexpected"].append(f"{sym}_{day}")
    return {k: sorted(v) for k, v in out.items()}
