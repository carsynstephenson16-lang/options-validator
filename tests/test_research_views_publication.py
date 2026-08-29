"""Strict immutable-generation publication tests for display-only research views."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from options_researcher import research_views_publication as publication

GENERATION_ID = "20260826T120000000000Z-0123456789abcdef0123456789abcdef"
PUBLISHED_AT = "2026-08-26T12:00:00.000000Z"
COMMIT = "a" * 40


class ResearchViewsPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.dashboard = self.root / ".tmp" / "dashboard"
        self.staging = self.dashboard / "research-views-generations" / f".staging-{GENERATION_ID}"
        self.staging.mkdir(parents=True)
        (self.staging / "experiments.html").write_text("experiments\n")
        (self.staging / "wasserstein-regime.txt").write_text("regime text\n")
        (self.staging / "wasserstein-regime.json").write_text("{}\n")

    def _publish(self) -> dict:
        return publication.publish_generation(
            dashboard_dir=self.dashboard,
            staging_dir=self.staging,
            generation_id=GENERATION_ID,
            published_at=PUBLISHED_AT,
            producer_commit=COMMIT,
        )

    def _publish_at(self, root: Path, generation_id: str, published_at: str, marker: str) -> dict:
        dashboard = root / ".tmp" / "dashboard"
        staging = dashboard / "research-views-generations" / f".staging-{generation_id}"
        staging.mkdir(parents=True)
        for name in publication.ARTIFACTS:
            (staging / name).write_text(f"{marker}:{name}\n")
        return publication.publish_generation(
            dashboard_dir=dashboard,
            staging_dir=staging,
            generation_id=generation_id,
            published_at=published_at,
            producer_commit=COMMIT,
        )

    def test_publish_writes_one_pointer_and_validates_exact_generation(self) -> None:
        pointer = self._publish()

        loaded = publication.load_current(self.dashboard)

        self.assertEqual(loaded["state"], "published")
        self.assertEqual(loaded["pointer"], pointer)
        self.assertEqual(loaded["generation_id"], GENERATION_ID)
        self.assertEqual(
            set(loaded["manifest"]["files"]),
            {
                "experiments.html",
                "wasserstein-regime.txt",
                "wasserstein-regime.json",
                "research-views-status.txt",
            },
        )
        self.assertFalse((self.dashboard / "research-views-published.json").exists())
        self.assertFalse((self.dashboard / "experiments.html").exists())

    def test_one_byte_artifact_mutation_fails_closed(self) -> None:
        self._publish()
        artifact = (
            self.dashboard / "research-views-generations" / GENERATION_ID / "experiments.html"
        )
        artifact.write_bytes(artifact.read_bytes() + b"x")

        self.assertEqual(publication.load_current(self.dashboard)["state"], "integrity_failed")

    def test_extra_generation_file_and_invalid_id_fail_closed(self) -> None:
        self._publish()
        generation = self.dashboard / "research-views-generations" / GENERATION_ID
        (generation / "unexpected.txt").write_text("not allow-listed")
        self.assertEqual(publication.load_current(self.dashboard)["state"], "integrity_failed")
        with self.assertRaises(publication.PublicationError):
            publication.publish_generation(
                dashboard_dir=self.dashboard,
                staging_dir=self.staging,
                generation_id="../escape",
                published_at=PUBLISHED_AT,
                producer_commit=COMMIT,
            )

    def test_pointer_directory_escape_fails_closed(self) -> None:
        pointer = self._publish()
        pointer["manifest"]["path"] = "../outside.json"
        (self.dashboard / "research-views-current.json").write_text(
            json.dumps(pointer, sort_keys=True, separators=(",", ":")) + "\n"
        )

        self.assertEqual(publication.load_current(self.dashboard)["state"], "integrity_failed")

    def test_symlinked_pointer_generation_manifest_or_artifact_fails_closed(self) -> None:
        for target_name in ("pointer", "generation", "manifest", "artifact"):
            with self.subTest(target=target_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._publish_at(root, GENERATION_ID, PUBLISHED_AT, target_name)
                dashboard = root / ".tmp" / "dashboard"
                generation = dashboard / "research-views-generations" / GENERATION_ID
                targets = {
                    "pointer": dashboard / "research-views-current.json",
                    "generation": generation,
                    "manifest": generation / "research-views-manifest.json",
                    "artifact": generation / "experiments.html",
                }
                target = targets[target_name]
                outside = root / f"outside-{target_name}"
                target.rename(outside)
                target.symlink_to(outside, target_is_directory=outside.is_dir())

                self.assertEqual(publication.load_current(dashboard)["state"], "integrity_failed")

    def test_copy_is_idempotent_and_never_copies_loose_aliases(self) -> None:
        source_pointer = self._publish()
        destination_root = self.root / "destination"

        first = publication.copy_publication(
            source_root=self.root, destination_root=destination_root
        )
        second = publication.copy_publication(
            source_root=self.root, destination_root=destination_root
        )

        self.assertEqual(first, "installed")
        self.assertEqual(second, "idempotent")
        loaded = publication.load_current(destination_root / ".tmp" / "dashboard")
        self.assertEqual(loaded["state"], "published")
        self.assertEqual(loaded["generation_id"], source_pointer["generation_id"])
        self.assertEqual(loaded["pointer"]["copied_from_root"], str(self.root.resolve()))
        self.assertFalse((destination_root / ".tmp" / "dashboard" / "experiments.html").exists())

    def test_copy_compare_and_swap_keeps_newer_destination_and_rejects_equal_time_conflict(
        self,
    ) -> None:
        self._publish()
        destination_root = self.root / "destination"
        newer_id = "20260826T140000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        self._publish_at(
            destination_root,
            newer_id,
            "2026-08-26T14:00:00.000000Z",
            "newer",
        )

        result = publication.copy_publication(
            source_root=self.root, destination_root=destination_root
        )

        self.assertEqual(result, "newer_destination")
        self.assertEqual(
            publication.load_current(destination_root / ".tmp" / "dashboard")["generation_id"],
            newer_id,
        )

        equal_root = self.root / "equal"
        equal_id = "20260826T120000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        self._publish_at(equal_root, equal_id, PUBLISHED_AT, "equal")
        with self.assertRaisesRegex(publication.PublicationError, "GENERATION_CONFLICT"):
            publication.copy_publication(source_root=self.root, destination_root=equal_root)

    def test_same_root_copy_skips_without_reading_or_writing(self) -> None:
        self.assertEqual(
            publication.copy_publication(source_root=self.root, destination_root=self.root),
            "same_root",
        )

    def test_pointer_replace_failure_preserves_prior_current(self) -> None:
        self._publish()
        pointer_before = (self.dashboard / "research-views-current.json").read_bytes()
        next_id = "20260826T130000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        staging = self.dashboard / "research-views-generations" / f".staging-{next_id}"
        staging.mkdir()
        for name in publication.ARTIFACTS:
            (staging / name).write_text(f"next:{name}\n")
        real_replace = publication.os.replace

        def fail_pointer(source, destination):
            if Path(destination).name == "research-views-current.json":
                raise OSError("injected pointer replace failure")
            return real_replace(source, destination)

        with mock.patch.object(publication.os, "replace", side_effect=fail_pointer):
            with self.assertRaisesRegex(OSError, "injected pointer"):
                publication.publish_generation(
                    dashboard_dir=self.dashboard,
                    staging_dir=staging,
                    generation_id=next_id,
                    published_at="2026-08-26T13:00:00.000000Z",
                    producer_commit=COMMIT,
                )

        self.assertEqual(
            (self.dashboard / "research-views-current.json").read_bytes(), pointer_before
        )
        self.assertEqual(list(self.dashboard.glob(".research-views-current.*.tmp")), [])

    def test_generation_parent_fsync_failure_preserves_prior_pointer(self) -> None:
        self._publish()
        pointer_before = (self.dashboard / "research-views-current.json").read_bytes()
        next_id = "20260826T131000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        staging = self.dashboard / "research-views-generations" / f".staging-{next_id}"
        staging.mkdir()
        for name in publication.ARTIFACTS:
            (staging / name).write_text(f"next:{name}\n")
        real_fsync = publication._fsync_directory
        generations = (self.dashboard / "research-views-generations").resolve()

        def fail_generation_parent(path):
            if Path(path).resolve() == generations:
                raise OSError("injected generations fsync failure")
            return real_fsync(path)

        with mock.patch.object(publication, "_fsync_directory", side_effect=fail_generation_parent):
            with self.assertRaisesRegex(OSError, "generations fsync"):
                publication.publish_generation(
                    dashboard_dir=self.dashboard,
                    staging_dir=staging,
                    generation_id=next_id,
                    published_at="2026-08-26T13:10:00.000000Z",
                    producer_commit=COMMIT,
                )

        self.assertEqual(
            (self.dashboard / "research-views-current.json").read_bytes(), pointer_before
        )

    def test_dashboard_parent_fsync_failure_occurs_after_valid_pointer_commit(self) -> None:
        real_fsync = publication._fsync_directory

        def fail_dashboard_parent(path):
            if Path(path).resolve() == self.dashboard.resolve():
                raise OSError("injected dashboard fsync failure")
            return real_fsync(path)

        with mock.patch.object(publication, "_fsync_directory", side_effect=fail_dashboard_parent):
            with self.assertRaisesRegex(OSError, "dashboard fsync"):
                self._publish()

        self.assertEqual(publication.load_current(self.dashboard)["state"], "published")
        self.assertFalse((self.dashboard / "research-views-published.json").exists())

    def test_failed_attempt_preserves_current_and_records_both_exits(self) -> None:
        current = self._publish()
        before = (self.dashboard / "research-views-current.json").read_bytes()
        failed_staging = (
            self.dashboard
            / "research-views-generations"
            / ".staging-20260826T130000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        )
        failed_staging.mkdir()

        publication.record_failure(
            dashboard_dir=self.dashboard,
            attempt_id="20260826T130000000000Z-abcdefabcdefabcdefabcdefabcdefab",
            attempted_at="2026-08-26T13:00:00.000000Z",
            producer_commit=COMMIT,
            producer_root=self.root,
            experiments_exit=17,
            wasserstein_exit=0,
            staging_dir=failed_staging,
        )

        self.assertEqual((self.dashboard / "research-views-current.json").read_bytes(), before)
        failure = json.loads((self.dashboard / "research-views-last-failure.json").read_text())
        self.assertEqual(failure["experiments_exit"], 17)
        self.assertEqual(failure["wasserstein_exit"], 0)
        self.assertEqual(failure["outcome"], "FAILED")
        self.assertFalse(failed_staging.exists())
        self.assertEqual(current["generation_id"], GENERATION_ID)

    def test_failure_reconciliation_never_regresses_and_equal_time_conflicts(self) -> None:
        def failure(attempt_id: str, completed_at: str) -> dict:
            return {
                "schema": "research_views_failure/v1",
                "attempt_id": attempt_id,
                "attempted_at": "2026-08-26T12:00:00.000000Z",
                "completed_at": completed_at,
                "producer_commit": COMMIT,
                "producer_root": str(self.root.resolve()),
                "experiments_exit": 17,
                "wasserstein_exit": 0,
                "outcome": "FAILED",
            }

        first_id = "20260826T130000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        older_id = "20260826T125000000000Z-bcdefabcdefabcdefabcdefabcdefabc"
        equal_id = "20260826T130000000000Z-cdefabcdefabcdefabcdefabcdefabcd"
        self.dashboard.mkdir(parents=True, exist_ok=True)
        with publication._publication_lock(self.dashboard):
            self.assertEqual(
                publication._reconcile_failure_locked(
                    self.dashboard,
                    failure(first_id, "2026-08-26T13:00:01.000000Z"),
                ),
                "installed",
            )
            self.assertEqual(
                publication._reconcile_failure_locked(
                    self.dashboard,
                    failure(older_id, "2026-08-26T13:00:00.000000Z"),
                ),
                "older",
            )
            with self.assertRaisesRegex(publication.PublicationError, "ATTEMPT_CONFLICT"):
                publication._reconcile_failure_locked(
                    self.dashboard,
                    failure(equal_id, "2026-08-26T13:00:01.000000Z"),
                )

        retained = publication.load_failure(self.dashboard)["failure"]
        self.assertEqual(retained["attempt_id"], first_id)

    def test_newer_failure_copies_even_when_generation_is_idempotent(self) -> None:
        self._publish()
        destination_root = self.root / "destination"
        self.assertEqual(
            publication.copy_publication(source_root=self.root, destination_root=destination_root),
            "installed",
        )
        failed_id = "20260826T150000000000Z-abcdefabcdefabcdefabcdefabcdefab"
        failed_staging = self.dashboard / "research-views-generations" / f".staging-{failed_id}"
        failed_staging.mkdir()
        with mock.patch.object(
            publication,
            "_utc_now",
            return_value=datetime(2026, 8, 26, 15, 0, 1, tzinfo=timezone.utc),
        ):
            publication.record_failure(
                dashboard_dir=self.dashboard,
                attempt_id=failed_id,
                attempted_at="2026-08-26T15:00:00.000000Z",
                producer_commit=COMMIT,
                producer_root=self.root,
                experiments_exit=0,
                wasserstein_exit=17,
                staging_dir=failed_staging,
            )

        self.assertEqual(
            publication.copy_publication(source_root=self.root, destination_root=destination_root),
            "idempotent",
        )
        copied_failure = publication.load_failure(destination_root / ".tmp" / "dashboard")[
            "failure"
        ]
        self.assertEqual(copied_failure["attempt_id"], failed_id)


if __name__ == "__main__":
    unittest.main()
