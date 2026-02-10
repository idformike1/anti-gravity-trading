from typing import List, Tuple, Optional
from risk.rules import RiskRule
from core.types import OrderIntent, SystemState
from core.events import EventBus, EventType

class RiskEngine:
    """
    Synchronous risk validator.
    All OrderIntents must pass through here.
    """
    def __init__(self, state_manager, event_bus: EventBus):
        self._state_manager = state_manager
        self._event_bus = event_bus
        self._rules: List[RiskRule] = []

    def add_rule(self, rule: RiskRule):
        self._rules.append(rule)

    async def validate_intent(self, intent: OrderIntent) -> Tuple[bool, Optional[str]]:
        state = self._state_manager.state
        
        for rule in self._rules:
            approved, reason = rule.validate(intent, state)
            if not approved:
                await self._event_bus.emit(EventType.RISK_RESULT, {
                    "intent_id": intent.intent_id,
                    "approved": False,
                    "reason": reason
                })
                await self._state_manager.add_audit_log({
                    "action": "RISK_REJECTED",
                    "intent_id": intent.intent_id,
                    "reason": reason
                })
                return False, reason

        await self._event_bus.emit(EventType.RISK_RESULT, {
            "intent_id": intent.intent_id,
            "approved": True,
            "reason": "Passed all risk checks"
        })
        return True, None
