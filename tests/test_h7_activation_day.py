"""Hermetic activation-day shell tests; no provider or operational store is used."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/h7_activation_day.sh"


class ActivationDayTests(unittest.TestCase):
    def setUp(self):
        self.zsh = shutil.which("zsh")
        if not self.zsh:
            self.skipTest("zsh required")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.env = {
            **os.environ,
            "HOME": str(self.base),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "PYTHONPATH": str(ROOT),
            "TEST_ROOT": str(self.repo),
        }
        for key in list(self.env):
            if key.startswith("GIT_") and key not in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"):
                self.env.pop(key)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", "")
        (self.repo / ".gitignore").write_text(".tmp/\n.env\n")
        (self.repo / "code.py").write_text("# reviewed\n")
        (self.repo / "tools").mkdir()
        if SCRIPT.exists():
            shutil.copyfile(SCRIPT, self.repo / "tools/h7_activation_day.sh")
        package = self.repo / "reports/schwab_chains/2026-09-04"
        package.mkdir(parents=True)
        (package / "manifest.json").write_text('{"manifest_hash":"manifest-fixture"}')
        (package / "preclose.json").write_text("{}")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture base")
        remote = self.base / "remote.git"
        self.git("init", "--bare", str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-qu", "origin", "main")
        self.initial = self.git("rev-parse", "HEAD")
        bindir = self.base / "bin"
        bindir.mkdir()
        self.env["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]
        self.env["RESTIC_REPOSITORY"] = "fixture-restic"
        self.env["RESTIC_PASSWORD_FILE"] = "fixture-password-path"
        (bindir / "uv").write_text("#!" + sys.executable + "\n" + FAKE_UV)
        (bindir / "uv").chmod(0o755)

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, env=self.env, text=True, capture_output=True, check=True
        ).stdout.strip()

    def run_script(self, *args, **env):
        target = self.repo / "tools/h7_activation_day.sh"
        self.assertTrue(target.exists(), "activation-day entry point is missing")
        completed = subprocess.run(
            [self.zsh, str(target), "--allow-checkout", str(self.repo), *args],
            cwd=self.base,
            env={**self.env, **env},
            capture_output=True,
            text=True,
            timeout=60,
        )
        return completed

    def calls(self):
        path = self.repo / ".tmp/calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_no_producers(self):
        self.assertFalse(
            any(
                c[0] in ("source", "gate", "backup", "restore", "feasibility") for c in self.calls()
            )
        )
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)

    def test_untracked_file_refuses_before_producers(self):
        (self.repo / "unknown.txt").write_text("keep")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--stage-routine-evidence", result.stdout)
        self.assert_no_producers()

    def test_non_evidence_ahead_refuses(self):
        (self.repo / "code.py").write_text("# unreviewed\n")
        self.git("add", "code.py")
        self.git("commit", "-qm", "code ahead")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("aligned", result.stdout)
        self.assertFalse(self.calls())

    def test_behind_origin_refuses(self):
        other = self.base / "other"
        subprocess.run(
            ["git", "clone", "-q", "-b", "main", str(self.base / "remote.git"), str(other)],
            env=self.env,
            check=True,
        )
        (other / "new.txt").write_text("remote code")
        for args in (
            ("config", "user.name", "Fixture"),
            ("config", "user.email", "fixture@example.invalid"),
            ("config", "core.hooksPath", ""),
            ("add", "."),
            ("commit", "-qm", "remote"),
            ("push", "-q", "origin", "main"),
        ):
            subprocess.run(["git", *args], cwd=other, env=self.env, check=True, capture_output=True)
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("aligned", result.stdout)
        self.assert_no_producers()

    def test_expired_token_refuses_before_producers(self):
        result = self.run_script(TEST_TOKEN="EXPIRED")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EXPIRED", result.stdout)
        self.assert_no_producers()

    def test_missing_package_refuses_before_producers(self):
        (self.repo / "reports/schwab_chains/2026-09-04/preclose.json").unlink()
        self.git("add", ".")
        self.git("commit", "-qm", "fixture gap")
        self.initial = self.git("rev-parse", "HEAD")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NO_PACKAGE_FOR_SESSION", result.stdout)
        self.assert_no_producers()

    def test_unhealthy_included_stops_even_source_exit_zero(self):
        result = self.run_script(TEST_UNHEALTHY="1", TEST_SOURCE_RC="0")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("h7_refresh_earnings.py", result.stdout)
        self.assertEqual(
            [c[0] for c in self.calls() if c[0] in ("source", "gate", "backup", "restore")],
            ["source"],
        )
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)

    def test_success_commits_index_and_leaves_clean_tree(self):
        self.assert_success(self.run_script(TEST_SOURCE_RC="1"))

    def test_quote_warning_three_continues(self):
        self.assert_success(self.run_script(TEST_GATE_RC="3"))

    def assert_success(self, result, commits="1"):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-list", "--count", self.initial + "..HEAD"), commits)
        changed = self.git("diff", "--name-only", self.initial, "HEAD").splitlines()
        self.assertIn("reports/h7_forward_schwab/2026-09-08-activation-day-receipts.json", changed)
        allowed = (
            re.search(
                r"EVIDENCE_ALLOW=\((.*?)\)",
                (ROOT / "tools/schwab_chain_capture.sh").read_text(),
                re.S,
            )
            .group(1)
            .split()
        )
        self.assertTrue(
            all(any(p == a or p.startswith(a + "/") for a in allowed) for p in changed), changed
        )
        kinds = [c[0] for c in self.calls()]
        self.assertLess(kinds.index("source"), kinds.index("gate"))
        self.assertLess(kinds.index("gate"), kinds.index("backup"))
        self.assertLess(kinds.index("backup"), kinds.index("restore"))
        self.assertIn("EVIDENCE TEMPLATE IS INCOMPLETE", result.stdout)
        self.assertIn("recompute code_commit", result.stdout)
        for option in ("--owner-typed-spec-sha256", "--confirm", "--trim-rule"):
            self.assertIn(option + " '<OWNER TYPES>'", result.stdout)
        self.assertIn("push origin main", result.stdout)
        template = json.loads(
            (self.repo / ".tmp/h7_activation_day/2026-09-08-evidence.template.json").read_text()
        )
        self.assertEqual(template["code_commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(self.git("rev-parse", "origin/main"), self.initial)

    def test_routine_intersection_accepts_only_allowed_paths(self):
        path = self.repo / "reports/ritual/new.json"
        path.parent.mkdir(parents=True)
        path.write_text("{}")
        self.assert_success(self.run_script("--stage-routine-evidence"), commits="2")

    def test_routine_refuses_closes_receipts_and_staged_code(self):
        for relative in ("reports/closes_receipts/new.json", "code.py"):
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("dirty")
            self.git("add", relative)
        result = self.run_script("--stage-routine-evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_producers()

    def test_data_gate_one_stops_before_backup(self):
        result = self.run_script(TEST_GATE_RC="1")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("backup", [c[0] for c in self.calls()])

    def test_data_gate_two_stops_before_backup(self):
        result = self.run_script(TEST_GATE_RC="2")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("backup", [c[0] for c in self.calls()])

    def test_partial_commit_requires_explicit_flag(self):
        result = self.run_script("--commit-partial", TEST_UNHEALTHY="1")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("partial activation-day", self.git("log", "-1", "--format=%s"))
        self.assertNotIn("gate", [c[0] for c in self.calls()])

    def test_restore_false_refuses_before_commit(self):
        result = self.run_script(TEST_RESTORE_BAD="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.initial)
        self.assertNotIn("EVIDENCE TEMPLATE IS INCOMPLETE", result.stdout)

    def test_feasibility_reuse_checks_both_hashes_not_code_sha(self):
        p = self.repo / "reports/h7_forward_schwab/2026-09-07-feasibility-cohort9.json"
        p.parent.mkdir(parents=True)
        p.write_text(
            json.dumps(
                {
                    "source_hash": "source",
                    "config_hash": "config",
                    "receipt_hash": "reuse",
                    "code_sha": "old-head",
                }
            )
        )
        self.git("add", str(p))
        self.git("commit", "-qm", "old evidence")
        self.initial = self.git("rev-parse", "HEAD")
        self.git("push", "-q", "origin", "main")
        self.assert_success(self.run_script())
        self.assertNotIn("feasibility", [c[0] for c in self.calls()])
        template = json.loads(
            (self.repo / ".tmp/h7_activation_day/2026-09-08-evidence.template.json").read_text()
        )
        self.assertEqual(template["feasibility_receipt_hash"], "reuse")

    def test_feasibility_config_mismatch_regenerates(self):
        p = self.repo / "reports/h7_forward_schwab/2026-09-07-feasibility-cohort9.json"
        p.parent.mkdir(parents=True)
        p.write_text(
            json.dumps({"source_hash": "source", "config_hash": "stale", "receipt_hash": "old"})
        )
        self.git("add", str(p))
        self.git("commit", "-qm", "old evidence")
        self.initial = self.git("rev-parse", "HEAD")
        self.git("push", "-q", "origin", "main")
        self.assert_success(self.run_script())
        self.assertIn("feasibility", [c[0] for c in self.calls()])

    def test_dotenv_unrelated_lines_never_execute_or_leak(self):
        marker = self.base / "must-not-exist"
        (self.repo / ".env").write_text(
            f"UNRELATED=$(touch {marker})\nSECRET=NEVER-PRINT-ME\nRESTIC_REPOSITORY=fixture\nRESTIC_PASSWORD_FILE=fixture\n"
        )
        result = self.run_script()
        self.assert_success(result)
        self.assertFalse(marker.exists())
        self.assertNotIn("NEVER-PRINT-ME", result.stdout + result.stderr)

    def test_alignment_function_and_routine_intersection_are_exact(self):
        source = SCRIPT.read_text()
        capture = (ROOT / "tools/schwab_chain_capture.sh").read_text()
        pattern = r"alignment_divergence_is_evidence_only\(\) \{.*?^\}"
        self.assertEqual(
            re.search(pattern, source, re.S | re.M).group(),
            re.search(pattern, capture, re.S | re.M).group(),
        )
        routine = set(re.search(r"ROUTINE_ALLOW=\((.*?)\)", source, re.S).group(1).split())
        daily = set(
            re.search(
                r"DATA_TIER_PATHS=\((.*?)\)", (ROOT / "tools/daily_ritual.sh").read_text(), re.S
            )
            .group(1)
            .split()
        )
        allowed = set(re.search(r"EVIDENCE_ALLOW=\((.*?)\)", capture, re.S).group(1).split())
        self.assertEqual(routine, daily & allowed)

    def test_printed_manual_command_supplies_import_environment(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        command = next(
            line
            for line in result.stdout.splitlines()
            if "uv run python tools/h7_schwab_manual_activate.py" in line
        )
        self.assertTrue(command.startswith("PYTHONPATH="), command)
        self.assertIn(str(self.repo), command)
        self.assertIn("cd " + str(self.repo), result.stdout)

    def test_one_staging_loop_commit_site_and_no_push_or_activation(self):
        self.assertTrue(SCRIPT.exists(), "activation-day entry point is missing")
        source = SCRIPT.read_text()
        code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
        self.assertEqual(len(re.findall(r"\bgit add\b", code)), 1)
        self.assertEqual(len(re.findall(r"\bgit commit\b", code)), 1)
        self.assertNotRegex(code, r"(?m)^\s*(?:git|\"\$UV\").*\bpush\b")
        self.assertNotRegex(code, r"(?m)^\s*\"\$UV\".*h7_schwab_manual_activate")


FAKE_UV = r"""import sys, os, json
from pathlib import Path
args=sys.argv[1:]
root=Path(os.environ["TEST_ROOT"])
def record(kind):
    p=root/".tmp/calls.jsonl";p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a") as out: out.write(json.dumps([kind,args])+"\n")
