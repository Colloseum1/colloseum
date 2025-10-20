"""
LanceDB knowledge base setup for Layer 4 agents.

Initializes LanceDB vector store with OpenAI text-embedding-3-small embedder.
Seeds knowledge base with sample strategy documents for NarratorAgent citations.

Usage:
    >>> from core.knowledge import setup_knowledge_base
    >>> knowledge = setup_knowledge_base()
    >>> # Use with NarratorAgent
    >>> narrator = create_narrator_agent(knowledge=knowledge)
"""

import os
from pathlib import Path
from typing import Optional

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType


# Global knowledge base instance (singleton pattern)
_knowledge_base: Optional[Knowledge] = None


def setup_knowledge_base(
    uri: Optional[str] = None,
    table_name: str = "layer4_knowledge",
    recreate: bool = False,
) -> Knowledge:
    """
    Initialize LanceDB knowledge base with sample documents.

    Creates a LanceDB vector store with OpenAI embeddings and seeds it with
    sample strategy documents (audits, risk policies, governance proposals).

    Args:
        uri: Path to LanceDB database directory
             Defaults to tmp/lancedb relative to this file
        table_name: LanceDB table name for storing embeddings
                   Defaults to 'layer4_knowledge'
        recreate: If True, delete existing knowledge base and recreate
                 Defaults to False (reuse existing if available)

    Returns:
        Configured Knowledge instance ready for use with agents

    Example:
        >>> # First time setup - creates and seeds knowledge base
        >>> knowledge = setup_knowledge_base(recreate=True)
        >>>
        >>> # Subsequent calls - reuse existing knowledge base
        >>> knowledge = setup_knowledge_base()
    """
    global _knowledge_base

    # Return existing instance if available and not recreating
    if _knowledge_base is not None and not recreate:
        return _knowledge_base

    # Set default URI to tmp/lancedb
    if uri is None:
        uri = str(Path(__file__).parent.parent.parent / "tmp" / "lancedb")

    # Initialize LanceDB with OpenAI embedder
    vector_db = LanceDb(
        uri=uri,
        table_name=table_name,
        search_type=SearchType.hybrid,  # Combines vector + keyword search
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    )

    # Create Knowledge instance
    knowledge = Knowledge(
        name="Layer 4 Strategy Knowledge Base",
        description="Strategy audits, risk policies, and governance documentation for safe DeFi trading",
        vector_db=vector_db,
        max_results=5,  # Return top 5 most relevant documents
    )

    # Seed with sample documents if recreating or first time
    if recreate:
        _seed_knowledge_base(knowledge)

    # Cache for future use
    _knowledge_base = knowledge

    return knowledge


def get_knowledge_base() -> Optional[Knowledge]:
    """
    Get existing knowledge base instance.

    Returns cached knowledge base if available, otherwise None.
    Use setup_knowledge_base() to initialize if not yet created.

    Returns:
        Cached Knowledge instance or None if not initialized
    """
    return _knowledge_base


def _seed_knowledge_base(knowledge: Knowledge) -> None:
    """
    Seed knowledge base with sample documents.

    Adds strategy audits, risk policies, and governance proposals
    from the docs/ directory to the knowledge base.

    Args:
        knowledge: Knowledge instance to seed
    """
    docs_dir = Path(__file__).parent / "docs"

    # Add all markdown files from docs directory
    if docs_dir.exists():
        for doc_file in docs_dir.glob("*.md"):
            try:
                knowledge.add_content(
                    name=doc_file.stem,
                    path=str(doc_file),
                    metadata={
                        "doc_type": "strategy_documentation",
                        "source": doc_file.name
                    }
                )
                print(f"✅ Added {doc_file.name} to knowledge base")
            except Exception as e:
                print(f"⚠️  Failed to add {doc_file.name}: {e}")

    # If no local docs, add sample content from text
    if not list(docs_dir.glob("*.md")):
        print("ℹ️  No local docs found, adding sample content...")
        _add_sample_content(knowledge)


def _add_sample_content(knowledge: Knowledge) -> None:
    """
    Add sample strategy documentation as text content.

    Used as fallback when no local markdown files exist in docs/.

    Args:
        knowledge: Knowledge instance to add content to
    """
    # Sample strategy audit
    sample_audit = """
    # SOL Trend Following Strategy Audit

    ## Overview
    Strategy: sol_trend_ema_cross_30d
    Archetype: trend_follow
    Risk Level: Medium
    Backtest Period: 2024-01-01 to 2024-12-31

    ## Performance Metrics
    - Sharpe Ratio: 1.52 (per simulate tool output)
    - Total Returns: 2,480 bps (per simulate tool output)
    - Max Drawdown: 820 bps (per simulate tool output)
    - Hit Rate: 64.2% (per simulate tool output)
    - Capacity: $485,000 (per simulate tool output)

    ## Safety Guardrails Enforced
    - Oracle staleness: max 30s
    - Max slippage: 50 bps
    - Max drawdown: 1000 bps (Medium risk)
    - Min liquidity: $100,000
    - Oracle delta: max 500 bps (5%)
    - Spread cap: 20 bps

    ## Compliance Status
    ✅ PIT-only datasets (pit.oracle_prices_by_feed)
    ✅ Venue allowlist validated (Jupiter, Phoenix)
    ✅ Risk caps within policy limits
    ✅ No freeform numeric claims (all from simulate tool)
    """

    knowledge.add_content(
        text_content=sample_audit,
        name="sample_strategy_audit",
        metadata={"doc_type": "strategy_audit", "strategy": "sol_trend_ema_cross_30d"}
    )

    # Sample risk policy
    sample_risk_policy = """
    # Risk Policy - Layer 4 Strategy Construction

    ## Risk Level Classifications

    ### Low Risk
    - Max Drawdown: 500 bps (5%)
    - Target Sharpe: >1.5
    - Min Hit Rate: 60%
    - Conservative position sizing (5% of capital)

    ### Medium Risk
    - Max Drawdown: 1000 bps (10%)
    - Target Sharpe: >1.0
    - Min Hit Rate: 55%
    - Moderate position sizing (10% of capital)

    ### High Risk
    - Max Drawdown: 2000 bps (20%)
    - Target Sharpe: >0.8
    - Min Hit Rate: 50%
    - Aggressive position sizing (20% of capital)

    ## Mandatory Guardrails

    ### Oracle Checks
    - Max staleness: 30,000ms (30s)
    - Max oracle delta: 500 bps (5%)

    ### Liquidity Requirements
    - Min liquidity: $100,000 per venue
    - Min depth: $50,000 within 50bps

    ### Slippage & Spread
    - Max slippage: 50 bps (default)
    - Max spread: 20 bps

    ### Venue Policy
    - Allowed venues: Jupiter, Phoenix, Orca, Raydium, Meteora, Drift
    - Disallowed: Mango, Zeta (decommissioned)
    """

    knowledge.add_content(
        text_content=sample_risk_policy,
        name="risk_policy",
        metadata={"doc_type": "risk_policy"}
    )

    print("✅ Added sample content to knowledge base")
