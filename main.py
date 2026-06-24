"""
CLI entry point for the gpt-image-2 background-replacement pipeline.
"""
from __future__ import annotations

import asyncio                                                                                                          # for async execution
import sys
import pyodbc
import time
from config import DEFAULT_CONFIG
from processor import run_batch
from utils.logger import get_logger

log = get_logger(__name__)

POLL_INTERVAL_SECONDS = 10 * 60
ERROR_RETRY_SECONDS = 60

async def _poll_forever() -> None:
    while True:
        try:
            results = await run_batch(DEFAULT_CONFIG)
        except (EnvironmentError, pyodbc.Error) as exc:
            log.error("Configuration/DB error: %s — retrying in %ds", exc, ERROR_RETRY_SECONDS)
            await asyncio.sleep(ERROR_RETRY_SECONDS)
            continue

        if results:
            # Jobs were found and processed — loop again immediately
            continue

        # wait before checking again.
        log.info("No pending jobs. Sleeping %d seconds", POLL_INTERVAL_SECONDS)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

def main() -> int:
    try:
        asyncio.run(_poll_forever())
    except KeyboardInterrupt:
        log.info("Stopped by user (Ctrl+C).")
        return 0


if __name__ == "__main__":
    sys.exit(main())

