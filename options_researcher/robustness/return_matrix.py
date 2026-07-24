"""Per-variant OOS return-matrix observability artifact for the robustness layer.

Owner-directed 2026-07-24. This module persists the per-day, per-parameter-
variant cost-adjusted OOS spread series that ``runner.run_experiment``
already computes (``screening.cost_adjusted_primary_metric(...).daily_spreads``)
but previously discarded, and exposes a measured-variance reader that feeds
``metrics.dsr`` with an actual trial-Sharpe population instead of a default
assumption.

FAIL-OPEN BY CONSTRUCTION -- this is the load-bearing property of the whole
addition. Every call into this module from ``runner.py`` is wrapped there in
a try/except that logs and continues: a capture or finalize failure must
NEVER change a computed metric, a registry row, or a written report. See
``docs/superpowers/specs/2026-07-24-robustness-return-matrix-addendum.md``.

Literature (established by the owner-directed deep-research brief this task
follows; see the addendum doc for the full reference list):
Official-source: Bailey, D.H. & Lopez de Prado, M. (2012, 2014); Bailey,
Borwein, Lopez de Prado & Zhu (CSCV / probability of backtest overfitting).
"T should be double the selection window" motivates capturing at DAILY
granularity here rather than per-fold aggregates, to maximize T.

Writes via the shared durable-write helper (data.atomic_io.atomic_parquet_write)
and hashes via the shared canonical-JSON helpers (research.hashing). Manifest
writes are write-once: an identical-bytes retry on the same run_id is a
benign no-op (the run_id is derived from the spec's immutable config_hash,
so a retry naturally reproduces the same bytes); differing bytes on the same
run_id is a loud refusal, mirroring options_researcher/h7_data_gate.py's
write_artifact() convention.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

import config
from data.atomic_io import atomic_parquet_write
from options_researcher.robustness.models import ExperimentSpec
from options_researcher.robustness.screening import PanelObservation, daily_spread_series
from research.hashing import canonical_json, sha256_file, sha256_hex

MATRIX_SCHEMA = "robustness_return_matrix_v1"
DEFAULT_MATRIX_ROOT = Path(".tmp/robustness/matrices")
PARQUET_NAME = "return_matrix.parquet"
MANIFEST_NAME = "return_matrix.manifest.json"


class ReturnMatrixError(RuntimeError):
    """Internal to this module. Callers (runner.py, reporting.py) MUST catch
    this -- and any other exception -- per the fail-open contract; it must
    never propagate into the registered run/report path."""


@dataclass(frozen=True, slots=True)
class _Row:
    parameter_id: str
    panel_date: str
    cost_adjusted_return: float
    fold: int
    observation_count: int


@dataclass(slots=True)
class ReturnMatrixWriter:
    """Accumulates per-variant daily OOS return rows for one experiment run,
    then flushes one parquet + one write-once manifest.

    Every public method may raise; the fail-open guard is the CALLER's
    responsibility (runner.py wraps each call site), not this class's -- the
    registered outputs must be identical whether or not that guard exists,
    so this class stays a plain, honestly-failing writer.
    """

    spec: ExperimentSpec
    matrix_root: str | Path = DEFAULT_MATRIX_ROOT
    _rows: list[_Row] = field(default_factory=list, init=False, repr=False)

    def _root(self) -> Path:
        return Path(self.matrix_root) / self.spec.run_id

    def capture(
        self,
        parameter_id: str,
        rows: Sequence[PanelObservation],
        *,
        bucket_count: int,
        date_to_fold: Mapping[str, int],
    ) -> None:
        """Append one parameter variant's daily OOS spread series.

        ``rows`` is the full aggregated OOS row set for ``parameter_id``
        (i.e. ``oos_rows[parameter_id]`` in runner.run_experiment) -- the
        same input already passed to ``cost_adjusted_primary_metric`` to
        build ``aggregate_metric``. ``date_to_fold`` maps every panel date
        that can appear in ``rows`` to the walk-forward fold that produced
        it; a date with no mapping is treated as a capture-time invariant
        violation and raises (never silently mis-attributed to fold 0).
        """
        for panel_date, spread_value, observation_count in daily_spread_series(
            rows, bucket_count=bucket_count
        ):
            if panel_date not in date_to_fold:
                raise ReturnMatrixError(
                    f"panel_date {panel_date!r} has no walk-forward fold mapping "
                    f"for parameter {parameter_id!r}"
                )
            value = float(spread_value)
            if not np.isfinite(value):
                raise ReturnMatrixError(
                    f"non-finite cost-adjusted return on {panel_date!r} "
                    f"for parameter {parameter_id!r}"
                )
            self._rows.append(
                _Row(
                    parameter_id=parameter_id,
                    panel_date=panel_date,
                    cost_adjusted_return=value,
                    fold=int(date_to_fold[panel_date]),
                    observation_count=int(observation_count),
                )
            )

    def finalize(self) -> dict[str, object] | None:
        """Flush the accumulated rows to parquet + a write-once manifest.

        Returns ``None`` (writes nothing) if no rows were ever captured --
        an empty artifact is not written, so its absence is exactly what
        ``matrix unavailable`` in the reporting bullet detects.
        """
        if not self._rows:
            return None
        root = self._root()
        parquet_path = root / PARQUET_NAME
        manifest_path = root / MANIFEST_NAME

        frame = pd.DataFrame(
            {
                "parameter_id": pd.array(
                    [row.parameter_id for row in self._rows], dtype="string"
                ),
                "panel_date": pd.array([row.panel_date for row in self._rows], dtype="string"),
                "cost_adjusted_return": np.array(
                    [row.cost_adjusted_return for row in self._rows], dtype="float64"
                ),
                "fold": np.array([row.fold for row in self._rows], dtype="int32"),
                "observation_count": np.array(
                    [row.observation_count for row in self._rows], dtype="int32"
                ),
            }
        )
        atomic_parquet_write(frame, parquet_path)

        parameter_ids = sorted({row.parameter_id for row in self._rows})
        dates = sorted({row.panel_date for row in self._rows})
        row_counts_per_variant = {
            parameter_id: sum(1 for row in self._rows if row.parameter_id == parameter_id)
            for parameter_id in parameter_ids
        }
        manifest_body: dict[str, object] = {
            "schema": MATRIX_SCHEMA,
            "experiment_id": self.spec.run_id,
            "research_question_id": self.spec.research_question_id,
            "lane": self.spec.lane,
            "config_hash": self.spec.config_hash,
            "dataset_fingerprint": self.spec.dataset_fingerprint,
            "git_sha": self.spec.git_commit_sha,
            "parameter_ids": parameter_ids,
            "matrix_shape": {"periods_t": len(dates), "variants_m": len(parameter_ids)},
            "time_index_bounds": {"start": dates[0], "end": dates[-1]},
            "row_counts": {"total": len(self._rows), "per_variant": row_counts_per_variant},
            "output": {"path": str(parquet_path), "sha256": sha256_file(parquet_path)},
        }
        manifest_body["manifest_hash"] = sha256_hex(canonical_json(manifest_body))
        write_manifest_once(manifest_path, canonical_json(manifest_body))
        return manifest_body


def write_manifest_once(path: str | Path, payload: str) -> None:
    """Create ``path`` exactly once. An identical-bytes retry is a benign
    no-op; a differing-bytes write on the same path is a loud refusal.

    Mirrors options_researcher/h7_data_gate.py's write_artifact() write-once
    convention: check-then-create via ``open("x")``, durable fsync of both
    the file and its parent directory entry, atomic publish via os.replace.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ReturnMatrixError(f"refusing to overwrite return-matrix manifest: {path}")
        return
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise


