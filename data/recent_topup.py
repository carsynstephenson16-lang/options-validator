"""data/recent_topup.py -- keep forward-paper chain caches current.

The one-month paid-cache plan (data/cache_runner.py) filled history through
config.BACKTEST_END. The H5 forward window then advances in real time, so new
EOD chains must be topped up as sessions pass. This module answers "which
recent trading days are missing?" (pure, tested here) and blind-caches them
via the same integrity-safe path cache_runner uses.

INTEGRITY: recent days are fetched by EXPLICIT DATE through blind_cache_chain
(writes parquet, surfaces no values, logs a BLIND_CACHE fact) -- config
boundaries (BACKTEST_END, IN_SAMPLE_END) are NEVER moved to admit them. Today
is always excluded: its EOD report is not finalized until the next session
(ThetaData refuses current-day bulk EOD), and substituting an intraday snapshot
would violate the EOD-gaps guardrail.

ORCHESTRATOR-ONLY network path: run_topup / the CLI are executed by the
controlling session after review, exactly like data/underlying_closes.
fetch_underlying_eod. Tests cover only the pure day-selection and audit logic.

Scheduled guarded path authorized by owner in-session 2026-08-20 (Decision 2 =
yes: automate the Yahoo closes refresh as a guarded daily ritual step); see
docs/superpowers/plans/2026-08-20-18-ok-starved-and-closes-cadence-codex-brief.md.

Run from the repo root:
    python data/recent_topup.py --dry-run
    python data/recent_topup.py --scope h7 --dry-run
    python data/recent_topup.py --scope display-extra --dry-run

Non-dry-run ThetaData top-up is operator-disabled as of 2026-07-31. Explicit
offline inventory and immutable cached reads remain available.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from data import (
    provider_policy,  # noqa: E402
    thetadata_adapter,  # noqa: E402
)
from data.atomic_io import atomic_text_write  # noqa: E402

# Strategy-selectable moneyness band (|delta|). Deep-ITM (|delta|~1) contracts
# carry benign IV=0 solver artifacts and far-OTM tails carry wide spreads; the
# H5 income lanes (CSP / covered call / PMCC) select inside this band, so audit
# BLOCKs gate on it while everything else is a warning.
SELECTABLE_ABS_DELTA = (0.15, 0.85)
MAX_IV = 5.0  # 500%


def scope_symbols(scope: str) -> list[str]:
    """Return a canonical, owner-scoped top-up universe.

    The default/core scope preserves the original four-name H5 behavior.
    H7 and the display-only extras are explicit because each is a larger paid-
    data operation and must never happen merely because a caller omitted an
    argument. The display-extra scope does not amend or extend H7.
    """
    if scope == "core":
        return list(config.UNIVERSE)
    if scope == "h7":
        from options_researcher.h7_scope import watch_universe

        return list(dict.fromkeys(watch_universe()))
    if scope == "display-extra":
        return list(config.ATTRACTIVENESS_EXTRA_NAMES)
    raise ValueError(f"unknown top-up scope: {scope!r}")


def _append_closes_fact(text: str, *, ledger_dir: str) -> None:
    from research import facts

    facts.append_fact(text, base_dir=ledger_dir)


# --------------------------------------------------------------------------
# Closes-refresh provenance receipt (finding DATA-03; brief 33).
#
# HONESTY CONSTRAINT -- read before extending this schema. The closes fetchers
# return a PATH, never a data frame and never the provider's raw response
# (data/underlying_closes.py:265 -> store_closes(...) at :290), and
# refresh_closes_guarded discards the return value and re-reads the file from
# disk. The receipt can therefore bind exactly ONE hash class: the sha256 of
# the STORED close parquet, read back immediately after that symbol's refresh
# step. That is a stored-artifact binding at acquisition time, NOT a hash of
# raw provider bytes -- nothing in this repo retains those bytes, and a field
# claiming otherwise would be false provenance.
# --------------------------------------------------------------------------

CLOSES_RECEIPT_DIR = Path("reports") / "closes_receipts"
CLOSES_RECEIPT_SCHEMA = "closes_refresh_receipt/v1"
CLOSES_VERIFICATION_SCHEMA = "closes_refresh_receipt_verification/v1"
# Scope discriminators are frozen: the guarded producer always writes
# `guarded-all-cached.json`; plain refresh_closes uses its CLI --scope value
# verbatim (core / h7 / display-extra).
GUARDED_CLOSES_SCOPE = "guarded-all-cached"
CLOSES_HASH_BINDING = (
    "stored_file_sha256 is the sha256 of the STORED close parquet, read back "
    "from disk immediately after that symbol's refresh step. It is NOT a hash "
    "of the provider's raw response: the fetcher returns a path and retains no "
    "raw bytes."
)
# Frozen outcome vocabulary. Every globbed symbol is attempted, so there is no
# `skipped` state; `failed` always carries one of CLOSES_FAILURE_STAGES.
CLOSES_OUTCOMES = ("refreshed", "restored", "failed")
CLOSES_FAILURE_STAGES = ("pre_read", "fetch", "post_read")


def _provider_identity(fetch_fn) -> str:
    """Dotted identity of the function that performed the acquisition."""
    module = getattr(fetch_fn, "__module__", None) or "unknown"
    name = getattr(fetch_fn, "__qualname__", None) or repr(fetch_fn)
    return f"{module}.{name}"


def _stored_file_fields(path: Path | None) -> dict:
    """`stored_file` + `stored_file_sha256` for one symbol's close parquet.

    A missing file yields a null hash rather than an exception: a symbol whose
    file vanished mid-run must still appear in the receipt.
    """
    if path is None:
        return {"stored_file": None, "stored_file_sha256": None}
    fields: dict = {"stored_file": str(path), "stored_file_sha256": None}
    try:
        if path.is_file():
            fields["stored_file_sha256"] = _sha256(path)
    except OSError as error:
        fields["stored_file_error"] = f"{type(error).__name__}: {error}"
    return fields


def _closes_entry(outcome: str, path: Path | None, max_session, **extra) -> dict:
    """One per-symbol receipt entry in the frozen vocabulary."""
    if outcome not in CLOSES_OUTCOMES:
        raise ValueError(f"unknown closes outcome: {outcome!r}")
    stage = extra.pop("stage", None)
    if outcome == "failed":
        if stage not in CLOSES_FAILURE_STAGES:
            raise ValueError(f"failed outcome needs a known stage, got {stage!r}")
    elif stage is not None:
        raise ValueError(f"stage is only valid on a failed outcome, got {outcome!r}")
    entry = {"outcome": outcome, "max_session": max_session, **_stored_file_fields(path)}
    if stage is not None:
        entry["stage"] = stage
    entry.update(extra)
    return entry


def _closes_receipt_payload(
    *, producer: str, scope: str, run_date: str, provider: str, requested_symbols, symbols: dict
) -> dict:
    return {
        "schema": CLOSES_RECEIPT_SCHEMA,
        "producer": producer,
        "scope": scope,
        "run_date": run_date,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": provider,
        "hash_binding": CLOSES_HASH_BINDING,
        "requested_symbols": list(requested_symbols),
        "symbols": symbols,
    }


def write_closes_receipt(payload: dict, *, receipts_dir: Path | str = CLOSES_RECEIPT_DIR) -> Path:
    """Create one dated, scoped closes receipt; byte-identical replay is a no-op.

    ``atomic_text_write``'s exclusive create (``temp.open("x")``) applies to
    its PID-named TEMP file only, and its ``os.replace`` then overwrites the
    destination unconditionally (data/atomic_io.py:70-76). The explicit
    pre-write existence check below is therefore the actual overwrite
    protection -- the same shape as
    ``options_researcher.h7_data_gate.write_artifact`` (:768-771).
    """
    path = Path(receipts_dir) / str(payload["run_date"]) / f"{payload['scope']}.json"
    text = json.dumps(payload, sort_keys=True, indent=1, ensure_ascii=True, allow_nan=False) + "\n"
    if path.exists():
        if path.read_text() != text:
            raise FileExistsError(f"refusing to overwrite closes receipt: {path}")
        return path
    atomic_text_write(text, path)
    return path


def _emit_closes_receipt(payload: dict, *, receipts_dir) -> tuple[Path | None, Exception | None]:
    """Write the receipt without losing the failure.

    The caller records the outcome in its DATA_PULL fact -- so a refresh that
    really happened is never unrecorded -- and then re-raises.
    """
    try:
        return write_closes_receipt(payload, receipts_dir=receipts_dir), None
    except Exception as error:
        return None, error


def _receipt_fact_token(path: Path | None, error: Exception | None) -> str:
    if error is not None:
        return f"UNWRITTEN ({type(error).__name__}: {error})"
    return str(path)


def _resolve_stored_close_path(returned, symbol: str, cache_dir) -> Path:
    """The stored close file for `symbol`, preferring the fetcher's own path."""
    candidates = []
    if isinstance(returned, (str, Path)):
        candidates.append(Path(returned))
    candidates.append(Path(cache_dir) / f"{symbol}.parquet")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _stored_max_session(path: Path) -> str | None:
    """Newest session in a stored close file; None when unreadable.

    Descriptive only. The guarded producer uses its own guard-aware max dates
    instead, so this never competes with the guard's decision logic.
    """
    if not path.is_file():
        return None
    try:
        frame = pd.read_parquet(path)
    except Exception:
        return None
    if "date" not in frame.columns or frame.empty:
        return None
    return max(str(value) for value in frame["date"])


