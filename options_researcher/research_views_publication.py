"""Fail-closed immutable publication for display-only research views."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENERATION_RE = re.compile(r"^[0-9]{8}T[0-9]{12}Z-[0-9a-f]{32}$")
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

ARTIFACTS = (
    "experiments.html",
    "wasserstein-regime.txt",
    "wasserstein-regime.json",
)
GENERATION_FILES = (*ARTIFACTS, "research-views-status.txt")


class PublicationError(RuntimeError):
    """A strict publication, validation, or compare-and-swap failure."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def mint_generation_id(value: datetime | None = None) -> str:
    now = (value or _utc_now()).astimezone(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S%fZ-") + uuid.uuid4().hex


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or TIMESTAMP_RE.fullmatch(value) is None:
        raise PublicationError("timestamp is not canonical UTC RFC 3339")
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    if canonical_timestamp(parsed) != value:
        raise PublicationError("timestamp is not canonical")
    return parsed


def _require_generation_id(value: object) -> str:
    if not isinstance(value, str) or GENERATION_RE.fullmatch(value) is None:
        raise PublicationError("invalid generation id")
    return value


def _require_commit(value: object) -> str:
    if not isinstance(value, str) or COMMIT_RE.fullmatch(value) is None:
        raise PublicationError("invalid producer commit")
    return value


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _read_canonical_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read canonical JSON {path.name}") from exc
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise PublicationError(f"noncanonical JSON {path.name}")
    return value


def _require_contained_entry(path: Path, parent: Path, *, directory: bool = False) -> Path:
    """Reject symlinks and require one direct regular child of ``parent``."""
    try:
        mode = path.lstat().st_mode
        resolved_parent = parent.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PublicationError(f"publication entry is absent: {path.name}") from exc
    expected_type = stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)
    if not expected_type or resolved.parent != resolved_parent:
        raise PublicationError(f"publication entry escapes or has invalid type: {path.name}")
    return resolved


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _metadata(raw: bytes) -> dict[str, object]:
    return {"sha256": _sha_bytes(raw), "bytes": len(raw)}


def _validate_metadata(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"sha256", "bytes"}:
        raise PublicationError("invalid file metadata keys")
    digest = value.get("sha256")
    size = value.get("bytes")
    if not isinstance(digest, str) or SHA_RE.fullmatch(digest) is None:
        raise PublicationError("invalid file digest")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise PublicationError("invalid file byte count")
    return value


def _write_fsynced(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _publication_lock(dashboard_dir: Path) -> Iterator[None]:
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    lock_path = dashboard_dir / ".research-views.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _validate_status(
    value: dict[str, Any], generation_id: str, published_at: str
) -> dict[str, Any]:
    required = {
        "schema",
        "generation_id",
        "published_at",
        "experiments_exit",
        "wasserstein_exit",
        "files",
    }
    if set(value) != required or value.get("schema") != "research_views_status/v1":
        raise PublicationError("invalid status schema")
    if value.get("generation_id") != generation_id or value.get("published_at") != published_at:
        raise PublicationError("status identity mismatch")
    _parse_timestamp(value.get("published_at"))
    if value.get("experiments_exit") != 0 or value.get("wasserstein_exit") != 0:
        raise PublicationError("status outcome mismatch")
    files = value.get("files")
    if not isinstance(files, dict) or set(files) != set(ARTIFACTS):
        raise PublicationError("invalid status file allow-list")
    for metadata in files.values():
        _validate_metadata(metadata)
    return value


