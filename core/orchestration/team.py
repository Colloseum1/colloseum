"""
Team Orchestration for Layer 4 Pipeline.

This module implements the Team that coordinates Router → Planner → Narrator flow
with session management, streaming responses, and shared context.

The Team pattern:
1. User asks → RouterAgent (parse to RouterDecision)
2. RouterDecision → PlannerAgent (build StrategySpec with tools)
3. StrategySpecOutput → NarratorAgent (explain with citations)
4. Final output: ExplainedPlan with all details

Key features:
- PostgreSQL session storage for multi-turn conversations
- Streaming responses with intermediate steps
- Shared dependencies (rules, endpoints) via template variables
- Session summaries and user memories enabled by default
- Member response visibility for transparency
- Automatic metrics tracking (via core.monitoring)
"""

import os
from typing import Optional, Dict, Any, AsyncIterator
from pathlib import Path

from agno.team import Team
from agno.models.openai import OpenAIChat
from agno.run.team import TeamRunOutputEvent

from ..agents import create_router_agent, create_planner_agent, create_narrator_agent
from ..config import (
    get_db_connection,
    get_team_config,
    get_shared_dependencies,
    validate_dependencies,
)
from ..monitoring import (
    track_session_start,
    track_session_end,
    track_team_execution,
)


# ============================================================================
# Team Factory Function
# ============================================================================

