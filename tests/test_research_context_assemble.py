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
from decimal import Decimal
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import tools.research_context_assemble as research_context_assemble
from options_researcher.attractiveness_research_v2 import (
    PJM_CATALYST_ID,
    ResearchArtifactError,
    UpstreamBlocked,
    finalize_bundle,
    load_successful_ritual,
    publish_bundle,
    render_markdown,
    validate_context,
    verify_bundle,
)
from tools.research_context_assemble import (
    check_dashboard_html,
    reconcile_final_attempt,
)
from tools.research_refresh_guard import reserve_attempt

AS_OF = "2026-07-24"
RUN_DATE = "2026-07-27"
CANDIDATE_ID = "NVDA:long_call:2026-08-07:212.50"
STARTED_AT = datetime(2026, 7, 27, 15, 0, tzinfo=ZoneInfo("America/New_York"))
FINISHED_AT = datetime(2026, 7, 27, 15, 30, tzinfo=ZoneInfo("America/New_York"))
VERIFIED_AT = datetime(2026, 7, 27, 15, 31, tzinfo=ZoneInfo("America/New_York"))
CODE_SHA = "a" * 40
SOURCE_SHA = "b" * 64
RITUAL_CODE_SHA = "c" * 40
ATTEMPT_ID = "research-2026-07-27-074000"


