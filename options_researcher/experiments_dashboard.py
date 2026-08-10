"""Standalone, display-only dashboard for the four attractiveness lanes.

This artifact is intentionally separate from the production attractiveness
dashboard. It builds every lane on explicit invocation, quarantines lane
failures into visible ERROR cards, and writes no state other than its HTML.
"""

from __future__ import annotations

import html
import os
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from options_researcher.exp_beta_qqq import build_exp_beta_board
from options_researcher.exp_spread_stability import build_exp_spread_board
from options_researcher.exp_tail_shape import build_exp_tail_board
from options_researcher.exp_tbill_carry import build_exp_tbill_board

EXPERIMENTS_OUTPUT_PATH = config.EXPERIMENTS_OUTPUT_PATH

_LANES = (
    ("exp_beta", "EXP-BETA", "adjusted closes + QQQ", "build_exp_beta_board"),
    ("exp_tail", "EXP-TAIL", "adjusted closes", "build_exp_tail_board"),
    (
        "exp_spread",
        "EXP-SPREAD",
        "cached option chains + earnings calendar",
        "build_exp_spread_board",
    ),
    ("exp_tbill", "EXP-TBILL", "cached option chains + Treasury curve", "build_exp_tbill_board"),
)


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _experiment_state_class(state: str) -> str:
    if state in {"OK", "ABOVE_TBILL"}:
        return "good"
    if "BLOCKED" in state or state == "ERROR":
        return "bad"
    return "unknown"


def _experiment_asof(cards: list[dict]) -> str:
    stamps = [
        str(card.get("max_asof") or card.get("asof"))
        for card in cards
        if card.get("max_asof") or card.get("asof")
    ]
    return max(stamps) if stamps else "unavailable"


def _experiment_health_html(data: Mapping[str, object]) -> str:
    cells = []
    for key, experiment_id, source, _builder_name in _LANES:
        cards_value = data.get(key) or []
        cards = cards_value if isinstance(cards_value, list) else []
        rendered = sum(
            not bool(card.get("data_blocked")) and card.get("state") != "ERROR" for card in cards
        )
        reasons = sorted(
            {
                str(card.get("reason"))
                for card in cards
                if (card.get("data_blocked") or card.get("state") == "ERROR") and card.get("reason")
            }
        )
        reason_html = (
            f'<div class="label">Blocked: {_esc("; ".join(reasons))}</div>' if reasons else ""
        )
        health_class = (
            "good" if cards and rendered == len(cards) else "bad" if rendered == 0 else "unknown"
        )
        cells.append(
            '<div class="panel composite-card">'
            f'<div class="slot-label"><span>{_esc(experiment_id)}</span>'
            f'<span class="status-badge {health_class}">'
            "ENABLED FOR THIS RENDER</span></div>"
            f'<div class="label">Source: {_esc(source)}</div>'
            f'<div class="label">max as-of {_esc(_experiment_asof(cards))}</div>'
            f'<div class="label">{rendered} / {len(cards)} names rendered</div>'
            f"{reason_html}</div>"
        )
    return '<div class="card-grid">' + "".join(cells) + "</div>"


def _experiment_blocked_line(card: Mapping[str, object]) -> str:
    reason = str(card.get("reason") or "required cached data unavailable")
    asof = str(card.get("max_asof") or card.get("asof") or "unavailable")
    return f"DATA BLOCKED as of {asof}: {reason}."


def _experiment_float(value: object) -> float:
    if isinstance(value, (str, int, float)):
        return float(value)
    raise TypeError(f"experiment numeric value has unsupported type {type(value).__name__}")


def _experiment_int(value: object) -> int:
    if isinstance(value, (str, int, float)):
        return int(value)
    raise TypeError(f"experiment integer value has unsupported type {type(value).__name__}")


