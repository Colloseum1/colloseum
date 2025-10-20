"""
Agno configuration for Layer 4 agents.

This module provides simple dict-based configuration for Agno agents and teams.
No complex Pydantic classes needed - Agno handles everything internally.
"""

import os
from typing import Dict, Any, Optional
from agno.db.postgres import PostgresDb


# ============================================================================
# Core Configuration Dictionary
# ============================================================================

AGNO_CONFIG: Dict[str, Any] = {
    # Session Management
    "enable_session_summaries": True,  # Automatically summarize long conversations
    "enable_user_memories": True,  # Remember user-specific context
    "add_session_summary_to_context": True,  # Include summaries in agent context
    "add_history_to_context": True,  # Include chat history in context
    "num_history_runs": 10,  # Number of previous runs to include
    "search_session_history": False,  # Search across multiple sessions (disable to save tokens)
    "num_history_sessions": 3,  # Number of past sessions to search (if enabled)

    # Session Storage
    "cache_session": True,  # Cache sessions in memory for faster access

    # Team Coordination
    "share_member_interactions": True,  # Team leader sees member agent interactions
    "show_members_responses": True,  # Include member responses in team output
    "store_member_responses": True,  # Store member responses in session

    # Streaming
    "stream": True,  # Enable streaming responses by default
    "stream_intermediate_steps": True,  # Show intermediate reasoning steps

    # Database Configuration (from environment)
    "db_url": os.getenv(
        "POSTGRES_DB_URL",
        "postgresql+psycopg://ai:ai@localhost:5532/ai"
    ),
    "session_table": "layer4_sessions",  # Dedicated table for Layer 4

    # OpenTelemetry / Observability
    "enable_telemetry": True,  # Enable automatic instrumentation
    "langfuse_host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    "langfuse_public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
    "langfuse_secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_db_connection() -> PostgresDb:
    """
    Get a PostgresDb connection using the configured database URL.

    Returns:
        PostgresDb: Configured database connection for session storage

    Raises:
        ValueError: If database URL is not configured

    Example:
        >>> db = get_db_connection()
        >>> agent = Agent(model=..., db=db)
    """
    db_url = AGNO_CONFIG["db_url"]
    if not db_url:
        raise ValueError(
            "PostgreSQL database URL not configured. "
            "Set POSTGRES_DB_URL environment variable."
        )

    return PostgresDb(
        db_url=db_url,
        session_table=AGNO_CONFIG["session_table"],
    )


def get_session_config(
    enable_summaries: Optional[bool] = None,
    enable_memories: Optional[bool] = None,
    **overrides: Any
) -> Dict[str, Any]:
    """
    Get session configuration dict for agent/team initialization.

    Args:
        enable_summaries: Override session summaries setting
        enable_memories: Override user memories setting
        **overrides: Additional config overrides

    Returns:
        Dict with session configuration parameters

    Example:
        >>> config = get_session_config(enable_summaries=True)
        >>> agent = Agent(model=..., db=db, **config)
    """
    config = {
        "enable_session_summaries": (
            enable_summaries
            if enable_summaries is not None
            else AGNO_CONFIG["enable_session_summaries"]
        ),
        "enable_user_memories": (
            enable_memories
            if enable_memories is not None
            else AGNO_CONFIG["enable_user_memories"]
        ),
        "add_session_summary_to_context": AGNO_CONFIG["add_session_summary_to_context"],
        "add_history_to_context": AGNO_CONFIG["add_history_to_context"],
        "num_history_runs": AGNO_CONFIG["num_history_runs"],
        "cache_session": AGNO_CONFIG["cache_session"],
    }

    # Apply overrides
    config.update(overrides)

    return config


def get_team_config(**overrides: Any) -> Dict[str, Any]:
    """
    Get team-specific configuration dict.

    Args:
        **overrides: Additional config overrides

    Returns:
        Dict with team configuration parameters

    Example:
        >>> config = get_team_config(show_members_responses=True)
        >>> team = Team(members=[...], **config)
    """
    config = {
        "share_member_interactions": AGNO_CONFIG["share_member_interactions"],
        "show_members_responses": AGNO_CONFIG["show_members_responses"],
        "store_member_responses": AGNO_CONFIG["store_member_responses"],
        **get_session_config(),
    }

    # Apply overrides
    config.update(overrides)

    return config


# ============================================================================
# Validation
# ============================================================================

def validate_config() -> bool:
    """
    Validate that all required configuration is present.

    Returns:
        bool: True if configuration is valid

    Raises:
        ValueError: If required configuration is missing
    """
    # Check database URL
    if not AGNO_CONFIG["db_url"]:
        raise ValueError(
            "PostgreSQL database URL not configured. "
            "Set POSTGRES_DB_URL environment variable."
        )

    # Check observability settings (warn only)
    if AGNO_CONFIG["enable_telemetry"]:
        if not AGNO_CONFIG["langfuse_public_key"]:
            print(
                "⚠️  Warning: Telemetry enabled but LANGFUSE_PUBLIC_KEY not set. "
                "Traces will not be exported."
            )
        if not AGNO_CONFIG["langfuse_secret_key"]:
            print(
                "⚠️  Warning: Telemetry enabled but LANGFUSE_SECRET_KEY not set. "
                "Traces will not be exported."
            )

    return True


# ============================================================================
# Environment Setup Helper
# ============================================================================

def print_config_status():
    """Print current configuration status for debugging."""
    print("=" * 70)
    print("Agno Configuration Status")
    print("=" * 70)
    print(f"Database URL: {AGNO_CONFIG['db_url'][:50]}...")
    print(f"Session Table: {AGNO_CONFIG['session_table']}")
    print(f"Session Summaries: {'✓' if AGNO_CONFIG['enable_session_summaries'] else '✗'}")
    print(f"User Memories: {'✓' if AGNO_CONFIG['enable_user_memories'] else '✗'}")
    print(f"History in Context: {'✓' if AGNO_CONFIG['add_history_to_context'] else '✗'}")
    print(f"Session Caching: {'✓' if AGNO_CONFIG['cache_session'] else '✗'}")
    print(f"Streaming: {'✓' if AGNO_CONFIG['stream'] else '✗'}")
    print(f"Telemetry: {'✓' if AGNO_CONFIG['enable_telemetry'] else '✗'}")

    if AGNO_CONFIG["enable_telemetry"]:
        has_langfuse = (
            AGNO_CONFIG["langfuse_public_key"] and
            AGNO_CONFIG["langfuse_secret_key"]
        )
        print(f"Langfuse Configured: {'✓' if has_langfuse else '✗ (keys missing)'}")

    print("=" * 70)


# Validate configuration on module import
try:
    validate_config()
except ValueError as e:
    print(f"⚠️  Configuration warning: {e}")
