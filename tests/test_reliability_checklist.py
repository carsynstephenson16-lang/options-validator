from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.reliability_checklist import (
    ADVISORY_BOUNDARY,
    audit_repository,
    main,
    score_priority,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _copy_reliability_tree(destination: Path) -> None:
    source = REPOSITORY_ROOT / "docs" / "reliability"
    target = destination / "docs" / "reliability"
    target.mkdir(parents=True)
    for path in source.iterdir():
        if path.is_file():
            (target / path.name).write_bytes(path.read_bytes())


def _write_profile(root: Path, profile: dict[str, object]) -> None:
    path = root / "docs" / "reliability" / "profile.json"
    path.write_text(json.dumps(profile, sort_keys=True), encoding="utf-8")


class ReliabilityChecklistTests(unittest.TestCase):
    def test_committed_profile_audits_without_writes(self) -> None:
        reliability = REPOSITORY_ROOT / "docs" / "reliability"
        before = {path.name: path.read_bytes() for path in reliability.iterdir() if path.is_file()}

        report = audit_repository(REPOSITORY_ROOT)

        after = {path.name: path.read_bytes() for path in reliability.iterdir() if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report["advisory_boundary"], ADVISORY_BOUNDARY)
        self.assertEqual(
            sum(sum(counts.values()) for counts in report["source_status_counts"].values()),
            120,
        )
        self.assertIsNotNone(report["mlts_score"])
        self.assertTrue(report["crosswalk_consolidations"])

    def test_tampered_snapshot_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_reliability_tree(root)
            snapshot = root / "docs" / "reliability" / "catalog.snapshot.json"
            snapshot.write_bytes(snapshot.read_bytes() + b" ")

            with self.assertRaisesRegex(ValueError, "catalog snapshot digest mismatch"):
                audit_repository(root)

    def test_evidence_path_escape_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_reliability_tree(root)
            profile_path = root / "docs" / "reliability" / "profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            mapping = next(item for item in profile["mappings"] if item["evidence"])
            mapping["evidence"][0]["path"] = "../outside"
            _write_profile(root, profile)

            with self.assertRaisesRegex(ValueError, "repository-relative"):
                audit_repository(root)

    def test_changed_evidence_hash_is_reported_stale(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_reliability_tree(root)
            profile_path = root / "docs" / "reliability" / "profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            mapping = next(item for item in profile["mappings"] if item["status"] == "ENFORCED")
            evidence = next(item for item in mapping["evidence"] if item["kind"] == "file_symbol")
            evidence_path = root / evidence["path"]
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text("changed", encoding="utf-8")

            report = audit_repository(root)

            self.assertTrue(
                any(item["item_id"] == mapping["item_id"] for item in report["stale_findings"])
            )

    def test_build_nothing_overrides_high_priority_score(self) -> None:
        priority = {
            "priority_id": "already-covered",
            "item_ids": ["RML-001"],
            "proposed_control": "Duplicate existing evidence",
            "equivalent_evidence": True,
            "risk_reduction": 5,
            "recurrence": 5,
            "auditability_gain": 5,
            "cross_project_reuse": 5,
            "implementation_effort": 1,
            "maintenance_burden": 1,
            "owner_decision_required": "Explicit approval",
        }

        result = score_priority(priority, gap_item_ids=frozenset({"RML-001"}))

        self.assertEqual(result["decision_band"], "BUILD_NOTHING")
        self.assertEqual(result["priority_score"], 100.0)

    def test_cli_real_path_returns_zero_and_json(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            result = main(["--root", str(REPOSITORY_ROOT), "audit", "--format", "json"])

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["advisory_boundary"], ADVISORY_BOUNDARY)


if __name__ == "__main__":
    unittest.main()
