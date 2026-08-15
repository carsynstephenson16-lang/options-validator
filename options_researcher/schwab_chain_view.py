"""Read-only DISPLAY view over VERIFIED Schwab pre-close chain sessions.

This is the ONE boundary module between the write-once Schwab capture store
(``options_researcher/schwab_chain_capture.py``) and the display layer. Nothing
else may read ``.cache/schwab_chains`` for rendering.

Three properties this module exists to guarantee:

* **Verified only.** A session is consumable only when
  ``tools.schwab_chain_manifest.verify_session`` succeeds against the session's
  OWN manifest universe (sha256 per file, row/expiration counts, receipt
  binding, ``force is False``, pre-close timing). A verification failure makes
  the session ABSENT and is reported to the caller so the page can say so out
  loud -- never a silent fallback to stale data.
* **Never an end-of-day close.** These are 15:45 ET snapshots. Every caller
  gets ``CONVENTION_LABEL`` / ``CLOSE_KIND`` so no surface can present the data
  as an EOD close (``h7_watch.py``'s standing invariant).
* **No writes, no network.** Reads local parquet and JSON only.

Nothing here is verdict-bearing, FIRE-capable, or a registered hypothesis
input. Spec: docs/superpowers/plans/2026-08-14-12-schwab-display-freshness-spec.md
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import pandas as pd

from tools.schwab_chain_manifest import (
    SchwabChainManifestError,
    verify_session,
)

# Mirrors the writer's paths (schwab_chain_capture.py:42-43). Deliberately
# module literals rather than config.py values: any config.py edit invalidates
# every capture receipt's config_hash (intraday_preview.py:81) until the next
# live capture, which would kill the intraday panel until the next session.
CHAIN_DIR = Path(".cache/schwab_chains")
REPORTS_DIR = Path("reports/schwab_chains")
INTRADAY_REPORTS_DIR = Path("reports/intraday_capture")

# PROVENANCE: owner-directed in-session 2026-08-14 ("i dont care abt et and
# usar just all the other tickers i cached for"). This exclusion applies to the
# FRESH display path only. The registered H7 cohort, h7_scope.watch_universe(),
# every capture universe, and each name's existing stale-path rendering are
# untouched -- an excluded name is still shown on the board from the frozen
# ThetaData cache, never silently dropped.
DISPLAY_EXCLUDED_SYMBOLS = frozenset({"ET", "USAR"})

# PROVENANCE: the store's own convention tag is ``preclose_snapshot_v1``
# (tools/schwab_chain_manifest.py:18). This is its human label; every date
# surface that shows schwab-sourced data must carry it.
CONVENTION_LABEL = "15:45 pre-close (Schwab)"
HEADER_CHIP_LABEL = "Pre-close 15:45 (Schwab)"
CHAIN_SOURCE = "schwab_preclose"
THETADATA_CHAIN_SOURCE = "thetadata_eod"
CLOSE_KIND = "preclose_mid_1545"
EOD_CLOSE_KIND = "eod_close"

# The display schema. gamma/theta/vega are native in the store and are kept so
# the frame is column-compatible with a ThetaData cache frame.
DISPLAY_COLUMNS = [
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "open_interest",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
]

class _ChainsAbsent(RuntimeError):
    """The receipt is present but its chain files are not in this checkout."""


# Failure kinds. MEASURED 2026-08-15: the capture RECEIPTS are tracked in git
# (commit 13d48a9, "first real Schwab preclose canary") but the chain parquet
# lives only in the ops execution checkout. Every research checkout therefore
# sees a receipt whose files are absent -- an expected deployment fact, not an
# integrity failure, and it must not render as a permanent red alarm that
# trains the reader to ignore the real one.
UNVERIFIED = "unverified"
CHAINS_ABSENT = "chains_absent"

# (cwd, chain_dir, reports_dir, session) -> (symbols | None, failure | None).
# Keyed on the resolved cwd because every path here is relative: the dashboard
# reads inputs under an explicitly switched root (_input_root_cwd), and a memo
# that survived that switch would answer for the wrong checkout.
_SESSION_MEMO: dict[
    tuple[str, str, str, str], tuple[list[str] | None, dict[str, str] | None]
] = {}


def _reset_memo_for_tests() -> None:
    """Clear the in-process verification memo (tests only)."""
    _SESSION_MEMO.clear()


def _canonical_session(value: str) -> str | None:
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError:
        return None
    return value if parsed.isoformat() == value else None


def _dirs(chain_dir: Path | str | None,
          reports_dir: Path | str | None) -> tuple[Path, Path]:
    return (Path(chain_dir) if chain_dir is not None else CHAIN_DIR,
            Path(reports_dir) if reports_dir is not None else REPORTS_DIR)


def _verify_one(session: str, chain_dir: Path,
                reports_dir: Path) -> tuple[list[str] | None, dict[str, str] | None]:
    """Verify one session against its OWN manifest universe.

    Reading the universe from the manifest (rather than assuming a fixed
    watchlist) is deliberate: a session captured with a different universe must
    still be verifiable on its own terms, and a mismatched hard-coded list would
    silently make every session unverifiable -- a total, invisible no-op.
    """
    key = (
        str(Path.cwd()),
        str(chain_dir),
        str(reports_dir),
        session,
    )
    memoized = _SESSION_MEMO.get(key)
    if memoized is not None:
        return memoized

    manifest_path = reports_dir / session / "manifest.json"
    receipt_path = reports_dir / session / "preclose.json"
    result: tuple[list[str] | None, dict[str, str] | None]
    try:
        manifest = json.loads(manifest_path.read_text())
        if not isinstance(manifest, dict):
            raise SchwabChainManifestError("manifest must be a JSON object")
        symbols = manifest.get("symbols")
        if (not isinstance(symbols, list)
                or not symbols
                or not all(isinstance(item, str) for item in symbols)):
            raise SchwabChainManifestError("manifest symbols are unusable")
        if not any((chain_dir / f"{symbol}_{session}.parquet").is_file()
                   for symbol in symbols):
            raise _ChainsAbsent(
                f"no chain files for session {session} in {chain_dir}")
        verify_session(session, symbols, chain_dir, manifest_path, receipt_path)
        result = ([str(symbol) for symbol in symbols], None)
    except _ChainsAbsent as exc:
        result = (None, {"session": session, "kind": CHAINS_ABSENT,
                         "reason": str(exc)})
    except (SchwabChainManifestError, OSError, ValueError) as exc:
        result = (None, {"session": session, "kind": UNVERIFIED,
                         "reason": f"{type(exc).__name__}: {exc}"})
    _SESSION_MEMO[key] = result
    return result


def verified_sessions(
    *,
    chain_dir: Path | str | None = None,
    reports_dir: Path | str | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Return ``(verified_sessions_ascending, failures)``.

    Each failure is ``{"session", "kind", "reason"}``. ``kind`` is
    ``UNVERIFIED`` for a package that exists but does not verify (a loud page
    state -- never a quiet fallback) or ``CHAINS_ABSENT`` for the expected
    research-checkout case where the tracked receipt has no local chain files.
    Empty sessions AND empty failures means "no Schwab receipts on disk".
    """
    chain_dir, reports_dir = _dirs(chain_dir, reports_dir)
    sessions: list[str] = []
    failures: list[dict[str, str]] = []
    for receipt_path in sorted(reports_dir.glob("*/preclose.json")):
        session = _canonical_session(receipt_path.parent.name)
        if session is None:
            continue
        symbols, failure = _verify_one(session, chain_dir, reports_dir)
        if symbols is None and failure is not None:
            failures.append(failure)
        elif symbols is not None:
            sessions.append(session)
    return sorted(sessions), failures