def refresh_closes(
    symbols,
    *,
    today: str,
    ledger_dir: str = "ledger",
    fetch_fn=None,
    scope: str = "core",
    receipts_dir: Path | str = CLOSES_RECEIPT_DIR,
) -> dict:
    """Refresh independent Yahoo closes for exactly the selected scope.

    This is an explicit network path used by the owner-run cancellation
    workflow. It never runs during ``--dry-run`` and is injectable so tests
    remain offline. Scheduled guarded path authorized by owner in-session
    2026-08-20 (Decision 2 = yes: automate the Yahoo closes refresh as a
    guarded daily ritual step); see
    docs/superpowers/plans/2026-08-20-18-ok-starved-and-closes-cadence-codex-brief.md.

    A provenance receipt is written under ``receipts_dir/<today>/<scope>.json``
    and its path is named in the DATA_PULL fact. Unlike the guarded producer
    this path has no per-symbol error isolation -- a fetch exception aborts the
    whole call, exactly as before -- so a receipt is emitted only for a run
    that attempted every symbol. Emitting a partial receipt would require an
    "unattempted" outcome, which the frozen vocabulary deliberately excludes.
    """
    if fetch_fn is None:
        from data.underlying_closes import fetch_underlying_eod_yahoo

        fetch_fn = fetch_underlying_eod_yahoo
    from data import underlying_closes

    result = {symbol: fetch_fn(symbol) for symbol in symbols}
    entries = {}
    for symbol, returned in result.items():
        path = _resolve_stored_close_path(returned, symbol, underlying_closes.CACHE_DIR)
        entries[symbol] = _closes_entry("refreshed", path, _stored_max_session(path))
    payload = _closes_receipt_payload(
        producer="data.recent_topup.refresh_closes",
        scope=scope,
        run_date=today,
        provider=_provider_identity(fetch_fn),
        requested_symbols=symbols,
        symbols=entries,
    )
    receipt_path, receipt_error = _emit_closes_receipt(payload, receipts_dir=receipts_dir)
    _append_closes_fact(
        f"DATA_PULL {today}: Yahoo closes refresh for forward scope "
        f"({'/'.join(symbols)}); same-day partial rows excluded by fetcher. "
        f"receipt={_receipt_fact_token(receipt_path, receipt_error)}",
        ledger_dir=ledger_dir,
    )
    if receipt_error is not None:
        raise receipt_error
    return result


