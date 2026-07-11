"""tools/h7_data_audit.py -- formal, content-addressed, fail-closed audit of
the full H7 backtest window. Version 2 (7b-2R, owner review 2026-07-11).

v1 (receipt.json, verdict BLOCK) is retained as a historical artifact and is
INELIGIBLE to authorize any run. v2 corrects its review findings:

  * ONE manifest: the audit consumes data.h7_manifest (the same enumeration
    the runner loads by); every cache file is accounted by identity --
    present / missing / present_but_excluded (quarantined) / unexpected /
    duplicate.
  * NO mtime fallback. EOD fetch provenance is tiered:
      - ledger_fact:      a BLIND_CACHE fact carries the fetch timestamp AND
                          sha256; the sha must match the file (mismatch
                          BLOCKS) and the timestamp must be post-close.
      - legacy_manifest:  no fact, but the exact sha appears in the
                          pre-existing tracked chain manifest
                          (data/chain_cache_manifest.txt), the session
                          predates that manifest's construction, and the
                          producing adapter is shown to use
                          option_history_greeks_eod. Recorded under the
                          owner-ratified legacy provenance assumption
                          (LEGACY_PROVENANCE_ASSUMPTION).
      - unproven:         anything else -> BLOCK, by identity.
  * Earnings UNKNOWN is split (owner decision H7_7B2R_DECISIONS):
      - proven_unknown: the session falls inside a declared source-complete
        coverage period (data/earnings/coverage.json) yet no schedule was
        public -- the trading gate stays UNKNOWN and the session is LOGGED,
        but the audit does not block;
      - data_gap: no coverage declaration -> the archive cannot prove what
        was known -> BLOCK.
  * data_coverage registry exclusions without an owner-ratified amendment
    BLOCK by identity (unratified_coverage_exclusions).
  * missing_puts is lane-aware: H7_CORE_LONG_ONLY names never trade puts
    (H7c-ineligible), so their missing-put days are recorded as
    inapplicable identities, not generic warns.
  * The receipt binds EVERY verdict input: eligible manifest + exclusions,
    every chain sha, quarantined/unexpected file shas, raw underlying-close
    file shas, earnings store + coverage shas, the fetch-provenance map
    hash, session-calendar identity + generated-session hash, the exception
    registry hash, audit + diagnostic source hashes/versions, config and
    cost-model hashes, and complete machine-readable findings.
    --verify RECOMPUTES each of these against the current repo state:
    mutating any bound input fails verification.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import subprocess
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from data.audit_exceptions import (
    H7_AUDIT_EXCEPTIONS,
    unratified_coverage_entries,
)
from data.h7_manifest import classify_cache, eligible_manifest
from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    canonical_json,
    config_hash,
    cost_model_hash,
    diagnostic_source_hash,
    sha256_file,
    sha256_hex,
)

AUDIT_VERSION = "h7-data-audit/2"
CHAIN_DIR = Path(".cache/chains")
CLOSES_DIR = Path(".cache/underlying")
FACTS_PATH = Path("ledger/facts.log")
TRACKED_MANIFEST_PATH = Path("data/chain_cache_manifest.txt")
COVERAGE_PATH = Path("data/earnings/coverage.json")
RECEIPT_PATH = Path("reports/h7_audit/receipt_v2.json")
V1_RECEIPT_PATH = Path("reports/h7_audit/receipt.json")   # historical, blocked
CHAIN_COLUMNS = ["expiration", "strike", "right", "bid", "ask",
                 "open_interest", "iv", "delta", "gamma", "theta", "vega"]
NY = ZoneInfo("America/New_York")
_BLIND_RE = re.compile(
    r"^(\S+)\tBLIND_CACHE symbol=(\S+) date=(\S+) rows=\S+ sha256=(\S+)")
ADAPTER_ENDPOINT = "option_history_greeks_eod"

LEGACY_PROVENANCE_ASSUMPTION = (
    "Owner-ratified 2026-07-11 (7b-2R): chain files fetched before "
    "BLIND_CACHE facts carried sha256 are accepted as EOD provenance ONLY "
    "when their exact sha appears in the pre-existing tracked chain "
    "manifest, their session predates that manifest's construction, and "
    "the producing adapter is shown to use option_history_greeks_eod. "
    "This is an assumption, not a proof; it is disclosed in every receipt."
)

# big receipt sections carried verbatim but bound through their own
# sub-hash (receipt_hash covers the sub-hash, verify recomputes both)
_BULK_KEYS = ("file_hashes", "quarantined_file_hashes", "provenance_map")


def expected_manifest(symbols=None, start=None, end=None, sessions=None,
                      registry=None) -> dict:
    """Back-compat shim over data.h7_manifest.eligible_manifest (the ONE
    enumeration): {"expected": [...]} <- {"eligible": [...]}."""
    man = eligible_manifest(symbols, start, end, sessions=sessions,
                            registry=registry)
    return {sym: {"expected": m["eligible"], "excluded": m["excluded"]}
            for sym, m in man.items()}


def fetch_facts_from_ledger(facts_path: Path = FACTS_PATH) -> dict:
    """{(symbol, day): {"fetched": datetime, "sha256": str}} from
    BLIND_CACHE fact lines (timestamp AND content hash)."""
    facts: dict = {}
    if not facts_path.exists():
        return facts
    with facts_path.open() as f:
        for line in f:
            m = _BLIND_RE.match(line)
            if m:
                facts[(m.group(2), m.group(3))] = {
                    "fetched": datetime.fromisoformat(m.group(1)),
                    "sha256": m.group(4),
                }
    return facts


def load_tracked_manifest(path: Path = TRACKED_MANIFEST_PATH) -> dict:
    """{filename: sha256} from the committed chain-cache manifest."""
    out: dict = {}
    if not path.exists():
        return out
    with path.open() as f:
        for line in f:
            parts = line.split()
            if len(parts) == 3:
                out[parts[2]] = parts[0]
    return out


def tracked_manifest_context(path: Path = TRACKED_MANIFEST_PATH) -> dict:
    """Construction date of the tracked manifest (its last git commit) and
    proof that the adapter at that commit used the EOD-greeks endpoint."""
    commit = subprocess.run(
        ["git", "log", "-1", "--format=%H %cI", "--", str(path)],
        capture_output=True, text=True).stdout.split()
    if len(commit) != 2:
        return {"commit": None, "committed": None, "adapter_endpoint_ok": False}
    sha, committed = commit
    adapter = subprocess.run(
        ["git", "show", f"{sha}:data/thetadata_adapter.py"],
        capture_output=True, text=True).stdout
    return {"commit": sha, "committed": committed,
            "adapter_endpoint_ok": ADAPTER_ENDPOINT in adapter}


def load_coverage_declarations(path: Path = COVERAGE_PATH) -> list[dict]:
    """Owner-visible declarations that the earnings archive is
    source-complete for (symbol, start, end). Absent file = no coverage."""
    if not path.exists():
        return []
    decls = json.loads(path.read_text())
    for d in decls:
        for key in ("symbol", "start", "end"):
            if not d.get(key):
                raise ValueError(f"{path}: coverage declaration missing "
                                 f"{key}: {d}")
    return decls


def _covered(symbol: str, day: str, decls: list[dict]) -> bool:
    return any(d["symbol"] == symbol and d["start"] <= day <= d["end"]
               for d in decls)


def session_calendar_identity(sessions: list[str]) -> dict:
    from importlib.metadata import version
    try:
        ver = version("pandas_market_calendars")
    except Exception:
        ver = "unknown"
    return {"calendar": "XNYS", "package": "pandas_market_calendars",
            "package_version": ver,
            "sessions_hash": sha256_hex(canonical_json(sessions))}


def audit_day(symbol: str, day: str, frame: pd.DataFrame,
              session_set: set, raw_close_days: set) -> dict:
    """Per-day defect counts. Never mutates or filters the frame."""
    d: dict = {"rows": len(frame)}
    if list(frame.columns) != CHAIN_COLUMNS:
        d["schema_invalid"] = 1
        return d
    dup = frame.duplicated(subset=["expiration", "strike", "right"]).sum()
    if dup:
        d["duplicate_rows"] = int(dup)
    two_sided = (frame["bid"] > 0) & (frame["ask"] > 0)
    d["crossed_books"] = int((frame["bid"] > frame["ask"]).sum())
    d["one_sided_books"] = int((~two_sided).sum())
    exp = frame["expiration"].astype(str)
    bad_exp = 0
    stale_exp = 0
    holiday_exp = 0
    for e in exp.unique():
        try:
            ed = Date.fromisoformat(e)
        except ValueError:
            bad_exp += 1
            continue
        if e < day:
            stale_exp += 1
        elif (session_set and ed.weekday() < 5 and e not in session_set
                and e <= max(session_set)):
            holiday_exp += 1
    if bad_exp:
        d["unparseable_expirations"] = bad_exp
    if stale_exp:
        d["stale_expirations"] = stale_exp
    if holiday_exp:
        d["holiday_expirations"] = holiday_exp
    d["unusable_delta_two_sided"] = int(
        (two_sided & (~frame["delta"].abs().between(1e-6, 1.0))).sum())
    rights = set(frame["right"].unique())
    if "C" not in rights:
        d["missing_calls"] = 1
    if "P" not in rights:
        d["missing_puts"] = 1
    if day not in raw_close_days:
        d["missing_raw_close"] = 1
    return d


def continuity_breaks(symbol: str, sessions: list[str]) -> list[dict]:
    """Adjusted-close continuity: any |1-day return| > 50% inside the
    window is a split-registry or data defect."""
    from data.underlying_closes import load_closes_adjusted
    if not sessions:
        return []
    adj = load_closes_adjusted(symbol, sessions[0], sessions[-1],
                               allow_oos=True)
    rets = adj.pct_change().dropna()
    breaks = rets[rets.abs() > 0.50]
    return [{"symbol": symbol, "day": str(idx), "adjusted_return": float(r)}
            for idx, r in breaks.items()]


def run_audit(symbols=None, start=None, end=None, *, chain_dir=CHAIN_DIR,
              closes_dir=CLOSES_DIR, sessions=None, assertions=None,
              fetch_facts=None, known_as_of_fn=None, registry=None,
              tracked_manifest=None, tracked_context=None,
              coverage_decls=None, facts_path: Path = FACTS_PATH,
              progress=False) -> dict:
    from options_researcher.h7_earnings import (
        GATE_UNKNOWN,
        earnings_gate,
        load_assertions,
    )
    from data.cache_runner import trading_days

    symbols = list(symbols or config.H7_BACKTEST_SYMBOLS)
    start = start or config.H7_BACKTEST_START
    end = end or config.H7_BACKTEST_END
    sessions = (list(sessions) if sessions is not None
                else trading_days(start, end))
    manifest = eligible_manifest(symbols, start, end, sessions=sessions,
                                 registry=registry)
    reg = H7_AUDIT_EXCEPTIONS if registry is None else registry
    if assertions is None:
        assertions = load_assertions()
    if fetch_facts is None:
        fetch_facts = fetch_facts_from_ledger(facts_path)
    if known_as_of_fn is None:
        from data.cache_runner import session_close_utc
        known_as_of_fn = session_close_utc
    if tracked_manifest is None:
        tracked_manifest = load_tracked_manifest()
    if tracked_context is None:
        tracked_context = tracked_manifest_context()
    if coverage_decls is None:
        coverage_decls = load_coverage_declarations()

    classification = classify_cache(manifest, chain_dir)
    counts = {
        "expected": sum(len(m["eligible"]) for m in manifest.values()),
        "present": len(classification["present"]),
        "missing": len(classification["missing"]),
        "excluded": sum(len(m["excluded"]) for m in manifest.values()),
        "present_but_excluded": len(classification["present_but_excluded"]),
        "unexpected": len(classification["unexpected"]),
        "duplicates": len(classification["duplicates"]),
    }

    warn: dict = {}
    block: dict = {}
    missing_days: dict = {}
    contaminated: list = []
    provenance_map: dict = {}
    tier_counts = {"ledger_fact": 0, "legacy_manifest": 0, "unproven": 0}
    unproven: list = []
    sha_mismatch: list = []
    unknown_data_gap: dict = {}
    unknown_data_gap_days: dict = {}
    proven_unknown: dict = {}
    puts_inapplicable: list = []
    file_hashes: dict = {}

    tracked_ok = bool(tracked_context.get("adapter_endpoint_ok"))
    tracked_day = (tracked_context.get("committed") or "")[:10]

    for sym, m in manifest.items():
        session_set = set(m["eligible"]) | set(m["excluded"])
        closes_path = Path(closes_dir) / f"{sym}.parquet"
        raw_close_days = (
            set(pd.read_parquet(closes_path, columns=["date"])["date"])
            if closes_path.exists() else set())
        put_lane_eligible = sym not in config.H7_CORE_LONG_ONLY
        sym_missing = []
        for day in m["eligible"]:
            key = f"{sym}_{day}"
            path = Path(chain_dir) / f"{key}.parquet"
            if not path.exists():
                sym_missing.append(day)
                continue
            digest = sha256_file(path)
            file_hashes[key] = digest
            try:
                frame = pd.read_parquet(path)
            except Exception:
                block["unreadable_files"] = block.get("unreadable_files", 0) + 1
                continue
            d = audit_day(sym, day, frame, session_set, raw_close_days)
            for k in ("schema_invalid", "duplicate_rows",
                      "missing_raw_close"):
                if d.get(k):
                    block[k] = block.get(k, 0) + d[k]
            for k in ("crossed_books", "one_sided_books",
                      "unparseable_expirations", "stale_expirations",
                      "holiday_expirations", "unusable_delta_two_sided",
                      "missing_calls"):
                if d.get(k):
                    warn[k] = warn.get(k, 0) + d[k]
            if d.get("missing_puts"):
                if put_lane_eligible:
                    warn["missing_puts"] = warn.get("missing_puts", 0) + 1
                else:
                    # lane-aware (7b-2R finding 2): this symbol never trades
                    # puts in its H7 diagnostic; inapplicable, by identity
                    puts_inapplicable.append(key)

            # ---- EOD fetch provenance, tiered; NO mtime fallback ---------
            fact = fetch_facts.get((sym, day))
            if fact is not None:
                tier = "ledger_fact"
                if fact["sha256"] != digest:
                    sha_mismatch.append(key)
                fetched_ny = fact["fetched"].astimezone(NY)
                if (fetched_ny.date().isoformat() == day
                        and fetched_ny.hour < 18):
                    contaminated.append({"symbol": sym, "day": day,
                                         "fetched": fetched_ny.isoformat()})
            elif (tracked_ok
                    and tracked_manifest.get(f"{key}.parquet") == digest
                    and tracked_day and day < tracked_day):
                tier = "legacy_manifest"
            else:
                tier = "unproven"
                unproven.append(key)
            tier_counts[tier] += 1
            provenance_map[key] = tier

            # ---- causal earnings coverage at the session's real close ----
            gate, _ = earnings_gate(sym, Date.fromisoformat(day), assertions,
                                    known_as_of=known_as_of_fn(day))
            if gate == GATE_UNKNOWN:
                if _covered(sym, day, coverage_decls):
                    proven_unknown[sym] = proven_unknown.get(sym, 0) + 1
                else:
                    unknown_data_gap[sym] = unknown_data_gap.get(sym, 0) + 1
                    unknown_data_gap_days.setdefault(sym, []).append(day)
        if sym_missing:
            missing_days[sym] = sym_missing
        if progress:
            print(f"  {sym}: {len(m['eligible'])} eligible, "
                  f"{len(sym_missing)} missing, "
                  f"{len(m['excluded'])} excluded")
        breaks = continuity_breaks(sym, m["eligible"])
        if breaks:
            block["adjusted_continuity_breaks"] = (
                block.get("adjusted_continuity_breaks", 0) + len(breaks))
            warn.setdefault("continuity_detail", []).extend(breaks[:10])

    # hash the quarantined / unexpected files too: the receipt proves WHAT
    # was refused, and any later mutation of those files is visible
    quarantined_hashes: dict = {}
    for key in (classification["present_but_excluded"]
                + classification["unexpected"]):
        p = Path(chain_dir) / f"{key}.parquet"
        if p.exists():
            quarantined_hashes[key] = sha256_file(p)

    closes_hashes = {
        sym: sha256_file(Path(closes_dir) / f"{sym}.parquet")
        for sym in symbols if (Path(closes_dir) / f"{sym}.parquet").exists()}

    if counts["missing"]:
        block["missing_sessions"] = counts["missing"]
    if counts["duplicates"]:
        block["duplicate_file_identities"] = counts["duplicates"]
    if contaminated:
        block["intraday_fetch_contamination"] = len(contaminated)
    if sha_mismatch:
        block["provenance_sha_mismatch"] = len(sha_mismatch)
    if unproven:
        block["unproven_provenance"] = len(unproven)
    unratified = list(unratified_coverage_entries(reg))
    if unratified:
        block["unratified_coverage_exclusions"] = len(unratified)
    if unknown_data_gap:
        block["earnings_data_gap_sessions"] = sum(unknown_data_gap.values())
    if proven_unknown:
        warn["earnings_proven_unknown_sessions"] = sum(proven_unknown.values())
    if puts_inapplicable:
        warn["missing_puts_inapplicable"] = len(puts_inapplicable)

    report = {
        "audit_version": AUDIT_VERSION,
        "window": {"start": start, "end": end},
        "symbols": symbols,
        "session_calendar": session_calendar_identity(sessions),
        "counts": counts,
        "cache_classification": classification,
        "manifest_hash": sha256_hex(canonical_json(manifest)),
        "exception_registry": [dict(e, source_urls=list(e.get("source_urls", ())))
                               for e in reg],
        "exception_registry_hash": sha256_hex(canonical_json(
            [dict(e, source_urls=list(e.get("source_urls", ()))) for e in reg])),
        "unratified_coverage_exclusions": [
            {"symbol": e["symbol"], "start": e["start"], "end": e["end"],
             "kind": e["kind"]} for e in unratified],
        "legacy_provenance_assumption": LEGACY_PROVENANCE_ASSUMPTION,
        "tracked_manifest": {
            "path": str(TRACKED_MANIFEST_PATH),
            "commit": tracked_context.get("commit"),
            "committed": tracked_context.get("committed"),
            "adapter_endpoint_ok": tracked_ok,
            "endpoint": ADAPTER_ENDPOINT,
        },
        "provenance_tiers": tier_counts,
        "provenance_map": provenance_map,
        "provenance_map_hash": sha256_hex(canonical_json(provenance_map)),
        "unproven_provenance_files": sorted(unproven),
        "provenance_sha_mismatch_files": sorted(sha_mismatch),
        "block_findings": block,
        "warn_findings": warn,
        "missing_days": missing_days,
        "contaminated_days": contaminated,
        "missing_puts_inapplicable": sorted(puts_inapplicable),
        "earnings_data_gap_by_symbol": unknown_data_gap,
        "earnings_data_gap_days": unknown_data_gap_days,
        "earnings_proven_unknown_by_symbol": proven_unknown,
        "earnings_coverage_declarations": coverage_decls,
        "closes_hashes": closes_hashes,
        "verdict": "BLOCK" if block else "PASS",
    }
    report["files_hash"] = sha256_hex(canonical_json(file_hashes))
    report["file_hashes"] = file_hashes
    report["quarantined_files_hash"] = sha256_hex(
        canonical_json(quarantined_hashes))
    report["quarantined_file_hashes"] = quarantined_hashes
    return report


def write_receipt(report: dict, path: Path = RECEIPT_PATH, *,
                  earnings_path: Path | None = None,
                  coverage_path: Path = COVERAGE_PATH) -> str:
    """Bind the report to code/config/data surfaces and persist. The
    receipt_hash covers every field except the bulk maps, each of which is
    bound through its own sub-hash inside the hashable set."""
    from options_researcher.h7_earnings import ASSERTIONS_PATH
    earnings_path = earnings_path or ASSERTIONS_PATH
    code_sha = subprocess.run(["git", "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    receipt = dict(report)
    receipt["code_sha"] = code_sha
    receipt["config_hash"] = config_hash()
    receipt["cost_model_hash"] = cost_model_hash()
    receipt["diagnostic_source_hash"] = diagnostic_source_hash()
    receipt["diagnostic_source_hash_version"] = DIAGNOSTIC_SOURCE_HASH_VERSION
    receipt["earnings_store_path"] = str(earnings_path)
    receipt["earnings_store_hash"] = (
        sha256_file(earnings_path) if Path(earnings_path).exists() else None)
    receipt["earnings_coverage_hash"] = (
        sha256_file(coverage_path) if Path(coverage_path).exists() else None)
    hashable = {k: v for k, v in receipt.items() if k not in _BULK_KEYS}
    receipt["receipt_hash"] = sha256_hex(canonical_json(hashable))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    return receipt["receipt_hash"]


def verify_receipt(path: Path = RECEIPT_PATH, *, chain_dir=CHAIN_DIR,
                   closes_dir=CLOSES_DIR,
                   earnings_path: Path | None = None,
                   coverage_path: Path = COVERAGE_PATH,
                   registry=None) -> tuple[bool, list[str]]:
    """Recompute EVERY bound input against current repo state. Returns
    (valid, failures). Any mutation -- chains, quarantined files, closes,
    earnings store, coverage declarations, exception registry, session
    calendar, config, cost model, diagnostic source surface, or any receipt
    field -- fails verification (7b-2R finding 3)."""
    from options_researcher.h7_earnings import ASSERTIONS_PATH
    earnings_path = Path(earnings_path or ASSERTIONS_PATH)
    receipt = json.loads(Path(path).read_text())
    failures: list[str] = []

    hashable = {k: v for k, v in receipt.items()
                if k not in _BULK_KEYS and k != "receipt_hash"}
    if sha256_hex(canonical_json(hashable)) != receipt["receipt_hash"]:
        failures.append("receipt_hash")

    for key, digest in receipt["file_hashes"].items():
        p = Path(chain_dir) / f"{key}.parquet"
        if not p.exists() or sha256_file(p) != digest:
            failures.append(f"chain:{key}")
            break
    if sha256_hex(canonical_json(receipt["file_hashes"])) != receipt["files_hash"]:
        failures.append("files_hash")
    for key, digest in receipt["quarantined_file_hashes"].items():
        p = Path(chain_dir) / f"{key}.parquet"
        if not p.exists() or sha256_file(p) != digest:
            failures.append(f"quarantined:{key}")
            break
    if (sha256_hex(canonical_json(receipt["quarantined_file_hashes"]))
            != receipt["quarantined_files_hash"]):
        failures.append("quarantined_files_hash")
    if (sha256_hex(canonical_json(receipt["provenance_map"]))
            != receipt["provenance_map_hash"]):
        failures.append("provenance_map_hash")

    for sym, digest in receipt["closes_hashes"].items():
        p = Path(closes_dir) / f"{sym}.parquet"
        if not p.exists() or sha256_file(p) != digest:
            failures.append(f"closes:{sym}")

    current_earnings = (sha256_file(earnings_path)
                        if earnings_path.exists() else None)
    if current_earnings != receipt["earnings_store_hash"]:
        failures.append("earnings_store_hash")
    current_coverage = (sha256_file(coverage_path)
                        if Path(coverage_path).exists() else None)
    if current_coverage != receipt["earnings_coverage_hash"]:
        failures.append("earnings_coverage_hash")

    reg = H7_AUDIT_EXCEPTIONS if registry is None else registry
    reg_json = [dict(e, source_urls=list(e.get("source_urls", ())))
                for e in reg]
    if sha256_hex(canonical_json(reg_json)) != receipt["exception_registry_hash"]:
        failures.append("exception_registry_hash")

    from data.cache_runner import trading_days
    sessions = trading_days(receipt["window"]["start"],
                            receipt["window"]["end"])
    if (sha256_hex(canonical_json(sessions))
            != receipt["session_calendar"]["sessions_hash"]):
        failures.append("sessions_hash")

    if config_hash() != receipt["config_hash"]:
        failures.append("config_hash")
    if cost_model_hash() != receipt["cost_model_hash"]:
        failures.append("cost_model_hash")
    if diagnostic_source_hash() != receipt["diagnostic_source_hash"]:
        failures.append("diagnostic_source_hash")

    return (not failures, failures)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true",
                        help="verify the committed v2 receipt instead of auditing")
    args = parser.parse_args(argv)
    if args.verify:
        ok, failures = verify_receipt()
        print("receipt VALID" if ok
              else f"receipt INVALID -- mutated inputs: {failures}")
        return 0 if ok else 2
    print(f"H7 full-window data audit ({AUDIT_VERSION}) -- "
          f"{config.H7_BACKTEST_START}..{config.H7_BACKTEST_END}, "
          f"{len(config.H7_BACKTEST_SYMBOLS)} symbols")
    report = run_audit(progress=True)
    receipt_hash = write_receipt(report)
    c = report["counts"]
    print(f"expected={c['expected']} present={c['present']} "
          f"missing={c['missing']} excluded={c['excluded']} "
          f"present_but_excluded={c['present_but_excluded']} "
          f"unexpected={c['unexpected']} duplicates={c['duplicates']}")
    print(f"provenance tiers: {report['provenance_tiers']}")
    print(f"block findings: {report['block_findings']}")
    print(f"warn findings: "
          f"{ {k: v for k, v in report['warn_findings'].items() if k != 'continuity_detail'} }")
    print(f"earnings DATA_GAP sessions by symbol: "
          f"{report['earnings_data_gap_by_symbol']}")
    print(f"earnings PROVEN_UNKNOWN sessions by symbol: "
          f"{report['earnings_proven_unknown_by_symbol']}")
    print(f"VERDICT: {report['verdict']}")
    print(f"receipt: {RECEIPT_PATH} ({receipt_hash})")
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
