"""
Basic setup tests to verify project configuration.
"""

import pytest
from pathlib import Path


def test_project_structure(project_root_path):
    """Test that the project structure is correct."""
    # Check main directories exist
    assert (project_root_path / "core").exists()
    assert (project_root_path / "data_plane").exists()
    assert (project_root_path / "schemas").exists()

    # Check core subdirectories
    core_subdirs = [
        "agents",
        "tools",
        "guardrails",
        "schemas",
        "tests",
        "knowledge",
        "orchestration",
        "workflows",
        "observability",
    ]

    for subdir in core_subdirs:
        assert (project_root_path / "core" / subdir).exists(), f"Missing core/{subdir}"
        assert (project_root_path / "core" / subdir / "__init__.py").exists(), \
            f"Missing core/{subdir}/__init__.py"


def test_core_dependencies_import():
    """Test that core dependencies can be imported."""
    # Test Agno framework
    import agno
    assert hasattr(agno, "__version__")

    # Test httpx
    import httpx
    assert hasattr(httpx, "__version__")

    # Test pydantic
    import pydantic
    assert hasattr(pydantic, "__version__")

    # Test OpenAI SDK
    import openai
    assert hasattr(openai, "__version__")

    # Test Anthropic SDK
    import anthropic
    assert hasattr(anthropic, "__version__")


def test_agno_agent_creation():
    """Test that we can create a basic Agno agent."""
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    # Create a test agent (won't run, just test instantiation)
    agent = Agent(
        name="test_agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        description="Test agent for setup verification"
    )

    assert agent.name == "test_agent"
    assert agent.description == "Test agent for setup verification"


def test_environment_variables(mock_env_vars):
    """Test that environment variables are accessible."""
    import os

    # Check required variables
    assert os.getenv("OPENAI_API_KEY") is not None
    assert os.getenv("POSTGRES_URL") is not None
    assert os.getenv("CLICKHOUSE_HTTP") is not None

    # Check that mock values are set
    assert "test" in os.getenv("OPENAI_API_KEY")


def test_config_files_exist(project_root_path):
    """Test that configuration files exist."""
    assert (project_root_path / ".env.example").exists()
    assert (project_root_path / ".gitignore").exists()
    assert (project_root_path / "pyproject.toml").exists()
    assert (project_root_path / "uv.lock").exists()
    assert (project_root_path / "docker-compose.yml").exists()
    assert (project_root_path / "core" / "README.md").exists()
    assert (project_root_path / "core" / "CONFIG.md").exists()


@pytest.mark.parametrize("subdir", [
    "agents",
    "tools",
    "guardrails",
    "schemas",
    "tests",
    "knowledge",
    "orchestration",
    "workflows",
    "observability",
])
def test_core_subdirectory_is_package(core_path, subdir):
    """Test that each core subdirectory is a proper Python package."""
    subdir_path = core_path / subdir
    assert subdir_path.exists(), f"{subdir} directory missing"
    assert subdir_path.is_dir(), f"{subdir} is not a directory"
    assert (subdir_path / "__init__.py").exists(), f"{subdir}/__init__.py missing"
