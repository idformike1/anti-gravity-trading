import asyncio
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from brokers.base import BaseBroker
from core.types import OrderIntent, BrokerOrder, Position, Instrument, OrderStatus, OrderSide

class PaperBroker(BaseBroker):
    """
    Simulated Broker Adapter.
    Used for PAPER and REPLAY modes.
    Executes orders based on current market price in state if available, 
    otherwise assumes immediate fill.
    """
    def __init__(self, state_manager):
        self._state_manager = state_manager
        self._live_orders: Dict[str, BrokerOrder] = {}

    async def connect(self):
        # Simulated connection
        pass

    async def place_order(self, intent: OrderIntent) -> BrokerOrder:
        client_order_id = f"paper_{uuid.uuid4().hex[:8]}"
        
        # In Paper mode, we simulate immediate filling for Market orders
        # For Limit orders, we'd need a matching engine (omitted for brevity but simulated)
        
        order = BrokerOrder(
            order_id=f"broker_{uuid.uuid4().hex[:8]}",
            client_order_id=client_order_id,
            intent_id=intent.intent_id,
            instrument=intent.instrument,
            side=intent.side,
            quantity=intent.quantity,
            filled_quantity=intent.quantity, # Immediate full fill simulation
            average_price=0.0, # Will be set by market price if available
            status=OrderStatus.FILLED,
            timestamp=datetime.now()
        )

        # Try to get market price from state
        state = self._state_manager.state
        symbol = intent.instrument.symbol
        if symbol in state.market_data:
            order.average_price = state.market_data[symbol].last_price
        
        self._live_orders[order.order_id] = order
        return order

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self._live_orders:
            self._live_orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    async def get_positions(self) -> List[Position]:
        # Paper broker manages positions locally or syncs with state manager
        state = self._state_manager.state
        return list(state.positions.values())

    async def get_funds(self) -> dict:
        state = self._state_manager.state
        return state.funds

    async def get_order_details(self, order_id: str) -> Optional[BrokerOrder]:
        return self._live_orders.get(order_id)
