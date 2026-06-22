from participants import owner_for_team


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
    "group_stage_upset": 5,
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


def score_finished_match(match):
    if match.get("status") != "FINISHED":
        return []

    winner = match_winner(match)
    if not winner or not is_group_stage_match(match):
        return []

    owner = owner_for_team(winner)
    if not owner:
        return []

    return [
        {
            "player": owner,
            "team": winner,
            "points": POINTS["group_stage_win"],
            "reason": "Group Stage Win",
            "match_id": str(match["id"]),
        }
    ]


def score_advancement(team_name, stage):
    owner = owner_for_team(team_name)
    points = KNOCKOUT_STAGE_POINTS.get(stage.upper())
    if not owner or not points:
        return None

    return {
        "player": owner,
        "team": team_name,
        "points": points,
        "reason": f"Reached {stage.replace('_', ' ').title()}",
        "match_id": f"advancement:{team_name}:{stage}",
    }
