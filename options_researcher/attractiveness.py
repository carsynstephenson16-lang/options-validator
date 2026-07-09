"""options_researcher/attractiveness.py -- which options look attractive?

Beginner-first cards for the three H5 roles (sell a put / sell a covered
call / buy a LEAPS), graded GREEN/AMBER/RED against the FROZEN H5_*
thresholds in config (anchored to Studies C/E; see config comments).
READ-ONLY: never trades, never writes. Every card states the promise in
dollars and ends with honesty lines, including Study A's: options that pay
more are pricing MORE REAL RISK, not free money. Attractiveness measures
price-vs-cushion-vs-liquidity today -- it does not predict the future.
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity
from options_researcher.chains import nearest_monthly

DELTA_BAND = config.H5_INCOME_DELTA_BAND
N_CANDIDATES = 3


def grade(value: float, green: float, amber: float, *,
          higher_is_better: bool = True) -> str:
    if higher_is_better:
        return "GREEN" if value >= green else ("AMBER" if value >= amber
                                               else "RED")
    return "GREEN" if value <= green else ("AMBER" if value <= amber
                                           else "RED")


def _expiry_rows(chain: pd.DataFrame, day: str, right: str,
                 exp: date | None = None) -> pd.DataFrame:
    today = date.fromisoformat(day)
    if exp is None:
        exp = nearest_monthly(chain, today)
    if exp is None:
        return pd.DataFrame()
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    rows = chain[(chain["right"] == right) & (exp_dates == exp)
                 & (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])].copy()
    rows["exp_date"] = exp
    rows["dte"] = (exp - today).days
    return rows


def _vol_prose(r) -> tuple[float | None, float | None, str]:
    """Return (vega, iv, sentence) for card verdicts; skip on missing/NaN."""
    if not (pd.notna(r.get("vega")) and pd.notna(r.get("iv"))):
        return None, None, ""
    vega = float(r["vega"])
    contract_iv = float(r["iv"])
    sentence = (
        f"this contract's own implied vol is {contract_iv:.0%}; if "
        f"implied vol drops 1 point the option loses ~${vega:,.0f} "
        f"(vega), on top of time decay; "
    )
    return vega, contract_iv, sentence


def _vrp_seller_grade(iv_minus_rv: float) -> str:
    """VRP PROXY, descriptive only. GREEN when front-month implied (atm_iv,
    forward-looking) sits at/above trailing 21d realized (iv_minus_rv >= 0);
    AMBER otherwise. NOT a true variance risk premium: trailing realized is
    not realized over the option's own cycle, and the tenors only roughly
    match. Surfaces premium richness vs recent realized -- which IV-rank
    (IV vs its own history) cannot see -- but never forecasts future vol."""
    return "GREEN" if iv_minus_rv >= config.H5_VRP_SELL_GREEN else "AMBER"


def put_card_rows(symbol: str, chain: pd.DataFrame, day: str, *,
                  close: float, rv21: float, iv_rank: float,
                  iv_minus_rv: float,
                  earnings_in_cycle: bool,
                  fomc_in_cycle: bool,
                  exp: date | None = None) -> list[dict]:
    """SELL-A-PUT candidates near the H5 income delta."""
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    puts = _expiry_rows(chain, day, "P", exp)
    if puts.empty:
        return []
    puts["dist"] = (puts["delta"].abs() - config.H5_INCOME_DELTA).abs()
    puts = puts[puts["dist"] <= DELTA_BAND].nsmallest(N_CANDIDATES, "dist")
    monthly_move = rv21 / math.sqrt(12.0) if rv21 and rv21 > 0 else float("nan")
    out = []
    for _, r in puts.iterrows():
        k = float(r["strike"])
        credit = float(r["bid"]) * (1 - h) * 100 - comm
        yield_mo = credit / (100.0 * k)
        otm = (close - k) / close
        cushion = otm / monthly_move if monthly_move == monthly_move else float("nan")
        grades = {
            "yield": grade(yield_mo, config.H5_PUT_YIELD_GREEN,
                           config.H5_PUT_YIELD_AMBER),
            "cushion": grade(cushion, config.H5_CUSHION_GREEN,
                             config.H5_CUSHION_AMBER),
            "iv_for_seller": ("GREEN" if iv_rank >= config.H5_IVR_SELL_GREEN
                              else "AMBER"),
            "vrp_for_seller": _vrp_seller_grade(iv_minus_rv),
            "earnings": "AMBER" if earnings_in_cycle else "GREEN",
            "fomc": "AMBER" if fomc_in_cycle else "GREEN",
            "liquidity": ("GREEN" if passes_liquidity(
                r["open_interest"], r["bid"], r["ask"]) else "RED"),
        }
        verdict = (f"you'd be promising to buy 100 sh of {symbol} at "
                   f"${k:.0f} (${k * 100:,.0f} set aside); pays "
                   f"${credit:,.0f} now = {100 * yield_mo:.2f}%/mo "
                   f"(~{100 * yield_mo * 12:.0f}%/yr); the stock is "
                   f"{100 * otm:.1f}% above your promise level and its "
                   f"typical monthly wiggle is {100 * monthly_move:.1f}%.")
        out.append({"strike": k, "expiry": r["exp_date"].isoformat(),
                    "dte": int(r["dte"]), "credit": credit,
                    "yield_mo": yield_mo, "cushion": cushion,
                    "annualized_yield": yield_mo * 365.0 / max(int(r["dte"]), 1),
                    "grades": grades, "verdict": verdict})
    return out


def cc_card_rows(symbol: str, chain: pd.DataFrame, day: str, *,
                 close: float, cost_basis: float, iv_rank: float,
                 iv_minus_rv: float,
                 earnings_in_cycle: bool,
                 fomc_in_cycle: bool,
                 exp: date | None = None) -> list[dict]:
    """SELL-A-COVERED-CALL candidates (against a declared 100-share lot)."""
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    calls = _expiry_rows(chain, day, "C", exp)
    if calls.empty:
        return []
    calls["dist"] = (calls["delta"].abs() - config.H5_INCOME_DELTA).abs()
    calls = calls[calls["dist"] <= DELTA_BAND].nsmallest(N_CANDIDATES, "dist")
    out = []
    for _, r in calls.iterrows():
        k = float(r["strike"])
        if k < cost_basis:
            out.append({"strike": k, "skipped":
                        f"strike ${k:.0f} sits BELOW your cost basis "
                        f"(${cost_basis:.2f}) -- H5 never locks in selling "
                        "your shares at a loss; no covered call this cycle "
                        "at this delta."})
            continue
        credit = float(r["bid"]) * (1 - h) * 100 - comm
        yield_mo = credit / (100.0 * close)
        upside = (k - close) / close
        grades = {
            "yield": grade(yield_mo, config.H5_CC_YIELD_GREEN,
                           config.H5_CC_YIELD_AMBER),
            "upside_room": ("GREEN" if upside >= config.H5_CC_UPSIDE_GREEN
                            else "AMBER"),
            "iv_for_seller": ("GREEN" if iv_rank >= config.H5_IVR_SELL_GREEN
                              else "AMBER"),
            "vrp_for_seller": _vrp_seller_grade(iv_minus_rv),
            "earnings": "AMBER" if earnings_in_cycle else "GREEN",
            "fomc": "AMBER" if fomc_in_cycle else "GREEN",
            "liquidity": ("GREEN" if passes_liquidity(
                r["open_interest"], r["bid"], r["ask"]) else "RED"),
        }
        verdict = (f"rents out your 100 sh for ${credit:,.0f} "
                   f"({100 * yield_mo:.2f}%/mo of today's value); if "
                   f"{symbol} finishes above ${k:.0f} you sell at "
                   f"${k * 100:,.0f} = {100 * (k / close - 1):+.1f}% vs today "
                   f"({100 * (k / cost_basis - 1):+.1f}% vs your cost) -- "
                   "that's the plan working, not a loss.")
        out.append({"strike": k, "expiry": r["exp_date"].isoformat(),
                    "dte": int(r["dte"]), "credit": credit,
                    "yield_mo": yield_mo, "upside": upside,
                    "annualized_yield": yield_mo * 365.0 / max(int(r["dte"]), 1),
                    "grades": grades, "verdict": verdict})
    return out


def pmcc_card_rows(symbol: str, chain: pd.DataFrame, day: str, *,
                   leaps_strike: float, leaps_premium: float, close: float,
                   iv_rank: float, iv_minus_rv: float,
                   earnings_in_cycle: bool,
                   fomc_in_cycle: bool,
                   exp: date | None = None) -> list[dict]:
    """SELL-A-CALL-AGAINST-YOUR-LEAPS (poor man's covered call) candidates.

    HARD safety gate: only strikes >= leaps_strike + leaps_premium are shown,
    because at/above that floor an assignment can be covered by exercising the
    LEAPS WITHOUT locking a loss (you keep the call credit on top). Yield is
    measured against the LEAPS premium actually deployed, not 100x stock.
    """
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    safety_strike = leaps_strike + leaps_premium
    calls = _expiry_rows(chain, day, "C", exp)
    if calls.empty:
        return []
    safe = calls[calls["strike"] >= safety_strike].copy()
    if safe.empty:
        return []
    safe["dist"] = (safe["delta"].abs() - config.H5_INCOME_DELTA).abs()
    safe = safe.nsmallest(N_CANDIDATES, "dist")
    leaps_cost = leaps_premium * 100.0
    out = []
    for _, r in safe.iterrows():
        k = float(r["strike"])
        credit = float(r["bid"]) * (1 - h) * 100 - comm
        yield_mo = credit / leaps_cost
        grades = {
            "yield": grade(yield_mo, config.H5_CC_YIELD_GREEN,
                           config.H5_CC_YIELD_AMBER),
            "safety": "GREEN",   # by construction: only safe strikes reach here
            "iv_for_seller": ("GREEN" if iv_rank >= config.H5_IVR_SELL_GREEN
                              else "AMBER"),
            "vrp_for_seller": _vrp_seller_grade(iv_minus_rv),
            "earnings": "AMBER" if earnings_in_cycle else "GREEN",
            "fomc": "AMBER" if fomc_in_cycle else "GREEN",
            "liquidity": ("GREEN" if passes_liquidity(
                r["open_interest"], r["bid"], r["ask"]) else "RED"),
        }
        verdict = (f"sells a ${k:.0f} call for ${credit:,.0f} against your "
                   f"{symbol} LEAPS; SAFE because ${k:.0f} >= LEAPS strike "
                   f"${leaps_strike:.0f} + premium ${leaps_premium:.2f} = "
                   f"${safety_strike:.2f}, so assignment can't lock a loss; "
                   f"income {100 * yield_mo:.2f}%/mo on the ${leaps_cost:,.0f} "
                   "you put into the LEAPS.")
        out.append({"strike": k, "expiry": r["exp_date"].isoformat(),
                    "dte": int(r["dte"]), "credit": credit,
                    "yield_mo": yield_mo,
                    "annualized_yield": yield_mo * 365.0 / max(int(r["dte"]), 1),
                    "grades": grades, "verdict": verdict})
    return out


def leaps_card_rows(symbol: str, chain: pd.DataFrame, day: str, *,
                    close: float, iv_rank: float,
                    bucket_room: float) -> list[dict]:
    """BUY-A-LEAPS candidates (H4/H5 thesis rules)."""
    from options_researcher.studies.long_call_carry import _leaps_candidate

    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    r = _leaps_candidate(chain, date.fromisoformat(day),
                         config.H4_THESIS_DELTA)
    if r is None:
        return []
    k = float(r["strike"])
    cost = float(r["ask"]) * (1 + h) * 100 + comm
    breakeven = k + cost / 100.0
    dte = int(r["dte"])
    extrinsic = max(0.0, cost / 100.0 - max(0.0, close - k))
    vega, contract_iv, vol_sentence = _vol_prose(r)
    grades = {
        "fits_bucket": "GREEN" if cost <= bucket_room else "RED",
        "iv_for_buyer": grade(iv_rank, config.H5_IVR_BUY_GREEN,
                              config.H5_IVR_BUY_RED,
                              higher_is_better=False),
        "liquidity": ("GREEN" if passes_liquidity(
            r["open_interest"], r["bid"], r["ask"]) else "RED"),
    }
    verdict = (f"${cost:,.0f} buys ~{abs(float(r['delta'])):.0%} of the "
               f"upside of 100 sh (${close * 100:,.0f} worth) until "
               f"{r['exp_date']}; breakeven ${breakeven:,.0f} "
               f"({100 * (breakeven / close - 1):+.1f}% move needed); time "
               f"decay costs ~${extrinsic * 100 / max(dte, 1):,.2f}/day if "
               f"the stock goes nowhere; {vol_sentence}"
               "max loss = what you paid, ever.")
    return [{"strike": k, "expiry": r["exp_date"].isoformat(), "dte": dte,
             "cost": cost, "breakeven": breakeven, "grades": grades,
             "verdict": verdict, "vega": vega, "iv": contract_iv}]


def long_call_card_rows(symbol: str, chain: pd.DataFrame, day: str, *,
                        close: float, iv_rank: float,
                        exp: date | None = None) -> list[dict]:
    """BUY-A-SHORT-DATED-CALL candidates (TACTICAL lane, H4_TACTICAL_DELTA on
    the nearest monthly). A long call's max loss IS its premium, so fits_cap
    grades cost against MAX_LOSS_PER_TRADE. iv_for_buyer prefers LOW IV-rank.
    Descriptive scanner preview -- NOT an H5 income lane, never sized/tracked."""
    h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
    calls = _expiry_rows(chain, day, "C", exp)
    if calls.empty:
        return []
    calls["dist"] = (calls["delta"].abs() - config.H4_TACTICAL_DELTA).abs()
    calls = calls[calls["dist"] <= DELTA_BAND].nsmallest(N_CANDIDATES, "dist")
    out = []
    for _, r in calls.iterrows():
        k = float(r["strike"])
        cost = float(r["ask"]) * (1 + h) * 100 + comm
        breakeven = k + cost / 100.0
        dte = int(r["dte"])
        extrinsic = max(0.0, cost / 100.0 - max(0.0, close - k))
        vega, contract_iv, vol_sentence = _vol_prose(r)
        grades = {
            "fits_cap": "GREEN" if cost <= config.MAX_LOSS_PER_TRADE else "RED",
            "iv_for_buyer": grade(iv_rank, config.H5_IVR_BUY_GREEN,
                                  config.H5_IVR_BUY_RED, higher_is_better=False),
            "liquidity": ("GREEN" if passes_liquidity(
                r["open_interest"], r["bid"], r["ask"]) else "RED"),
        }
        verdict = (f"${cost:,.0f} buys ~{abs(float(r['delta'])):.0%} of the "
                   f"upside of 100 sh of {symbol} until {r['exp_date']} "
                   f"({dte} days); breakeven ${breakeven:,.2f} "
                   f"({100 * (breakeven / close - 1):+.1f}% move needed); time "
                   f"decay ~${extrinsic * 100 / max(dte, 1):,.2f}/day if the "
                   f"stock goes nowhere; {vol_sentence}"
                   f"max loss = ${cost:,.0f} (the premium), "
                   "ever. TACTICAL preview, not an H5 income lane.")
        out.append({"strike": k, "expiry": r["exp_date"].isoformat(),
                    "dte": dte, "cost": cost, "breakeven": breakeven,
                    "breakeven_move": breakeven / close - 1.0,
                    "cost_per_delta": cost / (100.0 * abs(float(r["delta"]))),
                    "grades": grades, "verdict": verdict,
                    "vega": vega, "iv": contract_iv})
    return out


STUDY_A_LINE = ("  honesty: this name's options pay above their own median "
                "right now -- Study A measured that extra pay comes with "
                "extra REAL movement, not free money.")


def main():
    import glob
    import os

    from data.underlying_closes import load_closes
    from options_researcher.earnings import load_earnings
    from options_researcher.features import load_features
    from options_researcher.fomc import load_fomc
    from options_researcher.portfolio import HOLDINGS_PATH, load_holdings, load_positions

    holdings = (load_holdings() if os.path.exists(HOLDINGS_PATH)
                else pd.DataFrame(columns=["symbol", "shares", "cost_basis"]))
    positions = load_positions()
    thesis_used = 0.0
    held_leaps = {}   # symbol -> (strike, entry_price) of a held LEAPS
    if not positions.empty:
        t = positions[positions["bucket"] == "thesis"]
        thesis_used = float((t["entry_price"] * 100 * t["contracts"]).sum())
        for _, lp in positions[positions["structure"] == "leaps_call"].iterrows():
            held_leaps.setdefault(lp["symbol"],
                                  (float(lp["strike"]), float(lp["entry_price"])))
    bucket_room = config.H4_THESIS_MAX_PREMIUM_TOTAL - thesis_used

    print("WHICH OPTIONS LOOK ATTRACTIVE TODAY? (frozen H5 rubric; "
          "attractiveness = price vs cushion vs liquidity, NOT prediction)")
    for symbol in config.UNIVERSE:
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{symbol}_*.parquet")))
        if not files:
            print(f"\n{symbol}: no cached chains")
            continue
        day = os.path.basename(files[-1]).split("_")[1].replace(".parquet", "")
        chain = pd.read_parquet(files[-1])
        feats = load_features(symbol)
        row = feats.iloc[-1]
        close = float(load_closes(symbol, "2018-01-01", day,
                                  allow_oos=True).iloc[-1])
        rv21 = float(row["rv21"])
        iv_rank = float(row["iv_rank"]) if pd.notna(row["iv_rank"]) else 0.0
        iv_minus_rv = (float(row["iv_minus_rv"])
                       if pd.notna(row["iv_minus_rv"]) else 0.0)
        exp = nearest_monthly(chain, date.fromisoformat(day))
        earn_in_cycle = False
        if exp is not None:
            earn_in_cycle = any(date.fromisoformat(day) < e <= exp
                                for e in load_earnings(symbol))
        fomc_in_cycle = False
        if exp is not None:
            fomc_in_cycle = any(date.fromisoformat(day) < m <= exp
                                for m in load_fomc())
        print(f"\n=== {symbol} @ {day}  close ${close:,.2f}  "
              f"IV-rank {iv_rank:.2f} ===")
        print("-- SELL A PUT? (promise to buy 100 sh lower)")
        rows = put_card_rows(symbol, chain, day, close=close, rv21=rv21,
                             iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                             earnings_in_cycle=earn_in_cycle,
                             fomc_in_cycle=fomc_in_cycle)
        for c in rows or []:
            badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
            print(f"  ${c['strike']:.0f} {c['expiry']}: {c['verdict']}")
            print(f"    [{badges}]")
            if c["grades"]["iv_for_seller"] == "GREEN":
                print(STUDY_A_LINE)
        if not rows:
            print("  no candidates near the target delta this cycle")
        lot = holdings[holdings["symbol"] == symbol] if len(holdings) else []
        held_shares = int(lot.iloc[0]["shares"]) if len(lot) else 0
        if held_shares >= 100:
            print("-- SELL A COVERED CALL? (rent out shares you hold)")
            for c in cc_card_rows(symbol, chain, day, close=close,
                                  cost_basis=float(lot.iloc[0]["cost_basis"]),
                                  iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                                  earnings_in_cycle=earn_in_cycle,
                                  fomc_in_cycle=fomc_in_cycle):
                if "skipped" in c:
                    print(f"  ${c['strike']:.0f}: {c['skipped']}")
                    continue
                badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
                print(f"  ${c['strike']:.0f} {c['expiry']}: {c['verdict']}")
                print(f"    [{badges}]")
        elif held_shares > 0:
            print(f"-- COVERED CALL: you hold {held_shares} sh of {symbol} -- "
                  "a covered call needs 100 per contract. The scanner will "
                  "only show covered calls after a declared 100-share lot, "
                  "and PMCC rows only after a real LEAPS is recorded.")
        if symbol in held_leaps:
            k_leaps, prem_leaps = held_leaps[symbol]
            print(f"-- SELL A CALL AGAINST YOUR LEAPS? (PMCC; LEAPS ${k_leaps:.0f} "
                  f"cost ${prem_leaps:.2f})")
            pmcc = pmcc_card_rows(symbol, chain, day, leaps_strike=k_leaps,
                                  leaps_premium=prem_leaps, close=close,
                                  iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                                  earnings_in_cycle=earn_in_cycle,
                                  fomc_in_cycle=fomc_in_cycle)
            for c in pmcc:
                badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
                print(f"  ${c['strike']:.0f} {c['expiry']}: {c['verdict']}")
                print(f"    [{badges}]")
            if not pmcc:
                print(f"  no SAFE strike this cycle: the rule needs a call at "
                      f"${k_leaps + prem_leaps:.2f}+ and none is listed / all "
                      "too far out to pay -- selling closer would risk locking "
                      "a loss, so H5 shows nothing.")
        if symbol in config.H4_THESIS_NAMES:
            print(f"-- BUY A LEAPS? (bucket room ${bucket_room:,.0f})")
            for c in leaps_card_rows(symbol, chain, day, close=close,
                                     iv_rank=iv_rank,
                                     bucket_room=bucket_room):
                badges = " ".join(f"{k}:{v}" for k, v in c["grades"].items())
                print(f"  ${c['strike']:.0f} {c['expiry']}: {c['verdict']}")
                print(f"    [{badges}]")


if __name__ == "__main__":
    import sys
    if "--json" in sys.argv:
        from options_researcher.attractiveness_dashboard import sections_json
        print(sections_json())
    else:
        main()