def session_symbols(
    session: str,
    *,
    chain_dir: Path | str | None = None,
    reports_dir: Path | str | None = None,
) -> list[str]:
    """Return the VERIFIED universe of one session, or [] when unverified."""
    chain_dir, reports_dir = _dirs(chain_dir, reports_dir)
    canonical = _canonical_session(session)
    if canonical is None:
        return []
    symbols, _failure = _verify_one(canonical, chain_dir, reports_dir)
    return list(symbols or [])


def load_chain(
    symbol: str,
    session: str,
    *,
    chain_dir: Path | str | None = None,
) -> pd.DataFrame:
    """Load one verified session's chain in the display schema.

    ``iv`` is passed through UNCHANGED. The store's IV is already a decimal
    fraction: ``data/schwab_adapter.py:148-154`` (``_iv_decimal``) divides
    Schwab's percentage-point ``volatility`` by 100 at capture time. Dividing
    again here would render every implied vol ~100x too small and turn every
    IV badge into a lie.

    Non-standard and mini contracts are dropped: the ThetaData cache these
    frames stand in for is standard contracts only.
    """
    chain_dir, _reports = _dirs(chain_dir, None)
    frame = pd.read_parquet(chain_dir / f"{symbol}_{session}.parquet")
    for flag in ("non_standard", "mini"):
        if flag in frame.columns:
            frame = frame.loc[frame[flag] != True]  # noqa: E712 - NaN-safe
    missing = [column for column in DISPLAY_COLUMNS if column not in frame.columns]
    if missing:
        raise SchwabChainManifestError(
            f"schwab chain {symbol}_{session} is missing display columns: {missing}"
        )
    out = frame.loc[:, DISPLAY_COLUMNS].copy()
    out["open_interest"] = out["open_interest"].fillna(0).astype("int64")
    return out.reset_index(drop=True)