def _validate_manifest(
    value: dict[str, Any], generation_id: str, published_at: str
) -> dict[str, Any]:
    if set(value) != {"schema", "generation_id", "published_at", "producer_commit", "files"}:
        raise PublicationError("invalid manifest keys")
    if value.get("schema") != "research_views_manifest/v1":
        raise PublicationError("invalid manifest schema")
    if value.get("generation_id") != generation_id or value.get("published_at") != published_at:
        raise PublicationError("manifest identity mismatch")
    _parse_timestamp(value.get("published_at"))
    _require_commit(value.get("producer_commit"))
    files = value.get("files")
    if not isinstance(files, dict) or set(files) != set(GENERATION_FILES):
        raise PublicationError("invalid manifest file allow-list")
    for metadata in files.values():
        _validate_metadata(metadata)
    return value


def _validate_pointer(value: dict[str, Any]) -> tuple[str, str]:
    allowed = {"schema", "generation_id", "published_at", "manifest"}
    if "copied_from_root" in value:
        allowed.add("copied_from_root")
    if set(value) != allowed or value.get("schema") != "research_views_current/v1":
        raise PublicationError("invalid current pointer schema")
    generation_id = _require_generation_id(value.get("generation_id"))
    published_at = value.get("published_at")
    _parse_timestamp(published_at)
    if "copied_from_root" in value:
        copied = value["copied_from_root"]
        if (
            not isinstance(copied, str)
            or not Path(copied).is_absolute()
            or str(Path(copied).resolve()) != copied
        ):
            raise PublicationError("invalid copied_from_root")
    manifest = value.get("manifest")
    if not isinstance(manifest, dict) or set(manifest) != {"path", "sha256", "bytes"}:
        raise PublicationError("invalid pointer manifest metadata")
    expected = f"research-views-generations/{generation_id}/research-views-manifest.json"
    if manifest.get("path") != expected:
        raise PublicationError("manifest path mismatch")
    _validate_metadata({"sha256": manifest.get("sha256"), "bytes": manifest.get("bytes")})
    return generation_id, str(published_at)


def load_current(dashboard_dir: str | Path) -> dict[str, Any]:
    """Snapshot one pointer and validate its exact immutable generation."""
    dashboard = Path(dashboard_dir).resolve()
    pointer_path = dashboard / "research-views-current.json"
    try:
        pointer_mode = pointer_path.lstat().st_mode
    except FileNotFoundError:
        return {"state": "absent"}
    except OSError:
        return {"state": "integrity_failed"}
    if not stat.S_ISREG(pointer_mode):
        return {"state": "integrity_failed"}
    try:
        pointer = _read_canonical_json(pointer_path)
        generation_id, published_at = _validate_pointer(pointer)
        generations_path = dashboard / "research-views-generations"
        expected_parent = _require_contained_entry(generations_path, dashboard, directory=True)
        generation_root = _require_contained_entry(
            generations_path / generation_id, expected_parent, directory=True
        )
        if {path.name for path in generation_root.iterdir()} != {
            *GENERATION_FILES,
            "research-views-manifest.json",
        }:
            raise PublicationError("generation contains an unknown or missing file")
        manifest_path = _require_contained_entry(
            generation_root / "research-views-manifest.json", generation_root
        )
        manifest_raw = manifest_path.read_bytes()
        manifest_meta = pointer["manifest"]
        if _metadata(manifest_raw) != {
            "sha256": manifest_meta["sha256"],
            "bytes": manifest_meta["bytes"],
        }:
            raise PublicationError("manifest hash or size mismatch")
        manifest = _validate_manifest(
            _read_canonical_json(manifest_path), generation_id, published_at
        )
        artifact_paths: dict[str, Path] = {}
        for name in GENERATION_FILES:
            path = _require_contained_entry(generation_root / name, generation_root)
            raw = path.read_bytes()
            if _metadata(raw) != manifest["files"][name]:
                raise PublicationError(f"artifact hash or size mismatch: {name}")
            artifact_paths[name] = path
        status = _validate_status(
            _read_canonical_json(artifact_paths["research-views-status.txt"]),
            generation_id,
            published_at,
        )
        for name in ARTIFACTS:
            if status["files"][name] != manifest["files"][name]:
                raise PublicationError("status and manifest disagree")
        return {
            "state": "published",
            "generation_id": generation_id,
            "published_at": published_at,
            "pointer": pointer,
            "manifest": manifest,
            "generation_root": generation_root,
            "artifacts": artifact_paths,
            "status": status,
        }
    except (OSError, PublicationError, KeyError, TypeError, ValueError):
        return {"state": "integrity_failed"}


