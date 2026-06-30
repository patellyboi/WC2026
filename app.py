import argparse
import time

from api import FootballDataError, check_token, fetch_world_cup_matches
from database import add_score_event, connect, init_db, save_match
from leaderboard import format_leaderboard
from scoring import score_finished_match, score_locked_match_predictions


def update_scores():
    conn = connect()
    init_db(conn)

    matches = fetch_world_cup_matches()
    new_events = 0
    new_points = 0
    for match in matches:
        save_match(conn, match)
        for event in score_finished_match(match) + score_locked_match_predictions(conn, match):
            if add_score_event(conn, event):
                new_events += 1
                new_points += event["points"]

    conn.commit()
    return conn, len(matches), new_events, new_points


def run_once():
    conn, match_count, new_events, new_points = update_scores()
    print(
        f"Updated from {match_count} matches. "
        f"Added {new_events} scoring events for {new_points} points."
    )
    print()
    print(format_leaderboard(conn))


def run_loop(interval_seconds):
    while True:
        try:
            run_once()
        except FootballDataError as exc:
            print(f"API error: {exc}")
        time.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="World Cup sweepstake tracker")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep updating every interval instead of running once.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Update interval in seconds when --loop is used.",
    )
    parser.add_argument(
        "--check-token",
        action="store_true",
        help="Validate the football-data.org API token and exit.",
    )
    args = parser.parse_args()

    if args.check_token:
        try:
            check_token()
            print("Token is valid.")
        except FootballDataError as exc:
            print(f"API error: {exc}")
    elif args.loop:
        run_loop(args.interval)
    else:
        try:
            run_once()
        except FootballDataError as exc:
            print(f"API error: {exc}")


if __name__ == "__main__":
    main()

