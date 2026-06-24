"""
Async batch processor.

Flow:
  1. Fetch pending jobs from DB
  2. Process each job (read → edit via gpt-image-2 → write)
  3. Immediately write back status per job
"""
from __future__ import annotations

import asyncio                                                                                                          # for parallel execution
from aiolimiter import AsyncLimiter
from config import PipelineConfig
from core.pipeline import ProcessResult, process_image
from db_handler import StockImageJob, fetch_pending_jobs, update_job_status, STATUS_SUCCESS, STATUS_FAILURE
from utils.logger import get_logger

log = get_logger(__name__)


async def run_batch(cfg: PipelineConfig) -> list[ProcessResult]:
    jobs = await fetch_pending_jobs(cfg)                                                                                # all unprocessed images/jobs
    if not jobs:
        log.warning("No pending jobs returned by usp_GetStockImagesForWhiteBackground")
        return []

    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(cfg.max_workers)                                                                      # Only 2 jobs simultaneously(concurrency)
    limiter = AsyncLimiter(max_rate=cfg.requests_per_minute, time_period=60)                                            # throughput

    async def _bounded(job: StockImageJob) -> ProcessResult:
        async with semaphore:
            async with limiter:
                result = await process_image(job, cfg)

        # Write status back right away
        status = STATUS_SUCCESS if result.success else STATUS_FAILURE
        await update_job_status(cfg, job.id, status)
        return result

    log.info(
        "Starting batch: %d job(s), %d worker(s), %d req/min quota",
        len(jobs), cfg.max_workers, cfg.requests_per_minute,
    )
    results: list[ProcessResult] = await asyncio.gather(                                                                # runs multiple coroutines concurrently
        *(_bounded(j) for j in jobs),
        return_exceptions=False,
    )

    _print_summary(results)
    return results


def _print_summary(results: list[ProcessResult]) -> None:
    ok = [r for r in results if r.success]                                                                              # processed successfully
    fail = [r for r in results if not r.success]                                                                        # failed
    total_time = sum(r.elapsed for r in results)

    log.info(
        "Batch complete — %d succeeded, %d failed, total time %.1fs",
        len(ok), len(fail), total_time,
    )
    for r in fail:
        log.error("  FAILED: Id=%d %s — %s", r.job.id, r.job.stock_image, r.error)