def refresh_closes_guarded(
    *,
    today: str,
    ledger_dir: str = "ledger",
    fetch_fn=None,
    receipts_dir: Path | str = CLOSES_RECEIPT_DIR,
) -> dict:
    """Refresh every existing Yahoo closes cache with a retroactive-change guard.

    Each symbol is read before fetching and again afterward. If a fetched
    history changes an existing date beyond the relative tolerance, or drops
    an existing date entirely (a truncated provider response), the old frame
    is restored and the first differing or missing date is reported. A restored
    symbol stays stale until the owner amends ``SPLITS``; the closes freshness
    chip surfaces that designed, fail-visible outcome. Scheduled guarded path
    authorized by owner in-session 2026-08-20 (Decision 2 = yes: automate the
    Yahoo closes refresh as a guarded daily ritual step); see
    docs/superpowers/plans/2026-08-20-18-ok-starved-and-closes-cadence-codex-brief.md.

    Per-symbol read, fetch, and restore failures are recorded and do not abort
    the remaining symbols. Exactly one descriptive DATA_PULL fact is appended
    for every invocation, including when every symbol fails and including a
    run whose receipt could not be written (the fact says so, and the receipt
    error is then re-raised).

    A provenance receipt is written to
    ``receipts_dir/<today>/guarded-all-cached.json`` binding each symbol's
    stored-file sha256 at acquisition time; see the honesty constraint above
    ``CLOSES_RECEIPT_DIR``.
    """
    from data import underlying_closes

    cache_dir = Path(underlying_closes.CACHE_DIR)
    symbols = sorted(
        path.stem for path in cache_dir.glob("*.parquet") if path.is_file()
    )
    if fetch_fn is None:
        fetch_fn = underlying_closes.fetch_underlying_eod_yahoo

    max_dates: dict[str, str | None] = {}
    restored_symbols: dict[str, str] = {}
    restore_failed: dict[str, str] = {}
    fetch_errors: dict[str, list[str]] = {}
    # Per-symbol receipt entries, recorded at each terminal state so the hash
    # is taken immediately after that symbol's refresh step.
    outcomes: dict[str, dict] = {}
    ok_count = 0

    def _read_frame(path: Path, phase: str) -> pd.DataFrame:
        frame = pd.read_parquet(path)
        if list(frame.columns) != ["date", "close"]:
            raise ValueError(
                f"{phase}: expected columns ['date','close'], got {list(frame.columns)}"
            )
        return frame

    def _max_date(frame: pd.DataFrame) -> str | None:
        if frame.empty:
            return None
        return max(str(value) for value in frame["date"])

    def _values_by_date(frame: pd.DataFrame) -> dict[str, float]:
        return {
            str(day): float(close)
            for day, close in zip(frame["date"], frame["close"])
        }

    for symbol in symbols:
        path = cache_dir / f"{symbol}.parquet"
        try:
            before = _read_frame(path, "pre-read")
        except Exception as error:
            fetch_errors[symbol] = [f"pre-read: {type(error).__name__}: {error}"]
            max_dates[symbol] = None
            outcomes[symbol] = _closes_entry(
                "failed",
                path,
                max_dates[symbol],
                stage="pre_read",
                error=f"{type(error).__name__}: {error}",
            )
            continue

        try:
            fetch_fn(symbol)
        except Exception as error:
            fetch_errors[symbol] = [f"fetch: {type(error).__name__}: {error}"]
            max_dates[symbol] = _max_date(before)
            outcomes[symbol] = _closes_entry(
                "failed",
                path,
                max_dates[symbol],
                stage="fetch",
                error=f"{type(error).__name__}: {error}",
            )
            continue

        try:
            after = _read_frame(path, "post-read")
        except Exception as error:
            fetch_errors[symbol] = [f"post-read: {type(error).__name__}: {error}"]
            max_dates[symbol] = None
            outcomes[symbol] = _closes_entry(
                "failed",
                path,
                max_dates[symbol],
                stage="post_read",
                error=f"{type(error).__name__}: {error}",
            )
            continue

        try:
            before_by_date = _values_by_date(before)
            after_by_date = _values_by_date(after)
        except Exception as error:
            fetch_errors[symbol] = [
                f"post-read: {type(error).__name__}: {error}"
            ]
            max_dates[symbol] = _max_date(after)
            outcomes[symbol] = _closes_entry(
                "failed",
                path,
                max_dates[symbol],
                stage="post_read",
                error=f"{type(error).__name__}: {error}",
            )
            continue
        first_difference: str | None = None
        for day in sorted(set(before_by_date) & set(after_by_date)):
            old_close = before_by_date[day]
            new_close = after_by_date[day]
            if math.isnan(old_close) or math.isnan(new_close):
                changed = not (math.isnan(old_close) and math.isnan(new_close))
            else:
                changed = not math.isclose(
                    old_close, new_close, rel_tol=1e-4, abs_tol=0.0
                )
            if changed:
                first_difference = day
                break
        if first_difference is None:
            # A date present before but absent after is a truncated provider
            # response (observed live: Yahoo range=max returning 34-233 rows);
            # a pure intersection check would let it silently shorten the
            # cached history, so deletion counts as a retroactive change.
            deleted = sorted(set(before_by_date) - set(after_by_date))
            if deleted:
                first_difference = deleted[0]

        if first_difference is not None:
            try:
                underlying_closes.store_closes(symbol, before)
            except Exception as error:
                restore_failed[symbol] = f"{type(error).__name__}: {error}"
                max_dates[symbol] = _max_date(after)
                # The guard did NOT roll back, so the bytes on disk are the
                # CHANGED ones. Labelling this `restored` would be false
                # provenance; it is a failure detected and acted on in the
                # post-read stage, so it takes that frozen stage value.
                outcomes[symbol] = _closes_entry(
                    "failed",
                    path,
                    max_dates[symbol],
                    stage="post_read",
                    error=(
                        f"restore after retroactive change at {first_difference} "
                        f"failed: {type(error).__name__}: {error}"
                    ),
                    retroactive_change_session=first_difference,
                )
            else:
                restored_symbols[symbol] = first_difference
                max_dates[symbol] = _max_date(before)
                # Hash the RESTORED file: the true post-run state.
                outcomes[symbol] = _closes_entry(
                    "restored",
                    path,
                    max_dates[symbol],
                    retroactive_change_session=first_difference,
                )
        else:
            max_dates[symbol] = _max_date(after)
            ok_count += 1
            outcomes[symbol] = _closes_entry("refreshed", path, max_dates[symbol])

    payload = _closes_receipt_payload(
        producer="data.recent_topup.refresh_closes_guarded",
        scope=GUARDED_CLOSES_SCOPE,
        run_date=today,
        provider=_provider_identity(fetch_fn),
        requested_symbols=symbols,
        symbols=outcomes,
    )
    receipt_path, receipt_error = _emit_closes_receipt(payload, receipts_dir=receipts_dir)
    _append_closes_fact(
        f"DATA_PULL {today}: Yahoo closes guarded refresh for cached symbols; "
        f"guard: {ok_count} ok, {len(restored_symbols)} restored, "
        f"{len(restore_failed)} restore failures, "
        f"{len(fetch_errors)} fetch errors. "
        f"receipt={_receipt_fact_token(receipt_path, receipt_error)}",
        ledger_dir=ledger_dir,
    )
    if receipt_error is not None:
        raise receipt_error
    return {
        "max_dates": max_dates,
        "restored_symbols": restored_symbols,
        "restore_failed": restore_failed,
        "fetch_errors": fetch_errors,
        "receipt": str(receipt_path),
    }


