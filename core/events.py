import asyncio
from typing import Dict, List, Any, Callable, Awaitable
from enum import Enum

class EventType(str, Enum):
    # Market Facts
    TICK_RECEIVED = "TICK_RECEIVED"
    
    # Strategy Facts (Decisions)
    INTENT_EMITTED = "INTENT_EMITTED"
    
    # Risk Facts
    RISK_RESULT = "RISK_RESULT"
    
    # Execution Facts
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_UPDATED = "ORDER_UPDATED"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    
    # System Facts
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"
    MODE_CHANGED = "MODE_CHANGED"
    BROKER_SYNC_COMPLETED = "BROKER_SYNC_COMPLETED"

class EventBus:
    """
    Async Event Bus for factual communication.
    Events are facts: something happened.
    """
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable[[Any], Awaitable[None]]]] = {
            et: [] for et in EventType
        }

    def subscribe(self, event_type: EventType, callback: Callable[[Any], Awaitable[None]]):
        self._subscribers[event_type].append(callback)

    async def emit(self, event_type: EventType, data: Any):
        """Emits an event to all subscribers."""
        if event_type not in self._subscribers:
            return
            
        tasks = [callback(data) for callback in self._subscribers[event_type]]
        if tasks:
            # We don't await gather here to let emitters continue immediately
            # Use asyncio.create_task for fire-and-forget or task management
            for task in tasks:
                asyncio.create_task(self._safe_execute(task, event_type))

    async def _safe_execute(self, coro: Awaitable[None], event_type: EventType):
        try:
            await coro
        except Exception as e:
            # TODO: Integrate with global logger
            print(f"Error handling event {event_type}: {e}")