def _experiment_card_line(card: Mapping[str, object]) -> str:
    experiment_id = str(card.get("experiment_id") or "UNKNOWN")
    if card.get("state") == "ERROR":
        line = str(card.get("reason") or "lane failed")
    elif card.get("data_blocked"):
        line = _experiment_blocked_line(card)
    elif experiment_id == "EXP-BETA":
        line = (
            f"beta {_experiment_float(card['beta']):.2f} to QQQ; "
            f"R² {_experiment_float(card['r_squared']):.2f}; "
            f"half-window beta {_experiment_float(card['beta_half_window']):.2f}; "
            f"{_experiment_int(card['n_obs'])} sessions"
        )
    elif experiment_id == "EXP-TAIL":
        skew_direction = "down" if _experiment_float(card["skew"]) < 0 else "up"
        line = (
            f"{_experiment_int(card['jump_count'])} moves bigger than 3× normal in the "
            f"past year; recent surprises leaned {skew_direction}; sample "
            f"skew {_experiment_float(card['skew']):.2f}, excess kurtosis "
            f"{_experiment_float(card['excess_kurtosis']):.2f}"
        )
        if card.get("state") == "UNSTABLE":
            line += "; UNSTABLE across window choices"
    elif experiment_id == "EXP-SPREAD":
        line = (
            f"spread at the {str(card.get('max_asof') or card.get('asof') or '?')} "
            f"close was {_experiment_float(card['ratio']):.2f}× its usual level "
            f"(median of {_experiment_int(card['baseline_sessions_used'])} "
            "usable prior sessions)"
        )
        if card.get("today_is_earnings_week"):
            line += "; that close was in an asserted earnings week"
    elif experiment_id == "EXP-TBILL":
        rate_provenance = str(card.get("rate_provenance") or "rate provenance unavailable")
        line = (
            f"${_experiment_float(card['collateral']):,.0f} collateral; put credit yield "
            f"{_experiment_float(card['credit_annualized_yield']):.1%}/yr vs T-bills "
            f"{_experiment_float(card['tbill_annualized_yield']):.1%}/yr "
            f"(carry spread {_experiment_float(card['carry_spread']):+.1%}/yr; quote mid, "
            f"real fills are mid or worse). Treasury rate source: {rate_provenance}"
        )
    else:
        line = str(card.get("reason") or card.get("state") or "No display detail")

    asof = str(card.get("max_asof") or card.get("asof") or "unavailable")
    caveat = str(card.get("caveat") or "Descriptive history, not a forecast.")
    assignment = _as_mapping(card.get("assignment"))
    assignment_reason = assignment.get("reason")
    if experiment_id != "EXP-TBILL" or not assignment_reason:
        assignment_line = ""
    elif assignment_reason == "EX_DIV_DATE_UNAVAILABLE":
        assignment_line = " Early-assignment risk: unknown — no ex-dividend-date data on disk yet."
    else:
        assignment_line = f" Early-assignment risk caveat: {assignment_reason}."
    return f"{line} As of {asof}. {caveat}{assignment_line}"


def _experiment_lane_html(cards: list[dict], experiment_id: str) -> str:
    lines = "".join(
        '<div class="panel composite-card"><div class="slot-label">'
        f"<span>{_esc(str(card.get('symbol', '?')))}</span>"
        f'<span class="status-badge {_experiment_state_class(str(card.get("state", "?")))}">'
        f"{_esc(str(card.get('state', '?')))}</span>"
        f"</div><div>{_esc(_experiment_card_line(card))}</div></div>"
        for card in cards
    )
    return f'<div class="eyebrow">{_esc(experiment_id)}</div><div class="card-grid">{lines}</div>'


def _safe_experiment_lane_html(cards: list[dict], experiment_id: str, asof: str) -> str:
    try:
        return _experiment_lane_html(cards, experiment_id)
    except Exception as exc:
        return _experiment_lane_html([_error_card(experiment_id, asof, exc)], experiment_id)


def _experiments_html(data: Mapping[str, object], *, build_asof: str) -> str:
    lanes = "".join(
        _safe_experiment_lane_html(
            data.get(key) if isinstance(data.get(key), list) else [],
            experiment_id,
            build_asof,
        )
        for key, experiment_id, _source, _builder_name in _LANES
    )
    return (
        '<section class="panel"><div class="section-header"><div>'
        '<div class="eyebrow">EXPERIMENT HEALTH + COMPARISON</div>'
        "<h2>Experiments — display-only (not part of Top-3 ranking)</h2>"
        "<p>display-only research experiments — not part of Top-3 ranking, "
        "no verdict authority.</p>"
        f'<div class="label">Build max as-of {_esc(build_asof)}</div>'
        "<p>Isolated descriptive views. Missing data stays visibly blocked; "
        "each lane keeps its own data source and max as-of stamp.</p></div></div>"
        f"{_experiment_health_html(data)}{lanes}"
        '<div class="notice watch">Limitations: display-only and descriptive, '
        "not predictive. The chain lane is frozen at 2026-07-27 while closes "
        "currently extend to 2026-08-04; constants are LLM-proposed and not "
        "owner-ratified. Promotion requires a separate owner decision and every "
        "applicable registration and feasibility gate.</div></section>"
    )


