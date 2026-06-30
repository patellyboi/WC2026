import re

from database import predictions_for_match
from participants import PLAYERS, canonical_team_name, owner_for_team


POINTS = {
    "group_stage_win": 1,
    "round_of_32": 2,
    "round_of_16": 3,
    "quarter_finals": 5,
    "semi_finals": 8,
    "runner_up": 12,
    "world_cup_winner": 20,
    "winner_prediction": 10,
    "golden_boot": 10,
    "dark_horse": 10,
    "goals_scored": 10,
    "england_distance": 10,
    "group_stage_upset": 10,
    "knockout_correct_score": 3,
    "knockout_correct_winner": 1,
}


KNOCKOUT_STAGE_POINTS = {
    "LAST_32": POINTS["round_of_32"],
    "ROUND_OF_32": POINTS["round_of_32"],
    "LAST_16": POINTS["round_of_16"],
    "ROUND_OF_16": POINTS["round_of_16"],
    "QUARTER_FINALS": POINTS["quarter_finals"],
    "SEMI_FINALS": POINTS["semi_finals"],
    "FINAL": POINTS["runner_up"],
}


def _score_value(match, side):
    score = match.get("score", {}).get("fullTime", {})
    return score.get(side)


def match_winner(match):
    home_goals = _score_value(match, "home")
    away_goals = _score_value(match, "away")
    if home_goals is None or away_goals is None or home_goals == away_goals:
        return None

    if home_goals > away_goals:
        return match["homeTeam"]["name"]
    return match["awayTeam"]["name"]


def is_group_stage_match(match):
    stage = match.get("stage") or ""
    return stage.upper() in {"GROUP_STAGE", "GROUP"}


def is_knockout_match(match):
    return not is_group_stage_match(match)


def _normalize_team_name(name):
    return canonical_team_name(name or "").casefold()


def _prediction_teams(text):
    normalized_text = text.casefold()
    found = []
    seen = set()
    known_teams = {
        team
        for data in PLAYERS.values()
        for team in data["teams"]
    }
    for team in known_teams:
        normalized_team = team.casefold()
        index = normalized_text.find(normalized_team)
        if index >= 0 and normalized_team not in seen:
            found.append((index, team))
            seen.add(normalized_team)
    return [team for _, team in sorted(found)]


def _predicted_upset_winner(prediction, teams_in_order):
    normalized_prediction = prediction.casefold()
    for separator in (" beats ", " beat "):
        if separator in normalized_prediction:
            predicted_winner = prediction[: normalized_prediction.index(separator)].strip()
            return _normalize_team_name(predicted_winner)
    if re.search(r"(?<!\d)(\d{1,2})\s*[-:]\s*(\d{1,2})(?!\d)", prediction):
        return teams_in_order[0] if teams_in_order else None
    return None


def _group_stage_upset_score_events(match):
    home_team = match.get("homeTeam", {}).get("name")
    away_team = match.get("awayTeam", {}).get("name")
    home_goals = _score_value(match, "home")
    away_goals = _score_value(match, "away")
    if home_goals is None or away_goals is None:
        return []

    winner = match_winner(match)
    if not winner:
        return []

    match_team_names = {
        _normalize_team_name(home_team),
        _normalize_team_name(away_team),
    }
    events = []
    for player, data in PLAYERS.items():
        prediction = str(data["predictions"].get("group_stage_upset", ""))
        score_match = re.search(r"(?<!\d)(\d{1,2})\s*[-:]\s*(\d{1,2})(?!\d)", prediction)
        teams_in_order = [
            _normalize_team_name(team)
            for team in _prediction_teams(prediction)
        ]
        if len(teams_in_order) < 2 or set(teams_in_order) != match_team_names:
            continue

        reason = "Group Stage Upset"
        if score_match:
            first_score = int(score_match.group(1))
            second_score = int(score_match.group(2))
            if teams_in_order[0] == _normalize_team_name(home_team):
                predicted_home, predicted_away = first_score, second_score
            else:
                predicted_home, predicted_away = second_score, first_score
            if predicted_home != home_goals or predicted_away != away_goals:
                continue
            reason = "Group Stage Upset Exact Score"
        else:
            predicted_winner = _predicted_upset_winner(prediction, teams_in_order)
            if predicted_winner != _normalize_team_name(winner):
                continue

        events.append(
            {
                "player": player,
                "team": f"{home_team} vs {away_team}",
                "points": POINTS["group_stage_upset"],
                "reason": reason,
                "match_id": str(match["id"]),
            }
        )
    return events


