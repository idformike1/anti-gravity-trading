import asyncio
import os
import uvicorn

# Manual .env loader
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

load_env()

from datetime import datetime
from core.state import StateManager
from core.events import EventBus, EventType
from core.types import RunMode, Instrument
from brokers.paper_adapter import PaperBroker
from brokers.upstox_adapter import UpstoxBroker
from risk.engine import RiskEngine
from risk.rules import MaxLossRule, MaxQuantityRule, KillSwitchRule, DuplicateOrderRule, LiveReadOnlyRule
from market_data.upstox import UpstoxMarketData
from execution.orchestrator import ExecutionOrchestrator
from strategy.engine import StrategyEngine
from strategy.session_breakout import SessionBreakoutStrategy
from api import router
import safety.compliance
from safety.compliance import SafetyCompliance
from typing import Optional

# Surgical activation of safety layer (monkeypatch for missing asyncio in that module)
safety.compliance.asyncio = asyncio

class AntiGravitySystem:
    def __init__(self, mode: RunMode = RunMode.PAPER):
        self.state_manager = StateManager(initial_mode=mode)
        self.event_bus = EventBus()
        
        # 1. Initialize Broker
        if mode == RunMode.LIVE:
            # Requires real credentials
            self.broker = UpstoxBroker(
                api_key=os.getenv("UPSTOX_API_KEY", ""),
                api_secret=os.getenv("UPSTOX_API_SECRET", ""),
                redirect_uri=os.getenv("UPSTOX_REDIRECT", ""),
                access_token=os.getenv("UPSTOX_ACCESS_TOKEN", "")
            )
            self.market_data_provider = UpstoxMarketData(
                self.state_manager, 
                os.getenv("UPSTOX_ACCESS_TOKEN", "")
            )
        else:
            self.broker = PaperBroker(self.state_manager)
            self.market_data_provider = None

        # 2. Risk Engine
        self.risk_engine = RiskEngine(self.state_manager, self.event_bus)
        self.risk_engine.add_rule(KillSwitchRule())
        self.risk_engine.add_rule(MaxLossRule(max_loss=10000.0))
        self.risk_engine.add_rule(MaxQuantityRule(max_qty=500))
        self.risk_engine.add_rule(DuplicateOrderRule())
        
        if mode == RunMode.LIVE:
            self.risk_engine.add_rule(LiveReadOnlyRule())
            asyncio.create_task(self.state_manager.add_audit_log({
                "action": "LIVE_TRADING_PAUSED_REESTABLISHED_AFTER_FIRST_TRADE"
            }))
        
        # 3. Execution Orchestrator
        self.orchestrator = ExecutionOrchestrator(self.state_manager, self.event_bus, self.broker)

        # 4. Strategy Engine
        self.strategy_engine = StrategyEngine(self.state_manager, self.event_bus)
        self.strategy_engine.register_strategy(
            SessionBreakoutStrategy("breakout_nifty", Instrument(symbol="NSE:NIFTY50", exchange="NSE"))
        )

        # 5. Safety & Compliance
        self.compliance = SafetyCompliance(self.state_manager)

        # 6. Wire Events
        self.event_bus.subscribe(EventType.INTENT_EMITTED, self._on_intent_emitted)
        self.event_bus.subscribe(EventType.RISK_RESULT, self._on_risk_result)
        
        # Drive Strategy Engine on Market Facts (Deterministic Pulse)
        self.event_bus.subscribe(EventType.TICK_RECEIVED, self._on_tick_received)
        # Also drive on state-manager driven market data updates for UI/Manual consistency
        self.state_manager.subscribe(self._on_state_mutation)

    async def _on_state_mutation(self, change_type, data):
        if change_type == "MARKET_DATA_UPDATE":
            await self.strategy_engine.pulse()

    async def _on_tick_received(self, tick):
        await self.strategy_engine.pulse()

    async def _on_intent_emitted(self, intent):
        # When strategy emits intent -> Trigger Risk Check
        await self.risk_engine.validate_intent(intent)

    async def _on_risk_result(self, result):
        # When risk engine returns result -> If approved, trigger execution
        if result["approved"]:
            await self.orchestrator.execute_approved_intent(result["intent_id"])

    async def start(self):
        await self.broker.connect()
        
        # Trigger LIVE Read-Only Validation if in LIVE mode
        if self.state_manager.state.mode == RunMode.LIVE:
            await self.broker.validate_live_connection(self.state_manager, self.event_bus)
        
        # Start background safety monitoring (Autonomous enforcement)
        asyncio.create_task(self.compliance.run_safety_loop())
        
        print(f"Anti-Gravity System started in {self.state_manager.state.mode} mode.")

async def main():
    mode = RunMode.LIVE if os.getenv("RUN_MODE") == "LIVE" else RunMode.PAPER
    system = AntiGravitySystem(mode=mode)
    
    # Inject into API router for control
    router.state_manager = system.state_manager
    router.risk_engine = system.risk_engine
    
    # Start API server
    config = uvicorn.Config(router.app, port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        system.start(),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
