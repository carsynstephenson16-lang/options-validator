from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from repo_rag.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "fills.md").write_text(
            "Fills execute at quote mid or worse with a slippage haircut.\n",
            encoding="utf-8",
        )
        self.policy_path = self.root / "policy.json"
        self.policy_path.write_text(
            json.dumps(
                {
                    "application": "test-rag",
                    "repository": "test-repo",
                    "read_only": True,
                    "tracked_files_only": True,
                    "corpus_roots": ["docs"],
                    "denied_segments": [],
                    "supported_suffixes": [".md"],
                    "source_classes": {"derived": ["docs/"]},
                }
            ),
            encoding="utf-8",
        )
        self.index_dir = self.root / ".index"

    def _run(self, *argv: str) -> tuple[int, dict]:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(list(argv))
        return code, json.loads(stream.getvalue())

    def _ingest_args(self) -> list[str]:
        return [
            "ingest",
            "--policy", str(self.policy_path),
            "--repo-root", str(self.root),
            "--index-dir", str(self.index_dir),
            "--no-git",
        ]

    def test_ingest_then_query_answers_with_citation(self) -> None:
        code, report = self._run(*self._ingest_args())
        self.assertEqual(code, 0)
        self.assertEqual(report["sources_indexed"], 1)
        code, result = self._run(
            "query", "how do fills execute",
            "--index-dir", str(self.index_dir),
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["outcome"], "ANSWERED")
        self.assertIn("docs/fills.md:L1-L1", result["citations"])

    def test_query_abstention_exit_code(self) -> None:
        self._run(*self._ingest_args())
        code, result = self._run(
            "query", "zzqx unrelated",
            "--index-dir", str(self.index_dir),
        )
        self.assertEqual(code, 3)
        self.assertEqual(result["outcome"], "INSUFFICIENT_EVIDENCE")

    def test_query_without_index_exit_code(self) -> None:
        code, result = self._run(
            "query", "anything",
            "--index-dir", str(self.index_dir),
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["outcome"], "INDEX_MISSING")

    def test_query_corrupt_index_exit_code(self) -> None:
        self._run(*self._ingest_args())
        (self.index_dir / "manifest.json").write_text("{not json", encoding="utf-8")
        code, result = self._run(
            "query", "anything",
            "--index-dir", str(self.index_dir),
        )
        self.assertEqual(code, 2)
        self.assertEqual(result["outcome"], "INDEX_CORRUPT")

    def test_eval_subcommand_exit_codes(self) -> None:
        self._run(*self._ingest_args())
        golden = self.root / "golden.json"
        golden.write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "case_id": "fills",
                            "query": "how do fills execute",
                            "kind": "positive",
                            "expected_source_paths": ["docs/fills.md"],
                            "forbidden_source_paths": [],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        code, report = self._run(
            "eval", "--golden", str(golden), "--index-dir", str(self.index_dir)
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["passed"], 1)


if __name__ == "__main__":
    unittest.main()
