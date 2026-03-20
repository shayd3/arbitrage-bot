import base64
import json
import time
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from backend.config import settings
from backend.metrics import kalshi_api_latency_seconds
from backend.models import KalshiMarket


class KalshiAuthError(Exception):
    pass


def _dollars_to_cents(val) -> int | None:
    """Convert Kalshi dollar string (e.g. '0.8100') to cents int (81)."""
    if val is None:
        return None
    try:
        return round(float(val) * 100)
    except (ValueError, TypeError):
        return None


def _fp_to_int(val) -> int | None:
    """Convert Kalshi fixed-point string (e.g. '73774.00') to int."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _parse_market(m: dict) -> KalshiMarket:
    return KalshiMarket(
        ticker=m["ticker"],
        title=m.get("title", ""),
        status=m.get("status", ""),
        yes_bid=_dollars_to_cents(m.get("yes_bid_dollars") or m.get("yes_bid")),
        yes_ask=_dollars_to_cents(m.get("yes_ask_dollars") or m.get("yes_ask")),
        no_bid=_dollars_to_cents(m.get("no_bid_dollars") or m.get("no_bid")),
        no_ask=_dollars_to_cents(m.get("no_ask_dollars") or m.get("no_ask")),
        volume=_fp_to_int(m.get("volume_fp") or m.get("volume")),
        open_interest=_fp_to_int(m.get("open_interest_fp") or m.get("open_interest")),
        close_time=m.get("close_time"),
        result=m.get("result"),
    )


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
        # Kalshi signs only timestamp+method+path — body is NOT included in signature
        body_str = ""
        if "json" in kwargs:
            body_str = json.dumps(kwargs.pop("json"), separators=(",", ":"))
        auth_headers = self._sign_request(method, path, body="")
        headers = {**auth_headers, "Content-Type": "application/json"}
        # Strip leading path segment for a clean label (e.g. "/portfolio/balance" → "portfolio_balance")
        endpoint_label = path.strip("/").replace("/", "_")
        t0 = time.perf_counter()
        response = await client.request(
            method,
            path,
            headers=headers,
            content=body_str.encode("utf-8") if body_str else None,
            **kwargs,
        )
        kalshi_api_latency_seconds.labels(endpoint=endpoint_label).observe(time.perf_counter() - t0)
        response.raise_for_status()
        return response.json()

    async def get_balance(self) -> int:
        """Returns available balance in cents."""
        data = await self._request("GET", "/portfolio/balance")
        return int(data.get("balance", 0))

    async def get_markets(
        self, status: str = "open", limit: int = 100, cursor: str = "", series_ticker: str = ""
    ) -> list[KalshiMarket]:
        """Fetch open markets, optionally filtered."""
        params = {"status": status, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        if series_ticker:
            params["series_ticker"] = series_ticker
        data = await self._request("GET", "/markets", params=params)
        return [_parse_market(m) for m in data.get("markets", [])]

    async def get_market(self, ticker: str) -> KalshiMarket | None:
        try:
            data = await self._request("GET", f"/markets/{ticker}")
            m = data.get("market", {})
            return _parse_market(m)
        except httpx.HTTPStatusError:
            return None

    async def get_orderbook(self, ticker: str) -> dict:
        data = await self._request("GET", f"/markets/{ticker}/orderbook")
        return data.get("orderbook", {})

    async def create_order(
        self, ticker: str, side: str, count: int, price: int, order_type: str = "limit"
    ) -> dict:
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
            "time_in_force": "fill_or_kill",
        }
        data = await self._request("POST", "/portfolio/orders", json=body)
        return data.get("order", {})

    async def get_orders(self, status: str = "", limit: int = 100) -> list[dict]:
        """Fetch portfolio orders. status: 'resting', 'filled', 'canceled', or '' for all."""
        params: dict = {"limit": limit}
        if status:
            params["status"] = status
        data = await self._request("GET", "/portfolio/orders", params=params)
        return data.get("orders", [])

    async def get_settlements(self, limit: int = 100) -> list[dict]:
        """Fetch portfolio settlement events from /portfolio/settlements."""
        data = await self._request("GET", "/portfolio/settlements", params={"limit": limit})
        return data.get("settlements", [])

    async def get_positions(self) -> list[dict]:
        data = await self._request("GET", "/portfolio/positions")
        return data.get("market_positions", [])

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
kalshi_client = KalshiClient()
