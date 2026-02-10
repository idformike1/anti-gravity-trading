from abc import ABC, abstractmethod
from typing import List, Optional
from core.types import SystemState, OrderIntent

class BaseStrategy(ABC):
    """
    Stateless Strategy Interface.
    Decides based on full system state.
    """
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id

    @abstractmethod
    async def on_state_update(self, state: SystemState) -> List[OrderIntent]:
        """
        React to state change and return desired intents.
        Strategies should be pure functions of state -> [Intent].
        """
        return []

class StrategyEngine:
    """
    Orchestrates multiple strategies.
    Triggers strategies on state changes.
    """
    def __init__(self, state_manager, event_bus):
        self._state_manager = state_manager
        self._event_bus = event_bus
        self._strategies: List[BaseStrategy] = []

    def register_strategy(self, strategy: BaseStrategy):
        self._strategies.append(strategy)

    async def pulse(self):
        """
        Called on periodic interval or state change.
        Drives strategy logic.
        """
        state = self._state_manager.state
        for strategy in self._strategies:
            intents = await strategy.on_state_update(state)
            for intent in intents:
                await self._process_intent(intent)

    async def _process_intent(self, intent: OrderIntent):
        # 1. Update State Store with new intent
        await self._state_manager.update_order_intent(intent.intent_id, intent)
        from core.events import EventType
        await self._event_bus.emit(EventType.INTENT_EMITTED, intent)
