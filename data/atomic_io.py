"""Durable local-file writes for cache and provenance artifacts."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _sync(fd: int) -> None:
    os.fsync(fd)
    if sys.platform == "darwin":
        import fcntl

        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def atomic_parquet_write(frame, path: Path) -> None:
    """Write a parquet beside the destination, then publish it atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_parquet(temp, index=False)
        fd = os.open(temp, os.O_RDONLY)
        try:
            _sync(fd)
        finally:
            os.close(fd)
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            _sync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise


def atomic_text_write(text: str, path: Path) -> None:
    """Durably publish a text manifest/JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("x") as handle:
            handle.write(text)
            handle.flush()
            _sync(handle.fileno())
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            _sync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise
