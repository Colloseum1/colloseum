# Layer 4 Core Configuration Guide

This document describes the environment variables required for Layer 4 (Core Agent System) operation.

## Required Variables

### LLM Provider API Keys

**OPENAI_API_KEY**
- **Required**: Yes
- **Purpose**: OpenAI API access for GPT-4o and GPT-4o-mini models
- **Used by**: RouterAgent, PlannerAgent, NarratorAgent
- **Format**: `sk-...`
- **Obtain from**: https://platform.openai.com/api-keys

**ANTHROPIC_API_KEY**
- **Required**: Optional (if using Claude models instead)
- **Purpose**: Anthropic API access for Claude models
- **Format**: `sk-ant-...`
- **Obtain from**: https://console.anthropic.com/

### Observability & Tracing

**LANGFUSE_PUBLIC_KEY**
- **Required**: Yes (for production observability)
- **Purpose**: Langfuse public key for trace authentication
- **Format**: `pk-lf-...`
- **Obtain from**: https://langfuse.com/

**LANGFUSE_SECRET_KEY**
- **Required**: Yes (for production observability)
- **Purpose**: Langfuse secret key for trace authentication
- **Format**: `sk-lf-...`
- **Obtain from**: https://langfuse.com/

**LANGFUSE_OTLP_ENDPOINT**
- **Required**: Yes
- **Purpose**: OpenTelemetry endpoint for trace export
- **Default**: `http://localhost:4318/v1/traces`
- **Format**: URL with `/v1/traces` path

### Layer 4 Service Endpoints

**SIGNALS_URL**
- **Required**: Yes
- **Purpose**: Layer 3 signal service endpoint
- **Default**: `http://localhost:8082/signals`
- **Used by**: PlannerAgent (get_signals tool)

**VALIDATE_URL**
- **Required**: Yes
- **Purpose**: Strategy validation service endpoint
- **Default**: `http://localhost:8081/validate`
- **Used by**: PlannerAgent (validate tool)

**COMPILE_URL**
- **Required**: Yes
- **Purpose**: Strategy compilation service endpoint
- **Default**: `http://localhost:8081/compile`
- **Used by**: PlannerAgent (compile_spec tool)

**L5_SIM_URL**
- **Required**: Yes
- **Purpose**: Layer 5 simulator endpoint
- **Default**: `http://localhost:7090/simulate`
- **Used by**: PlannerAgent (simulate tool)

**CH_READ_URL**
- **Required**: Yes
- **Purpose**: ClickHouse HTTP query endpoint
- **Default**: `http://localhost:8123/query`
- **Used by**: PlannerAgent (ch_query tool)

### Database Configuration

**POSTGRES_URL**
- **Required**: Yes
- **Purpose**: PostgreSQL connection for Agno session storage
- **Default**: `postgresql+psycopg://ch:mdp@localhost:5432/mdp`
- **Format**: PostgreSQL connection string with psycopg driver
- **Note**: Uses existing infrastructure from docker-compose.yml

**LANCEDB_PATH**
- **Required**: Yes
- **Purpose**: LanceDB vector store path for knowledge base
- **Default**: `./core/knowledge/lancedb`
- **Format**: Relative or absolute filesystem path

## Optional Variables

**LOG_LEVEL**
- **Required**: No
- **Purpose**: Python logging level
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**OTLP_ENDPOINT**
- **Required**: No
- **Purpose**: Alternative OTLP endpoint (if not using Langfuse)
- **Default**: `http://localhost:4318/v1/traces`

## Existing Infrastructure Variables

Layer 4 also uses these existing variables from the colloseum project:

- **CLICKHOUSE_HTTP**: ClickHouse HTTP endpoint (Layer 1 data access)
- **CLICKHOUSE_USER**: ClickHouse username
- **CLICKHOUSE_PASSWORD**: ClickHouse password
- **REDIS_URL**: Redis connection string (for caching)
- **POSTGRES_URL**: PostgreSQL connection (session storage)

## Setup Instructions

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Obtain API keys:
   - OpenAI: https://platform.openai.com/api-keys
   - Langfuse: https://langfuse.com/ (or self-hosted)

3. Update `.env` with your actual keys

4. Verify configuration:
   ```bash
   uv run python core/scripts/validate_setup.py
   ```

## Security Notes

- **Never commit `.env` to git** - it's already in `.gitignore`
- **Rotate API keys regularly**
- **Use separate keys for dev/staging/prod**
- **PII scrubbing is enabled** - sensitive data is masked in traces

## See Also

- Main project README: `/home/degencodebeast/promptfi/colloseum/README.md`
- Layer 4 architecture: `/home/degencodebeast/promptfi/layer4-agno-plan.md`
- Infrastructure setup: `/home/degencodebeast/promptfi/colloseum/docker-compose.yml`
