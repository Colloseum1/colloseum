# Layer 4 Observability (Task 9)

Full distributed tracing with Langfuse integration for complete visibility into the Strategy Team pipeline.

## Quick Start

### 1. Set Up Langfuse (One-Time)

**Option A: Cloud (Recommended)**
```bash
# Sign up at https://cloud.langfuse.com
# Get your API keys from Settings > API Keys

export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"  # or https://us.cloud.langfuse.com
```

**Option B: Self-Hosted**
```bash
# Run Langfuse locally with Docker
docker run -d --name langfuse \
  -p 3000:3000 \
  -e DATABASE_URL="postgresql://user:pass@localhost:5432/langfuse" \
  langfuse/langfuse:latest

export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="http://localhost:3000"
```

### 2. Initialize Observability (Once at Startup)

```python
from core.observability import initialize_observability

# At application startup - BEFORE creating any agents!
initialize_observability()

# Now all team runs, agent executions, and tool calls are automatically traced!
```

### 3. Use Your Team (No Code Changes!)

```python
from core.orchestration import run_strategy_team

# Just use the team normally - traces are automatic!
result = run_strategy_team(
    "Build me a SOL trend following strategy",
    session_id="user_123",
    user_id="user_123",
)

# View traces in Langfuse UI within 5 seconds!
```

## What Gets Traced Automatically

AgnoInstrumentor automatically captures **everything** without any manual instrumentation:

### Team Level
- ✅ Team.run() execution (root span)
- ✅ Session ID, User ID
- ✅ Input message, output content
- ✅ Total duration

### Agent Level
- ✅ RouterAgent.run() → RouterDecision
- ✅ PlannerAgent.run() → StrategySpecOutput
- ✅ NarratorAgent.run() → ExplainedPlan
- ✅ Agent input/output
- ✅ Agent duration

### Tool Level
- ✅ validate(spec) calls → validation results
- ✅ compile_spec(spec) calls → compiled plans
- ✅ simulate(spec) calls → backtest metrics
- ✅ get_signals(spec) calls → signal data
- ✅ ch_query(sql) calls → query results
- ✅ Tool input parameters, output results
- ✅ Tool execution time

### LLM Level
- ✅ OpenAI/Anthropic/etc. model calls
- ✅ Prompt tokens, completion tokens, total tokens
- ✅ Model ID (gpt-4o, claude-3-5-sonnet, etc.)
- ✅ Latency (time to first token, total time)
- ✅ Temperature, max_tokens settings
- ✅ Tool calls from LLM (function calling)

### Error Tracking
- ✅ Exceptions automatically marked in spans
- ✅ Error messages and stack traces captured
- ✅ Failed tool calls highlighted
- ✅ Guardrail violations logged

## Trace Hierarchy Example

```
Team.run("Build SOL strategy")                    [45s]
├─ RouterAgent.run()                              [3s]
│  └─ OpenAI.chat("gpt-4o-mini")                  [2.5s]
│     ├─ tokens: 450 prompt + 120 completion
│     └─ cost: $0.0015
├─ PlannerAgent.run()                             [35s]
│  ├─ ReasoningTools()                            [1s]
│  ├─ ch_query("SELECT volatility...")            [0.5s]
│  ├─ get_signals(spec)                           [2s]
│  ├─ validate(spec)                              [1s]
│  ├─ compile_spec(spec)                          [5s]
│  ├─ simulate(spec)                              [20s]
│  └─ OpenAI.chat("gpt-4o")                       [5s]
│     ├─ tokens: 2500 prompt + 800 completion
│     └─ cost: $0.025
└─ NarratorAgent.run()                            [7s]
   ├─ Knowledge.search("leg_library")             [1s]
   ├─ Knowledge.search("rules.yml")               [1s]
   └─ OpenAI.chat("gpt-4o-mini")                  [4s]
      ├─ tokens: 1200 prompt + 600 completion
      └─ cost: $0.008
```

## Configuration Options

### Basic Setup

```python
from core.observability import initialize_observability

# Use environment variables (recommended)
initialize_observability()
```

### Custom Configuration

```python
# Override Langfuse settings
initialize_observability(
    langfuse_public_key="pk-lf-custom",
    langfuse_secret_key="sk-lf-custom",
    langfuse_host="https://us.cloud.langfuse.com",  # US region
    enable_console_export=True,  # Also print traces to console
)
```

### Development Mode (Console Only)

```python
# No Langfuse keys? Traces print to console for debugging
initialize_observability(enable_console_export=True)
```

## Manual Span Creation (Advanced)

For custom operations not auto-instrumented:

```python
from core.observability import get_tracer

tracer = get_tracer("my-custom-module")

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("user_id", "user_123")
    span.set_attribute("operation_type", "data_transform")

    # Your code here
    result = transform_data()

    span.set_attribute("rows_processed", len(result))
```

## Langfuse Dashboard Features

### Traces View
- See every team run with full hierarchy
- Filter by user_id, session_id, status
- Search for specific agents or tools
- Drill down into any span for details

### Analytics
- Token usage per agent (Router, Planner, Narrator)
- Cost breakdown by model (gpt-4o vs gpt-4o-mini)
- Latency percentiles (p50, p90, p99)
- Error rates per tool/agent

### Sessions
- Group traces by session_id
- See conversation history
- Track user journeys