def measured_trial_sr_stats(matrix_path: str | Path) -> tuple[float, float, int]:
    """Read a return-matrix parquet and compute (mean_trial_sr,
    trial_sr_variance, n_trials) -- the measured population that
    ``metrics.expected_max_sr``/``metrics.dsr`` deflate against, replacing
    the neutral ``config.DSR_DEFAULT_MEAN_TRIAL_SR`` assumption with an
    actual observed distribution of per-variant Sharpe ratios.

    Per-variant SR = mean(series) / std(series, ddof=1) over that variant's
    OWN daily cost-adjusted return series (each parameter_id is one trial).
    A variant with fewer than 2 observations, or a zero/non-finite std, is
    excluded (undefined SR) rather than raising -- the raise is reserved for
    the trial-count floor, matching this repo's refusal-not-crash convention
    for thin/degenerate samples (see metrics.sample_moments, metrics.psr).

    Raises ReturnMatrixError if fewer than config.DSR_MIN_N_TRIALS usable
    variants remain: "expected max of N trials" is meaningless below that
    floor (metrics.expected_max_sr's own contract).
    """
    frame = pd.read_parquet(matrix_path)
    required = {"parameter_id", "panel_date", "cost_adjusted_return", "fold", "observation_count"}
    missing = required - set(frame.columns)
    if missing:
        raise ReturnMatrixError(f"return matrix missing column(s): {sorted(missing)}")

    trial_srs: list[float] = []
    for _, group in frame.groupby("parameter_id"):
        series = group["cost_adjusted_return"].to_numpy(dtype=float)
        if len(series) < 2:
            continue
        std = float(series.std(ddof=1))
        if not np.isfinite(std) or std == 0.0:
            continue
        trial_srs.append(float(series.mean()) / std)

    n_trials = len(trial_srs)
    if n_trials < config.DSR_MIN_N_TRIALS:
        raise ReturnMatrixError(
            f"measured trial-SR population too small: {n_trials} usable variant(s) < "
            f"config.DSR_MIN_N_TRIALS={config.DSR_MIN_N_TRIALS}"
        )
    mean_trial_sr = float(np.mean(trial_srs))
    trial_sr_variance = float(np.var(trial_srs, ddof=1)) if n_trials > 1 else 0.0
    return mean_trial_sr, trial_sr_variance, n_trials
