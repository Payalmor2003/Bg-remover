"""
Background-replacement stage — Azure OpenAI gpt-image-2 edit endpoint.
JSON body is NOT supported by this endpoint.
"""
from __future__ import annotations

import asyncio
import base64
import requests as http_requests
from config import PipelineConfig
from core.azure_client import get_api_key, get_endpoint
from utils.logger import get_logger
from utils.retry import async_retry

log = get_logger(__name__)

@async_retry(max_retries=5, backoff_base=2.0)
async def replace_background(
    image_bytes: bytes,
    filename: str,
    cfg: PipelineConfig,
) -> bytes:
    """
    Send one edit request to gpt-image-2 and return resulting image bytes.
    Retried automatically on 429 / network / 5xx errors via @async_retry.
    """
    content_type = _content_type(filename)

    url = (
        f"{get_endpoint().rstrip('/')}"
        f"/openai/deployments/{cfg.deployment_name}"
        f"/images/edits"
        f"?api-version={cfg.api_version}"
    )

    headers = {
        "api-key": get_api_key(),
    }

    # Azure expects field name "image[]"
    files = {
        "image[]": (filename, image_bytes, content_type),
    }

    data = {                                                                                                            # multipart form fields
        "model": cfg.deployment_name,
        "prompt": cfg.prompt,
        "n": "1",
        "size": "auto",
        "quality": cfg.quality,
        "output_format": cfg.output_format,
        # input_fidelity omitted — gpt-image-2 always uses high fidelity automatically
    }

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(                                                                              # executes request in bg
        None,
        lambda: http_requests.post(
            url, headers=headers, files=files, data=data, timeout=120
        ),
    )

    if response.status_code != 200:
        raise RuntimeError(f"Error code: {response.status_code} - {response.json()}")

    result = response.json()                                                                                            # converts response body to dictionary
    b64_data = result["data"][0].get("b64_json")
    if not b64_data:
        raise RuntimeError(f"No image data returned for {filename}")

    return base64.b64decode(b64_data)


def _content_type(filename: str) -> str:                                                                                # MIME type decision
    ext = filename.lower().rsplit(".", 1)[-1]
    return "image/png" if ext == "png" else "image/jpeg"                                                                # special case - png