def _load_closes_receipt(path: Path) -> dict:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema") != CLOSES_RECEIPT_SCHEMA:
        raise ValueError(f"receipt schema must be {CLOSES_RECEIPT_SCHEMA}: {path}")
    return payload


def _closes_receipt_order(payload: dict) -> tuple[str, str]:
    """Total order over receipts: run date first, then retrieval timestamp."""
    return (str(payload.get("run_date") or ""), str(payload.get("retrieved_utc") or ""))


def verify_closes_receipt(receipt_path: Path | str, *, receipts_dir: Path | str | None = None):
    """Re-hash every stored close file a receipt binds. Offline; writes nothing.

    VALIDITY WINDOW: close files are rewritten in place -- one file per symbol
    (data/underlying_closes.py:24-25) -- so a receipt's hashes are a
    CURRENT-BYTES claim only until that symbol's next refresh, after which the
    receipt is a historical acquisition record. A symbol whose bytes changed
    AND for which a NEWER receipt exists is therefore reported ``superseded``,
    not a mismatch; only a mismatch against the LATEST receipt for that symbol
    is an integrity alarm.
    """
    receipt_path = Path(receipt_path)
    payload = _load_closes_receipt(receipt_path)
    root = Path(receipts_dir) if receipts_dir is not None else receipt_path.parent.parent
    this_order = _closes_receipt_order(payload)

    newer_by_symbol: dict[str, str] = {}
    for other in sorted(root.glob("*/*.json")):
        if other.resolve() == receipt_path.resolve():
            continue
        try:
            other_payload = _load_closes_receipt(other)
        except (OSError, ValueError):
            continue  # not a closes receipt; not evidence either way
        if _closes_receipt_order(other_payload) <= this_order:
            continue
        for symbol in other_payload.get("symbols") or {}:
            newer_by_symbol.setdefault(symbol, str(other))

    symbols: dict[str, dict] = {}
    mismatches: list[str] = []
    superseded: list[str] = []
    for symbol, entry in sorted((payload.get("symbols") or {}).items()):
        expected = entry.get("stored_file_sha256")
        stored = entry.get("stored_file")
        record: dict = {"expected_sha256": expected, "stored_file": stored}
        if symbol in newer_by_symbol:
            record["superseded_by"] = newer_by_symbol[symbol]
        if expected is None:
            # The receipt made no hash claim for this symbol (no stored file
            # after the run), so there is nothing to verify.
            record["status"] = "no_hash_claim"
            symbols[symbol] = record
            continue
        path = Path(stored) if stored else None
        record["actual_sha256"] = (
            _sha256(path) if path is not None and path.is_file() else None
        )
        if record["actual_sha256"] == expected:
            record["status"] = "match"
        elif symbol in newer_by_symbol:
            record["status"] = "superseded"
            superseded.append(symbol)
        else:
            record["status"] = "mismatch"
            mismatches.append(symbol)
        symbols[symbol] = record

    return {
        "schema": CLOSES_VERIFICATION_SCHEMA,
        "receipt": str(receipt_path),
        "run_date": payload.get("run_date"),
        "scope": payload.get("scope"),
        "status": "MISMATCH" if mismatches else "OK",
        "mismatches": mismatches,
        "superseded": superseded,
        "symbols": symbols,
    }


