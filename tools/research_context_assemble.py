"""tools/research_context_assemble.py — assemble/validate/verify the
attractiveness research context.

Pure core (no I/O): clean_claims, clean_symbol_blurb, build_context,
check_dashboard_html. CLI wires the core to live repo data:

  uv run python -m tools.research_context_assemble --print-ids
  uv run python -m tools.research_context_assemble --assemble --inputs DIR
  uv run python -m tools.research_context_assemble --verify

Advisory-only by construction: annotations pass through
options_researcher.top3_context.normalize_research_annotations (the same
gate the dashboard uses) and are keyed to candidates the deterministic
board already selected. This module can never add, remove, or reorder a
candidate.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

BANNED_HOSTS = ("reddit.", "youtube.", "youtu.be", "seekingalpha.",
                "medium.", "substack.", "wordpress.", "blogspot.",
                "stocktwits.", "fool.")
PRIMARY_TIERS = frozenset({"issuer_ir", "sec_filing", "regulator",
                           "market_operator"})
CLAIM_FIELDS = ("id", "text", "classification", "source_url",
                "unknown_rationale", "source_tier", "fact_date",
                "date_certainty", "countercase")
BLURB_FIELDS = ("news_summary", "sentiment", "catalysts", "move_thesis",
                "sources")
STALE_MARKERS = ("annotations are from", "do not match any card",
                 "Research evidence incomplete", "Research evidence stale")


class AssemblyError(ValueError):
    """A refusal: malformed or policy-violating research input."""


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _check_url(url, *, where: str) -> None:
    if url is None:
        return
    if any(b in _host(url) for b in BANNED_HOSTS):
        raise AssemblyError(f"{where}: banned source host {_host(url)}")


def clean_claims(symbol: str, claims: list) -> list[dict]:
    out = []
    for i, raw in enumerate(claims):
        where = f"{symbol}.claims[{i}]"
        claim = {k: raw.get(k) for k in CLAIM_FIELDS}
        if (claim.get("date_certainty") == "confirmed"
                and claim.get("source_tier") not in PRIMARY_TIERS):
            raise AssemblyError(
                f"{where}: confirmed date without primary tier")
        _check_url(claim.get("source_url"), where=where)
        out.append(claim)
    return out


def clean_symbol_blurb(symbol: str, blurb: dict) -> dict:
    keep = {k: blurb.get(k) for k in BLURB_FIELDS
            if blurb.get(k) is not None}
    for i, cat in enumerate(keep.get("catalysts") or []):
        _check_url(cat.get("source"), where=f"{symbol}.catalysts[{i}]")
    for i, url in enumerate(keep.get("sources") or []):
        _check_url(url, where=f"{symbol}.sources[{i}]")
    return keep


def build_context(*, as_of: str, researched_on: str,
                  candidate_ids: list[str], inputs: dict) -> dict:
    """Build the context dict from researcher output; validate through the
    dashboard's own annotation gate. inputs = {"market": {...},
    "symbol_research": {SYMBOL: {...incl. claims...}}}."""
    from options_researcher.top3_context import (
        AnnotationValidationError,
        normalize_research_annotations,
    )

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    annotations: dict[str, dict] = {}
    for cid in candidate_ids:
        symbol = cid.split(":", 1)[0]
        agent = (inputs.get("symbol_research") or {}).get(symbol)
        if agent is None:
            continue  # honest omission renders "evidence incomplete"
        annotations[cid] = {
            "research_as_of_utc": ts,
            "market_as_of_date": as_of,
            "claims": clean_claims(symbol, agent.get("claims") or []),
        }
    try:
        normalize_research_annotations(candidate_ids, annotations)
    except AnnotationValidationError as e:
        raise AssemblyError(f"annotation schema rejection: {e}") from e

    symbols: dict[str, dict] = {}
    for symbol, agent in (inputs.get("symbol_research") or {}).items():
        symbols[symbol] = clean_symbol_blurb(symbol, agent)
    market_block = (inputs.get("market") or {})
    for symbol, blurb in (market_block.get("symbols") or {}).items():
        symbols.setdefault(symbol, clean_symbol_blurb(symbol, blurb))

    market = market_block.get("market") or {}
    return {
        "as_of": as_of,
        "provenance": ("LLM-asserted (Claude subagents, web research "
                       f"{researched_on})"),
        "researched_on": researched_on,
        "market": {k: market.get(k) for k in ("summary", "regime", "notes")},
        "market_sources": market_block.get("market_sources") or [],
        "symbols": symbols,
        "annotations": annotations,
    }


def check_dashboard_html(html: str) -> list[str]:
    """Return the stale-research markers present in rendered HTML."""
    return [m for m in STALE_MARKERS if m in html]


# ---------------------------------------------------------------- CLI --

def _live_board():
    from options_researcher.attractiveness_dashboard import (
        assemble,
        select_qm_top_picks,
        select_top_picks,
    )
    from options_researcher.qm_dashboard import load_qm_context

    data = assemble()
    as_of = data.get("data_as_of")
    if not as_of:
        raise SystemExit("no data_as_of on the assembled board -- refusing")
    qm = load_qm_context(as_of)
    ids: list[str] = []
    for p in select_top_picks(data, include_csp_watch=True):
        ids.append(p["card"]["top3_snapshot"]["candidate_id"])
    for p in select_qm_top_picks(data, qm, include_csp_watch=True):
        cid = p["card"]["top3_snapshot"]["candidate_id"]
        if cid not in ids:
            ids.append(cid)
    return data, as_of, ids


def _cmd_print_ids() -> None:
    from options_researcher.attractiveness_dashboard import pinned_picks

    data, as_of, ids = _live_board()
    pinned = [p["symbol"] for p in pinned_picks(data)]
    print(json.dumps({"data_as_of": as_of, "candidate_ids": ids,
                      "pinned_symbols": pinned}))


def _cmd_assemble(inputs_dir: str) -> None:
    _data, as_of, ids = _live_board()
    with open(os.path.join(inputs_dir, "market.json")) as f:
        market = json.load(f)
    symbol_research = {}
    for name in sorted(os.listdir(inputs_dir)):
        if name == "market.json" or not name.endswith(".json"):
            continue
        with open(os.path.join(inputs_dir, name)) as f:
            blob = json.load(f)
        if blob.get("symbol"):
            symbol_research[blob["symbol"]] = blob
    ctx = build_context(
        as_of=as_of,
        researched_on=datetime.now(timezone.utc).date().isoformat(),
        candidate_ids=ids,
        inputs={"market": market, "symbol_research": symbol_research},
    )
    out = os.path.join("reports", "attractiveness_context", f"{as_of}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = f"{out}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(ctx, f, indent=1)
        f.write("\n")
    os.replace(tmp, out)
    covered = len(ctx["annotations"])
    print(f"wrote {out} (annotations {covered}/{len(ids)})")


def _cmd_verify() -> None:
    _data, as_of, _ids = _live_board()
    ctx_path = os.path.join("reports", "attractiveness_context",
                            f"{as_of}.json")
    if not os.path.exists(ctx_path):
        raise SystemExit(f"missing {ctx_path}")
    html_path = os.path.join(".tmp", "dashboard", "attractiveness.html")
    with open(html_path) as f:
        problems = check_dashboard_html(f.read())
    if problems:
        raise SystemExit("stale markers still present: " + "; ".join(problems))
    print(f"verify OK: {ctx_path} matches board and no stale markers remain")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--print-ids", action="store_true")
    group.add_argument("--assemble", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--inputs", help="directory of researcher JSON files")
    args = parser.parse_args()
    if args.print_ids:
        _cmd_print_ids()
    elif args.assemble:
        if not args.inputs:
            parser.error("--assemble requires --inputs DIR")
        _cmd_assemble(args.inputs)
    else:
        _cmd_verify()
