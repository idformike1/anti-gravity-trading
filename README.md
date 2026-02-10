# Anti-Gravity Trading System

Deterministic, event-driven autonomous trading system designed for safety and replayability.

## System Overview
Anti-Gravity is a high-integrity trading platform built on the principle of **Single Source of Truth** and **Fact-Based Communication**. It separates strategy logic from order execution through a mandatory risk gating layer, ensuring that every trade is validated against production-grade invariants.

## Core Design Principles
- **StateManager**: A central, thread-safe authority for all system state (positions, orders, market data).
- **Event-Driven Architecture**: Decoupled components communicate through an asynchronous Fact Bus.
- **Strategy Isolation**: Strategies are pure functions of state, returning intents without direct broker access.
- **Execution Gating**: Every `OrderIntent` must pass through the synchronous `RiskEngine`.
- **Safety First**: Autonomous kill switch and daily loss monitoring are first-class citizens.

## Modes of Operation
- **PAPER**: Simulated execution using local state, ideal for forward testing.
- **REPLAY**: Deterministic reconstruction of prior sessions from event logs.
- **LIVE (Guarded)**: Direct integration with Upstox API with mandatory read-only validation.

## Safety Guarantees
- **Kill Switch**: Immediate and absolute execution barrier.
- **Daily Loss Lock**: Autonomous shutdown upon breaching loss thresholds.
- **Risk Engine Gating**: Multi-rule validation (Quantity, Loss, Duplicates) per intent.
- **Idempotent Execution**: Intent-to-Order binding persists across restarts.

## How to Run

### PAPER Mode
Drivers the system using simulated market data and fills.
```bash
python3 main.py
# Default mode is PAPER
```

### REPLAY Mode
Replays a recorded session for debugging and validation.
```bash
python3 main.py --mode REPLAY --artifact <path_to_events.json>
```

### LIVE Mode (Dry-Run)
Connectivity validation without execution.
```bash
# Ensure UPSTOX_API_KEY and other secrets are in .env
python3 main.py --mode LIVE
```

## Explicit Non-Goals
- **No High-Frequency Trading (HFT)**: The system is designed for deterministic execution, not microsecond latency.
- **No Martingale or Toxic Strategies**: Inherently risky scaling behaviors are blocked by risk rules.
- **No Uncontrolled Scaling**: Quantitative limits are enforced at the engine level.

---
*Anti-Gravity: Precision in the void of market uncertainty.*
