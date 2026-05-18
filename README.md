# Async Trading System Audit Toolkit

A Python toolkit for auditing production async crypto trading systems. Identifies state inconsistencies, execution timing issues, and architectural fragility in asyncio-based exchange integrations.

## What It Detects

- **State inconsistencies**: shared mutable state across coroutines without proper locking
- **Execution timing problems**: blocking calls inside async functions, missing await chains
- **CCXT integration patterns**: improper error handling, rate limit violations, order state desync
- **Architectural fragility**: tight coupling between exchange layers and order management

## Architecture

```
async-trading-audit/
├── main.py                  # CLI entry point
├── audit/
│   ├── __init__.py
│   ├── analyzer.py          # AST-based async pattern analysis
│   ├── ccxt_checker.py      # CCXT-specific anti-pattern detection
│   └── state_tracker.py     # Shared state and lock usage analysis
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
python main.py --path /path/to/trading/system
```

## Sample Output

```
[CRITICAL] state_tracker.py:42 — shared dict `positions` mutated from 3 coroutines without asyncio.Lock
[HIGH]     exchange.py:118   — blocking time.sleep() inside async fetch_balance()
[HIGH]     order_manager.py:77 — CCXT exception not caught; order state left PENDING on network error
[MEDIUM]   websocket.py:203  — reconnect loop lacks exponential backoff; floods exchange on disconnect
```

## Usage

```python
from audit.analyzer import AsyncAuditor

auditor = AsyncAuditor("/path/to/your/system")
report = await auditor.run()
report.save("audit_report.json")
```
