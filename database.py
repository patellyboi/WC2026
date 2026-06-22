import sqlite3
from pathlib import Path

from participants import PLAYERS


DB_PATH = Path(__file__).with_name("database.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS teams (
    name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    FOREIGN KEY(owner) REFERENCES players(name)
);

CREATE TABLE IF NOT EXISTS predictions (
    player TEXT NOT NULL,
    category TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY(player, category),
    FOREIGN KEY(player) REFERENCES players(name)
);

CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    utc_date TEXT,
    competition TEXT,
    stage TEXT,
    status TEXT,
    home_team TEXT,
    away_team TEXT,
    home_score INTEGER,
    away_score INTEGER,
    raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS score_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT UNIQUE NOT NULL,
    player TEXT NOT NULL,
    team TEXT,
    points INTEGER NOT NULL,
    reason TEXT NOT NULL,
    source_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(player) REFERENCES players(name)
);
"""


def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    for player, data in PLAYERS.items():
        conn.execute("INSERT OR IGNORE INTO players(name) VALUES (?)", (player,))
        for team in data["teams"]:
            conn.execute(
                "INSERT OR REPLACE INTO teams(name, owner) VALUES (?, ?)",
                (team, player),
            )
        for category, value in data["predictions"].items():
            conn.execute(
                """
                INSERT OR REPLACE INTO predictions(player, category, value)
                VALUES (?, ?, ?)
                """,
                (player, category, str(value)),
            )
    conn.commit()


def save_match(conn, match):
    import json

    score = match.get("score", {}).get("fullTime", {})
    conn.execute(
        """
        INSERT OR REPLACE INTO matches(
            id, utc_date, competition, stage, status, home_team, away_team,
            home_score, away_score, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(match["id"]),
            match.get("utcDate"),
            match.get("competition", {}).get("name"),
            match.get("stage"),
            match.get("status"),
            match.get("homeTeam", {}).get("name"),
            match.get("awayTeam", {}).get("name"),
            score.get("home"),
            score.get("away"),
            json.dumps(match),
        ),
    )


def add_score_event(conn, event):
    event_key = (
        f"{event['match_id']}:{event['player']}:{event.get('team', '')}:"
        f"{event['reason']}"
    )
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO score_events(
            event_key, player, team, points, reason, source_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            event_key,
            event["player"],
            event.get("team"),
            event["points"],
            event["reason"],
            event["match_id"],
        ),
    )
    return cursor.rowcount == 1


def leaderboard(conn):
    return conn.execute(
        """
        SELECT p.name, COALESCE(SUM(e.points), 0) AS points
        FROM players p
        LEFT JOIN score_events e ON e.player = p.name
        GROUP BY p.name
        ORDER BY points DESC, p.name ASC
        """
    ).fetchall()


def score_events(conn):
    return conn.execute(
        """
        SELECT player, team, points, reason, source_id, created_at
        FROM score_events
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()


def recent_matches(conn, limit=20):
    return conn.execute(
        """
        SELECT utc_date, competition, stage, status, home_team, away_team,
               home_score, away_score
        FROM matches
        ORDER BY utc_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def played_matches(conn, limit=30):
    return conn.execute(
        """
        SELECT utc_date, competition, stage, status, home_team, away_team,
               home_score, away_score
        FROM matches
        WHERE status = 'FINISHED'
        ORDER BY utc_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def tournament_stats(conn):
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS stored_matches,
            SUM(CASE WHEN status = 'FINISHED' THEN 1 ELSE 0 END) AS finished_matches,
            SUM(CASE WHEN status != 'FINISHED' THEN 1 ELSE 0 END) AS upcoming_matches,
            SUM(
                CASE
                    WHEN status = 'FINISHED'
                    THEN COALESCE(home_score, 0) + COALESCE(away_score, 0)
                    ELSE 0
                END
            ) AS total_goals
        FROM matches
        """
    ).fetchone()
    return {
        "stored_matches": row["stored_matches"] or 0,
        "finished_matches": row["finished_matches"] or 0,
        "upcoming_matches": row["upcoming_matches"] or 0,
        "total_goals": row["total_goals"] or 0,
    }


def top_scoring_teams(conn, limit=8):
    return conn.execute(
        """
        SELECT team, SUM(goals) AS goals
        FROM (
            SELECT home_team AS team, COALESCE(home_score, 0) AS goals
            FROM matches
            WHERE status = 'FINISHED'
            UNION ALL
            SELECT away_team AS team, COALESCE(away_score, 0) AS goals
            FROM matches
            WHERE status = 'FINISHED'
        )
        WHERE team IS NOT NULL
        GROUP BY team
        ORDER BY goals DESC, team ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
