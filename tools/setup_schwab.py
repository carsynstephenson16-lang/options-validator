#!/usr/bin/env python3
"""One-secret bootstrap for Schwab read-only market data in both repositories."""

from __future__ import annotations

import argparse
import json
import stat
import sys
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from data.schwab_credentials import (  # noqa: E402
    PRIVATE_TOKEN_DIR,
    SHARED_TOKEN_PATH,
    load_client_secret,
    store_client_secret,
)

DEFAULT_EQUITY_REPO = REPO_ROOT.parent / "equity-research"
CALLBACK_URL = "https://127.0.0.1:8182"


def _quoted(value: str) -> str:
    return json.dumps(value)


def upsert_env(path: Path, updates: dict[str, str]) -> None:
    """Update named entries only; preserve all unrelated local settings."""
    original = path.read_text() if path.exists() else ""
    remaining = dict(updates)
    lines = []
    for line in original.splitlines():
        stripped = line.lstrip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                lines.append(f"{key}={_quoted(remaining.pop(key))}")
                continue
        lines.append(line)
    if remaining:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# Schwab Market Data API (read-only; managed by setup_schwab.py)")
        lines.extend(f"{key}={_quoted(value)}" for key, value in remaining.items())
    path.write_text("\n".join(lines).rstrip() + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def remove_env_keys(path: Path, keys: set[str]) -> None:
    """Remove deprecated secret-bearing entries without reading their values."""
    if not path.exists():
        return
    lines = []
    for line in path.read_text().splitlines():
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if key not in keys:
            lines.append(line)
    path.write_text("\n".join(lines).rstrip() + "\n")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _repo_settings(repo: Path) -> dict[str, str]:
    values = dotenv_values(repo / ".env")
    api_key = str(values.get("SCHWAB_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            f"{repo}/.env has no SCHWAB_API_KEY. The non-secret Client ID "
            "should have been preconfigured."
        )
    return {
        "SCHWAB_API_KEY": api_key,
        "SCHWAB_CALLBACK_URL": CALLBACK_URL,
        "SCHWAB_TOKEN_PATH": str(SHARED_TOKEN_PATH),
        "SCHWAB_TRADING_ENABLED": "false",
        "SCHWAB_ENTITLEMENT": "NP",
    }


def _authorize(repo: Path, secret: str):
    import schwab.auth

    values = dotenv_values(repo / ".env")
    token_path = Path(str(values["SCHWAB_TOKEN_PATH"]))
    token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_path.parent.chmod(0o700)
    print("\nAuthorize the shared read-only Schwab market-data session.")
    print("A Schwab browser page will open. Sign in and approve the app.")
    client = schwab.auth.client_from_login_flow(
        str(values["SCHWAB_API_KEY"]),
        secret,
        str(values["SCHWAB_CALLBACK_URL"]),
        str(token_path),
        callback_timeout=300.0,
    )
    token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    response = client.get_quote("SPY")
    response.raise_for_status()
    print("✓ Shared OAuth token saved and SPY quote check passed")
    return client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Configure Schwab Market Data in options-validator and "
            "equity-research. The app secret is requested once with hidden input."
        )
    )
    parser.add_argument(
        "--equity-repo",
        type=Path,
        default=DEFAULT_EQUITY_REPO,
        help=f"equity-research path (default: {DEFAULT_EQUITY_REPO})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate non-secret configuration without changing anything",
    )
    parser.add_argument(
        "--configure-only",
        action="store_true",
        help="secure local paths and remove plaintext secrets without starting OAuth",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repos = (REPO_ROOT.resolve(), args.equity_repo.expanduser().resolve())
    if args.check and args.configure_only:
        raise RuntimeError("--check and --configure-only cannot be combined.")
    if args.check:
        if not PRIVATE_TOKEN_DIR.is_dir():
            raise RuntimeError("The private Schwab token directory is missing.")
        if stat.S_IMODE(PRIVATE_TOKEN_DIR.stat().st_mode) != 0o700:
            raise RuntimeError("The private Schwab token directory must be mode 0700.")
    else:
        PRIVATE_TOKEN_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        PRIVATE_TOKEN_DIR.chmod(0o700)
    settings_by_repo: dict[Path, dict[str, str]] = {}
    for repo in repos:
        if not repo.is_dir():
            raise RuntimeError(f"repository not found: {repo}")
        settings = _repo_settings(repo)
        settings_by_repo[repo] = settings

    app_keys = {settings["SCHWAB_API_KEY"] for settings in settings_by_repo.values()}
    if len(app_keys) != 1:
        raise RuntimeError(
            "The repositories use different SCHWAB_API_KEY values. A shared "
            "refresh token is valid only for one Schwab app; align the app "
            "configuration or keep separately authorized apps."
        )

    for repo, settings in settings_by_repo.items():
        if repo == REPO_ROOT.resolve():
            settings["LIVE_MARKET_DATA_PROVIDER"] = "schwab"
        else:
            settings["EQUITY_RESEARCH_QUOTE_PROVIDER"] = "schwab"
        if args.check:
            values = dotenv_values(repo / ".env")
            if values.get("SCHWAB_APP_SECRET"):
                raise RuntimeError(f"{repo}/.env still contains plaintext SCHWAB_APP_SECRET.")
            configured_path = Path(str(values.get("SCHWAB_TOKEN_PATH") or "")).expanduser()
            if configured_path.resolve() != SHARED_TOKEN_PATH.resolve():
                raise RuntimeError(f"{repo}/.env does not use the shared token path.")
        else:
            remove_env_keys(repo / ".env", {"SCHWAB_APP_SECRET"})
            upsert_env(repo / ".env", settings)

    if args.check:
        if not SHARED_TOKEN_PATH.is_file():
            raise RuntimeError("The shared Schwab OAuth token is missing.")
        if stat.S_IMODE(SHARED_TOKEN_PATH.stat().st_mode) != 0o600:
            raise RuntimeError("The shared Schwab OAuth token must be mode 0600.")
        print("✓ Both repositories have valid non-secret Schwab configuration")
        return 0
    if args.configure_only:
        print("✓ Plaintext secrets removed and private token paths configured")
        return 0

    store_client_secret()
    secret = load_client_secret()
    try:
        options_api_client = _authorize(REPO_ROOT.resolve(), secret)
    finally:
        secret = ""

    from datetime import datetime
    from zoneinfo import ZoneInfo

    from data.schwab_adapter import SchwabMarketData
    from options_researcher import live_quotes

    now_ny = datetime.now(ZoneInfo(live_quotes.NY_TZ))
    if live_quotes.in_regular_session(now_ny):
        probe = live_quotes.run_probe(client=SchwabMarketData(options_api_client), now_ny=now_ny)
        print(f"✓ options-validator: live quote/option schema probe passed for {probe['ny_date']}")
    else:
        print(
            "\nOAuth is complete. The live schema probe requires an open NYSE "
            "session; run this once between 09:30 and 16:00 ET:\n"
            "  uv run python -m options_researcher.live_quotes --probe"
        )

    print("\nSetup complete. Trading remains disabled in both repositories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
