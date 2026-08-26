#!/usr/bin/env python3
"""Write-free Brief 26 WP-B/WP-C projection over one pinned board assembly."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter
from contextlib import redirect_stdout
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

with redirect_stdout(sys.stderr):
    import config  # noqa: E402
    from options_researcher import attractiveness_dashboard as ad  # noqa: E402

BRIEF_RELATIVE = Path("docs/superpowers/plans/2026-08-25-26-board-declutter-top5-codex-brief.md")
SIMULATOR_RELATIVE = Path(".tmp/controller/brief26_projection.py")
BRIEF = REPO_ROOT / BRIEF_RELATIVE
GRADE_RANK = {"UNKNOWN": 0, "RED": 1, "AMBER": 2, "GREEN": 3}
AXES = {
    "put": (("annualized_yield", 1), ("cushion", 1)),
    "cc": (("annualized_yield", 1), ("upside", 1)),
    "long_call": (("cost", -1), ("breakeven_move", -1)),
    "leaps": (("cost", -1), ("breakeven_distance", -1)),
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonable(value: object) -> object:
    """Return a deterministic, strict-JSON representation for receipt hashing."""
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, Path):
        return str(value)
    return value


def _strict_date(value: object) -> bool:
    from datetime import date

    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _candidate_id(card: dict[str, Any]) -> str | None:
    snapshot = card.get("top3_snapshot")
    value = snapshot.get("candidate_id") if isinstance(snapshot, dict) else None
    return value if isinstance(value, str) and value else None


def _axis_values(card: dict[str, Any], lane: str, close: float) -> tuple[float, ...] | None:
    values: list[float] = []
    for name, _direction in AXES[lane]:
        if name == "breakeven_distance":
            breakeven = _finite(card.get("breakeven"))
            if breakeven is None or close <= 0:
                return None
            values.append(abs(breakeven - close) / close)
        else:
            value = _finite(card.get(name))
            if value is None:
                return None
            values.append(value)
    return tuple(values)


def _dominates(y: dict[str, Any], x: dict[str, Any], lane: str, close: float) -> bool:
    y_values = _axis_values(y, lane, close)
    x_values = _axis_values(x, lane, close)
    if y_values is None or x_values is None:
        return False
    weak = True
    strict = False
    for (name, direction), y_value, x_value in zip(AXES[lane], y_values, x_values, strict=True):
        del name
        if direction == 1:
            weak = weak and y_value >= x_value
            strict = strict or y_value > x_value
        else:
            weak = weak and y_value <= x_value
            strict = strict or y_value < x_value
    y_grades = y.get("grades") if isinstance(y.get("grades"), dict) else {}
    x_grades = x.get("grades") if isinstance(x.get("grades"), dict) else {}
    for key in sorted(set(y_grades) & set(x_grades)):
        y_rank = GRADE_RANK.get(y_grades[key], 0)
        x_rank = GRADE_RANK.get(x_grades[key], 0)
        weak = weak and y_rank >= x_rank
        strict = strict or y_rank > x_rank
    return weak and strict


def _panel_status(section: dict[str, Any], stale_symbols: set[str]) -> tuple[list[str], bool]:
    cards = [card for group in section.get("groups", []) for card in group.get("cards", [])]
    labels: list[str] = []
    if any(
        ad._display_policy_tier(card) == ad._DISPLAY_POLICY_TIER["DATA_BLOCKED"] for card in cards
    ):
        labels.append("DATA_BLOCKED")
    if section.get("features_stale") is True or section.get("symbol") in stale_symbols:
        labels.append("STALE")
    if any("skipped" in card for card in cards):
        labels.append("SKIPPED")
    if any((card.get("grades") or {}).get("liquidity") == "RED" for card in cards):
        labels.append("LIQUIDITY WARNING")
    if not labels:
        labels.append("CURRENT")
    return labels, any(label in labels for label in ("DATA_BLOCKED", "STALE", "SKIPPED"))


def _emit_unavailable(*, base_sha: str, evaluation_date: str, root: str, detail: str) -> int:
    receipt = {
        "schema": "brief26_declutter_projection/v1",
        "base_sha": base_sha,
        "brief_sha256": _sha(BRIEF.read_bytes()),
        "simulator_sha256": _sha(Path(__file__).read_bytes()),
        "input_root": root,
        "evaluation_date": evaluation_date,
        "data_as_of": None,
        "chain_age_sessions": None,
        "assembled_payload_sha256": None,
        "source_manifest": None,
        "candidate_ids": {},
        "protected_ids": [],
        "lanes": [],
        "panels": [],
        "chrome": {
            "baseline": 0,
            "predicted": 0,
            "reduction_numerator": 0,
            "reduction_denominator": 0,
            "reduction_percent": 0.0,
        },
        "gate": {
            "board_available": False,
            "board_fresh": False,
            "reduction_at_least_30": False,
            "proceed": False,
            "reason_codes": ["BOARD_UNAVAILABLE", detail],
        },
    }
    print(json.dumps(receipt, indent=2, sort_keys=True) + "\n", end="")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--evaluation-date", required=True)
    args = parser.parse_args()
    if not _strict_date(args.evaluation_date):
        raise SystemExit("evaluation date must be strict YYYY-MM-DD")
    root_text = os.environ.get("ATTRACTIVENESS_INPUT_ROOT")
    if not root_text:
        raise SystemExit("ATTRACTIVENESS_INPUT_ROOT is required")
    try:
        input_root = Path(root_text).expanduser().resolve(strict=True)
    except OSError as exc:
        return _emit_unavailable(
            base_sha=args.base_sha,
            evaluation_date=args.evaluation_date,
            root=root_text,
            detail=f"INPUT_ROOT_{type(exc).__name__.upper()}",
        )
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", args.base_sha, "HEAD"], check=False
    )
    if ancestry.returncode != 0:
        raise SystemExit(f"base is not an ancestor of HEAD: {args.base_sha}")
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{args.base_sha}..HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    permitted_control_files = {str(BRIEF_RELATIVE), str(SIMULATOR_RELATIVE)}
    if set(changed) != permitted_control_files:
        raise SystemExit(f"pre-code diff is not control-only: {changed}")

    try:
        with redirect_stdout(sys.stderr), ad._input_root_cwd() as resolved:
            data = ad.assemble(today=args.evaluation_date)
    except Exception as exc:
        return _emit_unavailable(
            base_sha=args.base_sha,
            evaluation_date=args.evaluation_date,
            root=str(input_root),
            detail=f"ASSEMBLY_{type(exc).__name__.upper()}",
        )
    if Path(resolved).resolve() != input_root:
        raise SystemExit("resolved input root mismatch")

    snapshot = {
        key: data.get(key)
        for key in (
            "symbols",
            "blocked",
            "data_as_of",
            "evaluation_date",
            "chain_age_sessions",
            "fresh_symbols",
            "stale_symbols",
        )
    }
    payload = json.dumps(
        _jsonable(snapshot),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    all_ids: list[str] = []
    protected: set[str] = set()
    for section in data.get("symbols") or []:
        for group in section.get("groups") or []:
            for card in group.get("cards") or []:
                ident = _candidate_id(card)
                if ident is None:
                    continue
                all_ids.append(ident)
                if (
                    card.get("rank_leader")
                    or (card.get("grades") or {}).get("liquidity") == "RED"
                    or ad._display_policy_tier(card) == ad._DISPLAY_POLICY_TIER["DATA_BLOCKED"]
                ):
                    protected.add(ident)
    for pick in ad.select_top_picks(data, n=5):
        ident = _candidate_id(pick["card"])
        if ident:
            protected.add(ident)
    for pick in ad.select_top_picks(data, n=5, include_csp_watch=True):
        ident = _candidate_id(pick["card"])
        if ident:
            protected.add(ident)
    for record in ad.pinned_picks(data):
        if record.get("pick"):
            ident = _candidate_id(record["pick"]["card"])
            if ident:
                protected.add(ident)

    lanes: list[dict[str, Any]] = []
    hidden_global: set[str] = set()
    stale_symbols = set(data.get("stale_symbols") or [])
    panels: list[dict[str, Any]] = []
    baseline_chrome = 0
    predicted_chrome = 0
    for section in data.get("symbols") or []:
        labels, opened = _panel_status(section, stale_symbols)
        group_count = len(section.get("groups") or [])
        baseline_chrome += 1 + group_count
        predicted_chrome += 1 + (group_count if opened else 0)
        panels.append(
            {
                "symbol": section.get("symbol"),
                "labels": labels,
                "open": opened,
                "group_count": group_count,
            }
        )
        close = float(section["close"])
        section_stale = (
            section.get("features_stale") is True or section.get("symbol") in stale_symbols
        )
        for group_index, group in enumerate(section.get("groups") or []):
            lane = str(group.get("kind"))
            cards = [card for card in group.get("cards") or [] if _candidate_id(card)]
            ids = [_candidate_id(card) for card in cards]
            if section_stale or lane == "pmcc" or lane not in AXES or len(cards) <= 2:
                shown = set(ids)
                hidden: set[str] = set()
                dominators: dict[str, str] = {}
            else:
                front_indexes = [
                    i
                    for i, card in enumerate(cards)
                    if not any(
                        i != j and _dominates(other, card, lane, close)
                        for j, other in enumerate(cards)
                    )
                ]
                hidden = set()
                dominators = {}
                for index, card in enumerate(cards):
                    ident = ids[index]
                    if ident in protected or index in front_indexes:
                        continue
                    direct = [j for j in front_indexes if _dominates(cards[j], card, lane, close)]
                    if direct:
                        chosen = min(direct)
                        hidden.add(ident)
                        dominators[ident] = ids[chosen]
                shown = set(ids) - hidden
            hidden_global.update(hidden)
            lanes.append(
                {
                    "symbol": section.get("symbol"),
                    "group_index": group_index,
                    "lane": lane,
                    "shown_ids": sorted(shown),
                    "hidden_ids": sorted(hidden),
                    "dominators": dict(sorted(dominators.items())),
                }
            )

    manifest_path = (
        input_root / "reports" / "schwab_chains" / str(data.get("data_as_of")) / "manifest.json"
    )
    manifest = (
        {
            "path": str(manifest_path),
            "sha256": _sha(manifest_path.read_bytes()),
        }
        if manifest_path.is_file()
        else None
    )
    age = data.get("chain_age_sessions")
    unexpected_block = any(
        isinstance(record, dict) and record.get("unexpected") is True
        for record in data.get("blocked") or []
    )
    available = (
        bool(data.get("symbols"))
        and bool(all_ids)
        and _strict_date(data.get("data_as_of"))
        and data.get("evaluation_date") == args.evaluation_date
        and isinstance(age, int)
        and not isinstance(age, bool)
        and age >= 0
        and not unexpected_block
    )
    fresh = available and age < config.CHAIN_STALE_BLOCK_SESSIONS
    reduction_numerator = baseline_chrome - predicted_chrome
    reduction = reduction_numerator / baseline_chrome if baseline_chrome else 0.0
    reduction_ok = reduction >= 0.30
    reasons = []
    if not available:
        reasons.append("BOARD_UNAVAILABLE")
    if available and not fresh:
        reasons.append("BOARD_STALE")
    if not reduction_ok:
        reasons.append("REDUCTION_BELOW_30_PERCENT")
    receipt = {
        "schema": "brief26_declutter_projection/v1",
        "base_sha": args.base_sha,
        "brief_sha256": _sha(BRIEF.read_bytes()),
        "simulator_sha256": _sha(Path(__file__).read_bytes()),
        "input_root": str(input_root),
        "evaluation_date": args.evaluation_date,
        "data_as_of": data.get("data_as_of"),
        "chain_age_sessions": age,
        "assembled_payload_sha256": _sha(payload),
        "source_manifest": manifest,
        "candidate_ids": dict(sorted(Counter(all_ids).items())),
        "protected_ids": sorted(protected),
        "lanes": lanes,
        "panels": panels,
        "chrome": {
            "baseline": baseline_chrome,
            "predicted": predicted_chrome,
            "reduction_numerator": reduction_numerator,
            "reduction_denominator": baseline_chrome,
            "reduction_percent": round(reduction * 100, 6),
        },
        "gate": {
            "board_available": available,
            "board_fresh": fresh,
            "reduction_at_least_30": reduction_ok,
            "proceed": available and fresh and reduction_ok,
            "reason_codes": reasons,
        },
    }
    print(json.dumps(receipt, indent=2, sort_keys=True) + "\n", end="")
    return 0 if receipt["gate"]["proceed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
