"""Content-addressed manifest of the gitignored parquet chain cache.

The cache (.cache/chains) is what every offline backtest reads, but it is
gitignored and re-fetchable only with a live ThetaData subscription — so a
fresh clone cannot reproduce a logged experiment. This tool freezes the
cache's exact bytes into a committable manifest (one "sha256  size  name"
line per file) and verifies a cache against it, giving a reproducer
byte-level evidence that a re-fetch matches what a ledger record used.

Usage:
    uv run python tools/cache_manifest.py generate
    uv run python tools/cache_manifest.py verify
"""
import argparse
import hashlib
import os
import sys

DEFAULT_CACHE_DIR = os.path.join(".cache", "chains")
DEFAULT_MANIFEST = os.path.join("data", "chain_cache_manifest.txt")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build_manifest(cache_dir: str) -> list[tuple[str, str, int]]:
    """Sorted (name, sha256, size) for every regular file in cache_dir."""
    rows = []
    for name in sorted(os.listdir(cache_dir)):
        path = os.path.join(cache_dir, name)
        if os.path.isfile(path):
            rows.append((name, _sha256(path), os.path.getsize(path)))
    return rows


def write_manifest(cache_dir: str, out_path: str) -> int:
    rows = build_manifest(cache_dir)
    with open(out_path, "w") as fh:
        for name, digest, size in rows:
            fh.write(f"{digest}  {size}  {name}\n")
    return len(rows)


def read_manifest(path: str) -> dict[str, tuple[str, int]]:
    out = {}
    with open(path) as fh:
        for line in fh:
            digest, size, name = line.rstrip("\n").split("  ", 2)
            out[name] = (digest, int(size))
    return out


def verify_manifest(cache_dir: str, manifest_path: str) -> list[str]:
    """Empty list = cache matches manifest byte-for-byte. Otherwise one
    MISSING / EXTRA / MISMATCH line per problem."""
    expected = read_manifest(manifest_path)
    actual_names = {n for n in os.listdir(cache_dir)
                    if os.path.isfile(os.path.join(cache_dir, n))}
    problems = []
    for name in sorted(set(expected) - actual_names):
        problems.append(f"MISSING  {name}")
    for name in sorted(actual_names - set(expected)):
        problems.append(f"EXTRA    {name}")
    for name in sorted(actual_names & set(expected)):
        digest, size = expected[name]
        path = os.path.join(cache_dir, name)
        if os.path.getsize(path) != size or _sha256(path) != digest:
            problems.append(f"MISMATCH {name}")
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