def topup_days(last_cached: str, today: str, *, trading_days_fn=None) -> list[str]:
    """ISO trading days to fetch: strictly after `last_cached` and strictly
    before `today` (today excluded -- its EOD is not final). Holidays and
    weekends drop out via the XNYS calendar."""
    if trading_days_fn is None:
        from data.cache_runner import trading_days as trading_days_fn
    return [d for d in trading_days_fn(last_cached, today) if last_cached < d < today]


def latest_cached_date(symbols, *, cache_dir=None) -> str | None:
    """Legacy file-presence inventory.

    This helper remains for read-only historical diagnostics. Operational
    freshness must use :func:`latest_complete_session`, which also verifies
    the content-bound acquisition fact.

    The cohort's last file-present trading day = the MIN over symbols of
    each symbol's newest cached chain date. None if any symbol has no cache
    (so a never-cached name is never silently skipped). ISO dates sort
    lexicographically, so string max/min is correct."""
    cache_dir = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    per_symbol_latest = []
    for symbol in symbols:
        dates = [p.stem[len(symbol) + 1 :] for p in cache_dir.glob(f"{symbol}_*.parquet")]
        if not dates:
            return None
        per_symbol_latest.append(max(dates))
    return min(per_symbol_latest) if per_symbol_latest else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_complete_session(
    symbols,
    *,
    cache_dir=None,
    facts_path: Path | str = Path("ledger/facts.log"),
) -> str | None:
    """Latest cohort session with a file and matching canonical fact.

    The result is the newest session in the intersection of all per-symbol
    content-bound sessions. Taking the minimum of each symbol's newest session
    is insufficient: another symbol can have a gap on that exact date.
    Orphaned or mismatched newer files are ignored here and become explicit
    tasks in ``run_topup``; the publisher then refuses them unless a reviewed
    recovery manifest or durable pending attestation exists.
    """
    from data.cache_provenance import load_blind_cache_facts

    cache = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    facts_by_key = load_blind_cache_facts(Path(facts_path))
    per_symbol_paths: dict[str, dict[str, Path]] = {}
    for symbol in symbols:
        paths: dict[str, Path] = {}
        for path in cache.glob(f"{symbol}_*.parquet"):
            session = path.stem[len(symbol) + 1 :]
            paths[session] = path
        if not paths:
            return None
        per_symbol_paths[symbol] = paths
    if not per_symbol_paths:
        return None
    common = set.intersection(*(set(paths) for paths in per_symbol_paths.values()))
    for session in sorted(common, reverse=True):
        if all(
            (fact := facts_by_key.get((symbol, session))) is not None
            and fact["sha256"] == _sha256(per_symbol_paths[symbol][session])
            for symbol in symbols
        ):
            return session
    return None


