"""Standalone test runner for isolated real validation (no pytest needed)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import conftest  # noqa: F401,E402 - applies test environment bootstrap

# honor a committed .env file the way the app bootstrap would
env_file = os.path.join(ROOT, ".env")
if os.path.exists(env_file):
    with open(env_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from tests.test_login import test_login_returns_token  # noqa: E402

try:
    test_login_returns_token()
except Exception as exc:  # noqa: BLE001
    print(f"FAILED: {exc}")
    sys.exit(1)
print("1 passed")
