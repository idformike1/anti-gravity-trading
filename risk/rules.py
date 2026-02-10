from abc import ABC, abstractmethod
from typing import Tuple, Optional
from core.types import OrderIntent, SystemState

class RiskRule(ABC):
    @abstractmethod
    def validate(self, intent: OrderIntent, state: SystemState) -> Tuple[bool, Optional[str]]:
        """Returns (approved, reason)"""
        pass

class MaxLossRule(RiskRule):
    def __init__(self, max_loss: float):
        self.max_loss = max_loss

    def validate(self, intent: OrderIntent, state: SystemState) -> Tuple[bool, Optional[str]]:
        total_pnl = sum(p.realized_pnl + p.unrealized_pnl for p in state.positions.values())
        if total_pnl <= -self.max_loss:
            return False, f"Max loss breach: {total_pnl} <= -{self.max_loss}"
        return True, None

class MaxQuantityRule(RiskRule):
    def __init__(self, max_qty: int):
        self.max_qty = max_qty

    def validate(self, intent: OrderIntent, state: SystemState) -> Tuple[bool, Optional[str]]:
        if intent.quantity > self.max_qty:
            return False, f"Quantity {intent.quantity} exceeds limit {self.max_qty}"
        return True, None

class KillSwitchRule(RiskRule):
    def validate(self, intent: OrderIntent, state: SystemState) -> Tuple[bool, Optional[str]]:
        if state.kill_switch:
            return False, "Kill switch is active"
        return True, None

class DuplicateOrderRule(RiskRule):
    def validate(self, intent: OrderIntent, state: SystemState) -> Tuple[bool, Optional[str]]:
        # Check if an intent with same instrument and side was emitted in the last 1 second
        # (Very simple example of duplicate prevention)
        for existing in state.intents.values():
            if (existing.instrument.symbol == intent.instrument.symbol and 
                existing.side == intent.side and 
                (intent.timestamp - existing.timestamp).total_seconds() < 1 and
                existing.intent_id != intent.intent_id):
                return False, "Potential duplicate order detected"
        return True, None

class LiveReadOnlyRule(RiskRule):
    def validate(self, intent: OrderIntent, state: SystemState) -> Tuple[bool, Optional[str]]:
        return False, "LIVE_READ_ONLY_MODE_ACTIVE"
