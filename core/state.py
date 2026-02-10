import asyncio
import copy
from datetime import datetime
from typing import Any, Dict, List, Callable, Awaitable
from .types import SystemState, RunMode
import json

class StateManager:
    """
    Central Authority for System State.
    Enforces that all mutations go through managed methods.
    Emits events on mutation.
    """
    def __init__(self, initial_mode: RunMode = RunMode.PAPER):
        self._state = SystemState(mode=initial_mode)
        self._lock = asyncio.Lock()
        self._listeners: List[Callable[[str, Any], Awaitable[None]]] = []

    @property
    def state(self) -> SystemState:
        """Returns a read-only snapshot/copy of the current state."""
        return self._state.model_copy(deep=True)

    def subscribe(self, listener: Callable[[str, Any], Awaitable[None]]):
        self._listeners.append(listener)

    async def _emit_change(self, change_type: str, data: Any):
        tasks = [l(change_type, data) for l in self._listeners]
        if tasks:
            await asyncio.gather(*tasks)

    async def update_market_data(self, symbol: str, data: Any):
        async with self._lock:
            self._state.market_data[symbol] = data
            self._state.last_update = datetime.now()
        await self._emit_change("MARKET_DATA_UPDATE", {"symbol": symbol, "data": data})

    async def update_order_intent(self, intent_id: str, intent: Any):
        async with self._lock:
            self._state.intents[intent_id] = intent
            self._state.last_update = datetime.now()
        await self._emit_change("ORDER_INTENT_UPDATE", intent)

    async def update_broker_order(self, client_order_id: str, order: Any):
        async with self._lock:
            self._state.orders[client_order_id] = order
            self._state.last_update = datetime.now()
        await self._emit_change("BROKER_ORDER_UPDATE", order)

    async def update_position(self, symbol: str, position: Any):
        async with self._lock:
            self._state.positions[symbol] = position
            self._state.last_update = datetime.now()
        await self._emit_change("POSITION_UPDATE", position)

    async def set_kill_switch(self, active: bool):
        async with self._lock:
            self._state.kill_switch = active
            self._state.last_update = datetime.now()
        await self._emit_change("KILL_SWITCH_CHANGE", {"active": active})

    async def set_mode(self, mode: RunMode):
        async with self._lock:
            self._state.mode = mode
            self._state.last_update = datetime.now()
        await self._emit_change("MODE_CHANGE", {"mode": mode})

    async def update_execution_log(self, intent_id: str, client_order_id: str):
        async with self._lock:
            self._state.execution_log[intent_id] = client_order_id
            self._state.last_update = datetime.now()
        await self._emit_change("EXECUTION_LOG_UPDATE", {"intent_id": intent_id, "client_order_id": client_order_id})

    async def add_audit_log(self, entry: Dict[str, Any]):
        async with self._lock:
            self._state.audit_trail.append({
                "timestamp": datetime.now().isoformat(),
                **entry
            })
            # No event emission for every log to avoid loop overhead, 
            # unless specifically needed.

    def get_snapshot(self) -> str:
        """Returns JSON representation of state for persistence/replay."""
        return self._state.model_dump_json()

    async def load_snapshot(self, snapshot_json: str):
        """Loads state from a snapshot (used in REPLAY)."""
        async with self._lock:
            self._state = SystemState.model_validate_json(snapshot_json)
            await self._emit_change("STATE_RELOADED", self._state)
