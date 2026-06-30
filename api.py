import os
from datetime import date, timedelta
from pathlib import Path

import requests


BASE_URL = "https://api.football-data.org/v4"


class FootballDataError(RuntimeError):
    pass


def load_dotenv_file():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def get_api_key():
    load_dotenv_file()
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise FootballDataError(
            "Missing FOOTBALL_DATA_API_KEY. Add it to your environment or .env file."
        )
    return api_key


def _headers():
    return {"X-Auth-Token": get_api_key()}


def fetch_matches(date_from=None, date_to=None, competition=None, status=None):
    params = {}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    if competition:
        params["competitions"] = competition
    if status:
        params["status"] = status

    response = requests.get(
        f"{BASE_URL}/matches",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    if response.status_code >= 400:
        if response.status_code == 400 and "token is invalid" in response.text.lower():
            raise FootballDataError(
                "football-data.org says the API token is invalid. Check "
                "worldcup_tracker\\.env and make sure FOOTBALL_DATA_API_KEY is "
                "the exact token from your football-data.org account."
            )
        raise FootballDataError(
            f"football-data.org returned {response.status_code}: {response.text}"
        )

    return response.json().get("matches", [])


def check_token():
    response = requests.get(
        f"{BASE_URL}/matches",
        headers=_headers(),
        timeout=30,
    )
    if response.status_code >= 400:
        raise FootballDataError(
            f"Token check failed with {response.status_code}: {response.text}"
        )
    return True


def fetch_scorers(limit=10):
    load_dotenv_file()
    competition = os.getenv("FOOTBALL_DATA_COMPETITION", "WC")
    response = requests.get(
        f"{BASE_URL}/competitions/{competition}/scorers",
        headers=_headers(),
        params={"limit": limit},
        timeout=30,
    )
    if response.status_code >= 400:
        raise FootballDataError(
            f"Could not load scorers: football-data.org returned "
            f"{response.status_code}: {response.text}"
        )
    return response.json().get("scorers", [])


def fetch_recent_world_cup_matches(days_back=3, days_forward=3):
    load_dotenv_file()
    today = date.today()
    return fetch_matches(
        date_from=(today - timedelta(days=days_back)).isoformat(),
        date_to=(today + timedelta(days=days_forward)).isoformat(),
        competition=os.getenv("FOOTBALL_DATA_COMPETITION", "WC"),
    )


def fetch_world_cup_matches(days_forward=None):
    load_dotenv_file()
    competition = os.getenv("FOOTBALL_DATA_COMPETITION", "WC")
    start = date.fromisoformat(os.getenv("WORLD_CUP_START_DATE", "2026-06-11"))
    end_date = os.getenv("WORLD_CUP_END_DATE")
    if end_date:
        end = date.fromisoformat(end_date)
    elif days_forward is None:
        end = date.fromisoformat("2026-07-19")
    else:
        end = date.today() + timedelta(days=days_forward)
    matches = []
    window_start = start

    # football-data.org treats dateTo as an exclusive boundary here, while also
    # rejecting periods longer than 10 days.
    exclusive_end = end + timedelta(days=1)
    while window_start < exclusive_end:
        window_end = min(window_start + timedelta(days=10), exclusive_end)
        matches.extend(
            fetch_matches(
                date_from=window_start.isoformat(),
                date_to=window_end.isoformat(),
                competition=competition,
            )
        )
        window_start = window_end

    unique_matches = {}
    for match in matches:
        unique_matches[str(match.get("id"))] = match
    return list(unique_matches.values())



