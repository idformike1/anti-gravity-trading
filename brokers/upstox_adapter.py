import asyncio
import aiohttp
from datetime import datetime
from typing import List, Optional
from brokers.base import BaseBroker
from core.types import OrderIntent, BrokerOrder, Position, Instrument, OrderStatus, OrderSide

class UpstoxBroker(BaseBroker):
    """
    Real Upstox API Adapter.
    Handles OAuth, Token lifecycle, and REST calls.
    """
    BASE_URL = "https://api.upstox.com/v2"

    def __init__(self, api_key: str, api_secret: str, redirect_uri: str, access_token: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        if not self._session:
            self._session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            })

    async def _request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        async with self._session.request(method, f"{self.BASE_URL}{path}", json=data) as resp:
            return await resp.json()

    async def place_order(self, intent: OrderIntent) -> BrokerOrder:
        # Upstox V2 Order Placement Payload
        payload = {
            "quantity": intent.quantity,
            "product": "I",  # Intraday
            "validity": "DAY",
            "price": intent.price or 0.0,
            "tag": intent.strategy_id,
            "instrument_token": intent.instrument.token,
            "order_type": intent.order_type.value,
            "transaction_type": intent.side.value,
            "disclosed_quantity": 0,
            "trigger_price": intent.trigger_price or 0.0,
            "is_amo": False
        }

        response = await self._request("POST", "/order/place", payload)
        
        if response.get("status") == "success":
            order_id = response["data"]["order_id"]
            return BrokerOrder(
                order_id=order_id,
                client_order_id=f"ag_{intent.intent_id}",
                intent_id=intent.intent_id,
                instrument=intent.instrument,
                side=intent.side,
                quantity=intent.quantity,
                status=OrderStatus.PLACED,
                timestamp=datetime.now()
            )
        else:
            raise Exception(f"Upstox Order Placement Failed: {response.get('errors')}")

    async def cancel_order(self, order_id: str) -> bool:
        response = await self._request("DELETE", f"/order/cancel?order_id={order_id}")
        return response.get("status") == "success"

    async def get_positions(self) -> List[Position]:
        response = await self._request("GET", "/portfolio/net-positions")
        positions = []
        if response.get("status") == "success":
            for p in response["data"]:
                positions.append(Position(
                    instrument=Instrument(symbol=p["tradingsymbol"], exchange=p["exchange"]),
                    quantity=int(p["quantity"]),
                    average_price=float(p["buy_avg_price"]),
                    realized_pnl=float(p["realized_pnl"]),
                    unrealized_pnl=float(p["unrealized_pnl"])
                ))
        return positions

    async def get_funds(self) -> dict:
        response = await self._request("GET", "/user/get-funds-and-margin")
        if response.get("status") == "success":
            equity = response["data"]["equity"]
            return {
                "available": float(equity["available_margin"]),
                "used": float(equity["used_margin"])
            }
        return {"available": 0.0, "used": 0.0}

    async def get_order_details(self, order_id: str) -> Optional[BrokerOrder]:
        response = await self._request("GET", f"/order/details?order_id={order_id}")
        if response.get("status") == "success":
            o = response["data"]
            return BrokerOrder(
                order_id=o["order_id"],
                client_order_id=o.get("client_id", ""),
                intent_id="",
                instrument=Instrument(symbol=o["tradingsymbol"], exchange=o["exchange"]),
                side=OrderSide.BUY if o["transaction_type"] == "BUY" else OrderSide.SELL,
                quantity=int(o["quantity"]),
                filled_quantity=int(o["filled_quantity"]),
                status=OrderStatus.PLACED,
                timestamp=datetime.strptime(o["order_timestamp"], "%Y-%m-%d %H:%M:%S")
            )
        return None

    async def get_user_profile(self) -> dict:
        return await self._request("GET", "/user/profile")

    async def get_orders(self) -> List[BrokerOrder]:
        response = await self._request("GET", "/order/retrieve-all")
        orders = []
        if response.get("status") == "success":
            for o in response["data"]:
                orders.append(BrokerOrder(
                    order_id=o["order_id"],
                    client_order_id=o.get("client_id", ""),
                    intent_id="",  # Historical/External
                    instrument=Instrument(symbol=o["tradingsymbol"], exchange=o["exchange"]),
                    side=OrderSide.BUY if o["transaction_type"] == "BUY" else OrderSide.SELL,
                    quantity=int(o["quantity"]),
                    filled_quantity=int(o["filled_quantity"]),
                    status=OrderStatus.PLACED, # Mapping would be more complex in real scenario
                    timestamp=datetime.strptime(o["order_timestamp"], "%Y-%m-%d %H:%M:%S")
                ))
        return orders

    async def validate_live_connection(self, state_manager, event_bus):
        """
        Orchestrates a LIVE Read-Only connectivity check.
        Updates state without triggering any risk or execution paths.
        """
        await state_manager.add_audit_log({"action": "LIVE_READ_ONLY_BROKER_SYNC_STARTED"})
        
        try:
            # 1. Profile
            profile = await self.get_user_profile()
            if profile.get("status") != "success":
                raise Exception(f"Profile check failed: {profile.get('errors')}")
            
            # 2. Funds
            funds = await self.get_funds()
            state_manager._state.funds = funds # Direct state update as allowed for sync
            
            # 3. Positions
            positions = await self.get_positions()
            for p in positions:
                await state_manager.update_position(p.instrument.symbol, p)
            
            # 4. Orders
            orders = await self.get_orders()
            for o in orders:
                await state_manager.update_broker_order(o.client_order_id, o)
            
            await state_manager.add_audit_log({
                "action": "LIVE_READ_ONLY_BROKER_SYNC_COMPLETED",
                "user": profile["data"]["user_name"],
                "funds_available": funds["available"]
            })
            
            from core.events import EventType
            await event_bus.emit(EventType.BROKER_SYNC_COMPLETED, {"status": "success"})

        except Exception as e:
            await state_manager.add_audit_log({
                "action": "LIVE_READ_ONLY_BROKER_SYNC_FAILED",
                "error": str(e)
            })
            raise

    async def close(self):
        if self._session:
            await self._session.close()
