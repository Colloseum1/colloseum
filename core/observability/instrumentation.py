"""
OpenTelemetry Observability Setup for Layer 4 (Task 9).

Provides distributed tracing with Langfuse integration via OpenTelemetry.
Automatically instruments all Agno agents, tools, and model calls.

Usage:
    from core.observability import initialize_observability

    # Call once at startup
    initialize_observability()

    # All agent runs, tool calls, and LLM calls are now traced automatically!
"""

import os
import base64
from typing import Optional
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.agno import AgnoInstrumentor


# ============================================================================
# Global State
# ============================================================================

_observability_initialized = False


# ============================================================================
# Core Observability Setup
# ============================================================================

def initialize_observability(
    langfuse_public_key: Optional[str] = None,
    langfuse_secret_key: Optional[str] = None,
    langfuse_host: Optional[str] = None,
    enable_console_export: bool = False,
) -> None:
    """
    Initialize OpenTelemetry observability with Langfuse integration.

    This function sets up:
    1. TracerProvider for distributed tracing
    2. OTLPSpanExporter pointing to Langfuse
    3. AgnoInstrumentor for automatic agent/tool/LLM instrumentation

    All agent runs, tool calls, and LLM calls are automatically traced.

    Args:
        langfuse_public_key: Langfuse public API key (default: from LANGFUSE_PUBLIC_KEY env var)
        langfuse_secret_key: Langfuse secret API key (default: from LANGFUSE_SECRET_KEY env var)
        langfuse_host: Langfuse host URL (default: from LANGFUSE_HOST env var or https://cloud.langfuse.com)
        enable_console_export: If True, also export traces to console for debugging

    Example:
        >>> from core.observability import initialize_observability
        >>> initialize_observability()
        >>> # Now all agent runs are traced to Langfuse automatically!

    Note:
        - This should be called ONCE at application startup, before creating any agents
        - If Langfuse keys are not provided, tracing is disabled (warning logged)
        - AgnoInstrumentor automatically captures: agent runs, tool calls, LLM calls, tokens, errors
    """
    global _observability_initialized

    if _observability_initialized:
        print("⚠️  Observability already initialized, skipping...")
        return

    # Get Langfuse credentials from environment or parameters
    public_key = langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = langfuse_secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    host = langfuse_host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # Check if Langfuse is configured
    if not public_key or not secret_key:
        print("⚠️  Warning: Langfuse keys not set. Traces will not be exported.")
        print("⚠️  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable observability.")
        # Still initialize AgnoInstrumentor for local metrics
        AgnoInstrumentor().instrument()
        _observability_initialized = True
        return

    # Configure Langfuse authentication
    langfuse_auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()

    # Set OpenTelemetry endpoint and headers for Langfuse
    langfuse_endpoint = f"{host}/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = langfuse_endpoint
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {langfuse_auth}"

    # Step 1: Create TracerProvider
    tracer_provider = TracerProvider()

    # Step 2: Add OTLP Exporter with Langfuse endpoint
    otlp_exporter = OTLPSpanExporter(
        endpoint=langfuse_endpoint,
        headers={"Authorization": f"Basic {langfuse_auth}"}
    )
    tracer_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))

    # Optional: Add console exporter for debugging
    if enable_console_export:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(SimpleSpanProcessor(console_exporter))

    # Step 3: Set the global tracer provider
    trace_api.set_tracer_provider(tracer_provider=tracer_provider)

    # Step 4: Instrument Agno (automatically traces all agents, tools, LLM calls)
    AgnoInstrumentor().instrument()

    _observability_initialized = True
    print(f"✓ Observability initialized: Traces exporting to {host}")


def is_observability_enabled() -> bool:
    """Check if observability has been initialized."""
    return _observability_initialized


def get_tracer(name: str = "layer4.team"):
    """
    Get a tracer for manual span creation.

    Args:
        name: Tracer name (default: "layer4.team")

    Returns:
        OpenTelemetry Tracer instance

    Example:
        >>> from core.observability import get_tracer
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("custom_operation"):
        >>>     # Your code here
        >>>     pass
    """
    return trace_api.get_tracer(name)


# ============================================================================
# Convenience Functions
# ============================================================================

def shutdown_observability() -> None:
    """
    Shutdown observability and flush all pending traces.

    Should be called on application shutdown to ensure all traces are exported.
    """
    global _observability_initialized

    if not _observability_initialized:
        return

    # Get the tracer provider and shutdown
    provider = trace_api.get_tracer_provider()
    if hasattr(provider, 'shutdown'):
        provider.shutdown()

    _observability_initialized = False
    print("✓ Observability shutdown complete")
