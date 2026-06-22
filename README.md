# World Cup Sweepstake Tracker

Python tracker for Jay, Dad, Reuben, and Nicola's 2026 World Cup sweepstake.

## Setup

```powershell
cd x:\personal\WC2026
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create an API key at football-data.org, then set:

```powershell
$env:FOOTBALL_DATA_API_KEY="your_api_key_here"
```

Or copy `worldcup_tracker\.env.example` to `worldcup_tracker\.env` and put the
key there.

Check the token:

```powershell
python .\worldcup_tracker\app.py --check-token
```

Optional:

```powershell
$env:FOOTBALL_DATA_COMPETITION="WC"
```

## Run Once

```powershell
python .\worldcup_tracker\app.py
```

## Auto Update Every 5 Minutes

```powershell
python .\worldcup_tracker\app.py --loop --interval 300
```

## Dashboard

```powershell
streamlit run .\worldcup_tracker\dashboard.py
```

## What It Scores Automatically

The first version automatically scores finished group-stage wins from
football-data.org match data.

The database also stores participants, team ownership, predictions, matches, and
score events. Knockout advancement and prediction scoring are structured in
`scoring.py`, ready to extend once the API data for final standings and scorers
is available.
