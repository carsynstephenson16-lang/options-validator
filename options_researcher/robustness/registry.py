"""Versioned, idempotent SQLite registry for resumable research experiments."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from options_researcher.robustness.models import ExperimentSpec

SCHEMA_VERSION = 1


class IncompatibleSchemaError(RuntimeError):
    """The registry is corrupt or uses an unsupported schema version."""


class CheckpointConflictError(RuntimeError):
    """An existing run/task conflicts with the attempted idempotent replay."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class ExperimentRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(self.path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=FULL")
            version = int(self._connection.execute("PRAGMA user_version").fetchone()[0])
            if version not in {0, SCHEMA_VERSION}:
                raise IncompatibleSchemaError(
                    f"unsupported registry schema {version}; expected {SCHEMA_VERSION}"
                )
            if version == 0:
                self._create_schema()
            else:
                self._verify_schema()
        except sqlite3.DatabaseError as exc:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise IncompatibleSchemaError(f"corrupt experiment registry: {exc}") from exc

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE runs (
                    run_id TEXT PRIMARY KEY,
                    parent_experiment_id TEXT,
                    config_hash TEXT NOT NULL,
                    dataset_fingerprint TEXT NOT NULL,
                    git_sha TEXT NOT NULL,
                    started_at_utc TEXT NOT NULL,
                    completed_at_utc TEXT,
                    status TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    lane TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    spec_digest TEXT NOT NULL,
                    claim_label TEXT NOT NULL,
                    error_detail TEXT
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE tasks (
                    run_id TEXT NOT NULL,
                    fold INTEGER NOT NULL,
                    parameter_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    raw_p_value REAL,
                    adjusted_p_value REAL,
                    gate_outcomes_json TEXT NOT NULL,
                    error_detail TEXT,
                    artifact_paths_json TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    completed_at_utc TEXT NOT NULL,
                    PRIMARY KEY (run_id, fold, parameter_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
                """
            )
            self._connection.execute("CREATE INDEX tasks_run_status ON tasks(run_id, status)")
            self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def _verify_schema(self) -> None:
        expected = {"runs", "tasks"}
        actual = {
            str(row[0])
            for row in self._connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not expected.issubset(actual):
            raise IncompatibleSchemaError("registry schema is incomplete")

    def register_run(
        self, spec: ExperimentSpec, *, parent_experiment_id: str | None = None
    ) -> None:
        spec_json = spec.canonical_json()
        spec_digest = hashlib.sha256(spec_json.encode("utf-8")).hexdigest()
        existing = self._connection.execute(
            "SELECT spec_digest FROM runs WHERE run_id = ?", (spec.run_id,)
        ).fetchone()
        if existing is not None:
            if existing["spec_digest"] != spec_digest:
                raise CheckpointConflictError(
                    f"run {spec.run_id} exists with different specification"
                )
            return
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO runs (
                    run_id, parent_experiment_id, config_hash, dataset_fingerprint,
                    git_sha, started_at_utc, completed_at_utc, status, seed, lane,
                    spec_json, spec_digest, claim_label, error_detail
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    spec.run_id,
                    parent_experiment_id,
                    spec.config_hash,
                    spec.dataset_fingerprint,
                    spec.git_commit_sha,
                    _utc_now(),
                    "RUNNING",
                    spec.random_seed,
                    spec.lane,
                    spec_json,
                    spec_digest,
                    spec.claim_label,
                ),
            )

    def record_completed_task(
        self,
        run_id: str,
        fold: int,
        parameter_id: str,
        payload: Mapping[str, object],
    ) -> None:
        required = {
            "metrics",
            "raw_p_value",
            "adjusted_p_value",
            "gate_outcomes",
            "artifact_paths",
        }
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"task payload missing field(s): {sorted(missing)}")
        payload_digest = _digest(payload)
        existing = self._connection.execute(
            """
            SELECT payload_digest FROM tasks
            WHERE run_id = ? AND fold = ? AND parameter_id = ?
            """,
            (run_id, fold, parameter_id),
        ).fetchone()
        if existing is not None:
            if existing["payload_digest"] != payload_digest:
                raise CheckpointConflictError(
                    f"task {(run_id, fold, parameter_id)} already has different output"
                )
            return
        if (
            self._connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            is None
        ):
            raise ValueError(f"unknown run_id {run_id!r}")
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO tasks (
                    run_id, fold, parameter_id, status, metrics_json,
                    raw_p_value, adjusted_p_value, gate_outcomes_json,
                    error_detail, artifact_paths_json, payload_digest,
                    completed_at_utc
                ) VALUES (?, ?, ?, 'COMPLETE', ?, ?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    run_id,
                    fold,
                    parameter_id,
                    _canonical(payload["metrics"]),
                    payload["raw_p_value"],
                    payload["adjusted_p_value"],
                    _canonical(payload["gate_outcomes"]),
                    _canonical(payload["artifact_paths"]),
                    payload_digest,
                    _utc_now(),
                ),
            )

    def record_failed_task(
        self, run_id: str, fold: int, parameter_id: str, error_detail: str
    ) -> None:
        if not error_detail.strip():
            raise ValueError("error_detail must be non-empty")
        payload = {
            "metrics": {},
            "raw_p_value": None,
            "adjusted_p_value": None,
            "gate_outcomes": {"execution": "FAILED"},
            "artifact_paths": [],
            "error_detail": error_detail,
        }
        digest = _digest(payload)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO tasks (
                    run_id, fold, parameter_id, status, metrics_json,
                    raw_p_value, adjusted_p_value, gate_outcomes_json,
                    error_detail, artifact_paths_json, payload_digest,
                    completed_at_utc
                ) VALUES (?, ?, ?, 'FAILED', '{}', NULL, NULL, ?,
                          ?, '[]', ?, ?)
                ON CONFLICT(run_id, fold, parameter_id) DO NOTHING
                """,
                (
                    run_id,
                    fold,
                    parameter_id,
                    _canonical({"execution": "FAILED"}),
                    error_detail,
                    digest,
                    _utc_now(),
                ),
            )

    def completed_tasks(self, run_id: str) -> set[tuple[int, str]]:
        return {
            (int(row["fold"]), str(row["parameter_id"]))
            for row in self._connection.execute(
                """
                SELECT fold, parameter_id FROM tasks
                WHERE run_id = ? AND status = 'COMPLETE'
                """,
                (run_id,),
            )
        }

    def finish_run(self, run_id: str, *, status: str = "COMPLETE") -> None:
        if status not in {"COMPLETE", "BLOCKED", "FAILED"}:
            raise ValueError("invalid terminal run status")
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE runs SET status = ?, completed_at_utc = ?
                WHERE run_id = ?
                """,
                (status, _utc_now(), run_id),
            )
        if cursor.rowcount != 1:
            raise ValueError(f"unknown run_id {run_id!r}")

    def run_record(self, run_id: str) -> dict[str, object]:
        row = self._connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown run_id {run_id!r}")
        record = dict(row)
        record["spec"] = json.loads(str(record.pop("spec_json")))
        return record

    def task_records(self, run_id: str) -> list[dict[str, object]]:
        rows = self._connection.execute(
            """
            SELECT * FROM tasks WHERE run_id = ?
            ORDER BY fold, parameter_id
            """,
            (run_id,),
        )
        records: list[dict[str, object]] = []
        for row in rows:
            record = dict(row)
            for source, target in (
                ("metrics_json", "metrics"),
                ("gate_outcomes_json", "gate_outcomes"),
                ("artifact_paths_json", "artifact_paths"),
            ):
                record[target] = json.loads(str(record.pop(source)))
            records.append(record)
        return records

    def list_runs(self) -> list[dict[str, object]]:
        return [
            dict(row)
            for row in self._connection.execute(
                """
                SELECT run_id, parent_experiment_id, config_hash,
                       dataset_fingerprint, git_sha, started_at_utc,
                       completed_at_utc, status, seed, lane, claim_label,
                       error_detail
                FROM runs ORDER BY started_at_utc, run_id
                """
            )
        ]

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> ExperimentRegistry:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
