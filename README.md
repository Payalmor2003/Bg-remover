# bg-remover

Background-replacement pipeline using **Azure OpenAI gpt-image-2**. The model
edits each image in a single call, replacing the background with solid white
while preserving the main object's edges, corners, and proportions — no local
masking or compositing required.

```
input/
  └── part.jpg
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│              ASYNC BATCH PROCESSOR                        │
│  asyncio.Semaphore(workers)  +  AsyncLimiter(rpm)         │
│  retry w/ exponential back-off on 429 / network / 5xx     │
│                                                            │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ Preprocess │ → │ Edit (gpt-   │ → │ Postprocess  │    │
│  │ read+resize│   │ image-2 API) │   │ validate +   │    │
│  │            │   │ prompt-driven│   │ re-encode    │    │
│  │            │   │ white bg swap│   │              │    │
│  └────────────┘   └──────────────┘   └──────┬───────┘    │
│                                              │            │
│                                       ┌──────▼───────┐    │
│                                       │    Write     │    │
│                                       └──────────────┘    │
└──────────────────────────────────────────────────────────┘
        │
        ▼
output/
  └── part_white_bg.png
```

---

## Project Structure

Flat layout — no package wrapper, matches the Document_classifier style:

```
bg-remover/
├── main.py               # entry point — run this directly
├── config.py              # DEFAULT_CONFIG — all settings live here
├── processor.py            # batch runner: semaphore + rate limiter
├── core/
│   ├── azure_client.py    # cached AsyncAzureOpenAI client (env-var validated)
│   ├── pipeline.py        # single-image orchestrator
│   ├── preprocessor.py    # read + downscale before upload
│   ├── editor.py          # the actual gpt-image-2 edit() call
│   └── postprocessor.py   # validates/re-encodes the returned image
├── utils/
│   ├── image_io.py        # async read/write/resize
│   ├── logger.py           # shared logger
│   └── retry.py            # async_retry — retries 429/network/5xx only
├── tests/
│   └── test_pipeline.py   # 11 tests, Azure client fully mocked
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Why a single edit call (not generate + mask)

`gpt-image-2`'s edit endpoint does **not** document a `background=transparent`
parameter — that option exists only for `gpt-image-1`. Instead, this pipeline
sends the original image plus a precise prompt instructing the model to
replace the background with solid white while leaving the subject untouched.
`input_fidelity="high"` is set explicitly to bias the model toward preserving
the object's exact shape/edges rather than regenerating it.

## Rate limiting — important

Azure's default quota for `gpt-image-2` is **5 images/minute per deployment**.
This pipeline enforces that with two independent controls:

| Control | Purpose |
|---|---|
| `asyncio.Semaphore(max_workers)` | Caps concurrent in-flight requests |
| `AsyncLimiter(requests_per_minute)` | Caps the *rate* of new requests — the real constraint |
| `@async_retry` | Catches any 429s that slip through, backs off exponentially |

If you request a quota increase from Azure, raise the values in `config.py` to match.

---

## Setup

### 1. Install dependencies
```bash
pip install openai python-dotenv aiofiles aiolimiter Pillow numpy
```

### 2. Set Azure credentials via `.env`
Copy the template and fill in your real values:
```powershell
copy .env.example .env
notepad .env
```
```
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
```
The pipeline loads `.env` automatically on startup — no `setx`/`export` needed.

> If a real system environment variable with the same name already exists,
> it takes precedence over the `.env` value.

### 3. Deploy `gpt-image-2` in Azure
In the Azure Foundry portal, deploy a `gpt-image-2` model and note the
**deployment name** (default in `config.py` is `gpt-image-2` — edit
`config.py` if you named it differently).

---

## Usage

No CLI arguments — designed to run unattended (as a script or packaged
`.exe` on a server). Just run it:

```bash
python main.py
```

**Input/output locations are always relative to wherever `main.py` itself
lives** (anchored via `Path(__file__).resolve().parent` in `config.py`, NOT
the shell's current working directory):

```
bg-remover/            ← your project folder, can be anywhere (Downloads, C:\Projects, etc.)
├── main.py
├── input/              ← place source images here (PNG/JPG)
└── output/             ← processed images appear here (created automatically)
```

This means it behaves identically no matter where the project folder sits on
disk, or what directory a scheduler/service launches it from — it always
finds `input/` and `output/` next to `main.py`.

To change any setting (quality, model, prompt, rate limits, retries), edit
the defaults directly in `config.py` — there's a single `DEFAULT_CONFIG`
object used everywhere.

### Programmatic
```python
import asyncio
from config import DEFAULT_CONFIG
from processor import run_batch

results = asyncio.run(run_batch(DEFAULT_CONFIG))
```

> **Note:** DB-driven input discovery (fetching the folder path via a stored
> procedure, mirroring the Document_classifier project's `db_handler.py`
> pattern) is planned but not yet implemented — `input_dir`/`output_dir` are
> currently fixed paths in `config.py`. This will be added once the stored
> procedure contract is finalized.

---

## Cost & quota notes

- `quality="medium"` is the balanced default in `config.py`. Use `"low"` for bulk/preview runs, `"high"` only when final-output sharpness matters.
- Each image = one API call (no separate mask-generation step), keeping cost predictable.
- At the default 5 rpm quota, **100 images take ≈20 minutes**. Request a quota increase in the Azure portal if you need faster throughput.
- Input images are capped at 1536px long-edge by default to control upload size — raise `max_dimension` in `config.py` only if source detail is being lost.

---

## Running Tests
```bash
pytest tests/ -v
```
All tests mock the Azure client — no credentials or network access needed to run them.
