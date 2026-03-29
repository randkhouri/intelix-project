# SophosLabs Intelix — static file analysis client

Python client that uploads files from a local folder to **SophosLabs Intelix** static analysis, saves each JSON report as a **`.txt`** file, and logs progress to **stdout**.

## Historical vs current behavior

| Earlier design | Current design |
|----------------|----------------|
| Required exactly **one** `--exe`, **one** `--word`, and **one** `--pdf` | Scans a directory (default **`files/`**) for **all** matching files |
| Fixed count of three inputs | Any mix of counts (e.g. 5 PDFs, 1 EXE, 0 Word), up to a **per-type limit** |

Supported extensions (non-recursive scan of the chosen folder only):

- **EXE:** `.exe`
- **Word:** `.doc`, `.docx`
- **PDF:** `.pdf`

**Limits:** By default, at most **20** files per category are analyzed (`exe`, `word`, `pdf`). If more files exist, the first 20 per category (sorted by filename) are used and a warning is logged. Override with `--max-per-type`.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  main.py    │────▶│  AuthClient  │────▶│ Intelix OAuth   │
│  (CLI +     │     │  (auth.py)   │     │ /oauth2/token   │
│   discovery)│     └──────────────┘     └─────────────────┘
└──────┬──────┘
       │
       ▼
┌──────────────┐     ┌──────────────────────────────┐
│ IntelixClient│────▶│ Regional static analysis API │
│ (client.py)  │     │ POST file → 200 or 202+poll  │
└──────┬───────┘     └──────────────────────────────┘
       │
       ▼
┌──────────────┐
│ ReportManager│──▶ reports/<type>_<stem>.txt (JSON, pretty-printed)
│ (reporter.py)│
└──────────────┘
```

- **`config.py`** — Loads `.env` (credentials, base URL, region, timeouts, polling).
- **`auth.py`** — OAuth2 client credentials, token cache with expiry, retries on transient failures.
- **`client.py`** — Builds regional URL, multipart upload, handles `200` vs `202` + poll `/reports/{jobId}`.
- **`reporter.py`** — Writes UTF-8 `.txt` files containing JSON.
- **`main.py`** — Discovers files under `files/` (or `--files-dir`), enforces caps, orchestrates the pipeline.

## Prerequisites

- Python 3.10+ recommended (tested with 3.14 in development).
- SophosLabs Intelix credentials (AWS Marketplace / onboarding).
- Network access to `*.api.labs.sophos.com`.

## Setup

```bash
git clone https://github.com/randkhouri/intelix-project.git
cd intelix-project
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables

Create a **`.env`** in the project root (never commit it):

| Variable | Purpose |
|----------|---------|
| `INTELIX_CLIENT_ID` | OAuth client ID |
| `INTELIX_CLIENT_SECRET` | OAuth client secret |
| `INTELIX_BASE_URL` | Optional; default `https://api.labs.sophos.com` |
| `INTELIX_REGION` | Optional; default `us` (e.g. `de`) |
| `INTELIX_STATIC_ANALYSIS_PATH` | Optional; default `/analysis/file/static/v1` |
| `INTELIX_TIMEOUT_SECONDS` | Optional HTTP timeout |
| `INTELIX_MAX_POLL_ATTEMPTS` / `INTELIX_POLL_INTERVAL_SECONDS` | Optional async poll tuning |

## Usage

1. Place any number of supported files under the **`files/`** directory (or another path you pass in).

2. Run from the project root:

```bash
python src/main.py
```

This uses **`files/`** by default and **`reports/`** for output.

### Common options

```bash
# Custom input folder
python src/main.py --files-dir /path/to/my/documents

# Custom output folder
python src/main.py --output-dir ./out

# Allow up to 10 files per category (exe / word / pdf)
python src/main.py --max-per-type 10
```

### Capture stdout (e.g. for assignment logs)

```bash
python src/main.py 2>&1 | tee logs/run.txt
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Every discovered file produced a saved report |
| `1` | Configuration/directory error or no supported files found |
| `2` | Partial failure (some files failed) |
| `99` | Unexpected fatal exception |

## Security notes

- Do **not** commit `.env` or real credentials.
- Do not submit confidential files to Intelix; use only non-sensitive test files.

## Dependencies

- `requests` — HTTP client
- `python-dotenv` — Load `.env`

## License / use

Provided as-is for educational and integration demonstration purposes.