def score_finished_match(match):
    if match.get("status") != "FINISHED":
        return []

    if not is_group_stage_match(match):
        return []

    events = _group_stage_upset_score_events(match)
    winner = match_winner(match)
    if not winner:
        return events

    owner = owner_for_team(winner)
    if not owner:
        return events

    events.append(
        {
            "player": owner,
            "team": winner,
            "points": POINTS["group_stage_win"],
            "reason": "Group Stage Win",
            "match_id": str(match["id"]),
        }
    )
    return events


def score_advancement(team_name, stage):
    stage = stage.upper()
    team_name = canonical_team_name(team_name)
    owner = owner_for_team(team_name)
    points = KNOCKOUT_STAGE_POINTS.get(stage)
    if not owner or not points:
        return None

    return {
        "player": owner,
        "team": team_name,
        "points": points,
        "reason": f"Reached {stage.replace('_', ' ').title()}",
        "match_id": f"advancement:{team_name}:{stage}",
    }


def score_match_advancements(match):
    stage = (match.get("stage") or "").upper()
    if stage not in KNOCKOUT_STAGE_POINTS:
        return []

    events = []
    seen_teams = set()
    for side in ("homeTeam", "awayTeam"):
        team_name = match.get(side, {}).get("name")
        if not team_name:
            continue

        canonical_name = canonical_team_name(team_name)
        normalized_name = canonical_name.casefold()
        if normalized_name in seen_teams:
            continue
        seen_teams.add(normalized_name)

        event = score_advancement(canonical_name, stage)
        if event:
            events.append(event)
    return events


def score_world_cup_winner(match):
    if (match.get("stage") or "").upper() != "FINAL" or match.get("status") != "FINISHED":
        return None

    winner_side = _winner_side_from_api(match)
    if winner_side:
        winner = match.get(f"{winner_side}Team", {}).get("name")
    else:
        winner = match_winner(match)
    if not winner:
        return None

    winner = canonical_team_name(winner)
    owner = owner_for_team(winner)
    if not owner:
        return None

    return {
        "player": owner,
        "team": winner,
        "points": POINTS["world_cup_winner"],
        "reason": "World Cup Winner",
        "match_id": f"winner:{winner}",
    }


def _winner_side_from_api(match):
    winner = match.get("score", {}).get("winner")
    if winner == "HOME_TEAM":
        return "home"
    if winner == "AWAY_TEAM":
        return "away"
    return None


def _score_winner_from_values(home_goals, away_goals, penalty_winner=None):
    if home_goals is None or away_goals is None:
        return None
    if home_goals == away_goals:
        return penalty_winner
    return "home" if home_goals > away_goals else "away"

def _prediction_score_values(match):
    score = match.get("score", {})
    if score.get("duration") == "PENALTY_SHOOTOUT":
        regular = score.get("regularTime") or {}
        extra = score.get("extraTime") or {}
        regular_home = regular.get("home")
        regular_away = regular.get("away")
        if regular_home is None or regular_away is None:
            return _score_value(match, "home"), _score_value(match, "away")
        return (
            regular_home + (extra.get("home") or 0),
            regular_away + (extra.get("away") or 0),
        )
    return _score_value(match, "home"), _score_value(match, "away")


def score_locked_match_predictions(conn, match):
    if match.get("status") != "FINISHED" or not is_knockout_match(match):
        return []

    home_team = match.get("homeTeam", {}).get("name")
    away_team = match.get("awayTeam", {}).get("name")
    home_goals, away_goals = _prediction_score_values(match)
    if home_goals is None or away_goals is None:
        return []

    actual_winner = _winner_side_from_api(match) or _score_winner_from_values(home_goals, away_goals)
    match_label = f"{home_team} vs {away_team}"
    events = []
    for prediction in predictions_for_match(conn, match["id"]):
        predicted_home = prediction["home_score"]
        predicted_away = prediction["away_score"]
        predicted_winner = _score_winner_from_values(predicted_home, predicted_away, prediction["penalty_winner"])

        if predicted_home == home_goals and predicted_away == away_goals:
            events.append(
                {
                    "player": prediction["player"],
                    "team": match_label,
                    "points": POINTS["knockout_correct_score"],
                    "reason": "Knockout Correct Score",
                    "match_id": str(match["id"]),
                }
            )

            continue

        if predicted_winner and predicted_winner == actual_winner:
            events.append(
                {
                    "player": prediction["player"],
                    "team": match_label,
                    "points": POINTS["knockout_correct_winner"],
                    "reason": "Knockout Correct Winner",
                    "match_id": str(match["id"]),
                }
            )
    return events









