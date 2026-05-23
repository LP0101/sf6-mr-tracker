# sf6-mr-tracker

> This project was built with AI assistance. The code was written by someone who knows what they're doing and has been reviewed before shipping.

Polls your Street Fighter 6 Master Rating from the Buckler's Boot Camp site and logs every change to a Google Sheet with a timestamp.

## How it works

On each poll cycle the script fetches your rank battle log page, extracts the MR from the embedded `__NEXT_DATA__` JSON, and appends `[timestamp, MR]` to the first sheet in your spreadsheet — but only when the value has actually changed. Sheets 2+ are left free for your own charts and visualizations.

## Setup

### 1. Google Sheets service account

1. Create a service account in Google Cloud Console and download its JSON key.
2. Enable the **Google Sheets API** for the project.
3. Share your target spreadsheet with the service account email (Editor role).
4. Save the key file as `credentials.json` next to `tracker.py` (or set `GOOGLE_CREDENTIALS_PATH`).

### 2. Buckler cookie

Log in to [www.streetfighter.com/6/buckler](https://www.streetfighter.com/6/buckler), open DevTools, and copy the value of the `buckler_id` cookie. This is your session token — the tracker is entirely cookie-authenticated.

> The cookie TTL is unknown but community reports suggest it lasts weeks. When it expires the script prints `ERROR: HTTP 403 from Buckler` and sends a Discord notification if `DISCORD_WEBHOOK_URL` is set.

### 3. Environment variables

Create a `.env` file (or pass variables directly):

```env
BUCKLER_ID=<buckler_id cookie value>
CFN_PLAYER_ID=<numeric UID from your Buckler profile URL>
GOOGLE_SHEET_ID=<spreadsheet ID from the sheet URL>

# Optional
GOOGLE_CREDENTIALS_PATH=credentials.json
CFN_CHARACTER=M. Bison
POLL_INTERVAL_SECONDS=300
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

| Variable | Required | Default | Notes |
|---|---|---|---|
| `BUCKLER_ID` | yes | — | `buckler_id` cookie from `www.streetfighter.com` |
| `CFN_PLAYER_ID` | yes | — | Numeric UID from your Buckler profile URL |
| `GOOGLE_SHEET_ID` | yes | — | Spreadsheet ID from the sheet URL |
| `GOOGLE_CREDENTIALS_PATH` | no | `credentials.json` | Path to service account JSON key |
| `CFN_CHARACTER` | no | `M. Bison` | Warns if your tracked character doesn't match |
| `POLL_INTERVAL_SECONDS` | no | `300` | Seconds between polls (ignored with `--once`) |
| `DISCORD_WEBHOOK_URL` | no | — | If set, sends a Discord message when the cookie expires (HTTP 403) |

## Running

### Docker Compose (recommended)

```bash
sudo docker compose up -d
```

The compose file mounts `credentials.json` read-only and loads env from `.env`. The container restarts automatically unless stopped manually.

### Local Python

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Run once (useful for testing)
.venv/bin/python3 tracker.py --once

# Run as daemon
.venv/bin/python3 tracker.py
```

### Docker image

```bash
sudo docker build -t ghcr.io/lp0101/sf6-mr-tracker:latest .
```
