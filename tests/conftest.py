"""
tests/conftest.py
Pytest configuration and shared fixtures.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path for all tests
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Set mock mode for all tests to avoid requiring API keys
os.environ["LLM_MOCK"] = "1"

# Ensure test data paths are correct
os.environ["DATA_DIR"] = str(root_dir / "data")
