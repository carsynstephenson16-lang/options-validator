"""options_researcher/portfolio.py -- H4 book tracker/analyzer.

The owner's forward paper window runs through this module: positions live in
data/positions/positions.csv, and analyze() marks them against the LATEST
cached chain day per symbol with the frozen conservative convention (long
legs liquidate at bid x (1 - haircut); short legs cost ask x (1 + haircut)
to close; both entry and exit commissions counted). It also enforces the H4
risk buckets and raises flags -- it never trades, never advises, and a
missing quote is reported loudly, never bridged.

Structures: leaps_call (long C, thesis bucket), csp (short P, csp bucket),
tactical_call (long C, tactical bucket).
"""
from __future__ import annotations

import csv
import os
from datetime import date

import pandas as pd

import config

POSITIONS_PATH = os.path.join("data", "positions", "positions.csv")
HOLDINGS_PATH = os.path.join("data", "positions", "holdings.csv")
_FIELDS = ["id", "structure", "symbol", "right", "strike", "expiration",
           "contracts", "entry_date", "entry_price", "bucket"]
_HOLDINGS_FIELDS = ["symbol", "shares", "cost_basis", "acquired"]
_STRUCTURES = {"leaps_call": ("C", "thesis", "long"),
               "csp": ("P", "csp", "short"),
               "tactical_call": ("C", "tactical", "long"),
               # H5 income engine: short calls, ALWAYS backed (check_coverage
               # makes a naked short call structurally impossible).
               "covered_call": ("C", "income", "short"),
               "pmcc_call": ("C", "income", "short")}


def load_positions(path: str = POSITIONS_PATH) -> pd.DataFrame:
    """Validated positions frame; empty frame if only the header exists.
    Fail-loud on malformed rows -- a silently-skipped position is a lie."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} missing -- seed it (header: "
                                f"{','.join(_FIELDS)})")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != _FIELDS:
            raise ValueError(f"{path}: header must be {_FIELDS}, "
                             f"got {reader.fieldnames}")
        rows = list(reader)
    frame = pd.DataFrame(rows, columns=_FIELDS)
    if frame.empty:
        return frame
    if frame["id"].duplicated().any():
        raise ValueError(f"{path}: duplicate position ids")
    for i, row in frame.iterrows():
        line = i + 2
        if row["structure"] not in _STRUCTURES:
            raise ValueError(f"{path}:{line}: structure {row['structure']!r} "
                             f"not in {sorted(_STRUCTURES)}")
        want_right, want_bucket, _ = _STRUCTURES[row["structure"]]
        if row["right"] != want_right:
            raise ValueError(f"{path}:{line}: {row['structure']} must have "
                             f"right={want_right}")
        if row["bucket"] != want_bucket:
            raise ValueError(f"{path}:{line}: {row['structure']} belongs to "
                             f"bucket {want_bucket!r}")
        date.fromisoformat(row["expiration"])
        date.fromisoformat(row["entry_date"])
    frame["strike"] = frame["strike"].astype(float)
    frame["contracts"] = frame["contracts"].astype(int)
    frame["entry_price"] = frame["entry_price"].astype(float)
    if (frame["contracts"] <= 0).any():
        raise ValueError(f"{path}: contracts must be positive")
    return frame


def load_holdings(path: str = HOLDINGS_PATH) -> pd.DataFrame:
    """Owner-declared 100-share lots backing covered calls. Fail-loud."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} missing -- seed it (header: "
                                f"{','.join(_HOLDINGS_FIELDS)})")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != _HOLDINGS_FIELDS:
            raise ValueError(f"{path}: header must be {_HOLDINGS_FIELDS}, "
                             f"got {reader.fieldnames}")
        frame = pd.DataFrame(list(reader), columns=_HOLDINGS_FIELDS)
    if frame.empty:
        return frame
    frame["shares"] = frame["shares"].astype(int)
    frame["cost_basis"] = frame["cost_basis"].astype(float)
    for _, r in frame.iterrows():
        date.fromisoformat(r["acquired"])
    if (frame["shares"] <= 0).any() or (frame["cost_basis"] <= 0).any():
        raise ValueError(f"{path}: shares and cost_basis must be positive")
    return frame


