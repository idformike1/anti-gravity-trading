import asyncio
import uuid
from typing import Dict, Optional
from core.types import OrderIntent, BrokerOrder, OrderStatus, SystemState
from core.events import EventBus, EventType
from brokers.base import BaseBroker

class ExecutionOrchestrator:
    """
    Handles Order Lifecycle and Broker Reconciliation.
    Strictly follows allowed state transitions.
    Uses intent_id as the primary link for idempotency.
    """
    def __init__(self, state_manager, event_bus: EventBus, broker: BaseBroker):
        self._state_manager = state_manager
        self._event_bus = event_bus
        self._broker = broker

    async def execute_approved_intent(self, intent_id: str):
        state = self._state_manager.state
        
        # Idempotency check against State Manager
        if intent_id in state.execution_log:
            # Already being processed or processed
            return

        intent = state.intents.get(intent_id)
        if not intent:
            return

        client_order_id = f"ag_{intent_id}"
        
        # Record execution intent in State for persistence and replay safety
        await self._state_manager.update_execution_log(intent_id, client_order_id)

        try:
            # Transition state to PLACING
            placeholder_order = BrokerOrder(
                client_order_id=client_order_id,
                intent_id=intent_id,
                instrument=intent.instrument,
                side=intent.side,
                quantity=intent.quantity,
                status=OrderStatus.PLACING
            )
            await self._state_manager.update_broker_order(client_order_id, placeholder_order)

            # Call Broker
            broker_order = await self._broker.place_order(intent)
            
            # Update state with real broker order details
            broker_order.client_order_id = client_order_id # Ensure mapping
            await self._state_manager.update_broker_order(client_order_id, broker_order)
            
            await self._event_bus.emit(EventType.ORDER_PLACED, broker_order)
            await self._state_manager.add_audit_log({
                "action": "ORDER_PLACED",
                "client_order_id": client_order_id,
                "broker_order_id": broker_order.order_id
            })

        except Exception as e:
            # Handle Failure
            error_order = placeholder_order.model_copy()
            error_order.status = OrderStatus.FAILED
            error_order.broker_message = str(e)
            await self._state_manager.update_broker_order(client_order_id, error_order)
            
            await self._state_manager.add_audit_log({
                "action": "ORDER_FAILED",
                "intent_id": intent_id,
                "error": str(e)
            })

    async def handle_broker_update(self, broker_update: BrokerOrder):
        """Reconciliation from Broker WebSocket/Polling"""
        # Ensure it exists in state
        await self._state_manager.update_broker_order(broker_update.client_order_id, broker_update)
        await self._event_bus.emit(EventType.ORDER_UPDATED, broker_update)
        
        if broker_update.status == OrderStatus.FILLED:
            await self._event_bus.emit(EventType.TRADE_EXECUTED, broker_update)
            # Logic for position update would go here or in a separate position manager
