"""Regression: corporate sandbox gate executes before any ORM engine import.

The subprocess has no Neon/Clerk/Railway credentials or external networking.
"""
import os
from pathlib import Path
import subprocess
import sys


def test_sandbox_gate_precedes_legacy_create_all():
    source = Path("backend/main.py").read_text(encoding="utf-8")
    assert source.index('if os.getenv("AXS_CORPORATE_SANDBOX_ONLY"') < source.index(
        "from .db.core import Base_CORE, engine_core"
    )
    assert source.index("check_data(os.environ)") < source.index("Base_CORE.metadata.create_all(")


def test_sandbox_import_denied_with_missing_configuration():
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path.cwd()),
        "AXS_CORPORATE_SANDBOX_ONLY": "true",
        "AXS_CORPORATE_API_ENABLED": "false",
        "AXS_CORPORATE_PROVISIONING_ENABLED": "false",
        "APP_ENV": "development",
        "ENV": "development",
        "ENVIRONMENT": "production",
        # No DATABASE URLs or real secrets.
    }
    run = subprocess.run(
        [sys.executable, "-c", "import backend.main"],
        env=env, capture_output=True, text=True, timeout=20, check=False,
    )
    assert run.returncode != 0
    assert "Sandbox corporativo:" in run.stderr
    assert "create_all" not in run.stderr
