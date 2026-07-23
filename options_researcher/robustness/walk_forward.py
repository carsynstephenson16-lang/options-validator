"""Observation-based, leakage-safe walk-forward splitting for sparse date panels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold: int
    train_dates: tuple[str, ...]
    test_dates: tuple[str, ...]
    purge_dates: tuple[str, ...]
    embargo_dates: tuple[str, ...]

    def audit_ranges(self) -> dict[str, dict[str, str] | None]:
        def bounds(values: tuple[str, ...]) -> dict[str, str] | None:
            return {"start": values[0], "end": values[-1]} if values else None

        return {
            "train": bounds(self.train_dates),
            "test": bounds(self.test_dates),
            "purge": bounds(self.purge_dates),
            "embargo": bounds(self.embargo_dates),
        }


class WalkForwardSplitter:
    def __init__(
        self,
        train_observations: int,
        test_observations: int,
        step_observations: int,
        purge_observations: int,
        embargo_observations: int,
        *,
        mode: str = "expanding",
    ) -> None:
        for name, value in (
            ("train_observations", train_observations),
            ("test_observations", test_observations),
            ("step_observations", step_observations),
        ):
            if value < 1:
                raise ValueError(f"{name} must be positive")
        if purge_observations < 0 or embargo_observations < 0:
            raise ValueError("purge and embargo observations must be non-negative")
        if purge_observations >= train_observations:
            raise ValueError("purge must leave at least one training observation")
        if step_observations < test_observations + embargo_observations:
            raise ValueError("step must clear the prior test and embargo ranges")
        if mode not in {"expanding", "rolling"}:
            raise ValueError("mode must be expanding or rolling")
        self.train_observations = train_observations
        self.test_observations = test_observations
        self.step_observations = step_observations
        self.purge_observations = purge_observations
        self.embargo_observations = embargo_observations
        self.mode = mode

    def split(self, panel_dates: Iterable[str]) -> tuple[WalkForwardFold, ...]:
        parsed: dict[date, str] = {}
        for value in panel_dates:
            parsed_date = date.fromisoformat(value)
            parsed[parsed_date] = parsed_date.isoformat()
        dates = [parsed[key] for key in sorted(parsed)]
        if not dates:
            return ()

        folds: list[WalkForwardFold] = []
        test_start = self.train_observations
        while test_start + self.test_observations <= len(dates):
            raw_train_start = (
                0 if self.mode == "expanding" else test_start - self.train_observations
            )
            purge_start = test_start - self.purge_observations
            train = tuple(dates[raw_train_start:purge_start])
            purged = tuple(dates[purge_start:test_start])
            test_end = test_start + self.test_observations
            test = tuple(dates[test_start:test_end])
            embargo_end = min(test_end + self.embargo_observations, len(dates))
            embargo = tuple(dates[test_end:embargo_end])
            if train and test:
                folds.append(
                    WalkForwardFold(
                        fold=len(folds),
                        train_dates=train,
                        test_dates=test,
                        purge_dates=purged,
                        embargo_dates=embargo,
                    )
                )
            test_start += self.step_observations
        return tuple(folds)
