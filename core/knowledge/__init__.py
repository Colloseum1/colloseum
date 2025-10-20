"""
Knowledge base management for Layer 4 agents.

Provides LanceDB-based vector store for document retrieval and citation.
Used by NarratorAgent for evidence-based explanations with agentic RAG.

Exports:
- setup_knowledge_base: Initialize and seed knowledge base with documents
- get_knowledge_base: Get existing knowledge base instance
"""

from .setup import setup_knowledge_base, get_knowledge_base

__all__ = [
    "setup_knowledge_base",
    "get_knowledge_base",
]
