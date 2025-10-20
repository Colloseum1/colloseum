#!/usr/bin/env python3
"""
Layer 4 Core Setup Validation Script

This script validates that the Layer 4 core environment is correctly configured:
- All dependencies are installed
- Environment variables are set
- Infrastructure services are reachable
- Directory structure is correct
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check that all required dependencies are installed."""
    print("📦 Checking dependencies...")
    errors = []

    dependencies = [
        ("agno", "Agno framework"),
        ("httpx", "Async HTTP client"),
        ("pydantic", "Schema validation"),
        ("openai", "OpenAI SDK"),
        ("anthropic", "Anthropic SDK"),
        ("opentelemetry", "OpenTelemetry"),
        ("psycopg", "PostgreSQL driver"),
        ("lancedb", "LanceDB vector store"),
        ("fastapi", "FastAPI framework"),
    ]

    for module_name, description in dependencies:
        try:
            __import__(module_name)
            print(f"  ✓ {description} ({module_name})")
        except ImportError:
            errors.append(f"Missing dependency: {description} ({module_name})")
            print(f"  ✗ {description} ({module_name}) - NOT INSTALLED")

    return errors


def check_environment_variables():
    """Check that required environment variables are set."""
    print("\n🔐 Checking environment variables...")
    errors = []

    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        env_file = project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"  ℹ️  Loaded .env file from {env_file}")
        else:
            print(f"  ⚠️  No .env file found (using .env.example as reference)")
    except ImportError:
        errors.append("python-dotenv not installed (should be available)")

    # Required variables
    required_vars = [
        ("OPENAI_API_KEY", "OpenAI API key for GPT models"),
        ("POSTGRES_URL", "PostgreSQL connection string"),
        ("CLICKHOUSE_HTTP", "ClickHouse HTTP endpoint"),
    ]

    # Optional but recommended variables
    optional_vars = [
        ("ANTHROPIC_API_KEY", "Anthropic API key for Claude models"),
        ("LANGFUSE_PUBLIC_KEY", "Langfuse public key for observability"),
        ("LANGFUSE_SECRET_KEY", "Langfuse secret key for observability"),
        ("SIGNALS_URL", "Layer 3 signals service endpoint"),
        ("VALIDATE_URL", "Strategy validation service endpoint"),
        ("COMPILE_URL", "Strategy compilation service endpoint"),
        ("L5_SIM_URL", "Layer 5 simulator endpoint"),
    ]

    # Check required variables
    for var_name, description in required_vars:
        value = os.getenv(var_name)
        if not value or value.startswith("sk-...") or value.startswith("pk-..."):
            errors.append(f"Required: {var_name} ({description})")
            print(f"  ✗ {var_name} - NOT SET")
        else:
            # Mask sensitive values
            masked_value = f"{value[:10]}..." if len(value) > 10 else "***"
            print(f"  ✓ {var_name} = {masked_value}")

    # Check optional variables
    for var_name, description in optional_vars:
        value = os.getenv(var_name)
        if value and not value.startswith("sk-...") and not value.startswith("pk-..."):
            masked_value = f"{value[:10]}..." if len(value) > 10 else "***"
            print(f"  ✓ {var_name} = {masked_value} (optional)")
        else:
            print(f"  ⚠️  {var_name} - NOT SET (optional)")

    return errors


def check_directory_structure():
    """Check that the core directory structure is correct."""
    print("\n📁 Checking directory structure...")
    errors = []

    core_dir = project_root / "core"
    required_dirs = [
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

    if not core_dir.exists():
        errors.append("core/ directory not found")
        print(f"  ✗ core/ directory missing")
        return errors

    print(f"  ✓ core/ directory exists")

    for dir_name in required_dirs:
        dir_path = core_dir / dir_name
        init_file = dir_path / "__init__.py"

        if not dir_path.exists():
            errors.append(f"core/{dir_name}/ directory missing")
            print(f"  ✗ core/{dir_name}/")
        elif not init_file.exists():
            errors.append(f"core/{dir_name}/__init__.py missing")
            print(f"  ⚠️  core/{dir_name}/ (missing __init__.py)")
        else:
            print(f"  ✓ core/{dir_name}/")

    return errors


def check_infrastructure():
    """Check that infrastructure services are reachable."""
    print("\n🐳 Checking infrastructure services...")
    errors = []
    warnings = []

    import socket
    from urllib.parse import urlparse

    def check_port(host, port, service_name):
        """Check if a port is reachable."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            return False

    # Check required infrastructure
    services = [
        ("ClickHouse", "localhost", 8123),
        ("PostgreSQL", "localhost", 5432),
        ("Redis", "localhost", 6379),
    ]

    for service_name, host, port in services:
        if check_port(host, port, service_name):
            print(f"  ✓ {service_name} ({host}:{port})")
        else:
            warnings.append(f"{service_name} not reachable at {host}:{port}")
            print(f"  ⚠️  {service_name} ({host}:{port}) - NOT REACHABLE")

    # Optional services (Layer 4 specific)
    optional_services = [
        ("Grafana", "localhost", 3000),
    ]

    for service_name, host, port in optional_services:
        if check_port(host, port, service_name):
            print(f"  ✓ {service_name} ({host}:{port}) (optional)")
        else:
            print(f"  ⚠️  {service_name} ({host}:{port}) - NOT REACHABLE (optional)")

    if warnings:
        print(f"\n  💡 Run 'docker-compose up -d' to start infrastructure services")

    return errors


def main():
    """Run all validation checks."""
    print("=" * 70)
    print("Layer 4 Core Setup Validation")
    print("=" * 70)

    all_errors = []

    # Run all checks
    all_errors.extend(check_dependencies())
    all_errors.extend(check_environment_variables())
    all_errors.extend(check_directory_structure())
    all_errors.extend(check_infrastructure())

    # Report results
    print("\n" + "=" * 70)
    if all_errors:
        print("❌ Validation FAILED with errors:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print("\n💡 Fix the above issues and run this script again.")
        print("   See core/CONFIG.md for configuration details.")
        return 1
    else:
        print("✅ All validation checks PASSED!")
        print("\n🚀 Layer 4 core environment is ready for development.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
