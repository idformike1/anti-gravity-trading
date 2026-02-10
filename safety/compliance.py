from datetime import datetime, time
import logging
from core.types import SystemState

class SafetyCompliance:
    """
    Ensures trading halts and audit compliance.
    """
    def __init__(self, state_manager):
        self._state_manager = state_manager
        self.daily_loss_limit = 5000.0 # Configurable
        self.market_open = time(9, 15)
        self.market_close = time(15, 30)

    async def run_safety_loop(self):
        """Monitor state for breaches and trigger kill switch if needed."""
        while True:
            state = self._state_manager.state
            
            # 1. Daily Loss Check
            total_realized = sum(p.realized_pnl for p in state.positions.values())
            if total_realized <= -self.daily_loss_limit:
                await self._state_manager.set_kill_switch(True)
                await self._state_manager.add_audit_log({
                    "action": "SAFETY_HALT",
                    "reason": f"Daily loss limit {self.daily_loss_limit} exceeded"
                })

            # 2. Market Hours Check
            now = datetime.now().time()
            if now < self.market_open or now > self.market_close:
                # Not necessarily kill switch, but could block strategy
                pass

            await asyncio.sleep(5)  # Check every 5 seconds

    @staticmethod
    def setup_logger():
        logger = logging.getLogger("AntiGravityAudit")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler("audit_trail.log")
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
