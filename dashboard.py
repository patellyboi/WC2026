from html import escape
import altair as alt
import pandas as pd
import streamlit as st

from api import FootballDataError, fetch_scorers
from app import update_scores
from database import (
    connect,
    init_db,
    leaderboard,
    played_matches,
    recent_matches,
    score_events,
    top_scoring_teams,
    tournament_stats,
)
from participants import PLAYERS


st.set_page_config(page_title="World Cup Sweepstake", layout="wide")
alt.themes.enable("default")


PLAYER_COLORS = {
    "Jay": "#0b7285",
    "Dad": "#2f9e44",
    "Reuben": "#f08c00",
    "Nicola": "#ae3ec9",
}


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.35rem;
        padding-bottom: 1.5rem;
        max-width: 1240px;
    }

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"] {
        display: none;
    }

    div[data-testid="stAlert"] {
        background: #d3f9d8;
        border: 2px solid #2f9e44;
        border-radius: 8px;
        color: #102a2a;
    }

    div[data-testid="stAlert"] * {
        color: #102a2a !important;
        font-weight: 800;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(115, 221, 195, 0.28), transparent 28rem),
            radial-gradient(circle at bottom right, rgba(10, 147, 150, 0.14), transparent 30rem),
            linear-gradient(180deg, #f7fffc 0%, #eefbf7 100%);
    }

    h1 {
        font-size: 2.42rem !important;
        line-height: 1.05 !important;
        margin-bottom: 0.1rem !important;
    }

    h2, h3 {
        letter-spacing: 0 !important;
    }

    h2 {
        font-size: 1.65rem !important;
    }

    h3 {
        font-size: 1.38rem !important;
    }

    p, li, label, .stMarkdown, .stCaption {
        font-size: 1.04rem;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        padding: 0.75rem 0.9rem;
        box-shadow: 0 4px 12px rgba(8, 112, 105, 0.08);
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.98rem;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 1rem;
    }

    .hero {
        background: linear-gradient(135deg, #007f73 0%, #12b886 55%, #7bdcb5 100%);
        border-radius: 8px;
        color: white;
        padding: 0.95rem 1.15rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 10px 26px rgba(0, 127, 115, 0.18);
    }

    .hero p {
        font-size: 1.05rem;
        margin: 0.2rem 0 0;
        opacity: 0.92;
    }

    .leader-card {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        padding: 0.8rem 0.9rem;
        min-height: 96px;
        box-shadow: 0 5px 14px rgba(8, 112, 105, 0.1);
    }

    .leader-label {
        color: #667085;
        font-size: 0.99rem;
        font-weight: 700;
        text-transform: uppercase;
    }

    .leader-name {
        color: #101828;
        font-size: 1.6rem;
        font-weight: 800;
        line-height: 1.1;
        margin-top: 0.15rem;
    }

    .leader-points {
        color: #007f73;
        font-size: 1.82rem;
        font-weight: 900;
        line-height: 1;
        margin-top: 0.35rem;
    }

    .stat-card {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        padding: 0.8rem 0.9rem;
        box-shadow: 0 4px 12px rgba(8, 112, 105, 0.08);
    }

    .stat-label {
        color: #667085;
        font-size: 0.95rem;
        font-weight: 800;
        text-transform: uppercase;
    }

    .stat-value {
        color: #007f73;
        font-size: 1.75rem;
        font-weight: 900;
        margin-top: 0.2rem;
    }

    .team-pill {
        display: inline-block;
        background: #e6fcf5;
        border: 1px solid #96f2d7;
        border-radius: 999px;
        color: #00695f;
        font-size: 1.02rem;
        font-weight: 700;
        margin: 0.15rem 0.2rem 0.15rem 0;
        padding: 0.22rem 0.45rem;
    }

    .prediction-item {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        padding: 0.5rem 0.6rem;
        min-height: 74px;
    }

    .prediction-label {
        color: #667085;
        font-size: 0.86rem;
        font-weight: 800;
        text-transform: uppercase;
    }

    .prediction-value {
        color: #007f73;
        font-size: 1.16rem;
        font-weight: 800;
        margin-top: 0.2rem;
    }

    div[data-testid="stTabs"] button {
        color: #007f73;
        font-size: 1.22rem;
        font-weight: 800;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #004f48;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #12b886;
        height: 0.22rem;
    }

    div.stButton > button {
        background: #ffffff;
        border: 1px solid #96f2d7;
        border-radius: 8px;
        color: #007f73;
        font-size: 1.12rem;
        font-weight: 900;
        min-height: 3rem;
        box-shadow: 0 3px 10px rgba(8, 112, 105, 0.07);
    }

    div.stButton > button:hover {
        background: #e6fcf5;
        border-color: #12b886;
        color: #004f48;
    }

    .bar-card {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        margin-bottom: 0.55rem;
        padding: 0.65rem 0.75rem;
        box-shadow: 0 3px 10px rgba(8, 112, 105, 0.07);
    }

    .bar-row {
        align-items: center;
        display: flex;
        gap: 0.75rem;
        justify-content: space-between;
        margin-bottom: 0.35rem;
    }

    .bar-name {
        color: #102a2a;
        font-size: 1.05rem;
        font-weight: 900;
    }

    .bar-value {
        color: #007f73;
        font-size: 1.05rem;
        font-weight: 900;
    }

    .bar-track {
        background: #d9f7ef;
        border-radius: 999px;
        height: 0.9rem;
        overflow: hidden;
    }

    .bar-fill {
        background: linear-gradient(90deg, #12b886, #63e6be);
        border-radius: 999px;
        height: 100%;
    }

    .list-card {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        padding: 0.65rem 0.75rem;
        box-shadow: 0 3px 10px rgba(8, 112, 105, 0.07);
    }

    .list-top {
        align-items: center;
        display: flex;
        gap: 0.8rem;
        justify-content: space-between;
    }

    .list-title {
        color: #102a2a;
        font-size: 1.03rem;
        font-weight: 900;
    }

    .list-meta {
        color: #667085;
        font-size: 0.9rem;
        font-weight: 700;
        margin-top: 0.15rem;
    }

    .score-badge {
        background: #e6fcf5;
        border-radius: 999px;
        color: #007f73;
        font-size: 1.25rem;
        font-weight: 900;
        padding: 0.32rem 0.7rem;
        white-space: nowrap;
    }

    .points-badge {
        border-radius: 999px;
        color: white;
        font-size: 1.02rem;
        font-weight: 900;
        padding: 0.22rem 0.55rem;
        white-space: nowrap;
    }

    .scroll-panel {
        max-height: 340px;
        overflow-y: auto;
        padding-right: 0.35rem;
    }

    .scroll-panel::-webkit-scrollbar {
        width: 0.55rem;
    }

    .scroll-panel::-webkit-scrollbar-track {
        background: #e6fcf5;
        border-radius: 999px;
    }

    .scroll-panel::-webkit-scrollbar-thumb {
        background: #96f2d7;
        border-radius: 999px;
    }

    .match-title {
        color: #102a2a;
        font-size: 1.28rem;
        font-weight: 950;
        line-height: 1.15;
    }

    .match-meta {
        color: #667085;
        font-size: 0.92rem;
        font-weight: 800;
        margin-top: 0.15rem;
        text-transform: uppercase;
    }

    .player-detail-card {
        background: #ffffff;
        border: 1px solid #b8eadf;
        border-radius: 8px;
        box-shadow: 0 7px 18px rgba(8, 112, 105, 0.1);
        margin-top: 0.8rem;
        min-height: 220px;
        padding: 1rem;
        transform: rotateY(0deg);
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }

    .player-detail-card:hover {
        box-shadow: 0 10px 24px rgba(8, 112, 105, 0.16);
        transform: rotateY(2deg);
    }

    .player-detail-name {
        font-size: 1.8rem;
        font-weight: 950;
        line-height: 1.1;
    }

    .player-detail-sub {
        color: #667085;
        font-size: 1rem;
        font-weight: 800;
        margin: 0.25rem 0 0.75rem;
        text-transform: uppercase;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def title_case_label(value):
    return value.replace("_", " ").title()


def player_color(player):
    return PLAYER_COLORS.get(player, "#007f73")


def load_state():
    conn = connect()
    init_db(conn)
    leaders = [dict(row) for row in leaderboard(conn)]
    events = [dict(row) for row in score_events(conn)]
    matches = [dict(row) for row in recent_matches(conn)]
    played = [dict(row) for row in played_matches(conn)]
    stats = tournament_stats(conn)
    teams = [dict(row) for row in top_scoring_teams(conn)]
    return conn, leaders, events, matches, played, stats, teams


@st.cache_data(ttl=300)
def load_scorers():
    scorers = []
    for row in fetch_scorers(limit=10):
        player = row.get("player", {})
        team = row.get("team", {})
        scorers.append(
            {
                "Player": player.get("name"),
                "Team": team.get("name"),
                "Goals": row.get("goals", 0),
                "Assists": row.get("assists", 0),
                "Pens": row.get("penalties", 0),
            }
        )
    return scorers


def render_leader_cards(leaders):
    columns = st.columns(4)
    for index, row in enumerate(leaders):
        with columns[index]:
            st.markdown(
                f"""
                <div class="leader-card" style="border-left: 8px solid {player_color(row["name"])}">
                    <div class="leader-label">Player</div>
                    <div class="leader-name">{escape(row["name"])}</div>
                    <div class="leader-points" style="color: {player_color(row["name"])}">{row["points"]} pts</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_points_chart(leaders):
    if not leaders:
        st.info("No leaderboard data yet.")
        return

    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)
    chart_df = pd.DataFrame(
        {
            "Player": row["name"],
            "Points": row["points"],
            "Color": player_color(row["name"]),
        }
        for row in leaders
    )
    max_points = max(chart_df["Points"].max(), 1)
    chart = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusTopRight=8, cornerRadiusBottomRight=8, size=42)
        .encode(
            x=alt.X(
                "Points:Q",
                axis=alt.Axis(
                    grid=False,
                    labelPadding=10,
                    tickMinStep=1,
                    title=None,
                ),
                scale=alt.Scale(domain=[0, max_points + 0.45]),
            ),
            y=alt.Y(
                "Player:N",
                sort="-x",
                axis=alt.Axis(
                    labelFontSize=18,
                    labelFontWeight="bold",
                    labelPadding=14,
                    title=None,
                ),
            ),
            color=alt.Color("Player:N", scale=alt.Scale(domain=list(PLAYER_COLORS), range=list(PLAYER_COLORS.values())), legend=None),
            tooltip=["Player", "Points"],
        )
        .properties(height=360)
    )
    text = (
        alt.Chart(chart_df)
        .mark_text(align="left", baseline="middle", dx=10, fontSize=18, fontWeight="bold")
        .encode(
            x="Points:Q",
            y=alt.Y("Player:N", sort="-x"),
            text=alt.Text("Points:Q"),
            color=alt.value("#102a2a"),
        )
    )
    layered_chart = (
        (chart + text)
        .properties(
            background="transparent",
            padding={"top": 10, "right": 24, "bottom": 8, "left": 6},
        )
        .configure_view(stroke=None, fill="#ffffff")
        .configure_axis(
            domain=False,
            grid=False,
            labelColor="#102a2a",
            tickColor="#102a2a",
            titleColor="#102a2a",
        )
    )
    st.altair_chart(layered_chart, use_container_width=True)


def render_stat_cards(stats):
    cards = [
        ("Goals", stats["total_goals"]),
        ("Played", stats["finished_matches"]),
        ("Upcoming", stats["upcoming_matches"]),
        ("Stored", stats["stored_matches"]),
    ]
    columns = st.columns(4)
    for column, (label, value) in zip(columns, cards):
        with column:
            st.markdown(
                (
                    '<div class="stat-card">'
                    f'<div class="stat-label">{label}</div>'
                    f'<div class="stat-value">{value}</div>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )


def render_scorer_tables(teams):
    left, right = st.columns(2)
    with left:
        st.subheader("Goal Scorers")
        try:
            scorers = load_scorers()
        except FootballDataError as exc:
            st.info(str(exc))
            scorers = []

        if scorers:
            max_goals = max([row["Goals"] for row in scorers] + [1])
            for row in scorers[:8]:
                width = int((row["Goals"] / max_goals) * 100)
                st.markdown(
                    (
                        '<div class="bar-card">'
                        '<div class="bar-row">'
                        f'<div class="bar-name">{row["Player"]} <span style="color:#667085;font-weight:700">({row["Team"]})</span></div>'
                        f'<div class="bar-value">{row["Goals"]}</div>'
                        "</div>"
                        '<div class="bar-track">'
                        f'<div class="bar-fill" style="width: {width}%"></div>'
                        "</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.info("No scorer data available yet.")

    with right:
        st.subheader("Team Goals")
        if teams:
            max_goals = max([row["goals"] for row in teams] + [1])
            for row in teams:
                width = int((row["goals"] / max_goals) * 100)
                st.markdown(
                    (
                        '<div class="bar-card">'
                        '<div class="bar-row">'
                        f'<div class="bar-name">{row["team"]}</div>'
                        f'<div class="bar-value">{row["goals"]}</div>'
                        "</div>"
                        '<div class="bar-track">'
                        f'<div class="bar-fill" style="width: {width}%"></div>'
                        "</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.info("No team goal totals yet.")


def render_score_events(events):
    st.subheader("Scoring Log")
    if not events:
        st.info("No scoring events yet.")
        return

    cards = ['<div class="scroll-panel">']
    for event in events[:8]:
        color = player_color(event["player"])
        cards.append(
            '<div class="list-card">'
            '<div class="list-top">'
            "<div>"
            f'<div class="list-title">{escape(event["player"])} - {escape(event["team"] or "")}</div>'
            f'<div class="list-meta">{escape(event["reason"])}</div>'
            "</div>"
            f'<div class="points-badge" style="background: {color}">+{event["points"]}</div>'
            "</div>"
            "</div>"
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def render_recent_matches(matches):
    st.subheader("Played Matches")
    if not matches:
        st.info("No played matches stored yet.")
        return

    for match in matches:
        score = (
            "No score from API"
            if match["home_score"] is None or match["away_score"] is None
            else f"{int(match['home_score'])}-{int(match['away_score'])}"
        )
        st.markdown(
            (
                '<div class="list-card">'
                '<div class="list-top">'
                "<div>"
                f'<div class="match-title">{escape(match["home_team"])} vs {escape(match["away_team"])}</div>'
                f'<div class="match-meta">{escape(title_case_label(match["stage"] or ""))}</div>'
                "</div>"
                f'<div class="score-badge">{score}</div>'
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render_participants():
    st.subheader("Players")
    if "selected_player" not in st.session_state:
        st.session_state.selected_player = "Jay"

    selector_cols = st.columns(4)
    for column, player in zip(selector_cols, PLAYERS):
        with column:
            if st.button(player, use_container_width=True):
                st.session_state.selected_player = player

    player = st.session_state.selected_player
    data = PLAYERS[player]
    color = player_color(player)
    st.markdown(
        (
            f'<div class="player-detail-card" style="border-left: 8px solid {color}">'
            f'<div class="player-detail-name" style="color: {color}">{escape(player)}</div>'
            '<div class="player-detail-sub">Teams</div>'
            + " ".join(
                f'<span class="team-pill">{escape(team)}</span>' for team in data["teams"]
            )
            + '<div class="player-detail-sub" style="margin-top: 1rem;">Predictions</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    predictions = list(data["predictions"].items())
    for start in range(0, len(predictions), 3):
        cols = st.columns(3)
        for col, (category, value) in zip(cols, predictions[start : start + 3]):
            with col:
                st.markdown(
                    (
                        f'<div class="prediction-item" style="border-left: 5px solid {color}">'
                        f'<div class="prediction-label">{title_case_label(category)}</div>'
                        f'<div class="prediction-value" style="color: {color}">{escape(str(value))}</div>'
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )


conn, leaders, events, matches, played, stats, teams = load_state()

st.markdown(
    """
    <div class="hero">
        <h1>World Cup Sweepstake Tracker</h1>
        <p>Standings, teams, predictions, and recent match data.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

top_left, top_right = st.columns([1, 3])
with top_left:
    if st.button("Update Results", use_container_width=True, type="primary"):
        try:
            conn, count, new_events, new_points = update_scores()
            st.success(
                f"Updated {count} matches. Added {new_events} scoring events "
                f"for {new_points} points."
            )
            load_scorers.clear()
            conn, leaders, events, matches, played, stats, teams = load_state()
        except FootballDataError as exc:
            st.error(str(exc))
with top_right:
    st.caption("Updates pull from football-data.org and save locally.")

render_stat_cards(stats)

st.subheader("Leaderboard")
render_leader_cards(leaders)

chart_col, log_col = st.columns([1, 1], gap="medium")
with chart_col:
    render_points_chart(leaders)
with log_col:
    render_score_events(events)

render_scorer_tables(teams)

tabs = st.tabs(["Matches", "Players"])
with tabs[0]:
    render_recent_matches(played)
with tabs[1]:
    render_participants()


