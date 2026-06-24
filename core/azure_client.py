"""
Azure OpenAI client for gpt-image-2 image edits.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

from utils.logger import get_logger

log = get_logger(__name__)

_REQUIRED_ENV_VARS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")

# Loaded once at import time. Existing real environment variables always
# take precedence over .env values (override=False is the default).
load_dotenv()


def _validate_env() -> None:
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Create a .env file in the project root (see .env.example) or "
            "set them as system environment variables."
        )


@lru_cache(maxsize=1)
def get_client(api_version: str) -> AsyncAzureOpenAI:
    """
    Create a single shared async client for the process lifetime.
    Cached so repeated calls (one per image) don't re-init connections.
    """
    _validate_env()
    return AsyncAzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=api_version,
    )
def get_endpoint() -> str:
    """Return the Azure OpenAI endpoint (loads .env if needed)."""
    _validate_env()
    return os.environ["AZURE_OPENAI_ENDPOINT"]


def get_api_key() -> str:
    """Return the Azure OpenAI API key (loads .env if needed)."""
    _validate_env()
    return os.environ["AZURE_OPENAI_API_KEY"]