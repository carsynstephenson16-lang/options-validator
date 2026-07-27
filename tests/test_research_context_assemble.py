"""Offline tests for attractiveness_research/v2 production and verification."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from options_researcher.attractiveness_research_v2 import (
    PJM_CATALYST_ID,
    ResearchArtifactError,
    UpstreamBlocked,
    load_successful_ritual,
    publish_bundle,
    render_markdown,
    validate_context,
    verify_bundle,
)
from tools.research_context_assemble import check_dashboard_html

AS_OF = "2026-07-24"
RUN_DATE = "2026-07-27"
CANDIDATE_ID = "NVDA:long_call:2026-08-07:212.50"
GENERATED_AT = datetime(2026, 7, 27, 15, 30, tzinfo=ZoneInfo("America/New_York"))
CODE_SHA = "a" * 40
SOURCE_SHA = "b" * 64
RITUAL_CODE_SHA = "c" * 40


def _claim(symbol: str) -> dict[str, object]:
    source = f"https://investor.{symbol.lower()}.example/events"
    return {
        "id": f"{symbol.lower()}-event",
        "text": f"{symbol} has an issuer-listed event.",
        "classification": "fact",
        "source_url": source,
        "unknown_rationale": None,
        "source_tier": "issuer_ir",
        "fact_date": "2026-08-01",
        "date_certainty": "confirmed",
        "countercase": "The event timing does not establish a price response.",
    }


def _packet(symbol: str, *, pjm: bool = False) -> dict[str, object]:
    claim = _claim(symbol)
    catalysts: list[dict[str, object]] = [
        {
            "id": f"{symbol}_EARNINGS",
            "date": "2026-08-01",
            "what": f"{symbol} issuer event",
            "source": claim["source_url"],
            "confirmed": True,
        }
    ]
    sources = [claim["source_url"]]
    if pjm:
        pjm_source = "https://www.pjm.com/markets-and-operations/rpm"
        catalysts.append(
            {
                "id": PJM_CATALYST_ID,
                "date": None,
                "what": "Next PJM Base Residual Auction; exact date not published.",
                "source": pjm_source,
                "confirmed": False,
            }
        )
        sources.append(pjm_source)
    return {
        "symbol": symbol,
        "news_summary": f"{symbol} dated context.",
        "sentiment": "neutral",
        "catalysts": catalysts,
        "move_thesis": "Calendar context only.",
        "sources": sources,
        "claims": [claim],
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_run_status(root: Path, *, status: str = "OK") -> None:
    receipt_relative = Path("reports/ritual") / f"capture_receipt_{AS_OF}.json"
    receipt_path = root / receipt_relative
    _write_json(
        root / "reports/ritual" / f"run_status_{AS_OF}.json",
        {
            "schema_version": "daily_ritual/run_status/v1",
            "as_of": AS_OF,
            "run_date": RUN_DATE,
            "status": status,
            "code_sha": RITUAL_CODE_SHA,
            "capture_receipt_path": receipt_relative.as_posix(),
            "capture_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        },
    )


def _write_successful_ritual(root: Path) -> None:
    hypotheses: dict[str, dict[str, object]] = {}
    for hypothesis in ("H5", "H6", "H7", "H8", "H10"):
        evidence = Path("evidence") / f"{hypothesis.lower()}-{AS_OF}.json"
        evidence_path = root / evidence
        _write_json(evidence_path, {"hypothesis": hypothesis, "as_of": AS_OF})
        hypotheses[hypothesis] = {
            "status": "NO_SIGNAL",
            "evidence": evidence.as_posix(),
            "detail": "no signal",
        }
    receipt_path = root / "reports/ritual" / f"capture_receipt_{AS_OF}.json"
    _write_json(
        receipt_path,
        {"as_of": AS_OF, "run_date": RUN_DATE, "hypotheses": hypotheses},
    )
    _write_run_status(root)


def _write_packets(root: Path) -> Path:
    packet_dir = root / "inputs"
    _write_json(
        packet_dir / "market.json",
        {
            "market": {
                "summary": "Federal Reserve calendar context.",
                "regime": "mixed",
                "notes": ["Descriptive only."],
            },
            "symbols": {},
            "market_sources": ["https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"],
        },
    )
    for symbol in ("NVDA", "AMZN", "VST", "CEG"):
        _write_json(
            packet_dir / f"{symbol.lower()}.json",
            _packet(symbol, pjm=symbol in {"VST", "CEG"}),
        )
    return packet_dir


class RitualPreflightTest(unittest.TestCase):
    def test_exact_successful_session_is_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_successful_ritual(root)
            binding = load_successful_ritual(root, as_of=AS_OF, run_date=RUN_DATE)
            self.assertEqual(binding.as_of, AS_OF)
            self.assertEqual(binding.ritual_code_sha, RITUAL_CODE_SHA)
            self.assertEqual(set(binding.evidence_sha256), {"H5", "H6", "H7", "H8", "H10"})

    def test_global_broken_status_blocks_despite_successful_capture_statuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_successful_ritual(root)
            _write_run_status(root, status="BROKEN")
            with self.assertRaisesRegex(UpstreamBlocked, "not OK"):
                load_successful_ritual(root, as_of=AS_OF, run_date=RUN_DATE)

    def test_broken_hypothesis_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_successful_ritual(root)
            receipt_path = root / "reports/ritual" / f"capture_receipt_{AS_OF}.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["hypotheses"]["H6"]["status"] = "MISSING"
            _write_json(receipt_path, receipt)
            _write_run_status(root)
            with self.assertRaisesRegex(UpstreamBlocked, "H6 status"):
                load_successful_ritual(root, as_of=AS_OF, run_date=RUN_DATE)

    def test_capture_receipt_sha_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_successful_ritual(root)
            receipt_path = root / "reports/ritual" / f"capture_receipt_{AS_OF}.json"
            receipt_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(UpstreamBlocked, "capture_receipt_sha256"):
                load_successful_ritual(root, as_of=AS_OF, run_date=RUN_DATE)

    def test_wrong_run_date_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_successful_ritual(root)
            with self.assertRaisesRegex(UpstreamBlocked, "run_date mismatch"):
                load_successful_ritual(root, as_of=AS_OF, run_date="2026-07-28")


class BundleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ritual_root = self.root / "ritual-root"
        _write_successful_ritual(self.ritual_root)
        self.inputs = _write_packets(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def publish(self, **overrides):
        kwargs = {
            "root": self.root,
            "as_of": AS_OF,
            "candidate_ids": [CANDIDATE_ID],
            "pinned_symbols": ["AMZN"],
            "inputs_dir": self.inputs,
            "ritual_root": self.ritual_root,
            "run_date": RUN_DATE,
            "generated_at": GENERATED_AT,
            "producer_code_sha": CODE_SHA,
            "producer_source_sha": SOURCE_SHA,
        }
        kwargs.update(overrides)
        return publish_bundle(**kwargs)

    def verify(self):
        return verify_bundle(
            root=self.root,
            as_of=AS_OF,
            candidate_ids=[CANDIDATE_ID],
            pinned_symbols=["AMZN"],
            ritual_root=self.ritual_root,
        )

    def test_publish_and_verify_manifest_lineage(self):
        result = self.publish()
        self.assertEqual(result.status, "PUBLISHED")
        manifest = self.verify()
        self.assertEqual(manifest["schema_version"], "attractiveness_research/v2")
        self.assertEqual(manifest["run_id"], result.run_id)
        self.assertEqual(manifest["candidate_ids"], [CANDIDATE_ID])
        self.assertEqual(manifest["market_as_of_date"], AS_OF)

    def test_duplicate_input_returns_no_new_input_without_rewrite(self):
        first = self.publish()
        report_before = first.report_path.read_bytes()
        manifest_before = first.manifest_path.read_bytes()
        second = self.publish(
            generated_at=datetime(2026, 7, 27, 16, 45, tzinfo=ZoneInfo("America/New_York"))
        )
        self.assertEqual(second.status, "NO_NEW_INPUT")
        self.assertEqual(second.run_id, first.run_id)
        self.assertEqual(first.report_path.read_bytes(), report_before)
        self.assertEqual(first.manifest_path.read_bytes(), manifest_before)

    def test_duplicate_gate_does_not_hide_corrupted_outputs(self):
        first = self.publish()
        first.context_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ResearchArtifactError, "context sha256 mismatch"):
            self.publish()

    def test_markdown_is_deterministic_json_rendering(self):
        result = self.publish()
        context = json.loads(result.context_path.read_text(encoding="utf-8"))
        self.assertEqual(
            result.report_path.read_text(encoding="utf-8"),
            render_markdown(context),
        )
        result.report_path.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(ResearchArtifactError, "markdown sha256 mismatch"):
            self.verify()

    def test_candidate_packet_coverage_is_exact(self):
        (self.inputs / "nvda.json").unlink()
        with self.assertRaisesRegex(ResearchArtifactError, "candidate coverage"):
            self.publish()

    def test_claim_source_must_be_in_symbol_sources(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"] = ["https://investor.nvda.example/different"]
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "absent from symbol sources"):
            self.publish()

    def test_pjm_required_for_vst_and_ceg(self):
        path = self.inputs / "vst.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["catalysts"] = [
            item for item in packet["catalysts"] if item.get("id") != PJM_CATALYST_ID
        ]
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, PJM_CATALYST_ID):
            self.publish()

    def test_pjm_must_be_unconfirmed_and_official(self):
        path = self.inputs / "ceg.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        for catalyst in packet["catalysts"]:
            if catalyst.get("id") == PJM_CATALYST_ID:
                catalyst["confirmed"] = True
                catalyst["date"] = "2026-12-01"
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "confirmed must remain false"):
            self.publish()

    def test_pjm_must_use_official_pjm_source(self):
        path = self.inputs / "ceg.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        old_source = "https://www.pjm.com/markets-and-operations/rpm"
        new_source = "https://example.com/pjm-calendar"
        packet["sources"] = [
            new_source if source == old_source else source for source in packet["sources"]
        ]
        for catalyst in packet["catalysts"]:
            if catalyst.get("id") == PJM_CATALYST_ID:
                catalyst["source"] = new_source
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "official PJM URL"):
            self.publish()

    def test_temporal_parity_is_enforced(self):
        result = self.publish()
        context = json.loads(result.context_path.read_text(encoding="utf-8"))
        context["research_generated_at_et"] = "2026-07-27T16:30:00-04:00"
        with self.assertRaisesRegex(ResearchArtifactError, "different instants"):
            validate_context(
                context,
                candidate_ids=[CANDIDATE_ID],
                pinned_symbols=["AMZN"],
            )

    def test_packet_hash_tamper_is_rejected(self):
        result = self.publish()
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        packet_path = self.root / manifest["input_packets"]["nvda.json"]["path"]
        packet_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ResearchArtifactError, "input packet nvda.json sha256"):
            self.verify()

    def test_manifest_is_commit_marker_for_partial_publication(self):
        first = self.publish()
        prior_manifest = first.manifest_path.read_bytes()
        packet = json.loads((self.inputs / "nvda.json").read_text(encoding="utf-8"))
        packet["news_summary"] = "A changed, still sourced summary."
        _write_json(self.inputs / "nvda.json", packet)

        from options_researcher import attractiveness_research_v2 as module

        real_atomic_write = module.atomic_text_write

        def fail_on_report(text: str, path: Path) -> None:
            if path.name.endswith("-attractiveness-research-context.md"):
                raise OSError("simulated report publication failure")
            real_atomic_write(text, path)

        with mock.patch.object(module, "atomic_text_write", side_effect=fail_on_report):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.publish()
        self.assertEqual(first.manifest_path.read_bytes(), prior_manifest)
        with self.assertRaises(ResearchArtifactError):
            self.verify()


class ShellPreflightTest(unittest.TestCase):
    def test_blocked_preflight_never_invokes_llm(self):
        uv = shutil.which("uv")
        zsh = shutil.which("zsh")
        if uv is None or zsh is None:
            self.skipTest("uv and zsh are required")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            ritual_root = temp / "ritual"
            _write_successful_ritual(ritual_root)
            _write_run_status(ritual_root, status="BROKEN")
            log_dir = temp / "logs"
            invoked = temp / "llm-invoked"
            fake_claude = temp / "claude"
            fake_claude.write_text(
                f"#!/bin/zsh\n/usr/bin/touch '{invoked}'\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "RESEARCH_REFRESH_UV": uv,
                    "RESEARCH_REFRESH_CLAUDE": str(fake_claude),
                    "RESEARCH_REFRESH_LOG_DIR": str(log_dir),
                    "RESEARCH_RITUAL_ROOT": str(ritual_root),
                    "RESEARCH_MARKET_AS_OF": AS_OF,
                    "RESEARCH_RUN_DATE": RUN_DATE,
                }
            )
            script = Path(__file__).resolve().parents[1] / "tools/research_refresh.sh"
            result = subprocess.run(
                [zsh, str(script)],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 3)
            self.assertFalse(invoked.exists())
            logs = list(log_dir.glob("*.log"))
            self.assertEqual(len(logs), 1)
            self.assertIn("UPSTREAM_BLOCKED", logs[0].read_text(encoding="utf-8"))


class CheckHtmlTest(unittest.TestCase):
    def test_flags_every_stale_marker(self):
        html = (
            "annotations are from 2026-07-15 ... do not match any card "
            "... Research evidence incomplete ... Research evidence stale"
        )
        self.assertEqual(len(check_dashboard_html(html)), 4)

    def test_clean_html_passes(self):
        self.assertEqual(
            check_dashboard_html("all good Research evidence complete"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
