# Layer 4 Integration Tests (Task 8.5)

End-to-end integration tests for the complete Team orchestration flow: Router → Planner → Narrator.

## ✅ Test Verification (Latest Run)

**Date**: 2025-10-20
**Status**: All unit tests passing ✓

```bash
# Test Results:
# - 7 unit tests PASSED (no external dependencies required)
# - 5 integration tests SKIPPED (require PostgreSQL/OpenAI API)
# - All agent tests PASSING (router, planner verified)
```

**Unit Tests Verified**:
- ✅ Shared dependencies configuration
- ✅ Team creation (basic and with session config)
- ✅ Context sharing via dependencies
- ✅ Knowledge base setup (structure)
- ✅ Metrics tracking (Prometheus + AgnoInstrumentor)
- ✅ Error handling in team execution
- ✅ Mock fixtures working correctly

**Integration Tests** (skipped without services, ready to run when services available):
- Session persistence with PostgreSQL
- Multi-turn conversations
- Full end-to-end with real LLM calls
- Team streaming output

**Fixed Issues**:
1. Added `openinference-instrumentation-agno>=0.1.18` dependency
2. Fixed import: `from openinference.instrumentation.agno import AgnoInstrumentor`
3. Fixed Unicode encoding in `core/orchestration/__init__.py`

## Test Coverage

### Core Functionality
- ✅ Shared dependencies configuration
- ✅ Team creation with session management
- ✅ Context sharing between agents
- ✅ Session persistence (PostgreSQL)
- ✅ Knowledge base retrieval (LanceDB)
- ✅ Metrics tracking
- ✅ Error handling
- ✅ Multi-turn conversations
- ✅ Full end-to-end flow

### Test Levels

**Unit Tests** (Fast, No External Dependencies):
- Shared dependencies configuration
- Team creation
- Context sharing

**Integration Tests** (Require External Services):
- Session persistence (requires PostgreSQL)
- Knowledge base retrieval (requires LanceDB)
- Full end-to-end flow (requires all services + real LLM calls)

## Running Tests

### 1. Run All Tests (Unit Only)

```bash
cd /home/degencodebeast/promptfi/colloseum
uv run pytest tests/integration/test_team_orchestration.py -v
```

This runs only tests that don't require external services (mocked).

### 2. Run Integration Tests (Requires Services)

#### Prerequisites

**Required Services**:
- PostgreSQL with pgvector (for session storage)
- LanceDB (for knowledge base)
- OpenAI API key (for real LLM calls)

**Start PostgreSQL**:
```bash
docker run -d --name agno-postgres \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e POSTGRES_DB=ai \
  -p 5532:5432 \
  ankane/pgvector
```

**Set Environment Variables**:
```bash
export POSTGRES_DB_URL="postgresql+psycopg://ai:ai@localhost:5532/ai"
export OPENAI_API_KEY="sk-..."
```

**Run Integration Tests**:
```bash
uv run pytest tests/integration/test_team_orchestration.py -m integration -v
```

### 3. Run Specific Test

```bash
# Run single test
uv run pytest tests/integration/test_team_orchestration.py::test_shared_dependencies_configuration -v

# Run tests matching pattern
uv run pytest tests/integration/test_team_orchestration.py -k "session" -v
```

### 4. Run with Coverage

```bash
uv run pytest tests/integration/test_team_orchestration.py --cov=core.orchestration --cov-report=html -v
```

## Test Markers

Tests are marked with pytest markers to control execution:

```python
@pytest.mark.integration  # Requires external services
@pytest.mark.skipif(...)  # Conditional skip based on env vars
@pytest.mark.skip(...)    # Always skip (placeholder tests)
```

**View Available Markers**:
```bash
uv run pytest --markers
```

**Run Only Integration Tests**:
```bash
uv run pytest -m integration
```

**Exclude Integration Tests**:
```bash
uv run pytest -m "not integration"
```

## Test Structure

### Unit Tests (Fast, Isolated)

```python
def test_shared_dependencies_configuration():
    """Test dependencies without external calls."""
    deps = get_shared_dependencies()
    assert "rules" in deps
    assert "endpoints" in deps
```

