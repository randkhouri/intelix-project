# SophosLabs Intelix — static file analysis client

**Repository:** [github.com/randkhouri/intelix-project](https://github.com/randkhouri/intelix-project)

Python tool that scans a local **`files/`** folder, uploads each supported file to **SophosLabs Intelix** static analysis, saves every JSON response as a **`.txt`** report, and writes the same **INFO/ERROR** log lines to **stdout** and to a **timestamped file** under **`logs/`**.

---

## Workflow

1. **Configure logging** — Creates `logs/intelix_YYYYMMDD_HHMMSS.log` (unless you set `--log-file`) and mirrors all messages to the terminal.
2. **Validate** — Checks `.env` for `INTELIX_CLIENT_ID` and `INTELIX_CLIENT_SECRET`.
3. **Scan** — Reads the chosen directory (default **`files/`**, not subfolders) for regular files.
4. **Classify**
   - **Supported:** `.exe`, `.doc`, `.docx`, `.pdf` → queued for analysis (up to **20 per type** by default).
   - **Unsupported** (e.g. `.txt`, `.png`): **skipped** and an **`ERROR`** line is logged (terminal + log file).
   - **Subdirectories:** ignored (no error).
5. **Analyze** — For each queued file: OAuth token → POST file to Intelix → handle immediate `200` or async `202` + poll until the report JSON is ready.
6. **Save** — Writes `reports/<type>_<filename_stem>.txt` (pretty JSON). If two files would share the same name, a numeric suffix is added (`_2`, `_3`, …).


---

## Project layout

```
intelix-project/
├── files/              # Put inputs here (.exe, .doc, .docx, .pdf)
├── logs/               # Auto-created; one .log per run by default (gitignored)
├── reports/            # Intelix JSON saved as .txt (gitignored)
├── src/
│   ├── main.py         # CLI, folder scan, logging setup, orchestration
│   ├── config.py       # Environment / .env settings
│   ├── auth.py         # OAuth2 token + cache + expiry + retries
│   ├── client.py       # Static analysis API: upload + 200/202 + polling
│   └── reporter.py     # Write report JSON to .txt files
├── requirements.txt
├── .env                # You create this locally
└── README.md
```

---

## Prerequisites

- **Python 3.10+** (3.14 used in development).
- **Intelix** credentials (from AWS Marketplace).

## Setup

```bash
git clone https://github.com/randkhouri/intelix-project.git
cd intelix-project
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### `.env` (project root)

| Variable | Required | Purpose |
|----------|----------|---------|
| `INTELIX_CLIENT_ID` | Yes | OAuth client ID |
| `INTELIX_CLIENT_SECRET` | Yes | OAuth client secret |
| `INTELIX_BASE_URL` | No | Default `https://api.labs.sophos.com` |
| `INTELIX_REGION` | No | Default `us` (e.g. `de`) |
| `INTELIX_STATIC_ANALYSIS_PATH` | No | Default `/analysis/file/static/v1` |
| `INTELIX_TIMEOUT_SECONDS` | No | HTTP timeout (seconds) |
| `INTELIX_MAX_POLL_ATTEMPTS` | No | Max polls when job returns `202` |
| `INTELIX_POLL_INTERVAL_SECONDS` | No | Seconds between polls |

---

## Usage

```bash
# From project root: scan ./files, write ./reports, log to ./logs/intelix_<timestamp>.log
python src/main.py
```

### CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--files-dir` | `files` | Folder to scan (files only; not recursive) |
| `--output-dir` | `reports` | Where report `.txt` files are written |
| `--max-per-type` | `20` | Max files analyzed per category: exe, word, pdf |
| `--log-dir` | `logs` | Directory for log files |
| `--log-file` | *(timestamp)* | Log filename inside `--log-dir`; if omitted, `intelix_YYYYMMDD_HHMMSS.log` |

Examples:

```bash
python src/main.py --files-dir ~/Desktop/inbox --output-dir ./out
python src/main.py --max-per-type 10
python src/main.py --log-dir logs --log-file assignment.log
```