def check_coverage(frame: pd.DataFrame, holdings: pd.DataFrame) -> list[str]:
    """Short calls must be backed: covered_call by declared shares (100 per
    contract, strike >= that symbol's cost basis), pmcc_call by a live
    leaps_call on the same symbol with K_short >= K_leaps + entry_price
    (assignment then cannot lock a loss). Anything unbacked is an issue."""
    issues = []
    held = {r["symbol"]: r for _, r in holdings.iterrows()}
    for _, p in frame[frame["structure"] == "covered_call"].iterrows():
        lot = held.get(p["symbol"])
        need = 100 * int(p["contracts"])
        if lot is None or int(lot["shares"]) < need:
            issues.append(f"covered_call {p['id']} uncovered: need {need} "
                          f"shares of {p['symbol']} in holdings.csv")
        elif float(p["strike"]) < float(lot["cost_basis"]):
            issues.append(f"covered_call {p['id']} strike {p['strike']} "
                          f"below cost basis {lot['cost_basis']} -- H5 bans "
                          "locking in a sale at a loss")
    leaps = frame[frame["structure"] == "leaps_call"]
    for _, p in frame[frame["structure"] == "pmcc_call"].iterrows():
        ok = False
        for _, lp in leaps[leaps["symbol"] == p["symbol"]].iterrows():
            if float(p["strike"]) >= float(lp["strike"]) + float(lp["entry_price"]):
                ok = True
        if not ok:
            issues.append(f"pmcc_call {p['id']} fails the safety gate: "
                          "short strike must be >= LEAPS strike + premium "
                          "paid (else assignment can lock a loss)")
    return issues


def mark_position(row: pd.Series, chain: pd.DataFrame, close: float,
                  as_of: str, earnings: list[date]) -> dict:
    """Conservative mark + flags for one position on one chain day."""
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    right, _, side = _STRUCTURES[row["structure"]]
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    leg = chain[(chain["right"] == right)
                & (exp_dates == date.fromisoformat(row["expiration"]))
                & (chain["strike"] == row["strike"])
                & (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])]
    n = int(row["contracts"])
    out = {"id": row["id"], "structure": row["structure"],
           "symbol": row["symbol"], "strike": float(row["strike"]),
           "expiration": row["expiration"], "contracts": n,
           "dte": (date.fromisoformat(row["expiration"])
                   - date.fromisoformat(as_of)).days,
           "flags": []}
    if leg.empty:
        out.update({"mark": None, "pnl": None})
        out["flags"].append("QUOTE_MISSING")
    else:
        r0 = leg.iloc[0]
        if side == "long":
            liq = float(r0["bid"]) * (1 - h)
            pnl = (liq - float(row["entry_price"])) * 100.0 * n - 2 * comm * n
        else:
            cost = float(r0["ask"]) * (1 + h)
            pnl = (float(row["entry_price"]) - cost) * 100.0 * n - 2 * comm * n
            liq = cost
        out.update({"mark": round(liq, 4), "pnl": round(pnl, 2)})

    if row["structure"] == "leaps_call" and out["dte"] <= config.H4_THESIS_ROLL_DTE:
        out["flags"].append(f"ROLL_DUE(dte<={config.H4_THESIS_ROLL_DTE})")
    if row["structure"] == "csp" and close and \
            abs(close - float(row["strike"])) / float(row["strike"]) <= 0.02:
        out["flags"].append("ASSIGNMENT_WATCH(|close-K|<=2%)")
    horizon = date.fromisoformat(as_of)
    for e in earnings:
        if 0 <= (e - horizon).days <= 7:
            out["flags"].append(f"EARNINGS_{e.isoformat()}")
            break
    return out


