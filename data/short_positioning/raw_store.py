"""Immutable raw-artifact storage.

Raw provider bytes are written before any normalization and are never
rewritten. Every artifact carries a SHA-256 that normalized rows bind to.
These files stay local and gitignored.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from data.short_positioning.provider import ArtifactIntegrityError, CaptureRequest, RawArtifact


def _sync(fd: int) -> None:
    os.fsync(fd)
    if sys.platform == "darwin":
        import fcntl

        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def _atomic_bytes_write(payload: bytes, path: Path) -> None:
    """Publish bytes exactly, or leave nothing behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            _sync(handle.fileno())
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            _sync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def raw_partition_dir(root: Path, request: CaptureRequest) -> Path:
    return (
        Path(root)
        / "raw"
        / f"provider={request.provider}"
        / f"dataset={request.dataset}"
        / f"publication_date={request.publication_date.isoformat()}"
    )


def write_raw_artifact(
    payload: bytes,
    *,
    root: Path,
    request: CaptureRequest,
    retrieved_at: datetime,
) -> RawArtifact:
    """Write raw bytes plus a redacted manifest. Refuses to overwrite."""
    partition = raw_partition_dir(root, request)
    path = partition / f"{request.request_id}.json"
    manifest_path = path.with_suffix(".manifest.json")
    if path.exists() or manifest_path.exists():
        raise ArtifactIntegrityError(
            f"raw artifact {path.name} already exists; captures are immutable"
        )

    digest = hashlib.sha256(payload).hexdigest()
    _atomic_bytes_write(payload, path)

    manifest = {
        "provider": request.provider,
        "dataset": request.dataset,
        "publication_date": request.publication_date.isoformat(),
        "request_id": request.request_id,
        "source_data_version": request.source_data_version,
        "symbols_requested": list(request.symbols),
        "retrieved_at": retrieved_at.isoformat(),
        "raw_sha256": digest,
        "byte_count": len(payload),
    }
    try:
        _atomic_bytes_write(
            (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(), manifest_path
        )
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    return RawArtifact(
        path=path,
        sha256=digest,
        byte_count=len(payload),
        retrieved_at=retrieved_at,
        request_id=request.request_id,
    )


def verify_raw_artifact(artifact: RawArtifact) -> None:
    """Raise ``ArtifactIntegrityError`` unless the bytes still hash as recorded."""
    path = Path(artifact.path)
    if not path.exists():
        raise ArtifactIntegrityError(f"raw artifact is missing: {path}")

    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != artifact.sha256:
        raise ArtifactIntegrityError(
            f"raw artifact {path.name} hashes to {digest}, recorded {artifact.sha256}"
        )

    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        raise ArtifactIntegrityError(f"raw manifest is missing for {path.name}")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("raw_sha256") != digest or manifest.get("byte_count") != len(payload):
        raise ArtifactIntegrityError(f"raw manifest disagrees with the bytes for {path.name}")
