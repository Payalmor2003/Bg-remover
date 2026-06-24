"""
Pipeline orchestrator: read → preprocess → edit (gpt-image-2) → postprocess → write
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from config import PipelineConfig
from core.preprocessor import preprocess
from core.editor import replace_background
from core.postprocessor import postprocess
from db_handler import StockImageJob
from utils.image_io import write_bytes_async
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class ProcessResult:                                                                                                    # stores result in a structured format
    job: StockImageJob
    output_path: Path | None
    success: bool
    elapsed: float
    error: str = ""


async def process_image(job: StockImageJob, cfg: PipelineConfig) -> ProcessResult:
    start = time.monotonic()
    input_path = cfg.input_dir / job.stock_image
    output_path = cfg.output_dir / job.stock_image   # same filename, output folder

    try:
        if not input_path.exists():
            raise FileNotFoundError(f"Source image not found: {input_path}")

        # 1. Pre-process (read + downscale)
        log.debug("[Id=%d] preprocessing %s…", job.id, job.stock_image)
        prepared = await preprocess(input_path, cfg)

        # 2. Edit via gpt-image-2 (retry handled inside replace_background)
        log.debug("[Id=%d] calling gpt-image-2…", job.id)
        edited = await replace_background(prepared, job.stock_image, cfg)

        # 3. Post-process (validate + normalise)
        log.debug("[Id=%d] postprocessing…", job.id)
        final = postprocess(edited, cfg.output_format)

        # 4. Write — same filename as input, into the output directory
        log.debug("[Id=%d] writing → %s…", job.id, output_path)
        await write_bytes_async(final, output_path)

    except Exception as exc:
        elapsed = time.monotonic() - start
        log.error("✗ [Id=%d] %s — %s", job.id, job.stock_image, exc)
        return ProcessResult(job, None, False, elapsed, str(exc))

    elapsed = time.monotonic() - start
    log.info("✓ [Id=%d] %s  (%.1fs)", job.id, job.stock_image, elapsed)
    return ProcessResult(job, output_path, True, elapsed)