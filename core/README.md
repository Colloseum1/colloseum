# Layer 4 Core - Router/Planner/RAG

This directory contains the Layer 4 "brain" of PromptFi - the AI agent orchestration system for strategy planning and execution.

## Directory Structure

```
core/
├── agents/              # AI agents (Router, Planner, Narrator)
├── tools/               # HTTP tool wrappers (validate, compile, simulate, ch_query, get_signals)
├── guardrails/          # Custom guardrails (PITOnlySql, NoFreeformNumbers, VenueAllow)
├── schemas/             # Pydantic models for agent I/O
├── orchestration/       # Team coordination and session management
├── workflows/           # Creative Engine background workflows
├── knowledge/           # LanceDB knowledge base for RAG
├── observability/       # OpenTelemetry instrumentation and tracing
└── tests/               # Test suite for core components
```

## Architecture

**Three-Agent Pipeline**: Router → Planner → Narrator

- **Router Agent** (gpt-4o-mini): Fast intent parsing from natural language asks
- **Planner Agent** (gpt-4o): Sophisticated strategy construction with tool orchestration
- **Narrator Agent** (gpt-4o-mini): Evidence-based explanations with citations

## Key Features

- **PIT-only data access**: Prevents lookahead bias in backtesting
- **Policy enforcement**: Dual enforcement at compile-time and runtime
- **Agentic RAG**: LanceDB knowledge base with automatic citation generation
- **Full observability**: OpenTelemetry tracing with Langfuse integration
- **Session continuity**: Multi-turn conversations with PostgreSQL storage

## Integration

This module integrates with:
- **data_plane/**: Layer 1 data collectors
- **schemas/**: Shared database schemas
- **docker-compose.yml**: Infrastructure (ClickHouse, PostgreSQL, Redis, Grafana)

## Getting Started

See the main project README for setup instructions and the Layer 4 implementation plan at `/promptfi/layer4-agno-plan.md`.