def verify_cohort_provenance(
    symbols,
    session: str,
    *,
    cache_dir=None,
    facts_path: Path | str = Path("ledger/facts.log"),
) -> dict:
    """Fail closed unless every symbol has matching session bytes and fact."""
    from data.cache_provenance import load_blind_cache_facts

    cache = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    facts_by_key = load_blind_cache_facts(Path(facts_path))
    errors: list[str] = []
    identities: dict[str, str] = {}
    for symbol in symbols:
        path = cache / f"{symbol}_{session}.parquet"
        if not path.is_file():
            errors.append(f"{symbol}@{session}: missing cache file {path}")
            continue
        sha256 = _sha256(path)
        fact = facts_by_key.get((symbol, session))
        if fact is None:
            errors.append(f"{symbol}@{session}: missing BLIND_CACHE fact")
        elif fact["sha256"] != sha256:
            errors.append(
                f"{symbol}@{session}: BLIND_CACHE sha256 mismatch "
                f"fact={fact['sha256']} file={sha256}"
            )
        else:
            identities[symbol] = f"{symbol}:{session}:{sha256}"
    if errors:
        raise RuntimeError("cohort provenance preflight failed:\n- " + "\n- ".join(errors))
    return {
        "session": session,
        "symbols": list(symbols),
        "identities": identities,
        "status": "VERIFIED",
    }


def repair_from_manifest(
    manifest_path: Path | str,
    *,
    symbols,
    as_of: str,
    ledger_dir: str = "ledger",
) -> dict:
    """Network-free, all-or-nothing preflight for an approved orphan repair."""
    path = Path(manifest_path)
    payload = json.loads(path.read_text())
    if payload.get("schema") != "cache_recovery/v1":
        raise ValueError("repair manifest schema must be cache_recovery/v1")
    review = payload.get("review")
    if not isinstance(review, dict) or review.get("status") != "approved_for_operational_recovery":
        raise ValueError("repair manifest must be reviewed and approved for operational recovery")
    manifest_session = payload.get("session", payload.get("evaluation_session"))
    if manifest_session != as_of:
        raise ValueError(f"repair manifest session {manifest_session!r} != {as_of!r}")
    expected_symbols = list(symbols)
    raw_entries = payload.get("entries", payload.get("files"))
    if not isinstance(raw_entries, list) or len(raw_entries) != len(expected_symbols):
        raise ValueError("repair manifest must contain exactly one entry per symbol")
    manifest_symbols = payload.get("symbols")
    if manifest_symbols is None:
        manifest_symbols = [entry.get("symbol") for entry in raw_entries if isinstance(entry, dict)]
    if manifest_symbols != expected_symbols:
        raise ValueError("repair manifest symbols do not match selected scope/order")
    entries = {entry.get("symbol"): entry for entry in raw_entries if isinstance(entry, dict)}
    if set(entries) != set(expected_symbols):
        raise ValueError("repair manifest entry symbols do not match selected scope")
    parquet_schema = payload.get("parquet_schema")
    declared_schema_columns = (
        parquet_schema.get("columns") if isinstance(parquet_schema, dict) else None
    )
    if declared_schema_columns is not None and not isinstance(declared_schema_columns, list):
        raise ValueError("repair manifest parquet_schema.columns must be a list")

    preflight: dict[str, dict] = {}
    mtimes: dict[str, int] = {}
    for symbol in expected_symbols:
        entry = entries[symbol]
        expected_path = thetadata_adapter._cache_path(symbol, as_of)
        if Path(entry.get("path", "")).resolve() != expected_path.resolve():
            raise ValueError(f"{symbol}: repair manifest path is not canonical")
        if not expected_path.is_file():
            raise FileNotFoundError(f"{symbol}: missing cache file {expected_path}")
        actual_sha = _sha256(expected_path)
        if actual_sha != entry.get("sha256"):
            raise RuntimeError(
                f"{symbol}: repair manifest sha256 mismatch "
                f"expected={entry.get('sha256')} actual={actual_sha}"
            )
        rows, columns = thetadata_adapter._parquet_metadata_without_values(expected_path)
        declared_columns = entry.get("columns")
        columns_match = (
            len(columns) == declared_columns
            if isinstance(declared_columns, int)
            else columns == declared_columns
        )
        if declared_schema_columns is not None:
            columns_match = columns_match and columns == declared_schema_columns
        stat = expected_path.stat()
        size_match = entry.get("size_bytes") is None or entry.get("size_bytes") == stat.st_size
        mtime_match = entry.get("mtime_ns") is None or entry.get("mtime_ns") == stat.st_mtime_ns
        if rows != entry.get("rows") or not columns_match or not size_match or not mtime_match:
            raise RuntimeError(f"{symbol}: repair manifest parquet metadata mismatch")
        mtimes[symbol] = stat.st_mtime_ns
        preflight[symbol] = entry

    results = []
    for symbol in expected_symbols:
        result = thetadata_adapter.blind_cache_chain(
            symbol,
            as_of,
            ledger_dir=ledger_dir,
            approved_sha256=preflight[symbol]["sha256"],
        )
        if result["already_cached"] is not True:
            raise RuntimeError(f"{symbol}: repair unexpectedly used fetch path")
        if result["attestation_status"] not in {"REPAIRED_ATTESTATION", "VERIFIED_NOOP"}:
            raise RuntimeError(f"{symbol}: unexpected repair status {result['attestation_status']}")
        cache_path = thetadata_adapter._cache_path(symbol, as_of)
        if cache_path.stat().st_mtime_ns != mtimes[symbol]:
            raise RuntimeError(f"{symbol}: repair changed cache mtime")
        results.append(result)

    verified = verify_cohort_provenance(
        expected_symbols,
        as_of,
        facts_path=Path(ledger_dir) / "facts.log",
    )
    return {
        "schema": "cache_recovery_result/v1",
        "manifest": str(path),
        "session": as_of,
        "results": results,
        "verification": verified,
    }