def create_strategy_team(
    team_model_provider: Optional[str] = None,
    team_model_id: Optional[str] = None,
    db_url: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    rules_path: Optional[Path] = None,
    override_endpoints: Optional[Dict[str, str]] = None,
    override_auth: Optional[Dict[str, str]] = None,
    enable_streaming: bool = True,
    enable_session_summaries: bool = True,
    enable_user_memories: bool = True,
) -> Team:
    """
    Create and configure the Strategy Team for Layer 4 execution.

    The Team coordinates three specialist agents:
    - RouterAgent (gpt-4o-mini): Fast intent parsing
    - PlannerAgent (gpt-4o): Complex strategy construction with tools
    - NarratorAgent (gpt-4o-mini): Fast explanation with citations

    Args:
        team_model_provider: Model provider for team leader (default: 'openai')
        team_model_id: Model ID for team leader (default: 'gpt-4o')
        db_url: PostgreSQL connection URL (default: POSTGRES_DB_URL env var)
        session_id: Session ID for conversation history
        user_id: User ID for memory management
        rules_path: Path to rules.yml file (default: core/schemas/rules.yml)
        override_endpoints: Override service endpoints (for testing)
        override_auth: Override auth headers (for testing)
        enable_streaming: Enable streaming responses (default: True)
        enable_session_summaries: Enable conversation summaries (default: True)
        enable_user_memories: Enable user memory tracking (default: True)

    Returns:
        Configured Team instance ready for use

    Example:
        >>> # Create team with defaults
        >>> team = create_strategy_team()
        >>> result = team.run("Build me a SOL trend following strategy")
        >>>
        >>> # With custom session tracking
        >>> team = create_strategy_team(
        ...     session_id="user_123_session_001",
        ...     user_id="user_123",
        ...     enable_streaming=True,
        ... )
        >>> for chunk in team.run("...", stream=True):
        ...     print(chunk.content, end="", flush=True)
        >>>
        >>> # Async usage
        >>> async for chunk in team.arun("...", stream=True):
        ...     print(chunk.content, end="", flush=True)
    """
    # Get shared dependencies (rules, endpoints, auth)
    shared_deps = get_shared_dependencies(
        rules_path=rules_path,
        override_endpoints=override_endpoints,
        override_auth=override_auth,
    )

    # Validate dependencies
    validate_dependencies(shared_deps)

    # Setup database connection for session management
    db = None
    if db_url or os.getenv("POSTGRES_DB_URL"):
        db_url = db_url or os.getenv("POSTGRES_DB_URL")
        db = get_db_connection()

    # Get team configuration (session management settings)
    team_config = get_team_config(
        enable_summaries=enable_session_summaries,
        enable_memories=enable_user_memories,
    )

    # Create specialist agents
    # Note: Agents will receive shared_deps via Team's dependencies parameter
    # This allows template variable substitution in agent instructions

    # RouterAgent: Fast intent parsing (gpt-4o-mini)
    router = create_router_agent(
        # Uses environment defaults or explicit overrides
        rules_path=rules_path,
    )

    # PlannerAgent: Complex reasoning with tools (gpt-4o)
    planner = create_planner_agent(
        # Uses environment defaults
        # db_url is passed to team, not individual agents
    )

    # NarratorAgent: Fast explanations with RAG (gpt-4o-mini)
    narrator = create_narrator_agent(
        # Uses environment defaults
    )

    # Create team leader model
    # Default to gpt-4o for intelligent orchestration
    team_model = OpenAIChat(
        id=team_model_id or os.getenv("TEAM_MODEL_ID", "gpt-4o"),
        temperature=0.2,  # Slightly creative for coordination
    )

    # Create Team with orchestration logic
    team = Team(
        name="PromptFi Strategy Team",
        model=team_model,

        # Specialist agents in execution order
        members=[
            router,     # Step 1: Parse ask → RouterDecision
            planner,    # Step 2: Build spec → StrategySpecOutput
            narrator,   # Step 3: Explain → ExplainedPlan
        ],

        # Shared dependencies (injected into all agents)
        dependencies=shared_deps,

        # Session management
        db=db,
        session_id=session_id,
        user_id=user_id,

        # Team coordination settings
        share_member_interactions=team_config["share_member_interactions"],
        show_members_responses=team_config["show_members_responses"],
        store_member_responses=team_config["store_member_responses"],

        # Session features
        enable_session_summaries=team_config["enable_session_summaries"],
        enable_user_memories=team_config["enable_user_memories"],
        add_session_summary_to_context=team_config["add_session_summary_to_context"],
        add_history_to_context=team_config["add_history_to_context"],
        num_history_runs=team_config["num_history_runs"],
        cache_session=team_config["cache_session"],

        # Team leader instructions
        instructions=[
            "You are the PromptFi Strategy Team Leader.",
            "",
            "Your role: Orchestrate Router → Planner → Narrator pipeline for safe DeFi strategy creation.",
            "",
            "# EXECUTION WORKFLOW",
            "",
            "1. **RouterAgent** (First):",
            "   - Parses user's natural language ask",
            "   - Outputs: RouterDecision with assets, risk, horizon, archetype, constraints",
            "",
            "2. **PlannerAgent** (Second):",
            "   - Receives RouterDecision",
            "   - Uses ReasoningTools for extended CoT",
            "   - Calls HTTP tools: get_signals, validate, compile_spec, simulate, ch_query",
            "   - Outputs: StrategySpecOutput with spec, plan, sim_metrics",
            "",
            "3. **NarratorAgent** (Third):",
            "   - Receives StrategySpecOutput",
            "   - Uses Knowledge (RAG) for citations",
            "   - Outputs: ExplainedPlan with summary, citations, caps_enforced, sim_metrics",
            "",
            "# COORDINATION RULES",
            "",
            "- Always execute agents in order: Router → Planner → Narrator",
            "- Wait for each agent to complete before delegating to next",
            "- If any agent fails, STOP and return error to user",
            "- Preserve all intermediate outputs (RouterDecision, StrategySpecOutput)",
            "- Final output should be ExplainedPlan from NarratorAgent",
            "",
            "# ERROR HANDLING",
            "",
            "- Router fails → Return error immediately (cannot proceed without constraints)",
            "- Planner fails → Return error with partial RouterDecision",
            "- Narrator fails → Return StrategySpecOutput without explanation (degraded mode)",
            "",
            "# SHARED CONTEXT",
            "",
            f"All agents have access to:",
            f"- Policy rules from rules.yml: {len(shared_deps['venue_allowlist'])} venues allowed",
            f"- Service endpoints: {', '.join(shared_deps['endpoint_names'])}",
            f"- Authentication configured for all services",
        ],

        # Streaming configuration
        stream=enable_streaming,
        stream_intermediate_steps=True,

        # Display configuration
        markdown=True,
    )

    return team


# ============================================================================
# Convenience Async Wrapper
# ============================================================================

