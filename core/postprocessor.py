"""
Post-processing stage.
"""
from __future__ import annotations

from io import BytesIO
from PIL import Image
from utils.logger import get_logger

log = get_logger(__name__)

def postprocess(image_bytes: bytes, output_format: str) -> bytes:
    """Validate the returned image is well-formed; re-encode defensively."""
    img = Image.open(BytesIO(image_bytes))                                                                              # pillow can't read files directly
    img.load()                                                                                                          # force decode now, not lazily later — surfaces corruption early

    buf = BytesIO()                                                                                                     # stores o/p image in memory
    fmt = "JPEG" if output_format.lower() == "jpeg" else "PNG"
    save_kwargs = {"quality": 95, "optimize": True} if fmt == "JPEG" else {"optimize": True}
    img.convert("RGB" if fmt == "JPEG" else img.mode).save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()                                                                                               # getvalue returns bytes of memory buffer