# --------------------------------------------------------------------------
# Offline audit of a freshly-cached day (structural + sanity subset of the
# options-data-audit checks that a single EOD chain can answer -- the
# underlying-vs-independent check #13 needs a separate source and is not run
# here). BLOCK gates on defects that touch a STRATEGY-SELECTABLE contract
# (liquid AND inside the moneyness band); anything filtered by the liquidity
# gate or outside the band is a warning, never a block.
# --------------------------------------------------------------------------


def _liquid_mask(df):
    mid = (df["bid"] + df["ask"]) / 2.0
    ok = (
        (df["open_interest"] >= config.MIN_OPEN_INTEREST)
        & (df["bid"] >= 0)
        & (df["ask"] > 0)
        & (df["ask"] >= df["bid"])
        & (mid > 0)
    )
    spread = (df["ask"] - df["bid"]) / mid.where(mid > 0, 1.0)
    return ok & (spread <= config.MAX_SPREAD_PCT)


def audit_chain(df, *, selectable_mask=None, iv_selectable_mask=None) -> dict:
    """Audit one day's option chain. Returns
    {verdict, block, warn, rows, selectable}. verdict is BLOCK if any defect
    touches a selectable contract, else PASS WITH WARNINGS if any warning,
    else PASS. Callers with a registered strategy lane may supply its exact
    boolean selection mask; the default remains the generic liquid/delta
    proxy used by acquisition-time checks that have no independent spot."""
    liquid = _liquid_mask(df)
    selectable = (
        liquid & df["delta"].abs().between(*SELECTABLE_ABS_DELTA)
        if selectable_mask is None
        else pd.Series(selectable_mask, index=df.index).fillna(False).astype(bool)
    )
    iv_selectable = (
        selectable
        if iv_selectable_mask is None
        else pd.Series(iv_selectable_mask, index=df.index).fillna(False).astype(bool)
    )
    bad_iv = (df["iv"] <= 0) | (df["iv"] > MAX_IV) | df["iv"].isna()
    bad_greek = (df["delta"].abs() > 1.0) | (df["gamma"] < 0) | (df["vega"] < 0)
    negative = (df["bid"] < 0) | (df["ask"] < 0) | (df["open_interest"] < 0)
    crossed = df["bid"] > df["ask"]
    dup = df.duplicated(subset=["expiration", "strike", "right"], keep=False)

    block, warn = [], []
    n = int(bad_iv[iv_selectable].sum())
    if n:
        block.append(f"IV<=0/>500%/NaN on {n} selectable contracts")
    n = int(bad_greek[selectable].sum())
    if n:
        block.append(f"greek out of range on {n} selectable contracts")
    n = int(dup[selectable].sum())
    if n:
        block.append(f"duplicate (expiry,strike,right) on {n} selectable contracts")

    n = int((bad_iv & ~iv_selectable).sum())
    if n:
        warn.append(f"IV<=0/>500%/NaN on {n} non-selectable rows (deep-ITM/far-OTM)")
    n = int(negative.sum())
    if n:
        warn.append(f"{n} rows with negative bid/ask/OI (liquidity gate filters them)")
    n = int(crossed.sum())
    if n:
        warn.append(f"{n} crossed-market rows (liquidity gate filters them)")
    n = int(dup.sum())
    if n and not int(dup[selectable].sum()):
        warn.append(f"{n} duplicate rows, none selectable")

    verdict = "BLOCK" if block else ("PASS WITH WARNINGS" if warn else "PASS")
    return {
        "verdict": verdict,
        "block": block,
        "warn": warn,
        "rows": len(df),
        "selectable": int(selectable.sum()),
    }


def audit_day(symbol: str, date: str, *, cache_dir=None) -> dict:
    """Read a freshly-cached day's parquet and audit it. Thin I/O wrapper over
    audit_chain (the verdict logic is unit-tested there)."""
    import pandas as pd

    cache_dir = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    df = pd.read_parquet(cache_dir / f"{symbol}_{date}.parquet")
    return {"symbol": symbol, "date": date, **audit_chain(df)}


# --------------------------------------------------------------------------
# Orchestrator: pull + audit. Network path, run by the controlling session
# after review (see module docstring). Not unit-tested -- mirrors
# data/underlying_closes.fetch_underlying_eod.
# --------------------------------------------------------------------------


