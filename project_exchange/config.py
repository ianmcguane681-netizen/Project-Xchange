from __future__ import annotations

import os
import contextlib
import io
import logging
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


_ENV_LOADED: bool | None = None


def load_environment() -> bool:
    global _ENV_LOADED
    if _ENV_LOADED is not None:
        return _ENV_LOADED
    if not ENV_PATH.exists():
        _ENV_LOADED = False
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        _ENV_LOADED = False
        return False
    logger = logging.getLogger("dotenv.main")
    previous_disabled = logger.disabled
    logger.disabled = True
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            load_dotenv(ENV_PATH, override=False)
    finally:
        logger.disabled = previous_disabled
    _load_simple_env_fallback()
    _ENV_LOADED = True
    return True


def _load_simple_env_fallback() -> None:
    try:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_environment()


def secret(name: str) -> str:
    return os.getenv(name, "").strip()


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    status: str
    detail: str
    env_var: str


def status_for_key(provider: str, env_var: str, prefixes: tuple[str, ...] = (), min_length: int = 12) -> ProviderStatus:
    value = secret(env_var)
    if not value:
        return ProviderStatus(provider, "disconnected", f"{env_var} not set", env_var)
    if len(value) < min_length:
        return ProviderStatus(provider, "invalid", f"{env_var} looks too short", env_var)
    if prefixes and not value.startswith(prefixes):
        return ProviderStatus(provider, "invalid", f"{env_var} has an unexpected format", env_var)
    return ProviderStatus(provider, "connected", f"{env_var} loaded", env_var)


def provider_statuses() -> list[ProviderStatus]:
    return [
        status_for_key("OpenAI", "OPENAI_API_KEY", ("sk-",), 20),
        status_for_key("Tavily", "TAVILY_API_KEY", (), 12),
        status_for_key("SerpAPI", "SERPAPI_API_KEY", (), 12),
        status_for_key("NewsAPI", "NEWSAPI_API_KEY", (), 12),
    ]


def env_file_status() -> dict[str, object]:
    return {
        "env_file_detected": ENV_PATH.exists(),
        "dotenv_loaded": load_environment(),
        "path": str(ENV_PATH),
    }
