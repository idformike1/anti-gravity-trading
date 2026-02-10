import asyncio
import json
import websockets
from typing import Optional, List
from core.types import MarketData, Instrument
from datetime import datetime

class UpstoxMarketData:
    """
    WebSocket Ingester for Upstox Feed.
    Normalizes data and updates state.
    """
    WS_URL = "wss://api.upstox.com/v2/feed/market-data-feed"

    def __init__(self, state_manager, access_token: str):
        self._state_manager = state_manager
        self._access_token = access_token
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False

    async def start(self, instrument_tokens: List[str]):
        self._running = True
        async for websocket in websockets.connect(
            self.WS_URL,
            extra_headers={"Authorization": f"Bearer {self._access_token}"}
        ):
            try:
                self._ws = websocket
                # Upstox specific subscription payload
                subscribe_payload = {
                    "guid": "guid",
                    "method": "sub",
                    "data": {
                        "mode": "full",
                        "instrument_tokens": instrument_tokens
                    }
                }
                await websocket.send(json.dumps(subscribe_payload))

                async for message in websocket:
                    await self._handle_message(message)
                    if not self._running:
                        break
            except websockets.ConnectionClosed:
                if not self._running:
                    break
                await asyncio.sleep(1) # Reconnect delay
                continue

    async def _handle_message(self, message: bytes):
        # Decode and normalize Upstox Protobuf/JSON data
        # (Simplified to JSON for this implementation)
        try:
            data = json.loads(message)
            if "feeds" in data:
                for token, feed in data["feeds"].items():
                    # Extract last price, bid, ask etc.
                    lp = feed.get("ff", {}).get("market_ff", {}).get("ltpc", {}).get("lcp")
                    if lp:
                        # Find symbol for token in state (assuming pre-mapped)
                        # For now, using token as symbol placeholder or lookup
                        market_data = MarketData(
                            instrument=Instrument(symbol=token, exchange="NSE", token=token),
                            last_price=float(lp),
                            timestamp=datetime.now()
                        )
                        await self._state_manager.update_market_data(token, market_data)
        except Exception as e:
            print(f"Error parsing market data: {e}")

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
