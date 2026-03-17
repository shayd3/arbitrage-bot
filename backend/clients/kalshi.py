import httpx
import base64
import hashlib
import time
import json
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime
from backend.config import settings
from backend.models import KalshiMarket

class KalshiAuthError(Exception):
    pass

class KalshiClient:
    def __init__(self):
        self.base_url = settings.kalshi_base_url
        self.api_key_id = settings.kalshi_api_key_id
        self._private_key = None
        self._client: httpx.AsyncClient | None = None

    def _load_private_key(self):
        if self._private_key is not None:
            return
        key_path = Path(settings.kalshi_private_key_path)
        if not key_path.exists():
            raise KalshiAuthError(f"Private key not found at {key_path}")
        pem_data = key_path.read_bytes()
        self._private_key = serialization.load_pem_private_key(pem_data, password=None)

    def _sign_request(self, method: str, path: str, body: str = "") -> dict:
        """Generate RSA-PSS signature headers for Kalshi API."""
        self._load_private_key()
        timestamp_ms = str(int(time.time() * 1000))
        # Kalshi signs the full path (e.g. /trade-api/v2/portfolio/balance), not just the relative path
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        full_path = parsed.path.rstrip("/") + path
        message = timestamp_ms + method.upper() + full_path + body
        signature = self._private_key.sign(
            message.encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("utf-8"),
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._get_client()
        body = ""
        if kwargs.get("json"):
            body = json.dumps(kwargs["json"])
        auth_headers = self._sign_request(method, path, body)
        response = await client.request(
            method, path,
            headers=auth_headers,
            **kwargs
        )
        response.raise_for_status()
        return response.json()

    async def get_balance(self) -> dict:
        """Returns available balance in cents."""
        data = await self._request("GET", "/portfolio/balance")
        return data.get("balance", {})

    async def get_markets(self, status: str = "open", limit: int = 100, cursor: str = "") -> list[KalshiMarket]:
        """Fetch open markets, optionally filtered."""
        params = {"status": status, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = await self._request("GET", "/markets", params=params)
        markets = []
        for m in data.get("markets", []):
            markets.append(KalshiMarket(
                ticker=m["ticker"],
                title=m.get("title", ""),
                status=m.get("status", ""),
                yes_bid=m.get("yes_bid"),
                yes_ask=m.get("yes_ask"),
                no_bid=m.get("no_bid"),
                no_ask=m.get("no_ask"),
                volume=m.get("volume"),
                open_interest=m.get("open_interest"),
                close_time=m.get("close_time"),
            ))
        return markets

    async def get_market(self, ticker: str) -> KalshiMarket | None:
        try:
            data = await self._request("GET", f"/markets/{ticker}")
            m = data.get("market", {})
            return KalshiMarket(
                ticker=m["ticker"],
                title=m.get("title", ""),
                status=m.get("status", ""),
                yes_bid=m.get("yes_bid"),
                yes_ask=m.get("yes_ask"),
                no_bid=m.get("no_bid"),
                no_ask=m.get("no_ask"),
                volume=m.get("volume"),
                open_interest=m.get("open_interest"),
                close_time=m.get("close_time"),
            )
        except httpx.HTTPStatusError:
            return None

    async def get_orderbook(self, ticker: str) -> dict:
        data = await self._request("GET", f"/markets/{ticker}/orderbook")
        return data.get("orderbook", {})

    async def create_order(self, ticker: str, side: str, count: int, price: int, order_type: str = "limit") -> dict:
        """
        Place an order.
        side: "yes" or "no"
        count: number of contracts
        price: price in cents (1-99)
        order_type: "limit" or "market"; use "limit" with IOC action
        """
        body = {
            "ticker": ticker,
            "action": "buy",
            "side": side,
            "count": count,
            "type": order_type,
            "yes_price": price if side == "yes" else 100 - price,
            "time_in_force": "ioc",  # immediate-or-cancel
        }
        data = await self._request("POST", "/portfolio/orders", json=body)
        return data.get("order", {})

    async def get_positions(self) -> list[dict]:
        data = await self._request("GET", "/portfolio/positions")
        return data.get("market_positions", [])

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

# Singleton
kalshi_client = KalshiClient()