def _pointer_record(
    *,
    generation_id: str,
    published_at: str,
    manifest_raw: bytes,
    copied_from_root: Path | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema": "research_views_current/v1",
        "generation_id": generation_id,
        "published_at": published_at,
        "manifest": {
            "path": f"research-views-generations/{generation_id}/research-views-manifest.json",
            **_metadata(manifest_raw),
        },
    }
    if copied_from_root is not None:
        value["copied_from_root"] = str(copied_from_root.resolve())
    return value


def _replace_pointer(dashboard: Path, pointer: Mapping[str, object]) -> None:
    temp = dashboard / f".research-views-current.{uuid.uuid4().hex}.tmp"
    _write_fsynced(temp, _canonical_bytes(pointer))
    try:
        os.replace(temp, dashboard / "research-views-current.json")
    finally:
        if temp.is_file():
            temp.unlink()
    _fsync_directory(dashboard)


def publish_generation(
    *,
    dashboard_dir: str | Path,
    staging_dir: str | Path,
    generation_id: str,
    published_at: str,
    producer_commit: str,
) -> dict[str, Any]:
    dashboard = Path(dashboard_dir).resolve()
    staging = Path(staging_dir).resolve()
    generation_id = _require_generation_id(generation_id)
    _parse_timestamp(published_at)
    producer_commit = _require_commit(producer_commit)
    generations = (dashboard / "research-views-generations").resolve()
    expected_staging = generations / f".staging-{generation_id}"
    if staging != expected_staging or not staging.is_dir():
        raise PublicationError("staging directory identity mismatch")
    if set(path.name for path in staging.iterdir()) != set(ARTIFACTS):
        raise PublicationError("staging artifacts do not match allow-list")

    artifact_metadata = {name: _metadata((staging / name).read_bytes()) for name in ARTIFACTS}
    status = {
        "schema": "research_views_status/v1",
        "generation_id": generation_id,
        "published_at": published_at,
        "experiments_exit": 0,
        "wasserstein_exit": 0,
        "files": artifact_metadata,
    }
    _write_fsynced(staging / "research-views-status.txt", _canonical_bytes(status))
    manifest = {
        "schema": "research_views_manifest/v1",
        "generation_id": generation_id,
        "published_at": published_at,
        "producer_commit": producer_commit,
        "files": {
            **artifact_metadata,
            "research-views-status.txt": _metadata(
                (staging / "research-views-status.txt").read_bytes()
            ),
        },
    }
    manifest_raw = _canonical_bytes(manifest)
    _write_fsynced(staging / "research-views-manifest.json", manifest_raw)
    for name in (*GENERATION_FILES, "research-views-manifest.json"):
        with (staging / name).open("rb") as handle:
            os.fsync(handle.fileno())
    _fsync_directory(staging)
    pointer = _pointer_record(
        generation_id=generation_id,
        published_at=published_at,
        manifest_raw=manifest_raw,
    )
    with _publication_lock(dashboard):
        final = generations / generation_id
        if final.exists():
            raise PublicationError("generation collision")
        os.replace(staging, final)
        _fsync_directory(generations)
        _replace_pointer(dashboard, pointer)
    return pointer