def write(path,value):
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value));return path
# Inline orchestration helpers are real Python with fixture imports supplied below.
if "-" in args:
    code=sys.stdin.read()
    import types
    def module(name):
        value=types.ModuleType(name);sys.modules[name]=value;return value
    cohort=module("options_researcher.h7_cohort")
    cohort.load_registered_cohort=lambda: types.SimpleNamespace(included=("AMD","AMZN"), excluded={"NVDA":"fixture"})
    watch=module("options_researcher.h7_watch")
    from datetime import date
    watch.evaluation_session=lambda value: date(2026,9,4)
    scope=module("options_researcher.h7_scope");scope.scope_identity=lambda: {"scope_id":"h7-forward-15-v1","symbols":["AMD","AMZN","NVDA"]}
    hashing=module("research.hashing");hashing.source_hash=lambda **kw: "source";hashing.config_hash=lambda: "config"
    reg=module("options_researcher.h7_schwab_window_registration")
    reg.FEASIBILITY_SOURCE_PATHS=("code.py",)
    reg.EVIDENCE_FIELDS=("review_evidence","activation_spec_sha256","code_commit","source_health_evidence_id","data_gate_evidence_id","data_gate_evidence_mode","source_health_receipt_hash","data_gate_receipt","data_gate_receipt_hash","last_historical_session","last_historical_manifest_receipt_hash","provider_identity","cache_namespace","feasibility_receipt","feasibility_receipt_hash","darwin_durability_verified","pre_append_state")
    receipts=module("research.receipts")
    def load(path,expected_type=None):
        value=json.loads(Path(path).read_text())
        if expected_type: assert value["receipt_type"]==expected_type
        return value
    receipts.load_receipt=load
    sys.argv=["-"]+args[args.index("-")+1:]
    code=code.replace('datetime.now(ZoneInfo("America/New_York")).date()', 'date(2026, 9, 8)')
    exec(compile(code,"<activation-helper>","exec"))
