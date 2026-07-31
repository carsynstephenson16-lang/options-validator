"""Content-addressed, schema-versioned manifest of the chain cache.

The cache (.cache/chains) is what every offline backtest reads, but it is
gitignored and re-fetchable only with a live ThetaData subscription — so a
fresh clone cannot reproduce a logged experiment. This tool freezes the
cache's exact bytes and schema eligibility into a committable manifest and
verifies both, giving a reproducer byte-level evidence that a re-fetch
matches what a ledger record used.

Usage:
    uv run python tools/cache_manifest.py generate
    uv run python tools/cache_manifest.py verify
"""

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass

# Preserve the documented `python tools/cache_manifest.py ...` entry point.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache_schema import chain_schema_metadata, expected_usage

DEFAULT_CACHE_DIR = os.path.join(".cache", "chains")
DEFAULT_MANIFEST = os.path.join("data", "chain_cache_manifest.txt")
MANIFEST_HEADER = "# chain-cache-manifest/v2"
LEGACY_DEFAULTS = "# legacy-entry-defaults schema_version=1 usage=display-only"


@dataclass(frozen=True)
class ManifestEntry:
    name: str
    sha256: str
    size: int
    schema_version: int
    usage: str


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _partition_metadata(path: str):
    """Read only Parquet file metadata; never materialize cached row values."""
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    return chain_schema_metadata(parquet.schema_arrow.names)


def build_manifest(cache_dir: str) -> list[ManifestEntry]:
    """Return one content- and schema-bound entry per cache partition."""
    rows: list[ManifestEntry] = []
    for name in sorted(os.listdir(cache_dir)):
        path = os.path.join(cache_dir, name)
        if os.path.isfile(path):
            metadata = _partition_metadata(path)
            rows.append(
                ManifestEntry(
                    name=name,
                    sha256=_sha256(path),
                    size=os.path.getsize(path),
                    schema_version=metadata.schema_version,
                    usage=metadata.usage,
                )
            )
    return rows


def write_manifest(cache_dir: str, out_path: str) -> int:
    rows = build_manifest(cache_dir)
    with open(out_path, "w") as fh:
        fh.write(f"{MANIFEST_HEADER}\n{LEGACY_DEFAULTS}\n")
        for entry in rows:
            fh.write(
                f"{entry.sha256}  {entry.size}  "
                f"schema_version={entry.schema_version}  "
                f"usage={entry.usage}  {entry.name}\n"
            )
    return len(rows)


def read_manifest(path: str) -> dict[str, ManifestEntry]:
    out: dict[str, ManifestEntry] = {}
    with open(path) as fh:
        for line_number, line in enumerate(fh, start=1):
            stripped = line.rstrip("\n")
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split("  ")
            if len(parts) == 3:
                digest, size_text, name = parts
                schema_version = 1
                usage = "display-only"
            elif len(parts) == 5:
                digest, size_text, schema_text, usage_text, name = parts
                if not schema_text.startswith("schema_version="):
                    raise ValueError(f"{path}:{line_number}: malformed schema_version")
                if not usage_text.startswith("usage="):
                    raise ValueError(f"{path}:{line_number}: malformed usage")
                schema_version = int(schema_text.removeprefix("schema_version="))
                usage = usage_text.removeprefix("usage=")
            else:
                raise ValueError(f"{path}:{line_number}: malformed manifest entry")
            if usage != expected_usage(schema_version):
                raise ValueError(
                    f"{path}:{line_number}: schema_version={schema_version} "
                    f"must use usage={expected_usage(schema_version)}"
                )
            if name in out:
                raise ValueError(f"{path}:{line_number}: duplicate manifest entry {name}")
            out[name] = ManifestEntry(
                name=name,
                sha256=digest,
                size=int(size_text),
                schema_version=schema_version,
                usage=usage,
            )
    return out


def verify_manifest(cache_dir: str, manifest_path: str) -> list[str]:
    """Empty list = cache matches manifest byte-for-byte. Otherwise one
    MISSING / EXTRA / MISMATCH line per problem."""
    expected = read_manifest(manifest_path)
    actual_names = {n for n in os.listdir(cache_dir) if os.path.isfile(os.path.join(cache_dir, n))}
    problems = []
    for name in sorted(set(expected) - actual_names):
        problems.append(f"MISSING  {name}")
    for name in sorted(actual_names - set(expected)):
        problems.append(f"EXTRA    {name}")
    for name in sorted(actual_names & set(expected)):
        entry = expected[name]
        path = os.path.join(cache_dir, name)
        if os.path.getsize(path) != entry.size or _sha256(path) != entry.sha256:
            problems.append(f"MISMATCH {name}")
            continue
        try:
            metadata = _partition_metadata(path)
        except (OSError, ValueError) as exc:
            problems.append(f"SCHEMA_INVALID {name}: {exc}")
            continue
        if metadata.schema_version != entry.schema_version or metadata.usage != entry.usage:
            problems.append(
                f"SCHEMA_MISMATCH {name}: manifest schema_version="
                f"{entry.schema_version} usage={entry.usage}; actual "
                f"schema_version={metadata.schema_version} "
                f"usage={metadata.usage}"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "verify"])
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    if args.command == "generate":
        n = write_manifest(args.cache_dir, args.manifest)
        print(f"wrote {n} entries to {args.manifest}")
        return 0
    problems = verify_manifest(args.cache_dir, args.manifest)
    for p in problems:
        print(p)
    print(f"verify: {'OK' if not problems else f'{len(problems)} problem(s)'}")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