def _error_card(experiment_id: str, asof: str, exc: Exception) -> dict:
    return {
        "symbol": "ALL",
        "experiment_id": experiment_id,
        "state": "ERROR",
        "data_blocked": False,
        "reason": f"{type(exc).__name__}: {exc}",
        "max_asof": asof,
        "caveat": "This lane failed; the other display-only lanes were still rendered.",
    }


def build_experiment_lanes(symbols: list[str], *, asof: str) -> dict[str, list[dict]]:
    """Build every lane and turn a lane exception into a visible ERROR card."""
    builders: dict[str, Callable[..., list[dict]]] = {
        "build_exp_beta_board": build_exp_beta_board,
        "build_exp_tail_board": build_exp_tail_board,
        "build_exp_spread_board": build_exp_spread_board,
        "build_exp_tbill_board": build_exp_tbill_board,
    }
    data: dict[str, list[dict]] = {}
    for key, experiment_id, _source, builder_name in _LANES:
        try:
            data[key] = builders[builder_name](symbols, asof=asof)
        except Exception as exc:
            data[key] = [_error_card(experiment_id, asof, exc)]
    return data


def render(data: Mapping[str, object], *, build_asof: str) -> str:
    """Render a self-contained experiments-only HTML artifact."""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Display-only research experiments</title>"
        f"<style>{_STYLE}</style></head><body>"
        '<header class="app-header"><div class="app-header-inner">'
        '<div><div class="eyebrow">Options research · experiments</div>'
        "<h1>Display-only research experiments</h1>"
        '<p class="header-sub">Not part of Top-3 ranking; no verdict authority.</p>'
        f'<div class="label">Build max as-of {_esc(build_asof)}</div></div>'
        '<div class="meta-row"><span class="meta-chip">Paper research</span></div>'
        '</div></header><main class="page-body">'
        f"{_experiments_html(data, build_asof=build_asof)}"
        '<footer class="page-footer">Display-only descriptive history, not a '
        "forecast or trading authorization.</footer>"
        "</main></body></html>"
    )


_STYLE = """
  :root { color-scheme: light; --ink:#172033; --muted:#5b667a; --line:#d9dfeb;
    --panel:#fff; --bg:#f5f7fb; --good:#197a4b; --bad:#a33b3b; --unknown:#80651b; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 -apple-system,
    BlinkMacSystemFont,"Segoe UI",sans-serif; }
  .app-header { background:#172033; color:#fff; padding:28px 5vw; }
  .app-header-inner, .page-body { max-width:1200px; margin:0 auto; }
  .page-body { padding:28px 5vw 48px; }
  h1, h2 { margin:0 0 8px; line-height:1.15; }
  h1 { font-size:clamp(28px,4vw,44px); }
  h2 { font-size:22px; }
  p { color:var(--muted); margin:8px 0; }
  .header-sub { color:#dbe4f5; }
  .eyebrow, .label { color:var(--muted); font-size:12px; letter-spacing:.08em;
    text-transform:uppercase; }
  .app-header .eyebrow, .app-header .label { color:#b8c7df; }
  .meta-row, .slot-label { display:flex; gap:10px; align-items:center; justify-content:space-between; }
  .meta-row { margin-top:18px; flex-wrap:wrap; justify-content:flex-start; }
  .meta-chip { background:#263550; border:1px solid #4b5c7d; border-radius:999px;
    padding:5px 10px; color:#eef3fb; font-size:12px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:14px;
    padding:20px; margin:0 0 18px; box-shadow:0 3px 12px rgba(23,32,51,.04); }
  .section-header { margin-bottom:16px; }
  .card-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:12px; }
  .composite-card { margin:0; padding:14px; box-shadow:none; }
  .status-badge { display:inline-block; border-radius:999px; padding:2px 8px; font-size:11px;
    font-weight:700; letter-spacing:.04em; }
  .status-badge.good { color:var(--good); background:#e4f5eb; }
  .status-badge.bad { color:var(--bad); background:#fbe8e8; }
  .status-badge.unknown { color:var(--unknown); background:#fff5cf; }
  .notice { border-radius:10px; padding:12px 14px; margin-top:16px; }
  .notice.watch { background:#fff7df; border:1px solid #edcf77; }
  .page-footer { color:var(--muted); font-size:12px; margin-top:24px; }
"""


def main() -> int:
    asof = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    data = build_experiment_lanes(list(config.ATTRACTIVENESS_UNIVERSE), asof=asof)
    output_path = Path(EXPERIMENTS_OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f"{output_path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(render(data, build_asof=asof))
    os.replace(tmp_path, output_path)
    print(f"wrote {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
