"""Shared private storage location for container and native installations.

Individual legacy path overrides take precedence in each adapter.
No directories or keys are created merely by importing this module.
"""
import os
from pathlib import Path


def config_dir(env=None):
    env = os.environ if env is None else env
    configured = env.get("FAMILY_CONFIG_DIR") or env.get("CALENDAR_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    # Dockerfile copies the backend into /app; native checkout keeps backend/.
    root = Path(__file__).resolve().parent
    return root / "config" if root == Path("/app") else root.parent / "config"


CONFIG_DIR = config_dir()
