PLAYERS = {
    "Jay": {
        "teams": [
            "Austria",
            "Colombia",
            "Congo DR",
            "Curacao",
            "France",
            "Iran",
            "Jordan",
            "Morocco",
            "Norway",
            "Saudi Arabia",
            "Spain",
            "Sweden",
        ],
        "predictions": {
            "winner": "Spain",
            "golden_boot": "Lamine Yamal",
            "dark_horse": "Scotland",
            "goals_scored": 201,
            "england_distance": "Semi-final",
            "group_stage_upset": "Iran beats Belgium",
        },
    },
    "Dad": {
        "teams": [
            "Australia",
            "Bosnia-Herzegovina",
            "Cabo Verde",
            "Canada",
            "Japan",
            "Mexico",
            "New Zealand",
            "Scotland",
            "Senegal",
            "South Africa",
            "Tunisia",
            "Turkey",
        ],
        "predictions": {
            "winner": "Spain",
            "golden_boot": "Harry Kane",
            "dark_horse": "Ivory Coast",
            "goals_scored": 184,
            "england_distance": "Semi-final",
            "group_stage_upset": "Norway vs France",
        },
    },
    "Reuben": {
        "teams": [
            "Argentina",
            "Belgium",
            "Brazil",
            "Ecuador",
            "Germany",
            "Panama",
            "Paraguay",
            "Portugal",
            "Qatar",
            "South Korea",
            "USA",
            "Uzbekistan",
        ],
        "predictions": {
            "winner": "Spain",
            "golden_boot": "Mikel Oyarzabal",
            "dark_horse": "Ecuador",
            "goals_scored": 162,
            "england_distance": "Final",
            "group_stage_upset": "Ecuador beats Germany",
        },
    },
    "Nicola": {
        "teams": [
            "Algeria",
            "Croatia",
            "Czech Republic",
            "Ivory Coast",
            "Egypt",
            "England",
            "Ghana",
            "Haiti",
            "Iraq",
            "Netherlands",
            "Switzerland",
            "Uruguay",
        ],
        "predictions": {
            "winner": "Spain",
            "golden_boot": "Mohamed Salah",
            "dark_horse": "Mexico",
            "goals_scored": 137,
            "england_distance": "Quarter-finals",
            "group_stage_upset": "Egypt beats Belgium",
        },
    },
}


TEAM_ALIASES = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde Islands": "Cabo Verde",
    "Congo DR": "Congo DR",
    "DR Congo": "Congo DR",
    "Cote d'Ivoire": "Ivory Coast",
    "Côte d’Ivoire": "Ivory Coast",
    "Curaçao": "Curacao",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "United States": "USA",
    "United States of America": "USA",
}


def canonical_team_name(name):
    return TEAM_ALIASES.get(name, name)


def owner_for_team(team_name):
    canonical_name = canonical_team_name(team_name)
    for player, data in PLAYERS.items():
        if canonical_name in data["teams"]:
            return player
    return None


