"""Secure read-only Schwab Trader API scaffold.

There are intentionally no order, replacement, cancel, exercise, transfer, or
money-movement methods in this module.
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping, Protocol
from urllib.parse import urlencode

from market_data.models import (
    DataTiming,
    OptionQuote,
    ProviderHealth,
    ProviderResponse,
    normalize_option_symbol,
    parse_option_symbol,
)
from market_data.providers.base import (
    ProviderBase,
    as_float,
    as_int,
    payload_dict,
    quote_from_fields,
    utc_now,
)
from market_data.transport import (
    DiskResponseCache,
    HttpFormTransport,
    HttpJsonTransport,
    JsonTransport,
    ProviderError,
    RateLimiter,
)


@dataclass(frozen=True)
class SchwabTokens:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    retrieved_at: str | None = None


class TokenStore(Protocol):
    def load(self) -> SchwabTokens | None: ...

    def save(self, tokens: SchwabTokens) -> None: ...


class FileTokenStore:
    """Repo-local, mode-0600 token storage with a hard path boundary."""

    def __init__(
        self,
        *,
        project_root: Path | str = ".",
        relative_path: str = ".secrets/schwab_tokens.json",
    ) -> None:
        root = Path(project_root).resolve()
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Schwab token path must remain inside PROJECT_ROOT")
        self.path = path

    def load(self) -> SchwabTokens | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            access_token = raw.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise ValueError("access_token missing")
            return SchwabTokens(
                access_token=access_token,
                refresh_token=raw.get("refresh_token"),
                expires_in=raw.get("expires_in"),
                retrieved_at=raw.get("retrieved_at"),
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError("invalid local Schwab token file") from exc

    def save(self, tokens: SchwabTokens) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    "access_token": tokens.access_token,
                    "refresh_token": tokens.refresh_token,
                    "expires_in": tokens.expires_in,
                    "retrieved_at": tokens.retrieved_at,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temp.chmod(0o600)
        temp.replace(self.path)
        self.path.chmod(0o600)


class SchwabReadOnlyProvider(ProviderBase):
    name = "schwab"
    oauth_authorize_url = "https://api.schwabapi.com/v1/oauth/authorize"
    oauth_token_url = "https://api.schwabapi.com/v1/oauth/token"
    api_base_url = "https://api.schwabapi.com"

    def __init__(
        self,
        *,
        app_key: str | None = None,
        app_secret: str | None = None,
        callback_url: str | None = None,
        account_hash: str | None = None,
        token_store: TokenStore | None = None,
        transport: JsonTransport | None = None,
        form_transport: HttpFormTransport | None = None,
    ) -> None:
        if transport is None:
            transport = HttpJsonTransport(
                cache=DiskResponseCache(".cache/market_data/schwab"),
                limiter=RateLimiter(120, 60.0),
            )
        super().__init__(transport)
        self._app_key = app_key or os.environ.get("SCHWAB_APP_KEY")
        self._app_secret = app_secret or os.environ.get("SCHWAB_APP_SECRET")
        self.callback_url = callback_url or os.environ.get("SCHWAB_CALLBACK_URL")
        self.account_hash = account_hash or os.environ.get("SCHWAB_ACCOUNT_HASH")
        self.token_store = token_store or FileTokenStore(project_root=Path.cwd())
        self.form_transport = form_transport or HttpFormTransport()

    def _tokens(self) -> SchwabTokens:
        tokens = self.token_store.load()
        if tokens is None:
            raise ProviderError("Schwab authorization is not complete; no local token is available")
        return tokens

    def authorization_url(self, state: str) -> str:
        if not self._app_key or not self.callback_url:
            raise ProviderError("SCHWAB_APP_KEY and SCHWAB_CALLBACK_URL are required")
        if not state:
            raise ValueError("OAuth state must not be empty")
        return f"{self.oauth_authorize_url}?{urlencode({'client_id': self._app_key, 'redirect_uri': self.callback_url, 'state': state})}"

    def exchange_authorization_code(self, code: str) -> SchwabTokens:
        if not self._app_key or not self._app_secret or not self.callback_url:
            raise ProviderError("Schwab app key, app secret, and callback URL are required")
        if not code:
            raise ValueError("authorization code must not be empty")
        basic = base64.b64encode(f"{self._app_key}:{self._app_secret}".encode()).decode()
        payload = payload_dict(
            self.form_transport.post_form(
                self.oauth_token_url,
                form={"grant_type": "authorization_code", "code": code, "redirect_uri": self.callback_url},
                headers={"Authorization": f"Basic {basic}"},
            ),
            provider=self.name,
        )
        tokens = self._tokens_from_payload(payload)
        self.token_store.save(tokens)
        return tokens

    def refresh_access_token(self) -> SchwabTokens:
        if not self._app_key or not self._app_secret:
            raise ProviderError("Schwab app key and app secret are required")
        current = self._tokens()
        if not current.refresh_token:
            raise ProviderError("Schwab refresh token is unavailable")
        basic = base64.b64encode(f"{self._app_key}:{self._app_secret}".encode()).decode()
        payload = payload_dict(
            self.form_transport.post_form(
                self.oauth_token_url,
                form={"grant_type": "refresh_token", "refresh_token": current.refresh_token},
                headers={"Authorization": f"Basic {basic}"},
            ),
            provider=self.name,
        )
        tokens = self._tokens_from_payload(payload)
        self.token_store.save(tokens)
        return tokens

    @staticmethod
    def _tokens_from_payload(payload: Mapping[str, object]) -> SchwabTokens:
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ProviderError("Schwab OAuth response did not contain an access token")
        refresh_token = payload.get("refresh_token")
        return SchwabTokens(
            access_token=access_token,
            refresh_token=refresh_token if isinstance(refresh_token, str) else None,
            expires_in=as_int(payload.get("expires_in")),
            retrieved_at=utc_now().isoformat(),
        )

    def _get(self, path: str, *, params: Mapping[str, object] | None = None) -> ProviderResponse:
        tokens = self._tokens()
        payload = payload_dict(
            self.transport.get_json(
                f"{self.api_base_url}{path}",
                params=params,
                headers={"Authorization": f"Bearer {tokens.access_token}"},
                cache_namespace=self.name,
            ),
            provider=self.name,
        )
        return ProviderResponse(
            provider=self.name,
            endpoint=path,
            payload=payload,
            retrieved_at=utc_now(),
            timing=DataTiming.REAL_TIME,
        )

    def health_check(self) -> ProviderHealth:
        missing = [name for name, value in (("SCHWAB_APP_KEY", self._app_key), ("SCHWAB_APP_SECRET", self._app_secret), ("SCHWAB_CALLBACK_URL", self.callback_url)) if not value]
        if missing:
            return self.missing_credentials(detail=f"missing {', '.join(missing)}")
        try:
            self._get("/trader/v1/accounts/accountNumbers")
        except ProviderError as exc:
            detail = str(exc)
            auth_status = "required" if "authorization is not complete" in detail else "unknown"
            return ProviderHealth(
                provider=self.name,
                connection_status="not_checked" if auth_status == "required" else "failed",
                authentication_status=auth_status,
                subscription_status="unknown",
                detail=detail,
            )
        return ProviderHealth(
            provider=self.name,
            connection_status="connected",
            authentication_status="accepted",
            subscription_status="read-only account data available",
            detail="account-number endpoint responded; no trading endpoint is implemented",
        )

    def get_account_numbers(self) -> ProviderResponse:
        return self._get("/trader/v1/accounts/accountNumbers")

    def get_account(self, account_hash: str | None = None) -> ProviderResponse:
        value = account_hash or self.account_hash
        if not value:
            raise ProviderError("SCHWAB_ACCOUNT_HASH is required for account retrieval")
        return self._get(f"/trader/v1/accounts/{value}", params={"fields": "positions"})

    def get_quote(self, symbol: str) -> ProviderResponse:
        return self._get(f"/marketdata/v1/{symbol.strip().upper()}/quotes")

    def get_option_chain(self, symbol: str, **params: object) -> list[OptionQuote]:
        response = self._get("/marketdata/v1/chains", params={"symbol": symbol.strip().upper(), **params})
        quotes: list[OptionQuote] = []
        for option_type, map_key in (("call", "callExpDateMap"), ("put", "putExpDateMap")):
            expiration_map = response.payload.get(map_key, {})
            if not isinstance(expiration_map, dict):
                continue
            for expiration_key, strike_map in expiration_map.items():
                expiration_text = str(expiration_key).split(":", 1)[0]
                try:
                    expiration = date.fromisoformat(expiration_text)
                except ValueError as exc:
                    raise ProviderError("Schwab returned an invalid option expiration") from exc
                if not isinstance(strike_map, dict):
                    continue
                for strike_text, contracts in strike_map.items():
                    if not isinstance(contracts, list):
                        continue
                    for contract in contracts:
                        if not isinstance(contract, dict):
                            continue
                        strike = as_float(contract.get("strikePrice", strike_text))
                        if strike is None:
                            raise ProviderError("Schwab returned an invalid option strike")
                        raw_contract_symbol = str(contract.get("symbol") or "")
                        try:
                            contract_symbol = parse_option_symbol(raw_contract_symbol).symbol
                        except ValueError:
                            contract_symbol = normalize_option_symbol(
                                symbol,
                                expiration,
                                "C" if option_type == "call" else "P",
                                strike,
                            )
                        quotes.append(
                            quote_from_fields(
                                provider=self.name,
                                symbol=contract_symbol,
                                underlying_symbol=symbol.strip().upper(),
                                option_type=option_type,
                                strike=strike,
                                expiration=expiration,
                                bid=contract.get("bid"),
                                ask=contract.get("ask"),
                                last_price=contract.get("last"),
                                volume=contract.get("totalVolume"),
                                open_interest=contract.get("openInterest"),
                                implied_volatility=contract.get("volatility"),
                                delta=contract.get("delta"),
                                gamma=contract.get("gamma"),
                                theta=contract.get("theta"),
                                vega=contract.get("vega"),
                                underlying_price=contract.get("underlyingPrice"),
                                quote_timestamp=contract.get("quoteTimeInLong"),
                                timing=DataTiming.REAL_TIME,
                            )
                        )
        return quotes