def run_topup(
    symbols=None,
    *,
    today=None,
    ledger_dir: str = "ledger",
    dry_run: bool = False,
    do_audit: bool = True,
    trading_days_fn=None,
    manifest_path: Path | None = None,
) -> dict:
    if not dry_run:
        provider_policy.require_thetadata_acquisition("recent chain top-up")
    import datetime as _dt
    from zoneinfo import ZoneInfo as _ZoneInfo

    from data.cache_runner import _run_window
    from data.thetadata_adapter import blind_cache_chain
    from research import facts

    symbols = list(config.UNIVERSE) if symbols is None else list(symbols)
    today = today or _dt.datetime.now(_ZoneInfo("America/New_York")).date().isoformat()

    facts_path = Path(ledger_dir) / "facts.log"
    last = latest_complete_session(symbols, facts_path=facts_path)
    if last is None:
        raise RuntimeError(
            "at least one symbol has no cache session with matching BLIND_CACHE "
            "provenance -- run the provenance preflight/approved recovery before "
            "topping up recent days."
        )
    days = topup_days(last, today, trading_days_fn=trading_days_fn)

    print(f"last complete (cohort): {last}   today (excluded): {today}")
    print(f"missing recent trading days: {days or '(none -- cache is current)'}")
    if dry_run:
        return {"last_cached": last, "today": today, "days": days, "dry_run": dry_run}
    if not days:
        verified = verify_cohort_provenance(
            symbols,
            last,
            facts_path=facts_path,
        )
        return {
            "last_cached": last,
            "today": today,
            "days": days,
            "dry_run": False,
            "provenance": verified,
        }

    def fetch_one(symbol, day):
        return blind_cache_chain(symbol, day, ledger_dir=ledger_dir)

    summary = _run_window(
        days,
        symbols,
        fetch_one,
        ledger_dir,
        inspect_existing=True,
        manifest_path=manifest_path,
    )
    summary.update({"last_cached": last, "today": today, "days": days, "dry_run": False})
    print(
        f"pull: fetched={summary['fetched']} repaired={summary['repaired']} "
        f"verified={summary['verified']} gaps={summary['gaps']}"
    )

    if days:
        verify_cohort_provenance(
            symbols,
            days[-1],
            facts_path=facts_path,
        )

    verdicts = {}
    if do_audit:
        worst = "PASS"
        rank = {"PASS": 0, "PASS WITH WARNINGS": 1, "BLOCK": 2}
        for day in days:
            for symbol in symbols:
                if not thetadata_adapter._cache_path(symbol, day).exists():
                    continue  # gap day -- nothing cached to audit
                a = audit_day(symbol, day)
                verdicts[f"{symbol} {day}"] = a["verdict"]
                if rank[a["verdict"]] > rank[worst]:
                    worst = a["verdict"]
                mark = {"PASS": "ok", "PASS WITH WARNINGS": "warn", "BLOCK": "BLOCK"}
                print(
                    f"  audit {symbol} {day}: {mark[a['verdict']]} "
                    f"(rows={a['rows']} selectable={a['selectable']})"
                    + ("" if not a["block"] else f" -> {a['block']}")
                )
        summary["audit_verdict"] = worst
        print(f"audit overall: {worst}")

    facts.append_fact(
        f"DATA_PULL_TOPUP {today}: recent-days chain top-up "
        f"({'/'.join(symbols)}) days={days} fetched={summary['fetched']} "
        f"repaired={summary['repaired']} verified={summary['verified']} "
        f"gaps={summary['gaps']} audit={summary.get('audit_verdict', 'skipped')}. "
        "Blind-cache path, no reveal; config boundaries unchanged; today excluded "
        "(EOD not final).",
        base_dir=ledger_dir,
    )
    return summary


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="Top up recent EOD chains for the selected forward scope (blind cache + audit)."
    )
    p.add_argument(
        "--scope",
        choices=("core", "h7", "display-extra"),
        default="core",
        help="core = existing four-name H5 scope (default); "
        "h7 = exact 15-name H7 forward scope; display-extra = "
        "explicit NBIS/AMAT/CLSK display-only scope",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="list missing recent days and exit (no network)"
    )
    p.add_argument("--no-audit", action="store_true", help="skip the post-pull offline audit")
    p.add_argument(
        "--refresh-closes",
        action="store_true",
        help="also refresh independent Yahoo closes for the exact "
        "selected scope (network; ignored during --dry-run)",
    )
    p.add_argument("--as-of", help="exact completed session for --repair-manifest")
    p.add_argument(
        "--repair-manifest", type=Path, help="reviewed cache_recovery/v1 manifest; network-free"
    )
    p.add_argument(
        "--verify-closes-receipt",
        type=Path,
        help="re-hash the stored close files a closes receipt binds (offline, "
        "writes nothing); exit 1 only on a mismatch against the latest "
        "receipt for that symbol",
    )
    args = p.parse_args(argv)
    if args.verify_closes_receipt:
        report = verify_closes_receipt(args.verify_closes_receipt)
        print(json.dumps(report, sort_keys=True, indent=1))
        return 0 if report["status"] == "OK" else 1
    symbols = scope_symbols(args.scope)
    if args.repair_manifest:
        if not args.as_of:
            p.error("--repair-manifest requires --as-of YYYY-MM-DD")
        if args.dry_run or args.refresh_closes:
            p.error("--repair-manifest cannot be combined with network options")
        result = repair_from_manifest(
            args.repair_manifest,
            symbols=symbols,
            as_of=args.as_of,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.as_of:
        p.error("--as-of is only valid with --repair-manifest")
    result = run_topup(
        symbols=symbols,
        dry_run=args.dry_run,
        do_audit=not args.no_audit,
        manifest_path=Path("reports/cache_runs") / f"recent_topup_{args.scope}.json",
    )
    if args.refresh_closes and not args.dry_run and result.get("audit_verdict") != "BLOCK":
        closes = refresh_closes(symbols, today=result["today"], scope=args.scope)
        print(f"closes: refreshed {len(closes)}/{len(symbols)} symbols")
    return 2 if result.get("audit_verdict") == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