def _source(
    url: str,
    source_tier: str,
    *,
    published_at: str | None = "2026-07-01T12:00:00-04:00",
    retrieved_at_utc: str = "2026-07-27T19:15:00Z",
    final_url: str | None = None,
    publisher: str | None = None,
    fetched_via: str | None = None,
    capture_sha256: str | None = None,
    independence_group: str | None = None,
) -> dict[str, object]:
    source: dict[str, object] = {
        "url": url,
        "source_tier": source_tier,
        "published_at": published_at,
        "publication_time_unknown_rationale": (
            "The canonical page does not expose a publication timestamp."
            if published_at is None
            else None
        ),
        "retrieved_at_utc": retrieved_at_utc,
    }
    # The cross-project research source standard's remaining receipt fields
    # (docs/evidence-upgrade/2026-08-03-cross-project-source-standard.md §2)
    # are OPTIONAL: only set them when a caller passes a value, so most
    # existing callers keep producing the legacy 5-field source shape.
    optional_fields = {
        "final_url": final_url,
        "publisher": publisher,
        "fetched_via": fetched_via,
        "capture_sha256": capture_sha256,
        "independence_group": independence_group,
    }
    for field, value in optional_fields.items():
        if value is not None:
            source[field] = value
    return source


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
    sources = [_source(str(claim["source_url"]), "issuer_ir")]
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
        sources.append(_source(pjm_source, "market_operator", published_at=None))
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
    fed_url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    _write_json(
        packet_dir / "market.json",
        {
            "market": {
                "summary": "Federal Reserve calendar context.",
                "regime": "mixed",
                "notes": ["Descriptive only."],
            },
            "symbols": {},
            "market_sources": [_source(fed_url, "regulator")],
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
        (self.root / "uv.lock").write_text("lock-v1\n", encoding="utf-8")
        self.ritual_root = self.root / "ritual-root"
        _write_successful_ritual(self.ritual_root)
        self.inputs = _write_packets(self.root)

    def tearDown(self):
        self.temp.cleanup()

    @property
    def final_manifest(self) -> Path:
        return self.root / "reports/attractiveness_research" / AS_OF / "manifest.json"

    @property
    def pending_manifest(self) -> Path:
        return self.root / "reports/attractiveness_research" / AS_OF / "manifest.pending.json"

    @property
    def previous_manifest(self) -> Path:
        return self.root / "reports/attractiveness_research" / AS_OF / "manifest.previous.json"

    def publish(self, **overrides):
        kwargs = {
            "root": self.root,
            "as_of": AS_OF,
            "candidate_ids": [CANDIDATE_ID],
            "pinned_symbols": ["AMZN"],
            "inputs_dir": self.inputs,
            "ritual_root": self.ritual_root,
            "run_date": RUN_DATE,
            "started_at": STARTED_AT,
            "producer_attempt_id": ATTEMPT_ID,
            "finished_at": FINISHED_AT,
            "producer_code_sha": CODE_SHA,
            "producer_source_sha": SOURCE_SHA,
        }
        kwargs.update(overrides)
        return publish_bundle(**kwargs)

    def verify(self, *, pending: bool = False):
        return verify_bundle(
            root=self.root,
            as_of=AS_OF,
            candidate_ids=[CANDIDATE_ID],
            pinned_symbols=["AMZN"],
            ritual_root=self.ritual_root,
            pending=pending,
        )

    def write_clean_dashboard(self) -> Path:
        path = self.root / ".tmp/dashboard/attractiveness.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Research evidence complete", encoding="utf-8")
        return path

    def finalize(self):
        self.write_clean_dashboard()
        return finalize_bundle(
            root=self.root,
            as_of=AS_OF,
            candidate_ids=[CANDIDATE_ID],
            pinned_symbols=["AMZN"],
            ritual_root=self.ritual_root,
            verified_at=VERIFIED_AT,
        )

    def test_pending_then_final_manifest_lineage(self):
        result = self.publish()
        self.assertEqual(result.status, "PENDING_DASHBOARD")
        self.assertTrue(self.pending_manifest.is_file())
        self.assertFalse(self.final_manifest.exists())
        pending = self.verify(pending=True)
        self.assertEqual(pending["publication_status"], "PENDING_DASHBOARD")

        manifest = self.finalize()
        self.assertEqual(manifest["publication_status"], "FINAL")
        self.assertFalse(self.pending_manifest.exists())
        verified = self.verify()
        self.assertEqual(verified["run_id"], result.run_id)
        self.assertEqual(verified["producer_attempt_id"], ATTEMPT_ID)
        self.assertEqual(
            json.loads(result.context_path.read_text(encoding="utf-8"))["lineage"][
                "producer_attempt_id"
            ],
            ATTEMPT_ID,
        )
        self.assertEqual(verified["candidate_ids"], [CANDIDATE_ID])
        self.assertEqual(verified["market_as_of_date"], AS_OF)

    def test_duplicate_input_returns_no_new_input_without_rewrite(self):
        first = self.publish()
        self.finalize()
        report_before = first.report_path.read_bytes()
        manifest_before = self.final_manifest.read_bytes()
        second = self.publish(
            started_at=datetime(2026, 7, 28, 7, 40, tzinfo=ZoneInfo("America/New_York")),
            producer_attempt_id="research-2026-07-28-074000",
            finished_at=datetime(2026, 7, 28, 8, 10, tzinfo=ZoneInfo("America/New_York")),
        )
        self.assertEqual(second.status, "NO_NEW_INPUT")
        self.assertEqual(second.run_id, first.run_id)
        self.assertEqual(first.report_path.read_bytes(), report_before)
        self.assertEqual(self.final_manifest.read_bytes(), manifest_before)
        self.assertEqual(
            json.loads(self.final_manifest.read_text(encoding="utf-8"))[
                "producer_attempt_id"
            ],
            ATTEMPT_ID,
        )
        self.assertFalse(self.pending_manifest.exists())

    def test_crash_after_final_is_reconciled_before_next_reservation(self):
        state_dir = self.root / "guard-state"
        reserve_attempt(
            state_dir,
            attempt_id=ATTEMPT_ID,
            now_et=STARTED_AT,
        )
        self.publish()
        self.finalize()

        manifest = self.verify()
        reconcile_final_attempt(
            manifest,
            guard_state_dir=state_dir,
            now_et=datetime(2026, 7, 28, 7, 39, tzinfo=ZoneInfo("America/New_York")),
        )
        self.assertEqual(
            reserve_attempt(
                state_dir,
                attempt_id="research-2026-07-28-074000",
                now_et=datetime(
                    2026,
                    7,
                    28,
                    7,
                    40,
                    tzinfo=ZoneInfo("America/New_York"),
                ),
                attempt_budget_usd=Decimal("8.00"),
                monthly_budget_usd=Decimal("200.00"),
                max_failures=2,
                stale_minutes=120,
            ),
            "RESERVED",
        )
        state = json.loads((state_dir / "guard_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["attempts"][0]["status"], "SUCCEEDED")
        self.assertIn("published_success_at_utc", state["attempts"][0])
        self.assertNotEqual(state["attempts"][0]["status"], "STALE_FAILED")

    def test_duplicate_gate_does_not_hide_corrupted_outputs(self):
        first = self.publish()
        self.finalize()
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
            self.verify(pending=True)

    def test_candidate_packet_coverage_is_exact(self):
        (self.inputs / "nvda.json").unlink()
        with self.assertRaisesRegex(ResearchArtifactError, "candidate coverage"):
            self.publish()

    def test_claim_source_must_be_in_symbol_sources(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"] = [_source("https://investor.nvda.example/different", "issuer_ir")]
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "absent from symbol sources"):
            self.publish()

    def test_claim_source_tier_must_match_source_metadata(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["claims"][0]["source_tier"] = "sec_filing"
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "source_tier differs"):
            self.publish()

    def test_source_retrieval_must_be_inside_run_window(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["retrieved_at_utc"] = "2026-07-27T18:59:59Z"
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "outside research start/finish"):
            self.publish()

    def test_unknown_publication_time_requires_rationale(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["published_at"] = None
        packet["sources"][0]["publication_time_unknown_rationale"] = None
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "requires a rationale"):
            self.publish()

    def test_manifest_has_explicit_source_metadata_and_usage(self):
        self.publish()
        manifest = self.verify(pending=True)
        self.assertGreater(len(manifest["sources"]), 1)
        for source in manifest["sources"]:
            self.assertEqual(
                set(source),
                {
                    "url",
                    "source_tier",
                    "published_at",
                    "publication_time_unknown_rationale",
                    "retrieved_at_utc",
                    "final_url",
                    "publisher",
                    "fetched_via",
                    "capture_sha256",
                    "independence_group",
                    "used_by",
                },
            )
            self.assertTrue(source["used_by"])

    def test_legacy_source_without_standard_fields_still_validates(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        legacy_source = packet["sources"][0]
        self.assertEqual(
            set(legacy_source),
            {
                "url",
                "source_tier",
                "published_at",
                "publication_time_unknown_rationale",
                "retrieved_at_utc",
            },
        )
        result = self.publish()
        self.assertEqual(result.status, "PENDING_DASHBOARD")
        manifest = self.verify(pending=True)
        nvda_source = next(
            source for source in manifest["sources"] if source["url"] == legacy_source["url"]
        )
        for field in ("final_url", "publisher", "fetched_via", "capture_sha256", "independence_group"):
            self.assertIsNone(nvda_source[field])

    def test_source_standard_receipt_fields_validate_when_present(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        url = str(packet["sources"][0]["url"])
        packet["sources"][0] = _source(
            url,
            "issuer_ir",
            final_url=url + "?utm_source=test",
            publisher="NVIDIA Investor Relations",
            fetched_via="WebFetch",
            capture_sha256="a" * 64,
            independence_group="nvidia-ir",
        )
        _write_json(path, packet)
        self.publish()
        manifest = self.verify(pending=True)
        nvda_source = next(source for source in manifest["sources"] if source["url"] == url)
        self.assertEqual(nvda_source["final_url"], url + "?utm_source=test")
        self.assertEqual(nvda_source["publisher"], "NVIDIA Investor Relations")
        self.assertEqual(nvda_source["fetched_via"], "WebFetch")
        self.assertEqual(nvda_source["capture_sha256"], "a" * 64)
        self.assertEqual(nvda_source["independence_group"], "nvidia-ir")

    def test_bad_final_url_is_rejected(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["final_url"] = "not-a-url"
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, r"final_url: invalid source URL"):
            self.publish()

    def test_empty_publisher_is_rejected(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["publisher"] = "  "
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, r"publisher: non-empty string"):
            self.publish()

    def test_empty_fetched_via_is_rejected(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["fetched_via"] = ""
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, r"fetched_via: non-empty string"):
            self.publish()

    def test_capture_sha256_wrong_length_is_rejected(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["capture_sha256"] = "a" * 63
        _write_json(path, packet)
        with self.assertRaisesRegex(
            ResearchArtifactError, r"capture_sha256: expected 64 lowercase hex characters"
        ):
            self.publish()

    def test_capture_sha256_uppercase_is_rejected(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["capture_sha256"] = "A" * 64
        _write_json(path, packet)
        with self.assertRaisesRegex(
            ResearchArtifactError, r"capture_sha256: expected 64 lowercase hex characters"
        ):
            self.publish()

    def test_empty_independence_group_is_rejected(self):
        path = self.inputs / "nvda.json"
        packet = json.loads(path.read_text(encoding="utf-8"))
        packet["sources"][0]["independence_group"] = ""
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, r"independence_group: non-empty string"):
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
        for source in packet["sources"]:
            if source["url"] == old_source:
                source["url"] = new_source
        for catalyst in packet["catalysts"]:
            if catalyst.get("id") == PJM_CATALYST_ID:
                catalyst["source"] = new_source
        _write_json(path, packet)
        with self.assertRaisesRegex(ResearchArtifactError, "official PJM URL"):
            self.publish()

    def test_temporal_parity_is_enforced(self):
        result = self.publish()
        context = json.loads(result.context_path.read_text(encoding="utf-8"))
        context["research_finished_at_et"] = "2026-07-27T16:30:00-04:00"
        with self.assertRaisesRegex(ResearchArtifactError, "different instants"):
            validate_context(
                context,
                candidate_ids=[CANDIDATE_ID],
                pinned_symbols=["AMZN"],
            )

    def test_uv_lock_is_bound_and_tamper_is_rejected(self):
        self.publish()
        manifest = self.verify(pending=True)
        self.assertEqual(
            manifest["uv_lock_sha256"],
            hashlib.sha256((self.root / "uv.lock").read_bytes()).hexdigest(),
        )
        (self.root / "uv.lock").write_text("lock-v2\n", encoding="utf-8")
        with self.assertRaisesRegex(ResearchArtifactError, "uv_lock_sha256 mismatch"):
            self.verify(pending=True)

    def test_packet_hash_tamper_is_rejected(self):
        self.publish()
        manifest = self.verify(pending=True)
        packet_path = self.root / manifest["input_packets"]["nvda.json"]["path"]
        packet_path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ResearchArtifactError, "input packet nvda.json sha256"):
            self.verify(pending=True)

    def test_stale_dashboard_refuses_final_manifest(self):
        self.publish()
        path = self.root / ".tmp/dashboard/attractiveness.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Research evidence stale", encoding="utf-8")
        with self.assertRaisesRegex(ResearchArtifactError, "stale markers"):
            finalize_bundle(
                root=self.root,
                as_of=AS_OF,
                candidate_ids=[CANDIDATE_ID],
                pinned_symbols=["AMZN"],
                ritual_root=self.ritual_root,
                verified_at=VERIFIED_AT,
            )
        self.assertFalse(self.final_manifest.exists())
        self.assertTrue(self.pending_manifest.exists())

    def test_manifest_is_commit_marker_for_partial_publication(self):
        self.publish()
        self.finalize()
        prior_manifest = self.final_manifest.read_bytes()
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
        self.assertFalse(self.final_manifest.exists())
        self.assertEqual(self.previous_manifest.read_bytes(), prior_manifest)
        with self.assertRaises(ResearchArtifactError):
            self.verify()


class ShellPreflightTest(unittest.TestCase):
    def run_script(
        self,
        temp: Path,
        *,
        ritual_status: str,
        now_et: str,
        manual_override: bool = False,
        uv_override: str | None = None,
        extra_env: dict[str, str] | None = None,
        script_override: Path | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        uv = uv_override or shutil.which("uv")
        zsh = shutil.which("zsh")
        if uv is None or zsh is None:
            self.skipTest("uv and zsh are required")
        ritual_root = temp / "ritual"
        _write_successful_ritual(ritual_root)
        _write_run_status(ritual_root, status=ritual_status)
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
                "RESEARCH_REFRESH_STATE_DIR": str(temp / "state"),
                "RESEARCH_REFRESH_TEST_OVERRIDE": "1",
                "RESEARCH_REFRESH_NOW_ET": now_et,
                "RESEARCH_RITUAL_ROOT": str(ritual_root),
                "RESEARCH_MARKET_AS_OF": AS_OF,
                "RESEARCH_RUN_DATE": RUN_DATE,
            }
        )
        if manual_override:
            env["RESEARCH_REFRESH_MANUAL_OVERRIDE"] = "1"
        if extra_env:
            env.update(extra_env)
        script = (
            script_override
            or Path(__file__).resolve().parents[1] / "tools/research_refresh.sh"
        )
        result = subprocess.run(
            [zsh, str(script)],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return result, invoked, log_dir

    def test_blocked_preflight_never_invokes_llm(self):
        with tempfile.TemporaryDirectory() as directory:
            result, invoked, log_dir = self.run_script(
                Path(directory),
                ritual_status="BROKEN",
                now_et="2026-07-27T07:40:00-04:00",
            )
            self.assertEqual(result.returncode, 3)
            self.assertFalse(invoked.exists())
            logs = list(log_dir.glob("*.log"))
            self.assertEqual(len(logs), 1)
            self.assertIn("UPSTREAM_BLOCKED", logs[0].read_text(encoding="utf-8"))

    def test_schedule_blocked_never_invokes_llm(self):
        with tempfile.TemporaryDirectory() as directory:
            result, invoked, log_dir = self.run_script(
                Path(directory),
                ritual_status="OK",
                now_et="2026-07-25T07:40:00-04:00",
            )
            self.assertEqual(result.returncode, 4)
            self.assertFalse(invoked.exists())
            logs = list(log_dir.glob("*.log"))
            self.assertEqual(len(logs), 1)
            self.assertIn("SCHEDULE_BLOCKED", logs[0].read_text(encoding="utf-8"))

    def test_active_attempt_blocks_concurrent_shell_before_llm(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            reserve_attempt(
                temp / "state",
                attempt_id="already-running",
                now_et=datetime(
                    2026,
                    7,
                    27,
                    7,
                    39,
                    tzinfo=ZoneInfo("America/New_York"),
                ),
            )
            result, invoked, log_dir = self.run_script(
                temp,
                ritual_status="OK",
                now_et="2026-07-27T07:40:00-04:00",
            )
            self.assertEqual(result.returncode, 8)
            self.assertFalse(invoked.exists())
            logs = list(log_dir.glob("*.log"))
            self.assertEqual(len(logs), 1)
            log = logs[0].read_text(encoding="utf-8")
            self.assertIn("SINGLE_FLIGHT_ACTIVE", log)
            self.assertIn("LLM invocation was not attempted", log)

    def test_valid_final_reconciles_reserved_attempt_and_recreates_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            canonical_repo = temp / "canonical-repo"
            canonical_script = canonical_repo / "tools/research_refresh.sh"
            canonical_script.parent.mkdir(parents=True)
            source_script = (
                Path(__file__).resolve().parents[1] / "tools/research_refresh.sh"
            )
            shutil.copy2(source_script, canonical_script)
            state_dir = temp / "state"
            producer_attempt_id = "published-before-receipt"
            reserve_attempt(
                state_dir,
                attempt_id=producer_attempt_id,
                now_et=datetime(
                    2026,
                    7,
                    27,
                    7,
                    39,
                    tzinfo=ZoneInfo("America/New_York"),
                ),
            )
            final_manifest = (
                canonical_repo
                / "reports/attractiveness_research"
                / AS_OF
                / "manifest.json"
            )
            _write_json(
                final_manifest,
                {
                    "schema_version": "attractiveness_research/v2",
                    "publication_status": "FINAL",
                    "producer_attempt_id": producer_attempt_id,
                },
            )
            log_dir = temp / "logs"
            log_dir.mkdir()
            receipt = log_dir / f"receipt_v2_{AS_OF}_premarket.json"
            receipt.write_text('{"status":"ok","corrupted":true}\n', encoding="utf-8")

            fake_uv = temp / "fake-uv"
            fake_uv.write_text(
                """#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

args = sys.argv[1:]
module_index = args.index("-m")
module = args[module_index + 1]
module_args = args[module_index + 2:]
source_root = os.environ["FAKE_SOURCE_ROOT"]
if module == "tools.research_refresh_guard":
    env = os.environ.copy()
    env["PYTHONPATH"] = source_root
    raise SystemExit(
        subprocess.run(
            [sys.executable, "-m", module, *module_args],
            env=env,
            check=False,
        ).returncode
    )
if module != "tools.research_context_assemble":
    raise SystemExit(99)
if "--preflight" in module_args:
    receipt_out = Path(module_args[module_args.index("--receipt-out") + 1])
    receipt_out.write_text(
        json.dumps(
            {
                "ritual_run_status_sha256": "status-sha",
                "ritual_receipt_sha256": "receipt-sha",
                "status": "OK",
            },
            separators=(",", ":"),
        )
        + "\\n",
        encoding="utf-8",
    )
    raise SystemExit(0)
if "--verify" not in module_args:
    raise SystemExit(98)
if "--reconcile-published-attempt" in module_args:
    sys.path.insert(0, source_root)
    from tools.research_refresh_guard import record_outcome

    state_dir = Path(module_args[module_args.index("--guard-state-dir") + 1])
    attempt_id = os.environ["FAKE_PRODUCER_ATTEMPT_ID"]
    record_outcome(
        state_dir,
        attempt_id=attempt_id,
        succeeded=True,
        published_success=True,
        now_et=datetime.fromisoformat("2026-07-27T07:40:00-04:00"),
    )
    receipt_out = Path(module_args[module_args.index("--receipt-out") + 1])
    receipt_out.write_text(
        json.dumps(
            {
                "schema_version": "attractiveness_research/v2",
                "run_id": "research-2026-07-24-test",
                "producer_attempt_id": attempt_id,
                "context_sha256": "context-sha",
                "ritual_run_status_sha256": "status-sha",
                "ritual_receipt_sha256": "receipt-sha",
                "status": "verified",
            },
            separators=(",", ":"),
        )
        + "\\n",
        encoding="utf-8",
    )
raise SystemExit(0)
""",
                encoding="utf-8",
            )
            fake_uv.chmod(0o755)

            result, invoked, _returned_log_dir = self.run_script(
                temp,
                ritual_status="OK",
                now_et="2026-07-27T07:40:00-04:00",
                uv_override=str(fake_uv),
                extra_env={
                    "FAKE_SOURCE_ROOT": str(Path(__file__).resolve().parents[1]),
                    "FAKE_PRODUCER_ATTEMPT_ID": producer_attempt_id,
                },
                script_override=canonical_script,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(invoked.exists())
            state = json.loads(
                (state_dir / "guard_state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["attempts"][0]["attempt_id"], producer_attempt_id)
            self.assertEqual(state["attempts"][0]["status"], "SUCCEEDED")
            self.assertIn("published_success_at_utc", state["attempts"][0])
            recreated = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(recreated["producer_attempt_id"], producer_attempt_id)
            self.assertEqual(recreated["status"], "ok")
            self.assertNotIn("corrupted", recreated)
            self.assertEqual(list(log_dir.glob("receipt_v2_*.tmp")), [])
            logs = list(log_dir.glob("*.log"))
            self.assertEqual(len(logs), 1)
            self.assertIn(
                "RECOVERED: valid final manifest reconciled before LLM invocation",
                logs[0].read_text(encoding="utf-8"),
            )

    def test_receipt_section_has_no_pre_reconciliation_success_exit(self):
        script = (
            Path(__file__).resolve().parents[1] / "tools/research_refresh.sh"
        ).read_text(encoding="utf-8")
        receipt_section = script[
            script.index('RECEIPT="$LOGDIR/receipt_v2_') :
            script.index("verify_reconcile_final()")
        ]
        self.assertNotIn("exit 0", receipt_section)
        self.assertNotIn("PRIOR_STATUS", receipt_section)
        self.assertNotIn("CURRENT_RITUAL_SHA", receipt_section)


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


class BoardRootTest(unittest.TestCase):
    def test_live_board_reads_ops_root_and_restores_deployment_cwd(self):
        original_cwd = Path.cwd()
        observed: list[Path] = []

        def assemble():
            observed.append(Path.cwd())
            return {"data_as_of": AS_OF}

        def load_qm_context(_as_of):
            observed.append(Path.cwd())
            return {}

        with tempfile.TemporaryDirectory() as temp:
            board_root = Path(temp).resolve()
            with (
                mock.patch.dict(
                    os.environ,
                    {"RESEARCH_BOARD_ROOT": str(board_root)},
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.assemble",
                    side_effect=assemble,
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.select_top_picks",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.select_qm_top_picks",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.pinned_picks",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.qm_dashboard.load_qm_context",
                    side_effect=load_qm_context,
                ),
            ):
                result = research_context_assemble._live_board()

        self.assertEqual(observed, [board_root, board_root])
        self.assertEqual(Path.cwd(), original_cwd)
        self.assertEqual(result, ({"data_as_of": AS_OF}, AS_OF, [], []))

    def test_a_pre_close_board_date_stays_coherent_downstream(self):
        """brief 12 D3: data_as_of may now be a 15:45 pre-close session.

        The artifact consumer must carry that exact date through (no
        re-derivation, no silent substitution) and QM must be asked for the
        board session, not for its own daily-bar session.
        """
        preclose_session = "2026-08-14"
        asked: list[str] = []

        def assemble():
            return {"data_as_of": preclose_session,
                    "as_of_kind": "schwab_preclose",
                    "fresh_symbols": ["NVDA"],
                    "symbols": []}

        def load_qm_context(board_session):
            asked.append(board_session)
            return {"status": "CURRENT", "as_of": "2026-08-13",
                    "board_session": board_session, "symbols": {}}

        with tempfile.TemporaryDirectory() as temp:
            board_root = Path(temp).resolve()
            with (
                mock.patch.dict(
                    os.environ, {"RESEARCH_BOARD_ROOT": str(board_root)}
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.assemble",
                    side_effect=assemble,
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.select_top_picks",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.select_qm_top_picks",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.attractiveness_dashboard.pinned_picks",
                    return_value=[],
                ),
                mock.patch(
                    "options_researcher.qm_dashboard.load_qm_context",
                    side_effect=load_qm_context,
                ),
            ):
                data, as_of, candidate_ids, pinned = (
                    research_context_assemble._live_board())

        self.assertEqual(as_of, preclose_session)
        self.assertEqual(data["data_as_of"], preclose_session)
        self.assertEqual(asked, [preclose_session])
        self.assertEqual((candidate_ids, pinned), ([], []))


if __name__ == "__main__":
    unittest.main()
