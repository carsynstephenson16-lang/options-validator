"""Presence-and-size guard for gitignored data that cannot be re-acquired.

WHY THIS EXISTS (incident 2026-08-03): the parked future-ticker capture --
1,536 partitions, 2,499,624 rows, 3,072 provider calls, taken BEFORE the
ThetaData cancellation -- existed in exactly one place on disk: a disposable
git worktree under ~/Downloads. Nothing tracked its existence, because the
bytes are gitignored and `tools/cache_manifest.py` only covers .cache/chains.
Deleting that worktree would have destroyed it permanently, and no test,
manifest, or CI check would have noticed.

ThetaData acquisition is disabled (OD-4). Every namespace listed in the
inventory is now UNREPLACEABLE: if the bytes go, the evidence goes with them.

This tool freezes a committable inventory (per-namespace file count and total
size) and verifies the working copy against it. It is deliberately cheap --
counts and sizes, not content hashes -- so it can be run before any worktree
removal, cleanup sweep, or disk operation. Use --deep for content hashes when
you need byte-level proof; use tools/cache_manifest.py for the canonical v1
chain cache's per-file hash binding.

Usage:
    uv run python tools/irreplaceable_data_guard.py verify
    uv run python tools/irreplaceable_data_guard.py verify --deep
    uv run python tools/irreplaceable_data_guard.py generate

Exit codes: 0 = every recorded namespace is present and no smaller than
recorded; 1 = something is missing or has shrunk (investigate before any
delete); 2 = usage/inventory error.

A fresh clone legitimately has no cache. Pass --allow-absent to treat a
wholly-absent namespace as a skip; a namespace that exists but has LOST files
always fails, because that is the silent-corruption case this guards.

Inventory paths are relative to the MAIN checkout's root, and the tool anchors
there no matter where it is invoked from. Linked worktrees carry the committed
inventory but never the gitignored bytes, so resolving against the invoking
directory manufactured a total-loss report from every worktree (false alarm,
2026-08-09) -- in the exact situation CLAUDE.md requires running this guard.
When the main checkout cannot be located at all, the tool exits 2 with a
LOCATION error, which is never a data-loss finding.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

DEFAULT_INVENTORY = os.path.join("data", "irreplaceable_data_inventory.json")

# Namespaces that cannot be re-acquired now that provider acquisition is off.
# Paths are repo-relative. Add a namespace here the moment it becomes
# irreplaceable -- not after an incident.
DEFAULT_NAMESPACES = [
    ".cache/chains",
    ".cache/chains_v2",
    ".cache/future_tickers",
    ".cache/intraday",
    ".cache/schwab_chains",
    ".cache/underlying",
    ".cache/underlying_ohlcv",
    "reports/schwab_chains",
]


def resolve_repo_root() -> str:
    """Absolute path of the main checkout's working tree, from any cwd.

    The recorded namespaces are gitignored, so their bytes exist ONLY in the
    main checkout; a linked worktree shares the repository but not the data.
    `git rev-parse --git-common-dir` names the main checkout's .git from the
    main checkout, any subdirectory, and every linked worktree alike.
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() if exc.stderr else str(exc)
        raise RuntimeError(f"not inside a git checkout ({detail})") from exc
    return os.path.dirname(os.path.abspath(proc.stdout.strip()))


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def scan(root: str, deep: bool = False) -> dict:
    """Count files and bytes under `root`, recursively and deterministically.

    Returns file_count, total_bytes, and (when deep) a single digest over the
    sorted relative-path + per-file-hash list, which changes if any byte,
    name, or file count changes.
    """
    if not os.path.isdir(root):
        return {"present": False, "file_count": 0, "total_bytes": 0}

    entries = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.isfile(path) and not os.path.islink(path):
                entries.append((os.path.relpath(path, root), path))
    entries.sort()

    total = sum(os.path.getsize(p) for _rel, p in entries)
    out = {"present": True, "file_count": len(entries), "total_bytes": total}

    if deep:
        roll = hashlib.sha256()
        for rel, path in entries:
            roll.update(rel.encode())
            roll.update(_sha256(path).encode())
        out["content_digest"] = roll.hexdigest()
    return out


def build_inventory(namespaces: list[str], deep: bool = False, root: str = ".") -> dict:
    return {
        "note": (
            "Gitignored, unreplaceable data. Provider acquisition is disabled; "
            "these bytes cannot be re-fetched. Verify before any worktree "
            "removal or cleanup sweep."
        ),
        "namespaces": {ns: scan(os.path.join(root, ns), deep=deep) for ns in namespaces},
    }


