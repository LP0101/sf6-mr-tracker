# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Run once (for testing / debugging)
.venv/bin/python3 tracker.py --once

# Run as daemon (polls on POLL_INTERVAL_SECONDS)
.venv/bin/python3 tracker.py

# Build Docker image
sudo docker build -t ghcr.io/lp0101/sf6-tracker:latest .

# Run via Compose
sudo docker compose up -d
```

## Architecture

Single-file script (`tracker.py`) with no framework. On each poll cycle:

1. **Fetch MR** — GET `https://www.streetfighter.com/6/buckler/profile/{CFN_PLAYER_ID}/battlelog/rank` with the `buckler_id` cookie. Parses `#__NEXT_DATA__` embedded JSON; MR lives at `props.pageProps.fighter_banner_info.favorite_character_league_info.master_rating`. Auth is entirely cookie-based — `buckler_id` on `www.streetfighter.com` is the session token.

2. **Deduplication** — reads the last value in column B of the first sheet (by index, not by name) via the Sheets API. Skips writing if MR is unchanged.

3. **Append** — writes `[timestamp, MR]` to the first sheet if MR changed.

The first sheet is resolved by index at startup via `init_sheet_title()` so renaming it doesn't break anything. Sheets 2+ are reserved for user-built visualizations.

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `BUCKLER_ID` | yes | — | `buckler_id` cookie value from `www.streetfighter.com` |
| `CFN_PLAYER_ID` | yes | — | Numeric UID from Buckler profile URL |
| `GOOGLE_SHEET_ID` | yes | — | Spreadsheet ID from the sheet URL |
| `GOOGLE_CREDENTIALS_PATH` | no | `credentials.json` | Service account JSON key |
| `CFN_CHARACTER` | no | `M. Bison` | Warns if favorite character doesn't match |
| `POLL_INTERVAL_SECONDS` | no | `300` | Ignored when running with `--once` |
| `DISCORD_WEBHOOK_URL` | no | — | If set, sends a Discord message when the cookie expires (HTTP 403) |

Google Sheets access uses a service account. The sheet must be shared with the service account email (Editor role).

## Cookie TTL

`buckler_id` has an unknown TTL — community reports suggest weeks. When expired, the script exits with `ERROR: HTTP 403 from Buckler`.