### Metrics
- Total token usage (daily, weekly, monthly)
- Total costs (grouped by model, user, team)
- Request volumes
- Average latencies

## Testing

### Run Unit Tests (No External Services)

```bash
cd /home/degencodebeast/promptfi/colloseum
uv run pytest tests/observability/test_langfuse_integration.py -v -m "not integration"
```

Expected output:
```
test_initialize_observability_with_langfuse_keys PASSED
test_initialize_observability_without_keys PASSED
test_initialize_observability_called_twice PASSED
test_get_tracer_returns_valid_tracer PASSED
test_shutdown_observability PASSED
test_manual_span_creation_with_tracer PASSED
test_span_attributes_are_captured PASSED
test_error_spans_are_marked PASSED
test_console_export_enabled PASSED
test_observability_docstrings_exist PASSED
test_observability_module_exports PASSED
```

### Run Integration Tests (Requires Langfuse)

**Prerequisites**:
- Langfuse account with API keys
- Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."

uv run pytest tests/observability/test_langfuse_integration.py -m integration -v
```

Expected output:
```
test_traces_reach_langfuse_within_5_seconds PASSED
✓ Trace exported to Langfuse in 1.23s
✓ Check Langfuse UI for trace: 'test-trace-export'

test_agent_run_creates_trace_hierarchy PASSED
✓ Agent run completed
✓ Check Langfuse UI for trace hierarchy:
  - Root span: Team run
  - Child spans: Router, Planner, Narrator agents
  - Grandchild spans: Tool calls, LLM calls
```

## Troubleshooting

### Traces Not Appearing in Langfuse

**Check 1: API Keys**
```bash
echo $LANGFUSE_PUBLIC_KEY  # Should start with pk-lf-
echo $LANGFUSE_SECRET_KEY  # Should start with sk-lf-
```

**Check 2: Initialization**
```python
from core.observability import is_observability_enabled
print(is_observability_enabled())  # Should be True
```

**Check 3: Flush Traces**
```python
from opentelemetry import trace
provider = trace.get_tracer_provider()
provider.force_flush(timeout_millis=5000)
```

**Check 4: Network**
```bash
curl -I https://cloud.langfuse.com/api/public/otel
# Should return 404 (endpoint exists, but needs POST with auth)
```

### Slow Trace Export

Traces are exported **asynchronously** - they don't block your code. If you need to ensure export before shutdown:

```python
from core.observability import shutdown_observability

# At application shutdown
shutdown_observability()  # Flushes all pending traces
```

### High Cardinality Attributes

Avoid setting attributes with unbounded values (user input, long strings):

```python
# ❌ BAD: Unbounded user input
span.set_attribute("user_query", user_input)

# ✅ GOOD: Truncate or hash
span.set_attribute("user_query_hash", hash(user_input)[:16])
span.set_attribute("user_query_length", len(user_input))
```

## Cost Estimation

Based on typical Strategy Team usage:

| Component | Tokens/Run | Cost/Run (gpt-4o) | Cost/1000 Runs |
|-----------|-----------|-------------------|----------------|
| RouterAgent | ~600 | $0.002 | $2 |
| PlannerAgent | ~3500 | $0.030 | $30 |
| NarratorAgent | ~2000 | $0.010 | $10 |
| **Total** | **~6100** | **$0.042** | **$42** |

Langfuse pricing (as of 2025):
- **Free tier**: 50,000 observations/month (enough for ~8,000 team runs)
- **Pro tier**: $99/month for 500,000 observations (~80,000 team runs)

## What's NOT in Task 9

This is the **complete** observability implementation. The following were considered but NOT needed:

- ❌ Custom span attributes for PII - AgnoInstrumentor handles this
- ❌ Manual cost tracking - Automatically captured from LLM calls
- ❌ Custom error span marking - Automatically marked on exceptions
- ❌ Performance metrics collection - Built into AgnoInstrumentor
- ❌ PII scrubbing - Handled by Langfuse + guardrails already block PII

## Architecture Comparison

### Task 8.4 (Monitoring) vs Task 9 (Observability)

| Feature | Task 8.4 | Task 9 |
|---------|----------|--------|
| **Purpose** | Aggregate metrics | Distributed tracing |
| **Granularity** | Counters, gauges | Per-request spans |
| **Tool** | Prometheus | OpenTelemetry + Langfuse |
| **Use Case** | "Are agents working?" | "Why did this fail?" |
| **Retention** | Forever (metrics) | 30 days (traces) |
| **Cost** | Free (self-hosted) | $99/mo (Pro) |
| **Setup** | `initialize_agno_instrumentation()` | `initialize_observability()` |

**Use both together**:
- **Monitoring**: Alerts when error rate > 5%
- **Observability**: Debug the specific failing requests

## Related Documentation

- [Team Orchestration](../orchestration/README.md)
- [Monitoring Metrics](../monitoring/README.md)
- [Agno Observability](https://docs.agno.com/concepts/observability)
- [Langfuse Documentation](https://langfuse.com/docs)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

## Next Steps (Task 10)

After Task 9, the following will use observability:

**Task 10 (Creative Engine)**:
- Workflow execution traces
- Background job monitoring
- Candidate generation analysis
- Circuit breaker tracing
- DLQ failure investigation