elif "options_researcher.schwab_token_age" in args:
    print("SCHWAB TOKEN " + os.environ.get("TEST_TOKEN","OK"))
elif "options_researcher.h7_source_health" in args:
    record("source");assert args[args.index("--as-of")+1]=="2026-09-08"
    p=write("reports/h7_receipts/h7-forward-15-v1/source_health/2026-09-04.json",{"receipt_type":"source_health","receipt_hash":"source-receipt","evaluation_session":"2026-09-04","scope":{"scope_id":"h7-forward-15-v1","symbols":["AMD","AMZN","NVDA"]},"symbols":{"AMD":{"healthy":os.environ.get("TEST_UNHEALTHY")!="1"},"AMZN":{"healthy":True},"NVDA":{"healthy":False}}})
    print("summary: 2/3 healthy; receipt="+p+"; exit 1 (unhealthy names above)");sys.exit(int(os.environ.get("TEST_SOURCE_RC","1")))
elif "tools/h7_schwab_data_gate_receipt.py" in args:
    record("gate");rc=int(os.environ.get("TEST_GATE_RC","0"))
    if rc==2: sys.exit(rc)
    p=write("reports/h7_data_gate_schwab/h7-forward-15-v1/receipts/2026-09-04.json",{"receipt_type":"data_gate","receipt_hash":"data-receipt"})
    write("reports/h7_data_gate_schwab/h7-forward-15-v1/2026-09-04.json",{})
    print("immutable receipt "+p);sys.exit(rc)
elif "tools/h7_forward_backup.py" in args:
    kind="backup" if "backup" in args else "restore";record(kind)
    assert (root/"reports/h7_data_gate_schwab/h7-forward-15-v1/receipts/2026-09-04.json").exists()
    p=args[args.index("--receipt")+1]
    write(p,{"receipt_type":"backup" if kind=="backup" else "backup_restore","receipt_hash":kind,"completed_session":"2026-09-04","scope":{"scope_id":"h7-forward-15-v1","symbols":["AMD","AMZN","NVDA"]},"verification":{"ok":os.environ.get("TEST_RESTORE_BAD")!="1"}})
    print(p)
elif "tools/h7_schwab_feasibility.py" in args:
    record("feasibility");write(args[args.index("--output")+1],{"source_hash":"source","config_hash":"config","receipt_hash":"feasibility"})
else:
    raise SystemExit("unexpected uv invocation: "+repr(args))
"""
