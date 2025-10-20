"""
Model factory for Layer 4 agents.

Provides centralized model creation supporting all Agno-compatible providers.
Configuration via environment variables for flexible deployment.

Example:
    >>> # Using environment variables
    >>> os.environ['ROUTER_MODEL_PROVIDER'] = 'openai'
    >>> os.environ['ROUTER_MODEL_ID'] = 'gpt-4o-mini'
    >>> model = create_model()

    >>> # Explicit configuration
    >>> model = create_model(
    ...     provider='anthropic',
    ...     model_id='claude-3-5-haiku-20241022',
    ...     temperature=0.1
    ... )
"""

from typing import Optional, Any, Dict, Type


# Provider registry mapping provider names to import paths
# Using lazy imports to avoid requiring all provider packages
PROVIDER_IMPORT_MAP: Dict[str, tuple] = {
    "openai": ("agno.models.openai", "OpenAIChat"),
    "anthropic": ("agno.models.anthropic", "Claude"),
    "google": ("agno.models.google", "Gemini"),
    "groq": ("agno.models.groq", "Groq"),
    "aws": ("agno.models.aws", "Claude"),
    "nexus": ("agno.models.nexus", "Nexus"),
    "openrouter": ("agno.models.openrouter", "OpenRouter"),
}


def _import_model_class(provider: str) -> Type:
    """
    Lazily import model class for given provider.

    Args:
        provider: Provider name (must be in PROVIDER_IMPORT_MAP)

    Returns:
        Model class for the provider

    Raises:
        ImportError: If provider package not installed
        ValueError: If provider not supported
    """
    if provider not in PROVIDER_IMPORT_MAP:
        raise ValueError(
            f"Unsupported provider: '{provider}'. "
            f"Supported providers: {', '.join(sorted(PROVIDER_IMPORT_MAP.keys()))}"
        )

    module_path, class_name = PROVIDER_IMPORT_MAP[provider]

    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ImportError as e:
        raise ImportError(
            f"Failed to import {provider} provider. "
            f"Please install the required package: {e}"
        )


def create_model(
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs: Any
):
    """
    Create an Agno-compatible model instance.

    Supports 7 providers: openai, anthropic, google, groq, aws, nexus, openrouter.
    Falls back to environment variables if parameters not provided.

    Args:
        provider: Provider name (openai|anthropic|google|groq|aws|nexus|openrouter)
                  Defaults to ROUTER_MODEL_PROVIDER env var or 'openai'
        model_id: Model identifier (e.g., 'gpt-4o-mini', 'claude-3-5-haiku-20241022')
                  Defaults to ROUTER_MODEL_ID env var or provider-specific default
        temperature: Sampling temperature (0.0-1.0)
                     Defaults to ROUTER_MODEL_TEMPERATURE env var or None
        **kwargs: Additional model-specific parameters

    Returns:
        Agno model instance ready for use in Agent()

    Raises:
        ValueError: If provider is unsupported or required parameters missing

    Examples:
        >>> # OpenAI with environment defaults
        >>> model = create_model()

        >>> # Anthropic with explicit config
        >>> model = create_model(
        ...     provider='anthropic',
        ...     model_id='claude-3-5-sonnet-20241022',
        ...     temperature=0.2
        ... )

        >>> # OpenRouter with custom parameters
        >>> model = create_model(
        ...     provider='openrouter',
        ...     model_id='anthropic/claude-3.5-sonnet',
        ...     temperature=0.1,
        ...     max_tokens=4000
        ... )

        >>> # Use in Agent
        >>> from agno.agent import Agent
        >>> agent = Agent(
        ...     name="Router",
        ...     model=create_model(provider='google', model_id='gemini-1.5-flash'),
        ...     ...
        ... )
    """
    import os

    # Default provider and model configurations
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-20241022",
        "google": "gemini-1.5-flash",
        "groq": "deepseek-r1-distill-llama-70b",
        "aws": "claude-3-5-haiku-20241022",
        "nexus": "anthropic/claude-sonnet-4-20250514",
        "openrouter": "anthropic/claude-3.5-sonnet",
    }

    # Resolve provider from parameter or environment
    provider = provider or os.getenv("ROUTER_MODEL_PROVIDER", "openai")
    provider = provider.lower().strip()

    # Validate provider (will raise ValueError if unsupported)
    # Import is done in _import_model_class()

    # Resolve model ID
    if model_id is None:
        model_id = os.getenv("ROUTER_MODEL_ID")
        if model_id is None:
            model_id = DEFAULT_MODELS[provider]

    # Resolve temperature
    if temperature is None:
        temp_env = os.getenv("ROUTER_MODEL_TEMPERATURE")
        if temp_env is not None:
            try:
                temperature = float(temp_env)
            except ValueError:
                raise ValueError(
                    f"Invalid ROUTER_MODEL_TEMPERATURE: '{temp_env}'. Must be a float."
                )

    # Build model kwargs
    model_kwargs = {"id": model_id, **kwargs}
    if temperature is not None:
        model_kwargs["temperature"] = temperature

    # Lazily import and instantiate model
    model_class = _import_model_class(provider)
    return model_class(**model_kwargs)
