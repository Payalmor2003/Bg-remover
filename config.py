"""
Central configuration for the gpt-image-2 background-replacement pipeline.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    PROJECT_ROOT: Path = Path(sys.executable).resolve().parent
    BUNDLE_DIR: Path = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
else:
    PROJECT_ROOT: Path = Path(__file__).resolve().parent
    BUNDLE_DIR: Path = PROJECT_ROOT

load_dotenv(BUNDLE_DIR / ".env")

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})                                             # less look-up time and immutable using frozen set
# Azure image edit endpoint accepts PNG/JPG only — anything else is rejected upstream.

MAX_INPUT_BYTES: int = 50 * 1024 * 1024   # Azure hard limit: 50 MB per input image


@dataclass(frozen=True)
class PipelineConfig:
    # ---- Azure OpenAI connection -------------------------------------------
    api_version: str = "2025-04-01-preview"
    deployment_name: str = "gpt-image-2"

    # ---- SQL Server connection -----------------------------------------------
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_server: str = field(default_factory=lambda: os.environ.get("DB_SERVER", ""))                         # evaluated at object creation time rather than instance creation
    db_database: str = field(default_factory=lambda: os.environ.get("DB_DATABASE", ""))
    db_username: str = field(default_factory=lambda: os.environ.get("DB_USERNAME", ""))
    db_password: str = field(default_factory=lambda: os.environ.get("DB_PASSWORD", ""))

    # ---- rate limiting -------------------------------------------------------
    requests_per_minute: int = 4
    max_workers: int = 2

    # ---- retry logic ---------------------------------------------------------
    max_retries: int = 5
    retry_backoff_base: float = 2.0

    # ---- preprocessing ---------------------------------------------------------
    max_dimension: int = 1536

    # ---- edit request ---------------------------------------------------------
    prompt: str = (
        "Replace the background with a solid pure white background (#FFFFFF). "
        "Keep the main object perfectly unchanged — preserve its exact shape, "
        "edges, corners, color, texture, and proportions. Do not alter, crop, "
        "rotate, or stylize the object in any way. Studio product photography style."
    )
    quality: str = "medium"
    output_format: str = "png"
    input_fidelity: str = "high"

    # ---- paths ---------------------------------------------------------------
    input_dir: Path = Path(r"E:\Uploads\Sandbox\StockSkuImage")
    output_dir: Path = Path(r"E:\Uploads\Sandbox\StockImage")


DEFAULT_CONFIG = PipelineConfig()