"""
Pre-processing stage.

"""
from __future__ import annotations

from pathlib import Path

from config import PipelineConfig
from utils.image_io import read_bytes_async, downscale_if_needed
from utils.logger import get_logger

log = get_logger(__name__)

async def preprocess(path: Path, cfg: PipelineConfig) -> bytes:                                                         # returns upload ready bytes
    """Read the source file and return upload-ready bytes."""
    raw = await read_bytes_async(path)
    resized = await downscale_if_needed(raw, cfg.max_dimension)
    return resized