async def run_strategy_team_async(
    user_ask: str,
    team: Optional[Team] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    stream: bool = True,
) -> AsyncIterator[TeamRunOutputEvent]:
    """
    Async wrapper for running the Strategy Team with streaming.

    Args:
        user_ask: User's natural language request
        team: Pre-configured Team (creates new if None)
        session_id: Session ID for this conversation
        user_id: User ID for memory tracking
        stream: Enable streaming (default: True)

    Yields:
        TeamRunOutputEvent chunks with content and metadata

    Example:
        >>> async for chunk in run_strategy_team_async(
        ...     "Build me a SOL trend following strategy",
        ...     session_id="user_123_session_001",
        ...     user_id="user_123",
        ... ):
        ...     print(chunk.content, end="", flush=True)
    """
    if team is None:
        team = create_strategy_team(
            session_id=session_id,
            user_id=user_id,
            enable_streaming=stream,
        )

    async for chunk in team.arun(
        user_ask,
        stream=stream,
        stream_intermediate_steps=True,
        session_id=session_id,
        user_id=user_id,
    ):
        yield chunk


# ============================================================================
# Synchronous Runner (for non-async contexts)
# ============================================================================

def run_strategy_team(
    user_ask: str,
    team: Optional[Team] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    stream: bool = False,
    enable_metrics: bool = True,
) -> Any:
    """
    Synchronous runner for the Strategy Team with automatic metrics tracking.

    Args:
        user_ask: User's natural language request
        team: Pre-configured Team (creates new if None)
        session_id: Session ID for this conversation
        user_id: User ID for memory tracking
        stream: Enable streaming (default: False for sync)
        enable_metrics: Enable automatic metrics tracking (default: True)

    Returns:
        TeamRunOutputEvent with final result

    Example:
        >>> result = run_strategy_team(
        ...     "Build me a SOL trend following strategy",
        ...     session_id="user_123_session_001",
        ...     user_id="user_123",
        ... )
        >>> print(result.content)
        >>>
        >>> # Metrics are automatically tracked:
        >>> # - team_runs_total{status="success"} += 1
        >>> # - team_run_duration_seconds observed
        >>> # - session_count tracked
    """
    if team is None:
        team = create_strategy_team(
            session_id=session_id,
            user_id=user_id,
            enable_streaming=stream,
        )

    # Track session start (if metrics enabled)
    if enable_metrics and session_id:
        track_session_start(session_id, user_id)

    # Run team with automatic metrics tracking
    if enable_metrics:
        with track_team_execution():
            result = team.run(
                user_ask,
                stream=stream,
                stream_intermediate_steps=stream,
                session_id=session_id,
                user_id=user_id,
            )
    else:
        result = team.run(
            user_ask,
            stream=stream,
            stream_intermediate_steps=stream,
            session_id=session_id,
            user_id=user_id,
        )

    return result


# ============================================================================
# Team Session Management Helpers
# ============================================================================

def get_team_session_summary(team: Team, session_id: Optional[str] = None) -> str:
    """
    Get session summary for a team conversation.

    Args:
        team: Team instance
        session_id: Session ID (uses team's current session if None)

    Returns:
        Session summary text

    Example:
        >>> team = create_strategy_team()
        >>> team.run("Build me a strategy")
        >>> summary = get_team_session_summary(team)
    """
    session_summary = team.get_session_summary(session_id=session_id)
    return session_summary.summary if session_summary else "No summary available"


def get_team_chat_history(team: Team) -> list:
    """
    Get full chat history for a team session.

    Args:
        team: Team instance

    Returns:
        List of chat messages

    Example:
        >>> team = create_strategy_team()
        >>> team.run("Build me a strategy")
        >>> history = get_team_chat_history(team)
    """
    return team.get_chat_history()


def set_team_session_name(team: Team, session_name: Optional[str] = None, autogenerate: bool = False):
    """
    Set or autogenerate a session name.

    Args:
        team: Team instance
        session_name: Custom session name (or None to autogenerate)
        autogenerate: Use LLM to generate name based on content

    Example:
        >>> team = create_strategy_team()
        >>> team.run("Build me a SOL trend strategy")
        >>> set_team_session_name(team, autogenerate=True)
        >>> print(team.get_session_name())  # "SOL Trend Following Strategy"
    """
    if autogenerate:
        team.set_session_name(autogenerate=True)
    elif session_name:
        team.set_session_name(session_name=session_name)
    else:
        raise ValueError("Must provide session_name or set autogenerate=True")
