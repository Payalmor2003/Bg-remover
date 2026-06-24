"""Async-friendly image I/O utilities."""
from __future__ import annotations

import asyncio
from io import BytesIO                                                                                                  # creates file like object in memory
from pathlib import Path
import aiofiles                                                                                                         # async file operations
from PIL import Image
from config import MAX_INPUT_BYTES
from utils.logger import get_logger

log = get_logger(__name__)

async def read_bytes_async(path: Path) -> bytes:
    async with aiofiles.open(path, "rb") as fh:                                                                   # reads images as binary
        data = await fh.read()
    if len(data) > MAX_INPUT_BYTES:                                                                                     # size validation
        raise ValueError(
            f"{path.name} is {len(data) / 1e6:.1f} MB — exceeds Azure's 50 MB limit"
        )
    return data


async def write_bytes_async(data: bytes, path: Path) -> None:                                                           # saving output file on disk
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "wb") as fh:
        await fh.write(data)


async def downscale_if_needed(data: bytes, max_dimension: int) -> bytes:                                                # resize large images
    if max_dimension <= 0:
        return data

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _resize_sync, data, max_dimension)                            # run_in_executor to avoid event loop blocking


def _resize_sync(data: bytes, max_dimension: int) -> bytes:                                                             # run_in_executor expects a sync callable
    img = Image.open(BytesIO(data))
    long_edge = max(img.size)
    if long_edge <= max_dimension:                                                                                      # resize on the basis of longest side
        return data

    scale = max_dimension / long_edge                                                                                   # preserves aspect ratio
    new_size = (int(img.width * scale), int(img.height * scale))
    img = img.convert("RGB").resize(new_size, Image.LANCZOS)                                                            # normalise image [LANCZOS-high quality downscaling]

    buf = BytesIO()                                                                                                     # all operations in memory
    img.save(buf, format="PNG")                                                                                         # png-lossless format
    return buf.getvalue()                                                                                               # final resized bytes