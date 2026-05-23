#!/usr/bin/env python3
import json
import os
import signal
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

CFN_PLAYER_ID = os.environ["CFN_PLAYER_ID"]
BUCKLER_ID = os.environ["BUCKLER_ID"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
EXPECTED_CHARACTER = os.environ.get("CFN_CHARACTER", "M. Bison")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", 300))

BUCKLER_URL = (
    f"https://www.streetfighter.com/6/buckler/profile/{CFN_PLAYER_ID}/battlelog/rank"
)

_sheet_title: str | None = None

_shutdown = False


def _handle_signal(signum, _frame) -> None:
    global _shutdown
    print(f"Received signal {signum}, shutting down after current sleep...", flush=True)
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def fetch_mr() -> tuple[int, str]:
    session = requests.Session()
    session.cookies.set("buckler_id", BUCKLER_ID, domain="www.streetfighter.com")
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0"
    )

    resp = session.get(BUCKLER_URL, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    next_data_el = soup.find("script", {"id": "__NEXT_DATA__"})
    if not next_data_el:
        raise RuntimeError(
            "Could not find __NEXT_DATA__ in page — cookie is likely expired"
        )

    data = json.loads(next_data_el.string)
    try:
        banner = data["props"]["pageProps"]["fighter_banner_info"]
        league = banner["favorite_character_league_info"]
        mr = league["master_rating"]
        character = banner["favorite_character_name"]
    except KeyError as e:
        raise RuntimeError(
            f"Unexpected page structure (missing key {e}) — check CFN_PLAYER_ID or cookie"
        ) from e

    return mr, character


def _sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def init_sheet_title() -> None:
    global _sheet_title
    service = _sheets_service()
    meta = service.spreadsheets().get(spreadsheetId=GOOGLE_SHEET_ID).execute()
    _sheet_title = meta["sheets"][0]["properties"]["title"]
    print(f"Targeting sheet: '{_sheet_title}'", flush=True)


def get_last_mr() -> int | None:
    result = _sheets_service().spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{_sheet_title}!B:B",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return None
    return int(rows[-1][0])


def append_to_sheet(mr: int) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _sheets_service().spreadsheets().values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{_sheet_title}!A:B",
        valueInputOption="RAW",
        body={"values": [[timestamp, mr]]},
    ).execute()


def poll() -> None:
    try:
        mr, character = fetch_mr()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        return
    except requests.HTTPError as e:
        print(f"ERROR: HTTP {e.response.status_code} from Buckler", file=sys.stderr, flush=True)
        return

    if character != EXPECTED_CHARACTER:
        print(
            f"WARNING: favorite character is '{character}', expected '{EXPECTED_CHARACTER}'. "
            "Tracking anyway — update CFN_CHARACTER if intentional.",
            file=sys.stderr,
            flush=True,
        )

    if mr == 0:
        print(f"MR is 0 for {character} — not in Master rank yet, skipping.", flush=True)
        return

    try:
        last_mr = get_last_mr()
    except HttpError as e:
        print(f"ERROR: Could not read sheet: {e}", file=sys.stderr, flush=True)
        return

    if last_mr == mr:
        print(f"MR unchanged ({mr}), skipping.", flush=True)
        return

    try:
        append_to_sheet(mr)
    except HttpError as e:
        print(f"ERROR: Failed to write to sheet: {e}", file=sys.stderr, flush=True)
        return

    arrow = f"{last_mr} → {mr}" if last_mr is not None else str(mr)
    print(f"Logged MR: {arrow}", flush=True)


def main() -> None:
    once = "--once" in sys.argv

    try:
        init_sheet_title()
    except HttpError as e:
        print(f"ERROR: Could not read spreadsheet metadata: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    if once:
        poll()
        return

    print(f"Starting SF6 MR tracker — polling every {POLL_INTERVAL}s (Ctrl-C to stop)", flush=True)
    while not _shutdown:
        poll()
        for _ in range(POLL_INTERVAL):
            if _shutdown:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
