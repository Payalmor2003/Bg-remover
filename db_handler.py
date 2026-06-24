"""
SQL Server DB handler.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import pyodbc
from config import PipelineConfig
from utils.logger import get_logger

log = get_logger(__name__)

# Status codes written back via usp_UpdateWhiteBackgroundStatus
STATUS_SUCCESS = 1
STATUS_FAILURE = 2


@dataclass(frozen=True)
class StockImageJob:
    """One row returned by usp_GetStockImagesForWhiteBackground."""
    id: int
    inventory_number: str
    stock_image: str                                                                                    # filename only
    part_type: int
    created_date: object


def _build_connection_string(cfg: PipelineConfig) -> str:
    missing = [                                                                                                         # missing validation
        name for name, val in {
            "DB_SERVER": cfg.db_server,
            "DB_DATABASE": cfg.db_database,
            "DB_USERNAME": cfg.db_username,
            "DB_PASSWORD": cfg.db_password,
        }.items() if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required DB environment variable(s): {', '.join(missing)}. "
        )

    return (
        f"DRIVER={{{cfg.db_driver}}};"
        f"SERVER={cfg.db_server};"
        f"DATABASE={cfg.db_database};"
        f"UID={cfg.db_username};"
        f"PWD={cfg.db_password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


def _get_connection(cfg: PipelineConfig) -> pyodbc.Connection:
    conn_str = _build_connection_string(cfg)
    return pyodbc.connect(conn_str, timeout=10)


def _fetch_jobs_sync(cfg: PipelineConfig) -> list[StockImageJob]:
    jobs: list[StockImageJob] = []
    with _get_connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("EXEC usp_GetStockImagesForWhiteBackground")
        rows = cursor.fetchall()                                                                                        # returns all rows
        for row in rows:
            jobs.append(StockImageJob(                                                                                  # converting rows to dataclass
                id=row.Id,
                inventory_number=row.InventoryNumber,
                stock_image=row.StockImage,
                part_type=row.Type,
                created_date=row.CreatedDate,
            ))
    return jobs


def _update_status_sync(cfg: PipelineConfig, job_id: int, status: int) -> None:
    with _get_connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "EXEC usp_UpdateWhiteBackgroundStatus @Id = ?, @Status = ?",
            job_id, status,
        )
        conn.commit()


async def fetch_pending_jobs(cfg: PipelineConfig) -> list[StockImageJob]:
    loop = asyncio.get_running_loop()
    jobs = await loop.run_in_executor(None, _fetch_jobs_sync, cfg)                                        # to avoid blocking event loop, run_in_executor
    log.info("Fetched %d pending job(s) from DB", len(jobs))
    return jobs


async def update_job_status(cfg: PipelineConfig, job_id: int, status: int) -> None:
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _update_status_sync, cfg, job_id, status)
        log.debug("Updated job Id=%d → status=%d", job_id, status)
    except Exception as exc:  # noqa: BLE001
        # A failed status write should not crash the batch
        log.error("Failed to update status for Id=%d: %s", job_id, exc)