# Layer 4 Monitoring (Task 8.4)

Simple session monitoring metrics for the Strategy Team with automatic AgnoInstrumentor integration.

## Quick Start

### 1. Initialize Agno Instrumentation (Once at Startup)

```python
from core.monitoring import initialize_agno_instrumentation

# Call once when your app starts
initialize_agno_instrumentation()
```

This ONE line enables automatic metrics for:
- LLM token usage (prompt, completion, total)
- LLM call latency
- Tool execution counts and latency
- Agent run success/failure rates

### 2. Use Team with Automatic Metrics

```python
from core.orchestration import run_strategy_team

# Metrics are automatically tracked!
result = run_strategy_team(
    "Build me a SOL trend following strategy",
    session_id="user_123_session_001",
    user_id="user_123",
    enable_metrics=True,  # default
)

# The following metrics are automatically tracked:
# - team_runs_total{status="success"} += 1
# - team_run_duration_seconds observed
# - session_count incremented
```

### 3. Expose Metrics Endpoint (for Prometheus Scraping)

```python
from fastapi import FastAPI, Response
from core.monitoring import get_metrics

app = FastAPI()

@app.get("/metrics")
def metrics():
    return Response(get_metrics(), media_type="text/plain")
```

### 4. View Metrics (Debugging)

```python
from core.monitoring import print_metrics_summary

print_metrics_summary()
```

Output:
```
======================================================================
Layer 4 Metrics Summary
======================================================================
Active Sessions: 3
Total Sessions by User: {'user_123': 5, 'user_456': 2}
Team Runs by Status: {'success': 6, 'error': 1}
AgnoInstrumentation: ✓ Enabled
======================================================================

For full metrics output, call get_metrics() and expose via HTTP endpoint.
```

## Available Metrics

### Session Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `layer4_active_sessions` | Gauge | Current number of active sessions |
| `layer4_sessions_total{user_id}` | Counter | Total sessions created per user |

### Team Run Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `layer4_team_runs_total{status}` | Counter | Total team runs (status: success/error) |
| `layer4_team_run_duration_seconds{status}` | Histogram | Team run duration in seconds |

### AgnoInstrumentor Automatic Metrics

When initialized, AgnoInstrumentor automatically provides:

- **LLM Metrics**:
  - Token usage (prompt, completion, total)
  - Call latency (time to first token, total time)
  - Model usage distribution

- **Agent Metrics**:
  - Run counts (success, failure)
  - Run duration
  - Session continuation rate

- **Tool Metrics**:
  - Tool call counts per type
  - Tool execution latency
  - Tool error rates

## Manual Tracking (Advanced)

If you need custom tracking:

```python
from core.monitoring import (
    track_session_start,
    track_session_end,
    track_team_run,
    track_team_execution,
)

# Manual session tracking
session_id = "my_session"
track_session_start(session_id, user_id="user_123")

# Manual run tracking
import time
start = time.time()
# ... your code ...
track_team_run("success", time.time() - start)

# Or use context manager
with track_team_execution():
    # Your code here
    # Metrics tracked automatically on exit
    pass

# End session
track_session_end(session_id)
```

## Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'layer4_team'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']  # Your app's /metrics endpoint
```

## Grafana Dashboard

Example queries:

```promql
# Active sessions
layer4_active_sessions

# Session creation rate (last 5min)
rate(layer4_sessions_total[5m])

# Success rate
rate(layer4_team_runs_total{status="success"}[5m])
  /
rate(layer4_team_runs_total[5m])

# 95th percentile latency
histogram_quantile(0.95, layer4_team_run_duration_seconds)
```

## What's NOT in Task 8.4

This is the **simplified** monitoring implementation. The following are in **Task 9** (Full Observability):

- ❌ Distributed tracing (see full Router → Planner → Narrator flow)
- ❌ OTLP exporter to Langfuse
- ❌ Detailed span attributes and enrichment
- ❌ PII scrubbing for traces
- ❌ Cost tracking per request
- ❌ Circuit breakers
- ❌ Complex health checks

For full observability, see `core/observability/` (Task 9).

## Architecture

```
┌─────────────────────────────────────────┐
│ User Request                            │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ run_strategy_team()                     │
│ - track_session_start()                 │
│ - with track_team_execution():          │
│     team.run(...)                       │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ Prometheus Metrics                      │
│ - session_count.inc()                   │
│ - team_runs_total{status}.inc()         │
│ - team_run_duration.observe()           │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ AgnoInstrumentor (Automatic)            │
│ - LLM tokens, latency                   │
│ - Tool call counts, timing              │
│ - Agent run success/failure             │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ /metrics Endpoint                       │
│ - Prometheus scrapes every 15s          │
│ - Grafana visualizes                    │
└─────────────────────────────────────────┘
```

## Testing

```python
# Test metrics collection
from core.monitoring import initialize_agno_instrumentation, print_metrics_summary
from core.orchestration import run_strategy_team

# Initialize
initialize_agno_instrumentation()

# Run a few test requests
for i in range(5):
    try:
        result = run_strategy_team(
            f"Test strategy {i}",
            session_id=f"test_session_{i}",
            user_id="test_user",
        )
        print(f"✓ Run {i} success")
    except Exception as e:
        print(f"✗ Run {i} failed: {e}")

# Check metrics
print_metrics_summary()
```

Expected output:
```
✓ Run 0 success
✓ Run 1 success
✓ Run 2 success
✓ Run 3 success
✓ Run 4 success

======================================================================
Layer 4 Metrics Summary
======================================================================
Active Sessions: 5
Total Sessions by User: {'test_user': 5}
Team Runs by Status: {'success': 5}
AgnoInstrumentation: ✓ Enabled
======================================================================
```