def _validate_failure(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "attempt_id",
        "attempted_at",
        "completed_at",
        "producer_commit",
        "producer_root",
        "experiments_exit",
        "wasserstein_exit",
        "outcome",
    }
    if set(value) != required or value.get("schema") != "research_views_failure/v1":
        raise PublicationError("invalid failure schema")
    _require_generation_id(value.get("attempt_id"))
    _parse_timestamp(value.get("attempted_at"))
    _parse_timestamp(value.get("completed_at"))
    _require_commit(value.get("producer_commit"))
    root = value.get("producer_root")
    if (
        not isinstance(root, str)
        or not Path(root).is_absolute()
        or str(Path(root).resolve()) != root
    ):
        raise PublicationError("invalid producer root")
    exits = (value.get("experiments_exit"), value.get("wasserstein_exit"))
    if any(isinstance(item, bool) or not isinstance(item, int) for item in exits):
        raise PublicationError("invalid failure exits")
    if exits == (0, 0) or value.get("outcome") != "FAILED":
        raise PublicationError("invalid failure outcome")
    return value


def _reconcile_failure_locked(dashboard: Path, incoming: dict[str, Any]) -> str:
    incoming = _validate_failure(incoming)
    path = dashboard / "research-views-last-failure.json"
    if path.is_file():
        current = _validate_failure(_read_canonical_json(path))
        current_time = _parse_timestamp(current["completed_at"])
        incoming_time = _parse_timestamp(incoming["completed_at"])
        if current["attempt_id"] == incoming["attempt_id"]:
            return "idempotent"
        if incoming_time < current_time:
            return "older"
        if incoming_time == current_time:
            raise PublicationError("ATTEMPT_CONFLICT")
    temp = dashboard / f".research-views-failure.{uuid.uuid4().hex}.tmp"
    _write_fsynced(temp, _canonical_bytes(incoming))
    os.replace(temp, path)
    _fsync_directory(dashboard)
    return "installed"


def record_failure(
    *,
    dashboard_dir: str | Path,
    attempt_id: str,
    attempted_at: str,
    producer_commit: str,
    producer_root: str | Path,
    experiments_exit: int,
    wasserstein_exit: int,
    staging_dir: str | Path,
) -> dict[str, Any]:
    dashboard = Path(dashboard_dir).resolve()
    staging = Path(staging_dir).resolve()
    expected = dashboard / "research-views-generations" / f".staging-{attempt_id}"
    if staging != expected.resolve():
        raise PublicationError("failure staging identity mismatch")
    failure = {
        "schema": "research_views_failure/v1",
        "attempt_id": _require_generation_id(attempt_id),
        "attempted_at": attempted_at,
        "completed_at": "",
        "producer_commit": _require_commit(producer_commit),
        "producer_root": str(Path(producer_root).resolve()),
        "experiments_exit": experiments_exit,
        "wasserstein_exit": wasserstein_exit,
        "outcome": "FAILED",
    }
    _parse_timestamp(attempted_at)
    with _publication_lock(dashboard):
        failure["completed_at"] = canonical_timestamp(_utc_now())
        _reconcile_failure_locked(dashboard, failure)
    if staging.is_dir():
        shutil.rmtree(staging)
    return failure


def _snapshot_failure(dashboard: Path) -> dict[str, Any] | None:
    path = dashboard / "research-views-last-failure.json"
    if not path.is_file():
        return None
    return _validate_failure(_read_canonical_json(path))


def load_failure(dashboard_dir: str | Path) -> dict[str, Any]:
    """Load the independent failure channel without affecting current validity."""
    dashboard = Path(dashboard_dir).resolve()
    path = dashboard / "research-views-last-failure.json"
    if not path.is_file():
        return {"state": "absent"}
    try:
        return {"state": "failed", "failure": _snapshot_failure(dashboard)}
    except (OSError, PublicationError, KeyError, TypeError, ValueError):
        return {"state": "integrity_failed"}


