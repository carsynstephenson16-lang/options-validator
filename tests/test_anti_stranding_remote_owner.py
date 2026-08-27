from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools" / "anti-stranding"
LIBRARY = TOOLS / "anti-stranding-lib.sh"
POST_COMMIT = TOOLS / "post-commit"
WORKTREE_GUARD = TOOLS / "worktree-remove-guard.sh"
RECONCILER = TOOLS / "repo-reconcile"
REAL_GIT = shutil.which("git")
ZSH = shutil.which("zsh")


@unittest.skipUnless(ZSH is not None, "requires zsh; anti-stranding scripts are macOS/zsh-only")
class AntiStrandingRemoteOwnerTests(unittest.TestCase):
    def setUp(self) -> None:
        if REAL_GIT is None:
            self.fail("git is required for anti-stranding integration tests")
        assert ZSH is not None
        self.zsh = ZSH
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.home = self.root / "home"
        self.bin = self.root / "stub-bin"
        self.calls = self.root / "calls.log"
        self.dangerous = self.root / "dangerous.log"
        self.home.mkdir()
        self.bin.mkdir()
        self._write_stubs()

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _write_executable(self, path: Path, body: str) -> None:
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def _write_stubs(self) -> None:
        self._write_executable(
            self.bin / "git",
            f"#!{self.zsh}\n"
            + """\
print -r -- "git $*" >> "$CALLS"
typeset -a original
original=("$@")
if [ "$1" = "-C" ]; then
  command_name="$3"
else
  command_name="$1"
fi
if [ "$command_name" = "push" ]; then
  print -r -- "git $*" >> "$DANGEROUS"
  exit 97
fi
if [ "$command_name" = "fetch" ]; then
  exit 0
fi
exec "$REAL_GIT" "${original[@]}"
""",
        )
        self._write_executable(
            self.bin / "gh",
            f"#!{self.zsh}\n"
            + """\
print -r -- "gh $*" >> "$CALLS"
if [ "$1" = "api" ] && [ "$2" = "user" ]; then
  [ -n "${GH_API_LOGIN:-}" ] || exit 1
  print -r -- "$GH_API_LOGIN"
  exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "list" ]; then
  print -r -- "0"
  exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "create" ]; then
  print -r -- "gh $*" >> "$DANGEROUS"
  exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "merge" ]; then
  print -r -- "gh $*" >> "$DANGEROUS"
  exit 97
fi
exit 97
""",
        )
        self._write_executable(self.bin / "osascript", f"#!{self.zsh}\nexit 0\n")

    def _env(self, *, gh_api_login: str = "") -> dict[str, str]:
        return {
            **os.environ,
            "CALLS": str(self.calls),
            "DANGEROUS": str(self.dangerous),
            "GH_API_LOGIN": gh_api_login,
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "REAL_GIT": str(REAL_GIT),
        }

    def _git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(REAL_GIT), *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    def _repo(self, remote: str, *, name: str = "project") -> Path:
        repo = self.home / name
        repo.mkdir()
        self._git("init", "-b", "feature", cwd=repo)
        self._git("config", "user.email", "test@example.invalid", cwd=repo)
        self._git("config", "user.name", "Anti-Stranding Test", cwd=repo)
        (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
        self._git("add", "tracked.txt", cwd=repo)
        self._git("commit", "-m", "fixture", cwd=repo)
        self._git("remote", "add", "origin", remote, cwd=repo)
        return repo

    def _install_library(self) -> None:
        if LIBRARY.exists():
            destination = self.home / "bin" / LIBRARY.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIBRARY, destination)

    def _parse_owner(self, remote: str) -> subprocess.CompletedProcess[str]:
        command = (
            f"source {shlex.quote(str(LIBRARY))}; anti_stranding_github_owner {shlex.quote(remote)}"
        )
        return subprocess.run(
            [self.zsh, "-c", command],
            capture_output=True,
            text=True,
        )

    def _owner_ok(self, repo: Path, login: str) -> subprocess.CompletedProcess[str]:
        command = (
            f"source {shlex.quote(str(LIBRARY))}; "
            f"anti_stranding_remote_owner_ok {shlex.quote(str(repo))} {shlex.quote(login)}"
        )
        return subprocess.run(
            [self.zsh, "-c", command],
            env=self._env(),
            capture_output=True,
            text=True,
        )

    def _wait_for_background_commands(self) -> None:
        for _ in range(40):
            if self.dangerous.exists():
                return
            time.sleep(0.025)

    def _dangerous_lines(self) -> list[str]:
        if not self.dangerous.exists():
            return []
        return self.dangerous.read_text(encoding="utf-8").splitlines()

    def test_parser_accepts_only_structural_github_repository_urls(self) -> None:
        accepted = {
            "https://github.com/Owner/repo.git": "Owner",
            "https://OWNER@GitHub.Com/Owner/repo": "Owner",
            "ssh://git@github.com/Owner/repo.git": "Owner",
            "git@GITHUB.COM:Owner/repo.git": "Owner",
        }
        for remote, expected_owner in accepted.items():
            with self.subTest(remote=remote):
                result = self._parse_owner(remote)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected_owner)

        refused = [
            "https://github.com.evil.com/Owner/repo.git",
            "https://github.com@evil.com/Owner/repo.git",
            "/tmp/Owner/repo.git",
            "https://github.com:443/Owner/repo.git",
            "ssh://git@github.com:22/Owner/repo.git",
            "https://github.com/Owner/repo/extra",
            "git@example.com:Owner/repo.git",
        ]
        for remote in refused:
            with self.subTest(remote=remote):
                result = self._parse_owner(remote)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout, "")

    def test_remote_verifier_checks_every_push_destination_and_login_case(self) -> None:
        repo = self._repo("https://github.com/owner/repo.git")
        result = self._owner_ok(repo, "OWNER")
        self.assertEqual(result.returncode, 0, result.stderr)

        self._git(
            "remote",
            "set-url",
            "--push",
            "origin",
            "https://github.com/owner/repo.git",
            cwd=repo,
        )
        self._git(
            "remote",
            "set-url",
            "--push",
            "--add",
            "origin",
            "https://evil.example/owner/repo.git",
            cwd=repo,
        )
        result = self._owner_ok(repo, "owner")
        self.assertNotEqual(result.returncode, 0)

    def test_remote_verifier_accepts_effective_push_instead_of_without_pushurl(self) -> None:
        repo = self._repo("mirror:Owner/repo.git")
        self._git("config", "url.https://github.com/.pushInsteadOf", "mirror:", cwd=repo)
        result = self._owner_ok(repo, "owner")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_post_commit_refuses_spoofed_host_without_invoking_push(self) -> None:
        repo = self._repo("https://evil.example/Owner/repo.git")
        self._install_library()
        cache = self.home / ".config" / "repo-reconcile" / "gh-login"
        cache.parent.mkdir(parents=True)
        cache.write_text("Owner\n", encoding="utf-8")

        result = subprocess.run(
            [self.zsh, str(POST_COMMIT)],
            cwd=repo,
            env=self._env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self._wait_for_background_commands()
        self.assertEqual(self._dangerous_lines(), [])

    def test_post_commit_fails_closed_when_shared_library_is_missing(self) -> None:
        repo = self._repo("https://github.com/Owner/repo.git")
        cache = self.home / ".config" / "repo-reconcile" / "gh-login"
        cache.parent.mkdir(parents=True)
        cache.write_text("Owner\n", encoding="utf-8")

        result = subprocess.run(
            [self.zsh, str(POST_COMMIT)],
            cwd=repo,
            env=self._env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self._wait_for_background_commands()
        self.assertEqual(self._dangerous_lines(), [])

    def test_worktree_guard_refuses_spoofed_host_without_invoking_push(self) -> None:
        repo = self._repo("ssh://git@evil.example/Owner/repo.git")
        self._install_library()
        cache = self.home / ".config" / "repo-reconcile" / "gh-login"
        cache.parent.mkdir(parents=True)
        cache.write_text("Owner\n", encoding="utf-8")
        payload = json.dumps({"worktree_path": str(repo)})

        result = subprocess.run(
            [self.zsh, str(WORKTREE_GUARD)],
            input=payload,
            env=self._env(),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('"decision":"block"', result.stdout)
        self._wait_for_background_commands()
        self.assertEqual(self._dangerous_lines(), [])

    def _reconciler_fixture(self) -> Path:
        repo = self._repo("https://github.com/Owner/project.git")
        initial = self._git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        self._git("branch", "-M", "main", cwd=repo)
        self._git("update-ref", "refs/remotes/origin/main", initial, cwd=repo)
        self._git("switch", "-c", "feature", cwd=repo)
        (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
        self._git("add", "tracked.txt", cwd=repo)
        self._git("commit", "-m", "feature", cwd=repo)
        feature = self._git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        self._git("update-ref", "refs/remotes/origin/feature", feature, cwd=repo)
        (self.home / "Desktop").mkdir()
        self._install_library()
        return repo

    def _run_reconciler(
        self, *, dry_run: bool, gh_api_login: str
    ) -> subprocess.CompletedProcess[str]:
        harness = self.root / "reconciler-harness.zsh"
        harness.write_text(
            f"""#!{self.zsh}
git() {{ {shlex.quote(str(self.bin / "git"))} "$@"; }}
gh() {{ {shlex.quote(str(self.bin / "gh"))} "$@"; }}
osascript() {{ {shlex.quote(str(self.bin / "osascript"))} "$@"; }}
source {shlex.quote(str(RECONCILER))}
""",
            encoding="utf-8",
        )
        env = self._env(gh_api_login=gh_api_login)
        env["DRY_RUN"] = "1" if dry_run else "0"
        return subprocess.run([self.zsh, str(harness)], env=env, capture_output=True, text=True)

    def test_reconciler_dry_run_is_inert_and_created_pr_is_always_draft(self) -> None:
        self._reconciler_fixture()

        dry_run = self._run_reconciler(dry_run=True, gh_api_login="Owner")
        self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
        self.assertEqual(self._dangerous_lines(), [])

        action = self._run_reconciler(dry_run=False, gh_api_login="Owner")
        self.assertEqual(action.returncode, 0, action.stderr)
        dangerous = self._dangerous_lines()
        creates = [line for line in dangerous if line.startswith("gh pr create ")]
        self.assertGreaterEqual(len(creates), 1, dangerous)
        for line in creates:
            self.assertIn("--draft", shlex.split(line))
        self.assertFalse(any(line.startswith("git ") for line in dangerous), dangerous)
        self.assertFalse(any("gh pr merge" in line for line in dangerous), dangerous)
        digest = self.home / ".local" / "state" / "repo-reconcile" / "digest.md"
        self.assertIn("DRAFT PR awaiting the owner's make-ready", digest.read_text())

    def test_reconciler_prefers_cached_login_when_live_lookup_fails(self) -> None:
        self._reconciler_fixture()
        cache = self.home / ".config" / "repo-reconcile" / "gh-login"
        cache.parent.mkdir(parents=True)
        cache.write_text("oWnEr\n", encoding="utf-8")

        result = self._run_reconciler(dry_run=False, gh_api_login="")
        self.assertEqual(result.returncode, 0, result.stderr)
        creates = [line for line in self._dangerous_lines() if line.startswith("gh pr create ")]
        self.assertGreaterEqual(len(creates), 1)


if __name__ == "__main__":
    unittest.main()
