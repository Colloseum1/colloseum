"""
Model factory for Layer 4 agents.

Provides centralized model creation supporting all Agno-compatible providers:
- OpenAI (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
- Anthropic (claude-3-5-sonnet, claude-3-5-haiku)
- Google (gemini-1.5-pro, gemini-1.5-flash)
- Groq (llama-3.1, deepseek-r1)
- AWS Bedrock (Claude via AWS)
- Nexus (multi-provider router)
- OpenRouter (100+ models)
"""

from .factory import create_model

__all__ = [
    "create_model",
]