def copy_publication(*, source_root: str | Path, destination_root: str | Path) -> str:
    source = Path(source_root).resolve()
    destination = Path(destination_root).resolve()
    if source == destination:
        return "same_root"
    source_dashboard = source / ".tmp" / "dashboard"
    destination_dashboard = destination / ".tmp" / "dashboard"
    loaded = load_current(source_dashboard)
    if loaded.get("state") != "published":
        raise PublicationError("source publication integrity failed")
    source_failure = _snapshot_failure(source_dashboard)
    generation_id = loaded["generation_id"]
    generation_files = (*GENERATION_FILES, "research-views-manifest.json")
    snapshot = {name: (loaded["generation_root"] / name).read_bytes() for name in generation_files}
    generations = destination_dashboard / "research-views-generations"
    generations.mkdir(parents=True, exist_ok=True)
    staging = generations / f".staging-{generation_id}"
    if staging.exists():
        raise PublicationError("destination staging collision")
    staging.mkdir()
    try:
        for name, raw in snapshot.items():
            _write_fsynced(staging / name, raw)
        _fsync_directory(staging)
        with _publication_lock(destination_dashboard):
            if source_failure is not None:
                _reconcile_failure_locked(destination_dashboard, source_failure)
            destination_current = load_current(destination_dashboard)
            if destination_current.get("state") == "published":
                if destination_current["generation_id"] == generation_id:
                    shutil.rmtree(staging)
                    return "idempotent"
                source_time = _parse_timestamp(loaded["published_at"])
                destination_time = _parse_timestamp(destination_current["published_at"])
                if destination_time > source_time:
                    shutil.rmtree(staging)
                    return "newer_destination"
                if destination_time == source_time:
                    raise PublicationError("GENERATION_CONFLICT")
            elif destination_current.get("state") == "integrity_failed":
                raise PublicationError("destination publication integrity failed")
            final = generations / generation_id
            if final.exists():
                raise PublicationError("generation collision")
            os.replace(staging, final)
            _fsync_directory(generations)
            manifest_raw = snapshot["research-views-manifest.json"]
            pointer = _pointer_record(
                generation_id=generation_id,
                published_at=loaded["published_at"],
                manifest_raw=manifest_raw,
                copied_from_root=source,
            )
            _replace_pointer(destination_dashboard, pointer)
        return "installed"
    except Exception:
        if staging.is_dir():
            shutil.rmtree(staging)
        raise


def _git_commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return _require_commit(result.stdout.strip())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research-view publication commit helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    begin = subparsers.add_parser("begin")
    begin.add_argument("--dashboard-dir", required=True)
    finish = subparsers.add_parser("finish")
    finish.add_argument("--dashboard-dir", required=True)
    finish.add_argument("--staging-dir", required=True)
    finish.add_argument("--generation-id", required=True)
    finish.add_argument("--attempted-at", required=True)
    finish.add_argument("--producer-root", required=True)
    finish.add_argument("--experiments-exit", required=True, type=int)
    finish.add_argument("--wasserstein-exit", required=True, type=int)
    args = parser.parse_args(argv)
    if args.command == "begin":
        dashboard = Path(args.dashboard_dir).resolve()
        generation_id = mint_generation_id()
        attempted_at = canonical_timestamp(_utc_now())
        staging = dashboard / "research-views-generations" / f".staging-{generation_id}"
        staging.mkdir(parents=True, exist_ok=False)
        print(generation_id)
        print(attempted_at)
        print(staging)
        return 0
    repo_root = Path(args.producer_root).resolve()
    commit = _git_commit(repo_root)
    if args.experiments_exit or args.wasserstein_exit:
        record_failure(
            dashboard_dir=args.dashboard_dir,
            attempt_id=args.generation_id,
            attempted_at=args.attempted_at,
            producer_commit=commit,
            producer_root=repo_root,
            experiments_exit=args.experiments_exit,
            wasserstein_exit=args.wasserstein_exit,
            staging_dir=args.staging_dir,
        )
        return 1
    publish_generation(
        dashboard_dir=args.dashboard_dir,
        staging_dir=args.staging_dir,
        generation_id=args.generation_id,
        published_at=canonical_timestamp(_utc_now()),
        producer_commit=commit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
