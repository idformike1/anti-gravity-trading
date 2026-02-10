from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from core.types import RunMode, OrderIntent

app = FastAPI(title="Anti-Gravity Control API")

@app.get("/")
async def root():
    return {
        "system": "Anti-Gravity",
        "status": "online",
        "endpoints": ["/state", "/mode", "/killswitch", "/manual-intent"]
    }

# These will be injected at runtime
state_manager = None
risk_engine = None

class ModeUpdate(BaseModel):
    mode: RunMode

class KillSwitchUpdate(BaseModel):
    active: bool

@app.get("/state")
async def get_state():
    if not state_manager:
        raise HTTPException(status_code=500, detail="State Manager not initialized")
    return state_manager.state

@app.post("/mode")
async def set_mode(update: ModeUpdate):
    await state_manager.set_mode(update.mode)
    return {"status": "success", "mode": update.mode}

@app.post("/killswitch")
async def set_killswitch(update: KillSwitchUpdate):
    await state_manager.set_kill_switch(update.active)
    return {"status": "success", "kill_switch": update.active}

@app.post("/manual-intent")
async def manual_intent(intent: OrderIntent):
    # Still goes through risk engine
    approved, reason = await risk_engine.validate_intent(intent)
    if not approved:
        raise HTTPException(status_code=400, detail=f"Risk Rejected: {reason}")
    
    await state_manager.update_order_intent(intent.intent_id, intent)
    return {"status": "approved", "intent_id": intent.intent_id}
