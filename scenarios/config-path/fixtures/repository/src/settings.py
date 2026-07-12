"""Settings loader for the blog CMS."""
import os

import yaml

CONFIG_ROOT = "config"


def load_settings(env: str | None = None) -> dict:
    env = env or os.environ.get("APP_ENV", "dev")
    path = f"{CONFIG_ROOT}/dev.yaml" if env in ("dev", "test") else f"{CONFIG_ROOT}/production.yaml"
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
