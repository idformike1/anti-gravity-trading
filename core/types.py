from enum import Enum
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class RunMode(str, Enum):
    LIVE = "LIVE"
    PAPER = "PAPER"
    REPLAY = "REPLAY"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class OrderStatus(str, Enum):
    INTENT = "INTENT"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    PLACING = "PLACING"
    PLACED = "PLACED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class Instrument(BaseModel):
    symbol: str
    exchange: str  # NSE, BSE, MCX
    token: Optional[str] = None
    expiry: Optional[datetime] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # CE, PE

class OrderIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str
    instrument: Instrument
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    reason: str
    timestamp: datetime = Field(default_factory=datetime.now)

class BrokerOrder(BaseModel):
    order_id: Optional[str] = None  # Broker provided ID
    client_order_id: str  # Idempotency key
    intent_id: str
    instrument: Instrument
    side: OrderSide
    quantity: int
    filled_quantity: int = 0
    average_price: float = 0.0
    status: OrderStatus
    broker_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class Position(BaseModel):
    instrument: Instrument
    quantity: int
    average_price: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

class Trade(BaseModel):
    trade_id: str
    order_id: str
    instrument: Instrument
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime

class MarketData(BaseModel):
    instrument: Instrument
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: datetime

class SystemState(BaseModel):
    mode: RunMode = RunMode.PAPER
    kill_switch: bool = False
    last_update: datetime = Field(default_factory=datetime.now)
    market_data: Dict[str, MarketData] = {}  # symbol -> data
    intents: Dict[str, OrderIntent] = {}
    orders: Dict[str, BrokerOrder] = {}
    positions: Dict[str, Position] = {}
    funds: Dict[str, float] = {"available": 0.0, "used": 0.0}
    risk_metrics: Dict[str, Any] = {}
    execution_log: Dict[str, str] = {}  # intent_id -> client_order_id
    audit_trail: List[Dict[str, Any]] = []
