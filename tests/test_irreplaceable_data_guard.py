"""Tests for tools/irreplaceable_data_guard.py.

These run entirely against temporary fixtures -- never the real 5 GB cache --
so they stay offline, fast, and green on a fresh clone with no cache present.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import irreplaceable_data_guard as guard


def _write(root: Path, rel: str, payload: bytes = b"x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


class ScanTests(unittest.TestCase):
    def test_absent_directory_reports_not_present(self):
        with tempfile.TemporaryDirectory() as temp:
            result = guard.scan(os.path.join(temp, "nope"))
        self.assertFalse(result["present"])
        self.assertEqual(result["file_count"], 0)
        self.assertEqual(result["total_bytes"], 0)

    def test_counts_nested_files_recursively(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "raw/MU/2025-07-25/chain.parquet", b"abc")
            _write(root, "raw/ET/2025-07-25/chain.parquet", b"de")
            _write(root, "top.parquet", b"f")
            result = guard.scan(str(root))
        self.assertTrue(result["present"])
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["total_bytes"], 6)

    def test_deep_digest_is_deterministic_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "a/one.parquet", b"one")
            _write(root, "b/two.parquet", b"two")
            first = guard.scan(str(root), deep=True)
            second = guard.scan(str(root), deep=True)
            self.assertEqual(first["content_digest"], second["content_digest"])

            _write(root, "b/two.parquet", b"CHANGED")
            third = guard.scan(str(root), deep=True)
        self.assertNotEqual(first["content_digest"], third["content_digest"])


class VerifyTests(unittest.TestCase):
    def test_healthy_cache_reports_no_problems(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}
            self.assertEqual(guard.verify(inventory), [])

    def test_lost_file_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            kept = _write(root, "b.parquet", b"bbb")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}

            kept.unlink()
            problems = guard.verify(inventory)
        self.assertEqual(len(problems), 2)  # lost file + shrank
        self.assertIn("LOST FILES", problems[0])

    def test_entirely_missing_namespace_fails_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}

            for child in root.iterdir():
                child.unlink()
            root.rmdir()
            problems = guard.verify(inventory)
        self.assertEqual(len(problems), 1)
        self.assertIn("MISSING ENTIRELY", problems[0])

    def test_allow_absent_skips_fresh_clone_but_still_catches_partial_loss(self):
        """A fresh clone has no cache (fine). A HALF-DELETED cache is not fine."""
        with tempfile.TemporaryDirectory() as temp:
            gone = Path(temp) / "gone"
            partial = Path(temp) / "partial"
            _write(gone, "a.parquet", b"aaa")
            _write(partial, "a.parquet", b"aaa")
            doomed = _write(partial, "b.parquet", b"bbb")
            inventory = {
                "namespaces": {
                    str(gone): guard.scan(str(gone)),
                    str(partial): guard.scan(str(partial)),
                }
            }

            gone.joinpath("a.parquet").unlink()
            gone.rmdir()
            doomed.unlink()

            problems = guard.verify(inventory, allow_absent=True)
        self.assertTrue(all("MISSING ENTIRELY" not in p for p in problems))
        self.assertTrue(any("LOST FILES" in p for p in problems))

    def test_growth_is_not_a_problem(self):
        """Adding data is fine; only loss is an incident."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}

            _write(root, "c.parquet", b"ccccc")
            self.assertEqual(guard.verify(inventory), [])

    def test_never_recorded_namespace_is_ignored(self):
        inventory = {
            "namespaces": {"/nonexistent/ns": {"present": False, "file_count": 0, "total_bytes": 0}}
        }
        self.assertEqual(guard.verify(inventory), [])

    def test_recorded_absent_population_is_detected_without_weakening_empty_skip(self):
        """Presence without a floor alarms; a genuinely empty namespace does not."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populated = root / "populated"
            empty = root / "empty"
            _write(populated, "one.parquet", b"abc")
            empty.mkdir()
            inventory = {
                "namespaces": {
                    "populated": {"present": False, "file_count": 0, "total_bytes": 0},
                    "empty": {"present": False, "file_count": 0, "total_bytes": 0},
                }
            }

            problems = guard.verify(inventory, root=str(root))

        self.assertEqual(len(problems), 1)
        self.assertIn("RECORDED ABSENT BUT POPULATED", problems[0])
        self.assertIn("populated", problems[0])
        self.assertNotIn("empty", problems[0])

    def test_allow_absent_does_not_suppress_recorded_absent_population(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "populated/one.parquet", b"abc")
            inventory = {
                "namespaces": {"populated": {"present": False, "file_count": 0, "total_bytes": 0}}
            }

            problems = guard.verify(inventory, allow_absent=True, root=str(root))

        self.assertEqual(len(problems), 1)
        self.assertIn("RECORDED ABSENT BUT POPULATED", problems[0])

    def test_tracked_namespace_is_exempt_from_absent_and_floor_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            namespace = "reports/schwab_chains"
            _write(root, f"{namespace}/x", b"x")
            recorded_absent = {
                "namespaces": {namespace: {"present": False, "file_count": 0, "total_bytes": 0}}
            }
            positive_floor = {
                "namespaces": {namespace: {"present": True, "file_count": 2, "total_bytes": 2}}
            }

            self.assertEqual(guard.verify(recorded_absent, root=str(root)), [])
            self.assertEqual(guard.verify(positive_floor, root=str(root)), [])

    def test_required_namespaces_report_missing_key_only_when_requested(self):
        inventory = {"namespaces": {}}

        problems = guard.verify(inventory, required_namespaces=["missing/ns"])

        self.assertEqual(
            problems,
            ["missing/ns: NO INVENTORY KEY -- required namespace is not recorded at all."],
        )
        self.assertEqual(guard.verify(inventory, required_namespaces=None), [])

    def test_deep_verify_detects_silent_content_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"original")
            inventory = {"namespaces": {str(root): guard.scan(str(root), deep=True)}}

            _write(root, "a.parquet", b"tampered")  # same name, same length
            shallow = guard.verify(inventory, deep=False)
            deep = guard.verify(inventory, deep=True)
        self.assertEqual(shallow, [])  # counts/sizes match -- invisible
        self.assertEqual(len(deep), 1)
        self.assertIn("CONTENT CHANGED", deep[0])


class InventoryShapeTests(unittest.TestCase):
    def test_schwab_chains_is_covered(self):
        self.assertIn(".cache/schwab_chains", guard.DEFAULT_NAMESPACES)

    def test_schwab_chain_reports_are_covered(self):
        self.assertIn("reports/schwab_chains", guard.DEFAULT_NAMESPACES)

    def test_future_tickers_is_covered(self):
        """The 2026-08-03 incident namespace must never drop off the list."""
        self.assertIn(".cache/future_tickers", guard.DEFAULT_NAMESPACES)

    def test_chains_v2_is_covered(self):
        self.assertIn(".cache/chains_v2", guard.DEFAULT_NAMESPACES)

    def test_committed_inventory_records_the_incident_namespace(self):
        import json

        repo_root = Path(__file__).resolve().parents[1]
        inventory_path = repo_root / guard.DEFAULT_INVENTORY
        if not inventory_path.exists():  # fresh clone before first generate
            self.skipTest("inventory not generated in this checkout")
        inventory = json.loads(inventory_path.read_text())
        self.assertIn(".cache/future_tickers", inventory["namespaces"])
        self.assertIn(".cache/schwab_chains", inventory["namespaces"])
        self.assertIn("reports/schwab_chains", inventory["namespaces"])


class RepoRootAnchoringTests(unittest.TestCase):
    """The CLI must anchor on the main checkout, never the invoking directory.

    2026-08-09 false alarm: run with cwd inside a linked worktree, the guard
    found the committed inventory (it travels with every checkout) but not the
    gitignored bytes (they exist only in the main checkout), and reported all
    ~5 GB as MISSING ENTIRELY while every byte sat safe. The one alarm that
    must never cry wolf was crying wolf in its primary use case -- CLAUDE.md
    requires running it exactly when worktrees are about to be deleted.
    """

    GUARD = str(Path(guard.__file__).resolve())

    def _run(self, cwd, *argv, env=None):
        return subprocess.run(
            [sys.executable, self.GUARD, *argv],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env,
        )

    def _fixture_repo(self, temp: Path) -> Path:
        """A tiny git repo shaped like the real one: committed inventory,
        gitignored-in-spirit (untracked) namespace bytes."""
        repo = temp / "main"
        repo.mkdir()

        def git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                check=True,
                capture_output=True,
            )

        git("init", "-q")
        _write(repo, "myns/a.parquet", b"aaa")
        namespaces = {
            ns: {"present": False, "file_count": 0, "total_bytes": 0}
            for ns in guard.DEFAULT_NAMESPACES
        }
        namespaces["myns"] = guard.scan(str(repo / "myns"))
        inventory = {"namespaces": namespaces}
        inv = repo / "data" / "irreplaceable_data_inventory.json"
        inv.parent.mkdir(parents=True)
        inv.write_text(json.dumps(inventory))
        git("add", "data")
        git("commit", "-qm", "inventory")
        return repo

    def _write_inventory(self, path: Path, inventory: dict) -> bytes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        return path.read_bytes()

    def test_verify_from_linked_worktree_is_not_a_loss_report(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            worktree = Path(temp) / "wt"
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "--detach", "-q", str(worktree)],
                check=True,
                capture_output=True,
            )
            result = self._run(worktree, "verify")
        self.assertNotIn("MISSING ENTIRELY", result.stderr)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("irreplaceable data: OK", result.stdout)
        self.assertIn("main checkout", result.stderr)  # says what it anchored on

    def test_verify_from_subdirectory_anchors_on_repo_root(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            sub = repo / "deep" / "dir"
            sub.mkdir(parents=True)
            result = self._run(sub, "verify")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("MISSING ENTIRELY", result.stderr)

    def test_outside_any_repo_is_a_location_error_not_a_loss(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(Path(temp).parent)}
            result = self._run(temp, "verify", env=env)
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("NOT a data-loss finding", result.stderr)
        self.assertNotIn("MISSING ENTIRELY", result.stderr)

    def test_genuine_loss_still_alarms_from_the_main_checkout(self):
        """The fix must not soften the real alarm -- only relocate its anchor."""
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            (repo / "myns" / "a.parquet").unlink()
            (repo / "myns").rmdir()
            result = self._run(repo, "verify")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING ENTIRELY", result.stderr)
        self.assertIn("cannot be re-fetched", result.stderr)
        # every namespace absent => point at the canonical checkout first
        self.assertIn("canonical", result.stderr)

    def test_cacheless_clone_reports_loss_not_location_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self._fixture_repo(root)
            clone = root / "clone"
            subprocess.run(
                ["git", "clone", "--local", "-q", str(source), str(clone)],
                check=True,
                capture_output=True,
            )

            result = self._run(clone, "verify")

        self.assertEqual(result.returncode, 1, msg=result.stderr)
        self.assertNotEqual(result.returncode, 2)
        self.assertIn("MISSING ENTIRELY", result.stderr)
        self.assertNotIn("LOCATION ERROR", result.stderr)

    def test_cli_required_namespace_check_is_default_only(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            default_path = repo / guard.DEFAULT_INVENTORY

            seeded = self._run(repo, "verify")
            self.assertEqual(seeded.returncode, 0, msg=seeded.stderr)
            self.assertIn("irreplaceable data: OK", seeded.stdout)

            inventory = json.loads(default_path.read_text())
            missing_namespace = guard.DEFAULT_NAMESPACES[0]
            del inventory["namespaces"][missing_namespace]
            default_path.write_text(json.dumps(inventory))
            missing = self._run(repo, "verify")
            self.assertEqual(missing.returncode, 1, msg=missing.stderr)
            self.assertIn("NO INVENTORY KEY", missing.stderr)
            self.assertIn(missing_namespace, missing.stderr)

            bespoke_path = repo / "bespoke.json"
            self._write_inventory(
                bespoke_path,
                {"namespaces": {"myns": guard.scan(str(repo / "myns"))}},
            )
            bespoke = self._run(repo, "verify", "--inventory", str(bespoke_path))
            self.assertEqual(bespoke.returncode, 0, msg=bespoke.stderr)
            self.assertNotIn("NO INVENTORY KEY", bespoke.stderr)

    def test_plain_generate_pins_populated_tracked_namespace_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            _write(repo, "reports/schwab_chains/x", b"tracked")

            result = self._run(repo, "generate")

            inventory = json.loads((repo / guard.DEFAULT_INVENTORY).read_text())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            inventory["namespaces"]["reports/schwab_chains"],
            {"present": False, "file_count": 0, "total_bytes": 0},
        )

    def test_generate_only_rescans_target_and_preserves_other_values(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            _write(repo, ".cache/schwab_chains/one.parquet", b"abc")
            inventory_path = repo / "scoped.json"
            inventory = {
                "note": "keep-this-note-byte-for-byte",
                "namespaces": {
                    ".cache/chains": {
                        "present": True,
                        "file_count": 77,
                        "total_bytes": 12345,
                        "content_digest": "untouched-digest",
                    },
                    ".cache/schwab_chains": {
                        "present": False,
                        "file_count": 0,
                        "total_bytes": 0,
                    },
                },
            }
            self._write_inventory(inventory_path, inventory)

            result = self._run(
                repo,
                "generate",
                "--deep",
                "--only",
                ".cache/schwab_chains",
                "--inventory",
                str(inventory_path),
            )

            updated = json.loads(inventory_path.read_text())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(updated["note"], inventory["note"])
        self.assertEqual(
            updated["namespaces"][".cache/chains"],
            inventory["namespaces"][".cache/chains"],
        )
        self.assertEqual(updated["namespaces"][".cache/schwab_chains"]["file_count"], 1)
        self.assertEqual(updated["namespaces"][".cache/schwab_chains"]["total_bytes"], 3)
        self.assertIn("content_digest", updated["namespaces"][".cache/schwab_chains"])

    def test_generate_only_refuses_lower_floor_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            _write(repo, ".cache/schwab_chains/one.parquet", b"x")
            inventory_path = repo / "scoped.json"
            before = self._write_inventory(
                inventory_path,
                {
                    "note": "unchanged",
                    "namespaces": {
                        ".cache/schwab_chains": {
                            "present": True,
                            "file_count": 2,
                            "total_bytes": 4,
                        }
                    },
                },
            )

            result = self._run(
                repo,
                "generate",
                "--only",
                ".cache/schwab_chains",
                "--inventory",
                str(inventory_path),
            )
            after = inventory_path.read_bytes()

        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("LOWER", result.stderr)
        self.assertEqual(after, before)

    def test_generate_only_refuses_unknown_namespace_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            inventory_path = repo / "scoped.json"
            before = self._write_inventory(inventory_path, {"note": "keep", "namespaces": {}})

            result = self._run(
                repo,
                "generate",
                "--only",
                "unknown/ns",
                "--inventory",
                str(inventory_path),
            )
            after = inventory_path.read_bytes()

        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("not in DEFAULT_NAMESPACES", result.stderr)
        self.assertEqual(after, before)

    def test_generate_only_honors_absolute_inventory_and_leaves_default_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            default_path = repo / guard.DEFAULT_INVENTORY
            default_before = default_path.read_bytes()
            _write(repo, ".cache/schwab_chains/one.parquet", b"abc")
            inventory_path = repo / "nested" / "scoped.json"
            self._write_inventory(
                inventory_path,
                {
                    "note": "scoped",
                    "namespaces": {
                        ".cache/schwab_chains": {
                            "present": False,
                            "file_count": 0,
                            "total_bytes": 0,
                        }
                    },
                },
            )

            result = self._run(
                repo,
                "generate",
                "--only",
                ".cache/schwab_chains",
                "--inventory",
                str(inventory_path),
            )

            updated = json.loads(inventory_path.read_text())
            default_after = default_path.read_bytes()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(updated["namespaces"][".cache/schwab_chains"]["file_count"], 1)
        self.assertEqual(default_after, default_before)

    def test_generate_only_creates_missing_default_namespace_key(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            _write(repo, ".cache/schwab_chains/one.parquet", b"abc")
            inventory_path = repo / "scoped.json"
            self._write_inventory(
                inventory_path,
                {"note": "keep", "namespaces": {".cache/chains": {"sentinel": "same"}}},
            )

            result = self._run(
                repo,
                "generate",
                "--only",
                ".cache/schwab_chains",
                "--inventory",
                str(inventory_path),
            )

            updated = json.loads(inventory_path.read_text())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(updated["namespaces"][".cache/schwab_chains"]["file_count"], 1)
        self.assertEqual(updated["namespaces"][".cache/chains"], {"sentinel": "same"})

    def test_generate_only_requires_existing_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            inventory_path = repo / "missing.json"

            result = self._run(
                repo,
                "generate",
                "--only",
                ".cache/schwab_chains",
                "--inventory",
                str(inventory_path),
            )
            inventory_exists = inventory_path.exists()

        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("inventory not found", result.stderr)
        self.assertFalse(inventory_exists)


if __name__ == "__main__":
    unittest.main()
