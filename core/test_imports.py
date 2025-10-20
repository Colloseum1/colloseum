"""Test script to verify core Layer 4 dependencies are installed correctly."""

import sys

def test_imports():
    """Test that all core dependencies can be imported."""
    errors = []

    # Test Agno framework
    try:
        import agno
        print(f"✓ agno {agno.__version__}")
    except ImportError as e:
        errors.append(f"✗ agno: {e}")

    # Test httpx
    try:
        import httpx
        print(f"✓ httpx {httpx.__version__}")
    except ImportError as e:
        errors.append(f"✗ httpx: {e}")

    # Test pydantic
    try:
        import pydantic
        print(f"✓ pydantic {pydantic.__version__}")
    except ImportError as e:
        errors.append(f"✗ pydantic: {e}")

    # Test basic Agno agent creation
    try:
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat

        # Create a simple test agent (won't run, just test instantiation)
        agent = Agent(
            name="test_agent",
            model=OpenAIChat(id="gpt-4o-mini"),
            description="Test agent for import verification"
        )
        print(f"✓ Agno Agent instantiation successful")
    except Exception as e:
        errors.append(f"✗ Agno Agent creation: {e}")

    # Report results
    if errors:
        print("\n❌ Some imports failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    else:
        print("\n✅ All core dependencies imported successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(test_imports())