def check_buckets(frame: pd.DataFrame) -> list[str]:
    """H4 bucket-rule violations (config-frozen caps)."""
    issues = []
    thesis = frame[frame["bucket"] == "thesis"]
    if len(thesis) > config.H4_THESIS_MAX_POSITIONS:
        issues.append(f"thesis positions {len(thesis)} > "
                      f"{config.H4_THESIS_MAX_POSITIONS}")
    prem = thesis["entry_price"] * 100 * thesis["contracts"]
    if prem.sum() > config.H4_THESIS_MAX_PREMIUM_TOTAL:
        issues.append(f"thesis premium ${prem.sum():,.0f} > "
                      f"${config.H4_THESIS_MAX_PREMIUM_TOTAL:,}")
    per = prem.groupby(thesis["symbol"]).sum()
    for sym, p in per.items():
        if p > config.H4_THESIS_MAX_PREMIUM_PER_NAME:
            issues.append(f"thesis premium {sym} ${p:,.0f} > "
                          f"${config.H4_THESIS_MAX_PREMIUM_PER_NAME:,}")
        if sym not in config.H4_THESIS_NAMES:
            issues.append(f"thesis name {sym} not in {config.H4_THESIS_NAMES}")
    csp = frame[frame["bucket"] == "csp"]
    if len(csp) > config.H4_CSP_MAX_POSITIONS:
        issues.append(f"csp positions {len(csp)} > {config.H4_CSP_MAX_POSITIONS}")
    for sym in csp["symbol"]:
        if sym not in config.H4_CSP_NAMES:
            issues.append(f"csp name {sym} not in {config.H4_CSP_NAMES}")
    tact = frame[frame["bucket"] == "tactical"]
    if len(tact) > config.H4_TACTICAL_MAX_OPEN:
        issues.append(f"tactical open {len(tact)} > {config.H4_TACTICAL_MAX_OPEN}")
    cost = tact["entry_price"] * 100 * tact["contracts"] \
        + 2 * config.COMMISSION_PER_CONTRACT * tact["contracts"]
    for pid, c in zip(tact["id"], cost):
        if c > config.MAX_LOSS_PER_TRADE:
            issues.append(f"tactical {pid} economic max loss ${c:,.0f} > "
                          f"${config.MAX_LOSS_PER_TRADE}")
    return issues


def analyze(path: str = POSITIONS_PATH) -> dict:
    import glob

    from data.underlying_closes import load_closes
    from options_researcher.earnings import load_earnings

    frame = load_positions(path)
    if frame.empty:
        print("book is empty -- add positions to", path)
        return {"marks": [], "bucket_issues": []}
    marks = []
    for sym in sorted(frame["symbol"].unique()):
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{sym}_*.parquet")))
        if not files:
            raise RuntimeError(f"no cached chains for {sym}")
        as_of = os.path.basename(files[-1]).split("_")[1].replace(".parquet", "")
        chain = pd.read_parquet(files[-1])
        closes = load_closes(sym, "2018-01-01", as_of, allow_oos=True)
        close = float(closes.iloc[-1]) if len(closes) else None
        earn = load_earnings(sym)
        for _, row in frame[frame["symbol"] == sym].iterrows():
            marks.append(mark_position(row, chain, close, as_of, earn))
    issues = check_buckets(frame)
    holdings = (load_holdings() if os.path.exists(HOLDINGS_PATH)
                else pd.DataFrame(columns=_HOLDINGS_FIELDS))
    coverage = check_coverage(frame, holdings)
    print(f"H5 book @ latest cache -- {len(marks)} position(s)")
    for m in marks:
        flags = " ".join(m["flags"]) or "-"
        pnl = "n/a" if m["pnl"] is None else f"${m['pnl']:,.0f}"
        print(f"  [{m['id']}] {m['structure']} {m['symbol']} "
              f"{m['strike']:.0f} exp {m['expiration']} (dte {m['dte']}) "
              f"x{m['contracts']}  pnl {pnl}  {flags}")
        if m["structure"] == "csp" and m["dte"] <= 0:
            print(f"    EXPIRED: if the close finished below {m['strike']:.0f}, "
                  f"add 100 sh/contract of {m['symbol']} @ {m['strike']:.0f} "
                  "to holdings.csv and remove this row; otherwise just "
                  "remove it (premium kept).")
    for issue in issues:
        print(f"  BUCKET BREACH: {issue}")
    for issue in coverage:
        print(f"  COVERAGE BREACH: {issue}")
    if not issues and not coverage:
        print("  buckets + coverage: all green")
    if coverage:
        raise RuntimeError("uncovered/mispriced short call in the book -- "
                           "fix positions.csv or holdings.csv before "
                           "trusting any number above")
    return {"marks": marks, "bucket_issues": issues,
            "coverage_issues": coverage}


if __name__ == "__main__":
    analyze()
