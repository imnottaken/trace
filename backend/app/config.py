"""
TRACE application configuration via pydantic-settings.
Loads from .env file and environment variables.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # --- Face ML ---
    FACE_MODEL: str = "buffalo_sc"
    FACE_DET_THRESH: float = 0.5
    SIMILARITY_THRESHOLD: float = 0.3

    # --- Search ---
    SEARCH_PROVIDER: str = "serpapi"  # serpapi | bing | mock
    SERPAPI_API_KEY: str = ""
    BING_SEARCH_API_KEY: str = ""
    MAX_SEARCH_CANDIDATES: int = 10

    # --- Blockchain ---
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"
    EVM_PRIVATE_KEY: str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    CONTRACT_ADDRESS: str = ""
    CHAIN_ID: int = 31337

    # --- Paths ---
    UPLOAD_DIR: str = "/tmp/trace_uploads"
    ABI_PATH: str = os.path.join(
        os.path.dirname(__file__), "blockchain", "abi", "TraceProof.json"
    )

    model_config = {
        "env_file": os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
