# Observability Tests (Task 9.3)

Verification tests for OpenTelemetry + Langfuse integration.

## ✅ Test Verification (Latest Run)

**Date**: 2025-10-20
**Status**: All tests passing ✓

```bash
# Test Results:
# - 11 unit/integration tests PASSED
# - 2 integration tests SKIPPED (require Langfuse API keys)
```

**Test Coverage**:
- ✅ Observability initialization (with/without Langfuse keys)
- ✅ TracerProvider configuration
- ✅ Manual span creation and hierarchy
- ✅ Span attributes capture (user_id, session_id, tokens)
- ✅ Error span marking (automatic exception tracking)
- ✅ Console export (development mode)
- ✅ Module exports and documentation
- ✅ Tracer provider reset between tests
- ✅ Shutdown and cleanup

**Integration Tests** (require Langfuse API):
- Traces reach Langfuse within 5 seconds
- Agent run creates correct span hierarchy

## Running Tests

### 1. Run All Tests (Unit + Mocked Integration)

```bash
cd /home/degencodebeast/promptfi/colloseum
uv run pytest tests/observability/test_langfuse_integration.py -v
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
test_traces_reach_langfuse_within_5_seconds SKIPPED (requires API keys)
test_agent_run_creates_trace_hierarchy SKIPPED (requires API keys)

======================== 11 passed, 2 skipped in 0.82s =========================
```

### 2. Run Only Unit Tests (Fast)

```bash
uv run pytest tests/observability/test_langfuse_integration.py -v -m "not integration"
```

### 3. Run Integration Tests (Requires Langfuse API)

**Prerequisites**:
- Langfuse account with API keys
- Set environment variables:

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export OPENAI_API_KEY="sk-..."  # For agent run test
```

**Run tests**:
```bash
uv run pytest tests/observability/test_langfuse_integration.py -m integration -v
```

Expected output:
```
test_traces_reach_langfuse_within_5_seconds PASSED
✓ Trace exported to Langfuse in 1.23s
✓ Check Langfuse UI for trace: 'test-trace-export'

test_agent_run_creates_trace_hierarchy PASSED
✓ Agent run completed
✓ Check Langfuse UI for trace hierarchy
```

### 4. Run Specific Test

```bash
# Test span hierarchy
uv run pytest tests/observability/test_langfuse_integration.py::test_manual_span_creation_with_tracer -v

# Test error marking
uv run pytest tests/observability/test_langfuse_integration.py::test_error_spans_are_marked -v

# Test Langfuse export (requires API keys)
uv run pytest tests/observability/test_langfuse_integration.py::test_traces_reach_langfuse_within_5_seconds -v
```

## Test Categories

### Unit Tests (No External Dependencies)

These tests use mocks and don't require external services:

- `test_initialize_observability_with_langfuse_keys` - Initialization with keys
- `test_initialize_observability_without_keys` - Graceful fallback without keys
- `test_initialize_observability_called_twice` - Idempotency check
- `test_get_tracer_returns_valid_tracer` - Tracer creation
- `test_shutdown_observability` - Cleanup
- `test_console_export_enabled` - Development mode
- `test_observability_docstrings_exist` - Documentation
- `test_observability_module_exports` - Public API

### Integration Tests (In-Memory)

These tests use real OpenTelemetry components but with in-memory exporters:

- `test_manual_span_creation_with_tracer` - Span hierarchy verification
- `test_span_attributes_are_captured` - Attribute capture
- `test_error_spans_are_marked` - Exception tracking

### Integration Tests (Requires Langfuse API)

These tests require valid Langfuse credentials and network access:

- `test_traces_reach_langfuse_within_5_seconds` - Real export to Langfuse
- `test_agent_run_creates_trace_hierarchy` - Full agent pipeline tracing

## Test Fixtures

### `reset_observability` (autouse)

Resets observability state before/after each test:
- Clears `_observability_initialized` flag
- Resets global TracerProvider
- Allows tests to run in isolation

### `mock_langfuse_env`

Sets mock Langfuse environment variables:
```python
LANGFUSE_PUBLIC_KEY="pk-test-123"
LANGFUSE_SECRET_KEY="sk-test-456"
LANGFUSE_HOST="https://cloud.langfuse.com"
```

### `in_memory_span_exporter`

Creates an in-memory span exporter for testing span capture.

### `test_tracer_provider`

Creates a test TracerProvider with in-memory exporter attached.

## Debugging Failed Tests

### View Detailed Test Output

```bash
uv run pytest tests/observability/test_langfuse_integration.py -vv --tb=long
```

### Run with Print Statements

```bash
uv run pytest tests/observability/test_langfuse_integration.py -s
```

### Drop into PDB on Failure

```bash
uv run pytest tests/observability/test_langfuse_integration.py --pdb
```

### Check Specific Span Attributes

```python
# In test, after span creation:
spans = in_memory_span_exporter.get_finished_spans()
for span in spans:
    print(f"Span: {span.name}")
    print(f"Attributes: {span.attributes}")
    print(f"Events: {span.events}")
    print(f"Status: {span.status}")
```

## Common Issues

### Issue: "Overriding of current TracerProvider is not allowed"

**Cause**: Global TracerProvider already set
**Fix**: The `reset_observability` fixture handles this automatically

### Issue: Spans not appearing in in_memory_span_exporter

**Cause**: Forgot to call `force_flush()`
**Fix**:
```python
test_tracer_provider.force_flush()
spans = in_memory_span_exporter.get_finished_spans()
```

### Issue: Integration tests always skipped

**Cause**: Missing environment variables
**Fix**:
```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
```

## Verification Checklist

- ✅ All unit tests pass without external services
- ✅ Span hierarchy is correct (parent-child relationships)
- ✅ Span attributes are captured correctly
- ✅ Errors are automatically marked in spans
- ✅ Observability can be initialized multiple times safely
- ✅ Shutdown cleans up resources properly
- ✅ Console export works for debugging
- ✅ Module exports match public API

## Related Documentation

- [Observability Setup](../../core/observability/README.md)
- [Integration Tests](../integration/README.md)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Langfuse Documentation](https://langfuse.com/docs)