### Integration Tests (Real Services)

```python
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("POSTGRES_DB_URL"),
    reason="Requires PostgreSQL"
)
def test_session_persistence_with_postgres():
    """Test session storage with real PostgreSQL."""
    team = create_strategy_team(
        session_id="test_session",
        user_id="test_user",
    )
    # Test real session persistence
```

### Full End-to-End (All Services)

```python
@pytest.mark.integration
@pytest.mark.skipif(
    not all([
        os.getenv("OPENAI_API_KEY"),
        os.getenv("POSTGRES_DB_URL"),
    ]),
    reason="Requires all services and real LLM calls"
)
def test_full_end_to_end_integration():
    """Complete flow with real agents, services, and LLM calls."""
    result = run_strategy_team(
        user_ask="Build me a SOL trend following strategy",
        session_id="integration_test",
        user_id="test_user",
    )
    assert result is not None
```

## Fixtures

### `mock_http_tools`
Mocks HTTP tool responses (validate, compile, simulate, get_signals, ch_query).

```python
def test_with_mocked_tools(mock_http_tools):
    # Tools return realistic mock data
    validate_result = mock_http_tools["validate"]()
```

### `mock_agents`
Mocks Router, Planner, Narrator agents.

```python
def test_with_mocked_agents(mock_agents):
    # Agents return realistic mock responses
    router = mock_agents["router"]()
```

### `test_session_config`
Provides test session configuration.

```python
def test_with_session(test_session_config):
    session_id = test_session_config["session_id"]
    user_id = test_session_config["user_id"]
```

## Common Test Scenarios

### Test Session Continuity

```python
def test_multi_turn_conversation():
    team = create_strategy_team(
        session_id="test_multi_turn",
        user_id="test_user",
    )

    # Turn 1
    result_1 = team.run("Build me a SOL strategy")

    # Turn 2 (should have context from turn 1)
    result_2 = team.run("Make it more aggressive")

    # Verify history
    history = team.get_chat_history()
    assert len(history) >= 2
```

### Test Metrics Collection

```python
def test_metrics_tracking():
    initialize_agno_instrumentation()

    # Run team
    run_strategy_team(
        "Build me a strategy",
        session_id="test_metrics",
        user_id="test_user",
        enable_metrics=True,
    )

    # Verify metrics
    print_metrics_summary()
    # Should show incremented counters
```

### Test Error Handling

```python
def test_error_handling(mock_agents):
    # Configure mock to raise error
    mock_agents["planner"]().run.side_effect = Exception("Test error")

    team = create_strategy_team()
    # Team should handle error gracefully
```

## Debugging Failed Tests

### View Detailed Output

```bash
uv run pytest tests/integration/test_team_orchestration.py -vv --tb=long
```

### Run with Print Statements

```bash
uv run pytest tests/integration/test_team_orchestration.py -s
```

### Drop into PDB on Failure

```bash
uv run pytest tests/integration/test_team_orchestration.py --pdb
```

### View Test Coverage

```bash
uv run pytest tests/integration/test_team_orchestration.py --cov=core --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: ankane/pgvector
        env:
          POSTGRES_USER: ai
          POSTGRES_PASSWORD: ai
          POSTGRES_DB: ai
        ports:
          - 5532:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run unit tests
        run: uv run pytest tests/integration -m "not integration" -v

      - name: Run integration tests
        env:
          POSTGRES_DB_URL: postgresql+psycopg://ai:ai@localhost:5532/ai
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: uv run pytest tests/integration -m integration -v
```

## Next Steps

After Task 8.5, the following tests will be added in future tasks:

**Task 9 (Full Observability)**:
- Distributed tracing validation
- OTLP exporter tests
- Langfuse integration tests
- Span enrichment tests
- Cost tracking tests

**Task 10 (Creative Engine)**:
- Workflow execution tests
- APScheduler integration tests
- Candidate generation tests
- Circuit breaker tests
- DLQ handling tests

## Related Documentation

- [Team Orchestration](../../core/orchestration/README.md) (if exists)
- [Monitoring Metrics](../../core/monitoring/README.md)
- [Agno Documentation](https://docs.agno.com/)