def newest_chain(
    symbol: str,
    *,
    chain_dir: Path | str | None = None,
    reports_dir: Path | str | None = None,
) -> tuple[pd.DataFrame, str] | None:
    """Newest VERIFIED session containing ``symbol``: ``(frame, session)``.

    Returns None for a display-excluded name and when no verified session
    carries the symbol. Exclusion is applied strictly AFTER verification so an
    excluded name can never change whether a session verifies.
    """
    name = str(symbol).upper()
    if name in DISPLAY_EXCLUDED_SYMBOLS:
        return None
    sessions, _failures = verified_sessions(
        chain_dir=chain_dir, reports_dir=reports_dir)
    for session in reversed(sessions):
        if name not in session_symbols(
                session, chain_dir=chain_dir, reports_dir=reports_dir):
            continue
        return load_chain(name, session, chain_dir=chain_dir), session
    return None


def load_preclose_spot(
    symbol: str,
    session: str,
    *,
    reports_dir: Path | str | None = None,
) -> tuple[float, str] | None:
    """Return ``(spot_mid, spot_ts)`` from the 15:45 intraday capture receipt.

    The Schwab chain lane records no underlying price, and the closes store is
    frozen well behind these sessions, so pairing a fresh chain with a stale
    close would misprice moneyness by several percent. This is the one
    internally consistent pairing available: both sides are the same 15:45
    instant.

    Fail-closed: the per-name record must be ``status == "ok"`` with a finite
    ``spot_mid`` from ``spot_source == "stock_snapshot"`` (never a parity
    fallback), on an unforced receipt for exactly this session. Any miss
    returns None and the caller must refuse to render the fresh chain.

    Deliberately does NOT check ``config_hash``: this is a display-only reader
    of an already-written receipt, and a config edit must not retro-invalidate
    a capture that was honest when it was taken (that check belongs to the live
    intraday panel, ``intraday_preview.py:81``).
    """
    root = Path(reports_dir) if reports_dir is not None else INTRADAY_REPORTS_DIR
    canonical = _canonical_session(session)
    if canonical is None:
        return None
    try:
        receipt = json.loads((root / canonical / "preclose.json").read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(receipt, dict):
        return None
    if receipt.get("receipt_kind") != "intraday_capture/v1":
        return None
    if receipt.get("force") is not False:
        return None
    if receipt.get("session_tag") != "preclose":
        return None
    names = receipt.get("names")
    record = names.get(str(symbol).upper()) if isinstance(names, dict) else None
    if not isinstance(record, dict):
        return None
    if record.get("status") != "ok" or record.get("spot_source") != "stock_snapshot":
        return None
    spot = record.get("spot_mid")
    if isinstance(spot, bool) or not isinstance(spot, (int, float)):
        return None
    spot = float(spot)
    if not math.isfinite(spot) or spot <= 0.0:
        return None
    timestamp = record.get("spot_ts")
    return spot, str(timestamp) if timestamp is not None else ""


def preclose_iv_rank_preview(
    symbol: str,
    session: str,
    *,
    reports_dir: Path | str | None = None,
) -> float | None:
    """Capture-lane IV-rank PREVIEW for one name, or None.

    This is the intraday lane's own preview rank, not the attractiveness
    feature store's percentile. It is never mixed with the ThetaData IV series:
    a percentile computed by splicing two providers' IV histories across a
    two-week hole would be a fabricated number.
    """
    root = Path(reports_dir) if reports_dir is not None else INTRADAY_REPORTS_DIR
    canonical = _canonical_session(session)
    if canonical is None:
        return None
    try:
        receipt = json.loads((root / canonical / "preclose.json").read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(receipt, dict) or receipt.get("force") is not False:
        return None
    names = receipt.get("names")
    record = names.get(str(symbol).upper()) if isinstance(names, dict) else None
    if not isinstance(record, dict) or record.get("status") != "ok":
        return None
    value = record.get("iv_rank_preview")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not math.isfinite(value) or not (0.0 <= value <= 1.0):
        return None
    return value


def as_of_label(session: str) -> str:
    """The one honest way to print a schwab session date on any surface."""
    return f"{session} · {CONVENTION_LABEL}"


__all__ = [
    "CHAINS_ABSENT",
    "CHAIN_DIR",
    "CHAIN_SOURCE",
    "CLOSE_KIND",
    "CONVENTION_LABEL",
    "DISPLAY_COLUMNS",
    "DISPLAY_EXCLUDED_SYMBOLS",
    "EOD_CLOSE_KIND",
    "HEADER_CHIP_LABEL",
    "INTRADAY_REPORTS_DIR",
    "REPORTS_DIR",
    "THETADATA_CHAIN_SOURCE",
    "UNVERIFIED",
    "as_of_label",
    "load_chain",
    "load_preclose_spot",
    "newest_chain",
    "preclose_iv_rank_preview",
    "session_symbols",
    "verified_sessions",
]