def verify(
    inventory: dict, deep: bool = False, allow_absent: bool = False, root: str = "."
) -> list[str]:
    """Return a list of human-readable problems; empty means healthy.

    Relative namespace paths resolve against `root` (the main checkout);
    absolute ones -- as the unit-test fixtures use -- are taken as-is.
    """
    problems = []
    for ns, recorded in sorted(inventory.get("namespaces", {}).items()):
        if not recorded.get("present"):
            continue  # never recorded as present; nothing to protect yet

        current = scan(os.path.join(root, ns), deep=deep and "content_digest" in recorded)

        # Doc note (audit L8, 2026-08-12): --allow-absent only skips a
        # namespace whose directory does not exist at all (scan()'s
        # `present: False`). A directory that EXISTS but is EMPTY -- e.g.
        # auto-mkdir'd as a side effect of importing a module that touches
        # its cache path, with no bytes ever written -- still has
        # `present: True` here and falls through to the file_count/
        # total_bytes comparison below, which alarms as LOST FILES if the
        # inventory recorded any files. This is intentional, not a bug: the
        # tool cannot distinguish "never populated" from "silently emptied"
        # once the directory exists, and silent emptying is exactly the
        # failure mode this guard exists to catch. Working as documented;
        # see reports/repo-audits/2026-08-12-low-findings-disposition.md.
        if not current["present"]:
            if allow_absent:
                continue
            problems.append(
                f"{ns}: MISSING ENTIRELY (recorded {recorded['file_count']} files, "
                f"{recorded['total_bytes']} bytes). This data cannot be re-acquired."
            )
            continue

        if current["file_count"] < recorded["file_count"]:
            problems.append(
                f"{ns}: LOST FILES -- {current['file_count']} present, "
                f"{recorded['file_count']} recorded "
                f"({recorded['file_count'] - current['file_count']} gone)."
            )
        if current["total_bytes"] < recorded["total_bytes"]:
            problems.append(
                f"{ns}: SHRANK -- {current['total_bytes']} bytes present, "
                f"{recorded['total_bytes']} recorded."
            )

        recorded_digest = recorded.get("content_digest")
        if deep and recorded_digest and current.get("content_digest") != recorded_digest:
            problems.append(
                f"{ns}: CONTENT CHANGED -- digest {current.get('content_digest')} "
                f"!= recorded {recorded_digest}."
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "verify"])
    parser.add_argument(
        "--inventory",
        default=DEFAULT_INVENTORY,
        help="inventory path; relative paths resolve against the MAIN checkout root",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="hash file contents (slow; use for byte-level proof)",
    )
    parser.add_argument(
        "--allow-absent",
        action="store_true",
        help="treat a wholly-absent namespace as a skip (fresh clone / CI)",
    )
    args = parser.parse_args(argv)

    try:
        root = resolve_repo_root()
    except RuntimeError as exc:
        print(f"LOCATION ERROR: {exc}", file=sys.stderr)
        print(
            "Refusing to run. This is NOT a data-loss finding -- invoke the "
            "guard from inside the repository so it can anchor on the main "
            "checkout.",
            file=sys.stderr,
        )
        return 2
    if os.path.realpath(os.getcwd()) != os.path.realpath(root):
        print(
            f"note: invoked from {os.getcwd()}\n"
            f"      verifying the main checkout at {root}",
            file=sys.stderr,
        )

    inventory_path = (
        args.inventory if os.path.isabs(args.inventory) else os.path.join(root, args.inventory)
    )

    if args.command == "generate":
        inventory = build_inventory(DEFAULT_NAMESPACES, deep=args.deep, root=root)
        with open(inventory_path, "w") as fh:
            json.dump(inventory, fh, indent=2, sort_keys=True)
            fh.write("\n")
        for ns, info in sorted(inventory["namespaces"].items()):
            state = (
                f"{info['file_count']} files, {info['total_bytes']} bytes"
                if info["present"]
                else "absent"
            )
            print(f"  {ns}: {state}")
        print(f"wrote {inventory_path}")
        return 0

    if not os.path.exists(inventory_path):
        print(f"inventory not found: {inventory_path}", file=sys.stderr)
        return 2
    with open(inventory_path) as fh:
        inventory = json.load(fh)

    problems = verify(inventory, deep=args.deep, allow_absent=args.allow_absent, root=root)
    if problems:
        print("IRREPLACEABLE DATA CHECK FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        recorded_present = sum(
            1 for rec in inventory.get("namespaces", {}).values() if rec.get("present")
        )
        missing = sum("MISSING ENTIRELY" in p for p in problems)
        if missing and missing == recorded_present:
            print(
                f"\nEvery recorded namespace is absent under {root}. If that is "
                "a secondary clone, the canonical checkout may still hold the "
                "bytes -- check it before concluding loss. If that IS the "
                "canonical checkout, treat this as a live incident.",
                file=sys.stderr,
            )
        print(
            "\nDo NOT delete any worktree, branch, or directory until this is "
            "understood. These bytes cannot be re-fetched.",
            file=sys.stderr,
        )
        return 1

    print("irreplaceable data: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
