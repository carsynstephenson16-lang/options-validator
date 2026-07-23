"""Typed, deterministic experiment specifications and governance validation."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Sequence

Scalar = str | int | float | bool | None
FrozenMapping = tuple[tuple[str, Scalar], ...]
FrozenGrid = tuple[FrozenMapping, ...]

LANES = {"sell_put", "covered_call", "pmcc", "leaps", "tactical_call"}
CLAIM_LABELS = {
    "Repo-verified",
    "Test-verified",
    "Official-source",
    "Inference",
    "Assumption",
}
REQUIRED_OWNER_CONTROLS = {
    "bucket_count",
    "minimum_adverse_bottom_bucket",
    "holm_sidedness",
    "forward_backstop",
}
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SpecValidationError(ValueError):
    """The experiment is incomplete, invalid, or not registered."""


def _as_date(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise SpecValidationError(f"{field_name} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SpecValidationError(f"{field_name} must be an ISO date") from exc


def _freeze_mapping(value: object, field_name: str) -> FrozenMapping:
    if not isinstance(value, Mapping):
        raise SpecValidationError(f"{field_name} must be an object")
    frozen: list[tuple[str, Scalar]] = []
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key:
            raise SpecValidationError(f"{field_name} keys must be non-empty strings")
        if not isinstance(raw_value, (str, int, float, bool)) and raw_value is not None:
            raise SpecValidationError(f"{field_name}.{raw_key} must be a JSON scalar")
        if isinstance(raw_value, float) and not math.isfinite(raw_value):
            raise SpecValidationError(f"{field_name}.{raw_key} must be finite")
        frozen.append((raw_key, raw_value))
    return tuple(sorted(frozen))


def _mapping_dict(value: FrozenMapping) -> dict[str, Scalar]:
    return dict(value)


def _require_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SpecValidationError(f"{field_name} must be an integer")
    return value


def _require_float(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SpecValidationError(f"{field_name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise SpecValidationError(f"{field_name} must be finite")
    return result


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecValidationError(f"{field_name} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class DateWindow:
    start: str
    end: str

    def __post_init__(self) -> None:
        start = _as_date(self.start, "window.start")
        end = _as_date(self.end, "window.end")
        if start > end:
            raise SpecValidationError("window.start must be on or before window.end")

    @classmethod
    def from_mapping(cls, value: object, field_name: str) -> DateWindow:
        if not isinstance(value, Mapping):
            raise SpecValidationError(f"{field_name} must contain start/end")
        try:
            return cls(start=str(value["start"]), end=str(value["end"]))
        except KeyError as exc:
            raise SpecValidationError(f"{field_name} must contain start/end") from exc

    def as_dict(self) -> dict[str, str]:
        return {"start": self.start, "end": self.end}


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_name: str
    version: str
    research_question_id: str
    lane: str
    signal_version: str
    dataset_fingerprint: str
    point_in_time_cutoff: str
    train_window: DateWindow
    validation_window: DateWindow
    test_window: DateWindow
    purge_observations: int
    embargo_observations: int
    forward_outcome_horizon: int
    walk_forward_mode: str
    train_observations: int
    test_observations: int
    step_observations: int
    cost_model: FrozenMapping
    parameter_grid: FrozenGrid
    random_seed: int
    permutation_count: int
    permutation_method: str
    multiple_testing_method: str
    multiple_testing_alpha: float
    git_commit_sha: str
    status: str
    claim_label: str
    owner_controls: FrozenMapping
    config_hash: str = field(default="")
    run_id: str = field(default="")

    def __post_init__(self) -> None:
        for field_name in (
            "experiment_name",
            "version",
            "research_question_id",
            "signal_version",
        ):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise SpecValidationError(f"{field_name} must be non-empty")
        if self.lane not in LANES:
            raise SpecValidationError(f"lane must be one of {sorted(LANES)}")
        if not SHA256.fullmatch(self.dataset_fingerprint):
            raise SpecValidationError("dataset_fingerprint must be a SHA-256 hex digest")
        cutoff = _as_date(self.point_in_time_cutoff, "point_in_time_cutoff")
        train_end = _as_date(self.train_window.end, "train_window.end")
        validation_start = _as_date(self.validation_window.start, "validation_window.start")
        validation_end = _as_date(self.validation_window.end, "validation_window.end")
        test_start = _as_date(self.test_window.start, "test_window.start")
        test_end = _as_date(self.test_window.end, "test_window.end")
        if not (train_end < validation_start and validation_end < test_start):
            raise SpecValidationError("train, validation, and test windows overlap")
        if test_end > cutoff:
            raise SpecValidationError("test_window exceeds point_in_time_cutoff")
        if self.purge_observations < 0 or self.embargo_observations < 0:
            raise SpecValidationError("purge and embargo observations must be non-negative")
        if self.forward_outcome_horizon < 1:
            raise SpecValidationError("forward_outcome_horizon must be positive")
        if self.purge_observations < self.forward_outcome_horizon:
            raise SpecValidationError("purge_observations must cover the forward_outcome_horizon")
        if self.walk_forward_mode not in {"expanding", "rolling"}:
            raise SpecValidationError("walk_forward_mode must be expanding or rolling")
        if (
            min(
                self.train_observations,
                self.test_observations,
                self.step_observations,
            )
            < 1
        ):
            raise SpecValidationError("walk-forward observation counts must be positive")
        if self.test_observations < 2 * self.forward_outcome_horizon:
            raise SpecValidationError(
                "test_observations must contain at least two forward-horizon blocks"
            )
        if self.purge_observations >= self.train_observations:
            raise SpecValidationError("purge must leave training observations")
        if self.step_observations < (self.test_observations + self.embargo_observations):
            raise SpecValidationError("walk-forward step must clear test plus embargo")
        if not self.parameter_grid:
            raise SpecValidationError("parameter_grid must not be empty")
        parameter_ids = [dict(item).get("parameter_id") for item in self.parameter_grid]
        if any(not isinstance(item, str) or not item for item in parameter_ids):
            raise SpecValidationError("every parameter set needs a parameter_id")
        if len(set(parameter_ids)) != len(parameter_ids):
            raise SpecValidationError("parameter_id values must be unique")
        if self.random_seed < 0 or self.permutation_count < 1:
            raise SpecValidationError("random_seed must be non-negative and permutations positive")
        if self.permutation_method != "circular_block":
            raise SpecValidationError("permutation_method must be circular_block")
        if self.multiple_testing_method != "holm":
            raise SpecValidationError("multiple_testing_method must be holm")
        if not 0.0 < self.multiple_testing_alpha < 1.0:
            raise SpecValidationError("multiple_testing_alpha must be between zero and one")
        if not GIT_SHA.fullmatch(self.git_commit_sha):
            raise SpecValidationError("git_commit_sha must be a full 40-character SHA")
        if self.status not in {"draft", "registered", "blocked", "complete"}:
            raise SpecValidationError("invalid experiment status")
        if self.claim_label not in CLAIM_LABELS:
            raise SpecValidationError(f"claim_label must be one of {sorted(CLAIM_LABELS)}")
        controls = _mapping_dict(self.owner_controls)
        missing_controls = REQUIRED_OWNER_CONTROLS - controls.keys()
        if missing_controls:
            raise SpecValidationError(f"missing owner control field(s): {sorted(missing_controls)}")
        bucket_count = controls["bucket_count"]
        minimum_adverse = controls["minimum_adverse_bottom_bucket"]
        if not isinstance(bucket_count, int) or isinstance(bucket_count, bool) or bucket_count < 2:
            raise SpecValidationError("owner control bucket_count must be an integer >= 2")
        if (
            not isinstance(minimum_adverse, int)
            or isinstance(minimum_adverse, bool)
            or minimum_adverse < 1
        ):
            raise SpecValidationError(
                "owner control minimum_adverse_bottom_bucket must be positive"
            )
        if controls["holm_sidedness"] != "one-sided-positive":
            raise SpecValidationError("owner control holm_sidedness must be one-sided-positive")
        _as_date(controls["forward_backstop"], "owner_controls.forward_backstop")

        expected_hash = self._derived_config_hash()
        if self.config_hash and self.config_hash != expected_hash:
            raise SpecValidationError("config_hash does not match canonical specification")
        object.__setattr__(self, "config_hash", expected_hash)
        expected_run_id = f"{self.research_question_id}-{self.lane}-{expected_hash[:16]}"
        if self.run_id and self.run_id != expected_run_id:
            raise SpecValidationError("run_id does not match canonical specification")
        object.__setattr__(self, "run_id", expected_run_id)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ExperimentSpec:
        required = {
            "experiment_name",
            "version",
            "research_question_id",
            "lane",
            "signal_version",
            "dataset_fingerprint",
            "point_in_time_cutoff",
            "train_window",
            "validation_window",
            "test_window",
            "purge_observations",
            "embargo_observations",
            "forward_outcome_horizon",
            "walk_forward_mode",
            "train_observations",
            "test_observations",
            "step_observations",
            "cost_model",
            "parameter_grid",
            "random_seed",
            "permutation_count",
            "permutation_method",
            "multiple_testing_method",
            "multiple_testing_alpha",
            "git_commit_sha",
            "status",
            "claim_label",
            "owner_controls",
        }
        missing = required - value.keys()
        if missing:
            raise SpecValidationError(f"missing experiment field(s): {sorted(missing)}")
        raw_grid = value["parameter_grid"]
        if not isinstance(raw_grid, Sequence) or isinstance(raw_grid, (str, bytes)):
            raise SpecValidationError("parameter_grid must be a list")
        return cls(
            experiment_name=_require_text(value["experiment_name"], "experiment_name"),
            version=_require_text(value["version"], "version"),
            research_question_id=_require_text(
                value["research_question_id"], "research_question_id"
            ),
            lane=_require_text(value["lane"], "lane"),
            signal_version=_require_text(value["signal_version"], "signal_version"),
            dataset_fingerprint=_require_text(value["dataset_fingerprint"], "dataset_fingerprint"),
            point_in_time_cutoff=_require_text(
                value["point_in_time_cutoff"], "point_in_time_cutoff"
            ),
            train_window=DateWindow.from_mapping(value["train_window"], "train_window"),
            validation_window=DateWindow.from_mapping(
                value["validation_window"], "validation_window"
            ),
            test_window=DateWindow.from_mapping(value["test_window"], "test_window"),
            purge_observations=_require_int(value["purge_observations"], "purge_observations"),
            embargo_observations=_require_int(
                value["embargo_observations"], "embargo_observations"
            ),
            forward_outcome_horizon=_require_int(
                value["forward_outcome_horizon"], "forward_outcome_horizon"
            ),
            walk_forward_mode=_require_text(value["walk_forward_mode"], "walk_forward_mode"),
            train_observations=_require_int(value["train_observations"], "train_observations"),
            test_observations=_require_int(value["test_observations"], "test_observations"),
            step_observations=_require_int(value["step_observations"], "step_observations"),
            cost_model=_freeze_mapping(value["cost_model"], "cost_model"),
            parameter_grid=tuple(
                _freeze_mapping(item, f"parameter_grid[{index}]")
                for index, item in enumerate(raw_grid)
            ),
            random_seed=_require_int(value["random_seed"], "random_seed"),
            permutation_count=_require_int(value["permutation_count"], "permutation_count"),
            permutation_method=_require_text(value["permutation_method"], "permutation_method"),
            multiple_testing_method=_require_text(
                value["multiple_testing_method"], "multiple_testing_method"
            ),
            multiple_testing_alpha=_require_float(
                value["multiple_testing_alpha"], "multiple_testing_alpha"
            ),
            git_commit_sha=_require_text(value["git_commit_sha"], "git_commit_sha"),
            status=_require_text(value["status"], "status"),
            claim_label=_require_text(value["claim_label"], "claim_label"),
            owner_controls=_freeze_mapping(value["owner_controls"], "owner_controls"),
            config_hash=str(value.get("config_hash", "")),
            run_id=str(value.get("run_id", "")),
        )

    def _base_dict(self) -> dict[str, object]:
        return {
            "experiment_name": self.experiment_name,
            "version": self.version,
            "research_question_id": self.research_question_id,
            "lane": self.lane,
            "signal_version": self.signal_version,
            "dataset_fingerprint": self.dataset_fingerprint,
            "point_in_time_cutoff": self.point_in_time_cutoff,
            "train_window": self.train_window.as_dict(),
            "validation_window": self.validation_window.as_dict(),
            "test_window": self.test_window.as_dict(),
            "purge_observations": self.purge_observations,
            "embargo_observations": self.embargo_observations,
            "forward_outcome_horizon": self.forward_outcome_horizon,
            "walk_forward_mode": self.walk_forward_mode,
            "train_observations": self.train_observations,
            "test_observations": self.test_observations,
            "step_observations": self.step_observations,
            "cost_model": _mapping_dict(self.cost_model),
            "parameter_grid": [_mapping_dict(item) for item in self.parameter_grid],
            "random_seed": self.random_seed,
            "permutation_count": self.permutation_count,
            "permutation_method": self.permutation_method,
            "multiple_testing_method": self.multiple_testing_method,
            "multiple_testing_alpha": self.multiple_testing_alpha,
            "git_commit_sha": self.git_commit_sha,
            "status": self.status,
            "claim_label": self.claim_label,
            "owner_controls": _mapping_dict(self.owner_controls),
        }

    def _derived_config_hash(self) -> str:
        encoded = json.dumps(
            self._base_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {**self._base_dict(), "config_hash": self.config_hash, "run_id": self.run_id}

    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

    def require_registration(self, records: Sequence[Mapping[str, object]]) -> None:
        if self.status != "registered":
            raise SpecValidationError("experiment status is not registered")
        matches = [
            record
            for record in records
            if record.get("hypothesis_id") == self.research_question_id
            and record.get("entry_type") in {"trial_intent", "run"}
        ]
        if not matches:
            raise SpecValidationError(
                f"{self.research_question_id} is not registered in the experiment ledger"
            )
