from abc import ABC, abstractmethod
from typing import List, Optional
from core.types import OrderIntent, BrokerOrder, Position, Instrument, OrderStatus, OrderSide

class BaseBroker(ABC):
    """
    Mandatory abstraction for all brokers (Upstox, Paper, etc.)
    """
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def place_order(self, intent: OrderIntent) -> BrokerOrder:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        pass

    @abstractmethod
    async def get_funds(self) -> dict:
        pass

    @abstractmethod
    async def get_order_details(self, order_id: str) -> Optional[BrokerOrder]:
        pass
