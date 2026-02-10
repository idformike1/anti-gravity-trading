from typing import List, Optional
from core.types import SystemState, OrderIntent, OrderSide, OrderType, Instrument, RunMode
from strategy.engine import BaseStrategy

class SessionBreakoutStrategy(BaseStrategy):
    """
    Session Breakout Strategy.
    Trades breakouts of the established session range.
    Internal state is used to track range and position.
    """
    def __init__(self, strategy_id: str, instrument: Instrument):
        super().__init__(strategy_id)
        self.instrument = instrument
        self.session_high: Optional[float] = None
        self.session_low: Optional[float] = None
        self.current_position: str = "FLAT"  # FLAT, LONG, SHORT

    async def on_state_update(self, state: SystemState) -> List[OrderIntent]:
        # Rule: PAPER or REPLAY mode only
        if state.mode not in [RunMode.PAPER, RunMode.REPLAY, RunMode.LIVE]:
            return []

        # Get latest price for our instrument
        symbol = self.instrument.symbol
        if symbol not in state.market_data:
            return []
        
        price = state.market_data[symbol].last_price
        intents = []

        # 1. Trading Logic (Check first before updating range)
        if self.session_high is not None and self.session_low is not None:
            if self.current_position == "FLAT":
                if price > self.session_high:
                    intents.append(self._create_intent(OrderSide.BUY, f"BUY: Breakout above session high {self.session_high}"))
                    self.current_position = "LONG"
                elif price < self.session_low:
                    intents.append(self._create_intent(OrderSide.SELL, f"SELL: Breakout below session low {self.session_low}"))
                    self.current_position = "SHORT"
            
            elif self.current_position == "LONG":
                if price < self.session_low:
                    # Exit Long
                    intents.append(self._create_intent(OrderSide.SELL, f"EXIT LONG: Price {price} broke session low {self.session_low}"))
                    # Enter Short
                    intents.append(self._create_intent(OrderSide.SELL, f"REVERSE SHORT: Session range flip"))
                    self.current_position = "SHORT"
            
            elif self.current_position == "SHORT":
                if price > self.session_high:
                    # Exit Short
                    intents.append(self._create_intent(OrderSide.BUY, f"EXIT SHORT: Price {price} broke session high {self.session_high}"))
                    # Enter Long
                    intents.append(self._create_intent(OrderSide.BUY, f"REVERSE LONG: Session range flip"))
                    self.current_position = "LONG"

        # 2. Update session high/low for establishing range
        if self.session_high is None or price > self.session_high:
            self.session_high = price
        if self.session_low is None or price < self.session_low:
            self.session_low = price
            
        return intents

    def _create_intent(self, side: OrderSide, reason: str) -> OrderIntent:
        return OrderIntent(
            strategy_id=self.strategy_id,
            instrument=self.instrument,
            side=side,
            quantity=1,
            order_type=OrderType.MARKET,
            reason=reason
        )
