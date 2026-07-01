import sqlite3
from datetime import datetime, timezone
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

CREATE TABLE IF NOT EXISTS match_predictions (
    player TEXT NOT NULL,
    match_id TEXT NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    locked_at TEXT DEFAULT CURRENT_TIMESTAMP,
    locked INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(player, match_id),
    FOREIGN KEY(player) REFERENCES players(name),
    FOREIGN KEY(match_id) REFERENCES matches(id)
);
"""


def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(match_predictions)")]
    if "penalty_winner" not in columns:
        conn.execute("ALTER TABLE match_predictions ADD COLUMN penalty_winner TEXT")
    if "locked" not in columns:
        conn.execute("ALTER TABLE match_predictions ADD COLUMN locked INTEGER NOT NULL DEFAULT 1")
    if "updated_at" not in columns:
        conn.execute("ALTER TABLE match_predictions ADD COLUMN updated_at TEXT")
        conn.execute(
            """
            UPDATE match_predictions
            SET updated_at = COALESCE(locked_at, CURRENT_TIMESTAMP)
            WHERE updated_at IS NULL
            """
        )
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
        SELECT e.player, e.team, e.points, e.reason, e.source_id, e.created_at,
               m.utc_date, m.stage, m.home_team, m.away_team
        FROM score_events e
        LEFT JOIN matches m ON m.id = e.source_id
        ORDER BY COALESCE(m.utc_date, e.created_at) DESC, e.id DESC
        """
    ).fetchall()


def all_match_predictions(conn):
    return conn.execute(
        """
        SELECT mp.player, mp.match_id, mp.home_score, mp.away_score,
               mp.penalty_winner, mp.locked_at, mp.locked, mp.updated_at,
               m.utc_date, m.stage, m.status,
               m.home_team, m.away_team
        FROM match_predictions mp
        LEFT JOIN matches m ON m.id = mp.match_id
        ORDER BY COALESCE(m.utc_date, mp.locked_at) ASC, m.id ASC, mp.player ASC
        """
    ).fetchall()


def add_manual_points(conn, player, points, reason):
    created_at = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    source_id = f"manual:{created_at}"
    event_key = f"{source_id}:{player}:{reason}"
    conn.execute(
        """
        INSERT INTO score_events(
            event_key, player, team, points, reason, source_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_key, player, None, int(points), reason, source_id),
    )
    conn.commit()
    return source_id

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
            SUM(
                CASE
                    WHEN status IN ('SCHEDULED', 'TIMED')
                     AND utc_date > strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                    THEN 1
                    ELSE 0
                END
            ) AS upcoming_matches,
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

def upcoming_matches(conn, limit=100):
    return conn.execute(
        """
        SELECT id, utc_date, competition, stage, status, home_team, away_team,
               home_score, away_score
        FROM matches
        WHERE status IN ('SCHEDULED', 'TIMED')
          AND utc_date > strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        ORDER BY utc_date ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def next_available_match(conn):
    rows = upcoming_matches(conn, limit=1)
    return rows[0] if rows else None


def match_lock_summary(conn):
    return conn.execute(
        """
        SELECT m.id AS match_id, m.utc_date, m.stage, m.status, m.home_team, m.away_team,
               COUNT(mp.player) AS locked_count
        FROM matches m
        LEFT JOIN match_predictions mp
          ON mp.match_id = m.id AND COALESCE(mp.locked, 1) = 1
        GROUP BY m.id, m.utc_date, m.stage, m.status, m.home_team, m.away_team
        ORDER BY m.utc_date ASC
        """
    ).fetchall()


def match_predictions(conn, match_id):
    return conn.execute(
        """
        SELECT player, match_id, home_score, away_score, penalty_winner,
               locked_at, locked, updated_at
        FROM match_predictions
        WHERE match_id = ? AND COALESCE(locked, 1) = 1
        ORDER BY player ASC
        """,
        (str(match_id),),
    ).fetchall()


def lock_match_prediction(conn, player, match_id, home_score, away_score, penalty_winner=None):
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO match_predictions(
            player, match_id, home_score, away_score, penalty_winner, locked, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """,
        (player, str(match_id), int(home_score), int(away_score), penalty_winner),
    )
    conn.commit()
    return cursor.rowcount == 1


def predictions_for_match(conn, match_id):
    return conn.execute(
        """
        SELECT player, home_score, away_score, penalty_winner
        FROM match_predictions
        WHERE match_id = ?
        """,
        (str(match_id),),
    ).fetchall()

def delete_match_prediction(conn, player, match_id):
    cursor = conn.execute(
        """
        DELETE FROM match_predictions
        WHERE player = ? AND match_id = ?
        """,
        (player, str(match_id)),
    )
    conn.commit()
    return cursor.rowcount






