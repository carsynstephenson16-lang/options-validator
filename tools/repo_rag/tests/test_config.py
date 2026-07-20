from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repo_rag.config import load_policy


class PolicyTests(unittest.TestCase):
    def test_load_policy_requires_complete_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps({"application": "test"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required fields"):
                load_policy(path)

    def test_policy_digest_is_stable(self) -> None:
        raw = {
            "application": "test-rag",
            "repository": "test-repo",
            "read_only": True,
            "tracked_files_only": True,
            "corpus_roots": ["README.md"],
            "denied_segments": [".env"],
            "supported_suffixes": [".md"],
            "source_classes": {"canonical": ["README.md"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            first = load_policy(path)
            second = load_policy(path)
            self.assertEqual(first.digest(), second.digest())
            self.assertEqual(len(first.digest()), 64)


if __name__ == "__main__":
    unittest.main()
