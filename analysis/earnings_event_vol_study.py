"""DESCRIPTIVE earnings-window option-behavior study (offline, read-only).

NOT a backtest: no entry/exit rule, no P&L, no win rate. Measures implied vs
realized moves, IV run-up/crush by tenor, contract price paths, spreads, decay.
Reads only local parquet caches + data/earnings/assertions_v2.csv.
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

# Run from the repo root: uv run python analysis/earnings_event_vol_study.py
sys.path.insert(0, os.getcwd())

from data.underlying_closes import load_closes  # noqa: E402  raw closes, aligned w/ strikes
from options_researcher.chains import is_monthly, load_range  # noqa: E402

NAMES = ["NVDA", "PLTR", "AMZN", "SMCI"]  # AMD/AVGO have no local historical dates
OFFSETS = [-15, -10, -5, -2, -1, 1, 3]
SHORT_BUCKET = (14, 30, 21)   # lo, hi, target
LONG_BUCKET = (45, 90, 60)
DELTA_LO, DELTA_HI = 0.30, 0.50
MIN_OI, MAX_SPREAD = 100, 0.10
MAX_ASK = 1000.0


def load_occurred(symbol: str) -> list[tuple[str, str]]:
    """(occurred_date_iso, session_timing) for status==occurred, sorted."""
    out = []
    with open("data/earnings/assertions_v2.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["symbol"] == symbol and row["status"] == "occurred" \
                    and row["occurred_date"].strip():
                st = (row["session_timing"] or "unknown").strip().lower()
                out.append((row["occurred_date"], st or "unknown"))
    out = sorted(set(out))
    return out


def sane(chain: pd.DataFrame) -> pd.DataFrame:
    return chain.loc[(chain["bid"] > 0) & (chain["ask"] >= chain["bid"])].copy()


def exp_dates(chain: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(chain["expiration"]).dt.date


def pick_bucket_exp(chain: pd.DataFrame, today: date, bucket) -> date | None:
    lo, hi, target = bucket
    eds = exp_dates(chain)
    dte = eds.map(lambda e: (e - today).days)
    inwin = sorted(set(eds[(dte >= lo) & (dte <= hi)]))
    if not inwin:
        return None
    return min(inwin, key=lambda e: abs((e - today).days - target))


def atm_iv(chain: pd.DataFrame, expiration: date, spot: float) -> float:
    """Mean of C and P iv at the strike nearest spot (iv>0 rows only)."""
    s = sane(chain)
    s = s.loc[(exp_dates(s) == expiration) & (s["iv"] > 0)]
    if s.empty:
        return float("nan")
    pos = int((s["strike"] - spot).abs().argmin())
    kstar = s.iloc[pos]["strike"]
    at = s.loc[s["strike"] == kstar]
    ivs = at["iv"].tolist()
    return float(np.mean(ivs)) if ivs else float("nan")


def atm_straddle_move(chain: pd.DataFrame, expiration: date, spot: float):
    """(straddle_mid/spot) at strike nearest spot; needs a C and a P."""
    s = sane(chain)
    s = s.loc[exp_dates(s) == expiration]
    if s.empty:
        return float("nan")
    pos = int((s["strike"] - spot).abs().argmin())
    kstar = s.iloc[pos]["strike"]
    c = s.loc[(s["strike"] == kstar) & (s["right"] == "C")]
    p = s.loc[(s["strike"] == kstar) & (s["right"] == "P")]
    if c.empty or p.empty:
        return float("nan")
    cmid = float((c["bid"].iloc[0] + c["ask"].iloc[0]) / 2)
    pmid = float((p["bid"].iloc[0] + p["ask"].iloc[0]) / 2)
    return (cmid + pmid) / spot


def first_exp_after(chain: pd.DataFrame, d: date) -> date | None:
    eds = sorted(set(e for e in exp_dates(chain) if e > d))
    return eds[0] if eds else None


def call_atm_row(chain: pd.DataFrame, expiration: date, spot: float):
    """Call on expiration with |delta| nearest 0.50 (for cost/IV proxy)."""
    s = sane(chain)
    s = s.loc[(exp_dates(s) == expiration) & (s["right"] == "C") & (s["iv"] > 0)]
    if s.empty:
        return None
    return s.loc[(s["delta"].abs() - 0.50).abs().idxmin()]


def h6_call_pick(chain: pd.DataFrame, today: date, bucket):
    """H6-style: nearest-monthly call in bucket, highest delta in [0.30,0.50],
    ask<=1000, OI>=100, spread<=10%. Returns row or None."""
    lo, hi, _ = bucket
    s = sane(chain)
    s = s.loc[s["right"] == "C"].copy()
    if s.empty:
        return None
    s["ed"] = exp_dates(s)
    s["dte"] = s["ed"].map(lambda e: (e - today).days)
    s = s.loc[(s["dte"] >= lo) & (s["dte"] <= hi)]
    # nearest monthly first (H6 uses monthlies); fall back to any if none
    monthlies = sorted(set(e for e in s["ed"] if is_monthly(e)))
    if monthlies:
        s = s.loc[s["ed"] == monthlies[0]]
    else:
        eds = sorted(set(s["ed"]))
        if not eds:
            return None
        s = s.loc[s["ed"] == eds[0]]
    s = s.loc[(s["delta"] >= DELTA_LO) & (s["delta"] <= DELTA_HI)
              & (s["ask"] <= MAX_ASK) & (s["open_interest"] >= MIN_OI)]
    mid = (s["bid"] + s["ask"]) / 2
    s = s.loc[((s["ask"] - s["bid"]) / mid) <= MAX_SPREAD]
    if s.empty:
        return None
    return s.loc[s["delta"].idxmax()]  # highest delta in band


def mid_of(chain: pd.DataFrame, expiration: date, strike: float, right: str):
    s = sane(chain)
    r = s.loc[(exp_dates(s) == expiration) & (s["strike"] == strike)
              & (s["right"] == right)]
    if r.empty:
        return None
    return float((r["bid"].iloc[0] + r["ask"].iloc[0]) / 2)


def halfspread_pct_of(chain, expiration, strike, right):
    s = sane(chain)
    r = s.loc[(exp_dates(s) == expiration) & (s["strike"] == strike)
              & (s["right"] == right)]
    if r.empty:
        return None
    b, a = float(r["bid"].iloc[0]), float(r["ask"].iloc[0])
    mid = (a + b) / 2
    return ((a - b) / 2) / mid if mid > 0 else None


def main():
    results = {}
    for sym in NAMES:
        closes = load_closes(sym, "2017-01-01", "2026-07-14", allow_oos=True)
        sessions: list[str] = list(closes.index)  # ISO strings, sorted
        spos = {d: i for i, d in enumerate(sessions)}
        chains = load_range(sym, "2018-01-01", "2026-07-14", allow_oos=True)
        events = load_occurred(sym)

        ev_rows = []          # implied vs realized
        tenor = {"short": {o: [] for o in OFFSETS}, "long": {o: [] for o in OFFSETS}}
        spread = {"short": [], "long": []}          # half-spread% at T-15..T-1
        decay = {"short": [], "long": []}            # daily %mid change pre-report
        traces = []                                   # recent-event contract paths
        gaps = []

        for ediso, timing in events:
            if ediso < sessions[0] or ediso > sessions[-1]:
                continue
            # anchor = last clean pre-report session (T-1)
            # AMC/unknown: announcement date itself; BMO: session before it
            # find session index of announcement date (or last session <= it)
            if ediso in spos:
                dpos = spos[ediso]
            else:
                prior = [d for d in sessions if d <= ediso]
                if not prior:
                    continue
                dpos = spos[prior[-1]]
            anchor = dpos - 1 if timing == "bmo" else dpos
            # need T-15..T+3 in range
            if anchor - 15 < 0 or anchor + 3 >= len(sessions):
                gaps.append(f"{ediso}: window out of session range")
                continue

            def sess(off):
                return sessions[anchor + (off if off < 0 else off)]
            # map offsets: T-1->anchor, T-2->anchor-1,... T+1->anchor+1, T+3->anchor+3
            def sess_off(off):
                idx = anchor + (off + 1 if off < 0 else off)
                return sessions[idx]

            # verify chain files present on needed sessions
            need = [sess_off(o) for o in OFFSETS]
            missing = [d for d in need if d not in chains]
            if missing:
                gaps.append(f"{ediso}: missing chains {missing}")
                continue

            tm1 = sess_off(-1)
            tp1 = sess_off(1)
            spot_m1 = float(closes.loc[tm1])
            spot_p1 = float(closes.loc[tp1])
            realized = abs(spot_p1 / spot_m1 - 1.0)

            # 1. implied move at T-1 using first expiry after event
            ch_m1 = chains[tm1]
            fe = first_exp_after(ch_m1, date.fromisoformat(ediso))
            implied = atm_straddle_move(ch_m1, fe, spot_m1) if fe else float("nan")
            ratio = realized / implied if implied and not np.isnan(implied) else float("nan")
            ev_rows.append(dict(event=ediso, timing=timing,
                                dte_frontexp=(fe - date.fromisoformat(tm1)).days if fe else None,
                                implied=implied, realized=realized, ratio=ratio,
                                pre2023=(ediso <= "2022-12-31")))

            # 2/3. tenor ATM IV at each offset
            for off in OFFSETS:
                d = sess_off(off)
                ch = chains[d]
                sp = float(closes.loc[d])
                today = date.fromisoformat(d)
                for label, bk in (("short", SHORT_BUCKET), ("long", LONG_BUCKET)):
                    exp = pick_bucket_exp(ch, today, bk)
                    iv = atm_iv(ch, exp, sp) if exp else float("nan")
                    tenor[label][off].append(iv)

            # 5. spreads at T-15..T-1 (pre-report obs dates)
            for off in (-15, -10, -5, -2, -1):
                d = sess_off(off)
                ch = chains[d]
                sp = float(closes.loc[d])
                today = date.fromisoformat(d)
                for label, bk in (("short", SHORT_BUCKET), ("long", LONG_BUCKET)):
                    exp = pick_bucket_exp(ch, today, bk)
                    if not exp:
                        continue
                    row = call_atm_row(ch, exp, sp)
                    if row is None:
                        continue
                    hs = halfspread_pct_of(ch, exp, float(row["strike"]), "C")
                    if hs is not None:
                        spread[label].append(hs)

            # 4 + 6. contract trace using H6 pick as of T-15 (both buckets)
            d15 = sess_off(-15)
            ch15 = chains[d15]
            today15 = date.fromisoformat(d15)
            trace_ev: dict[str, object] = dict(event=ediso, timing=timing,
                            pre2023=(ediso <= "2022-12-31"))
            for label, bk in (("long", LONG_BUCKET), ("short", SHORT_BUCKET)):
                pick = h6_call_pick(ch15, today15, bk)
                if pick is None:
                    trace_ev[label] = None
                    continue
                exp = date.fromisoformat(str(pd.to_datetime(pick["expiration"]).date()))
                K = float(pick["strike"])
                path = {}
                for off in OFFSETS:
                    d = sess_off(off)
                    ch = chains[d]
                    m = mid_of(ch, exp, K, "C")
                    # if expiry passed (short bucket may expire before T+3), None
                    if exp < date.fromisoformat(d):
                        m = None
                    path[off] = m
                trace_ev[label] = dict(exp=exp.isoformat(), strike=K,
                                       delta=float(pick["delta"]),
                                       dte0=(exp - today15).days,
                                       spot15=float(closes.loc[d15]),
                                       path=path)
                # decay: daily %mid change on pre-report sessions (T-15..T-2)
                pre = [-15, -10, -5, -2]
                # per-step normalized by sessions elapsed between sampled offsets
                steps = []
                for a, b in zip(pre[:-1], pre[1:]):
                    va, vb = path[a], path[b]
                    if va and vb and va > 0:
                        n = b - a  # sessions between samples
                        steps.append((vb / va) ** (1.0 / n) - 1.0)
                decay[label].extend(steps)
            traces.append(trace_ev)

        results[sym] = dict(ev_rows=ev_rows, tenor=tenor, spread=spread,
                            decay=decay, traces=traces, gaps=gaps,
                            n_events_total=len(events))
    return results


def fmt_pct(x, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{100*x:.{d}f}%"


def report(results):
    lines = []
    for sym in NAMES:
        R = results[sym]
        ev = R["ev_rows"]
        lines.append(f"\n{'='*70}\n{sym}  (covered events N={len(ev)} of {R['n_events_total']} occurred)\n{'='*70}")
        # implied vs realized
        lines.append("\n-- Implied vs Realized move (T-1 straddle/spot ; realized=|C(T+1)/C(T-1)-1|)")
        lines.append(f"{'event':11} {'tim':4} {'front_dte':9} {'implied':8} {'realized':8} {'r/i':6} {'era':5}")
        imp, rea, rat = [], [], []
        for r in ev:
            lines.append(f"{r['event']:11} {r['timing']:4} {str(r['dte_frontexp']):>9} "
                         f"{fmt_pct(r['implied']):>8} {fmt_pct(r['realized']):>8} "
                         f"{(f'{r['ratio']:.2f}' if r['ratio']==r['ratio'] else 'n/a'):>6} "
                         f"{'pre' if r['pre2023'] else 'post':>5}")
            if r["implied"] == r["implied"]:
                imp.append(r["implied"])
            if r["realized"] == r["realized"]:
                rea.append(r["realized"])
            if r["ratio"] == r["ratio"]:
                rat.append(r["ratio"])
        if imp:
            lines.append(f"  median implied={fmt_pct(np.median(imp))}  median realized={fmt_pct(np.median(rea))}  "
                         f"median realized/implied={np.median(rat):.2f}  (mean r/i={np.mean(rat):.2f})")
        # tenor IV
        lines.append("\n-- ATM IV by tenor at event offsets (mean across events)")
        lines.append(f"{'offset':7} {'short(14-30d)':14} {'long(45-90d)':14}")
        for off in OFFSETS:
            s = [x for x in R['tenor']['short'][off] if x==x]
            lo = [x for x in R["tenor"]["long"][off] if x == x]
            sm = fmt_pct(np.mean(s)) if s else "n/a"
            lm = fmt_pct(np.mean(lo)) if lo else "n/a"
            lines.append(f"T{off:+d}    {sm:>14} {lm:>14}")
        # run-up and crush summary
        def mean_at(bucket, off):
            v=[x for x in R['tenor'][bucket][off] if x==x]
            return np.mean(v) if v else float('nan')
        for bucket in ('short','long'):
            iv15, iv1, ivp1 = mean_at(bucket,-15), mean_at(bucket,-1), mean_at(bucket,1)
            runup = iv1-iv15
            crush = iv1-ivp1
            lines.append(f"  {bucket}: run-up T-15->T-1 = {fmt_pct(runup)} (abs IV pts); "
                         f"crush T-1->T+1 = {fmt_pct(crush)}  ({fmt_pct(crush/iv1) if iv1==iv1 and iv1 else 'n/a'} of T-1 level)")
        # spreads
        lines.append("\n-- Median half-spread %% of mid (ATM ~0.5-delta call), T-15..T-1")
        for bucket in ('short','long'):
            v=R['spread'][bucket]
            lines.append(f"  {bucket}: median={fmt_pct(np.median(v)) if v else 'n/a'} "
                         f"(N={len(v)} obs)")
        # decay
        lines.append("\n-- Per-session mid decay (CONFOUNDED by spot), pre-report T-15..T-2")
        for bucket in ('short','long'):
            v=R['decay'][bucket]
            lines.append(f"  {bucket}: median daily %mid change={fmt_pct(np.median(v),2) if v else 'n/a'} "
                         f"(N={len(v)} steps)")
        # traces: last 3 events
        lines.append("\n-- Contract price path (H6 call pick as of T-15; raw mid $); last 3 covered events")
        for tr in R['traces'][-3:]:
            lines.append(f"  event {tr['event']} ({tr['timing']}, {'pre2023' if tr['pre2023'] else 'post2023'}):")
            for bucket in ('long','short'):
                t=tr[bucket]
                if t is None:
                    lines.append(f"    {bucket}: no H6-qualifying call at T-15")
                    continue
                p=t['path']
                pathstr=" ".join(f"T{o:+d}={('%.2f'%p[o]) if p[o] is not None else 'exp/na'}" for o in OFFSETS)
                lines.append(f"    {bucket}: K={t['strike']} exp={t['exp']} dte0={t['dte0']} "
                             f"delta={t['delta']:.2f} spot15={t['spot15']:.2f}")
                lines.append(f"      mid: {pathstr}")
        # gaps
        if R['gaps']:
            lines.append(f"\n-- Skipped/gaps ({len(R['gaps'])}): " + "; ".join(R['gaps'][:8]))
    return "\n".join(lines)


if __name__ == "__main__":
    res = main()
    txt = report(res)
    print(txt)
    with open("/private/tmp/claude-501/-Users-carsynstephenson-options-validator/31729b33-d047-4c74-95b6-bd5ffd5600ac/scratchpad/earnings_report.txt", "w") as f:
        f.write(txt)
