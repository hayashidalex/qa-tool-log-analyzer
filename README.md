# log-analyzer-fabric

## Overview

A Flask-based log analyzer for FABRIC's Q&A and Code Generation tools. Team members can view, filter, and rate AI tool queries/responses stored in log files. Features include:

- Log ingestion from `*_query.log` files
- Review workflow with ratings (response quality, query quality, URL quality)
- Interactive Plotly graphs for metrics visualization
- User authentication (login required to access)

> **Note:** This app is under active development. See [TODO.md](TODO.md) for known issues and planned improvements.

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Create a `.env` file

Create a `.env` file in the project root (Example):

```
FLASK_SECRET_KEY=replace_this_with_a_secret_key
FLASK_HOST=127.0.0.1
FLASK_PORT=5001

# Directory containing *_query.log files
LOG_DIR=<path/to/dir>

# SQLite database path (created automatically on first run)
DATABASE_PATH=./logs.db  # Or another name
```

> **macOS note:** Port 5000 is used by AirPlay. Use 5001 or disable AirPlay Receiver in System Settings → General → AirDrop & Handoff.

### 3. Add log files

Place your `*_query.log` files in the directory specified by `LOG_DIR`.

**Expected log format:**
```
YYYY-MM-DD HH:MM:SS,mmm - QUERY: ...
RESPONSE: ...
MODEL: ...
TOOL: ...
TESTER: ...   (optional)
```

### 4. Run the app

```bash
uv run python app.py
```

Visit `http://127.0.0.1:5001` in your browser.

## Authentication

Login is required. Credentials are stored in `users.json` (gitignored, plaintext — see TODO.md for planned improvements). There are two access levels:

- **Write users** (`write_users`) — can view and submit reviews
- **Read-only users** (`read_only_users`) — can view but cannot submit reviews

`users.json` format:
```json
{
    "write_users": {
        "username": "password"
    },
    "read_only_users": {
        "username": "password"
    }
}
```

### 5. Create `users.json`

Create a `users.json` file in the project root with at least one entry in `write_users`.

## Log Ingestion

The app creates the database and ingests all log files from `LOG_DIR` on startup. Use the **Update Logs** button to ingest any new entries added since the last load.
