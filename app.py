import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

try:
    API_URL = st.secrets["API_URL"]
except (FileNotFoundError, KeyError):
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

API_URL = API_URL.rstrip("/")
st.set_page_config(
    page_title="IPL Analytics Dashboard",
    page_icon="🏏",
    layout="wide"
)

st.title(" IPL Data Analysis Dashboard")
st.caption("Explore IPL seasons, team performance, batting and bowling statistics.")

@st.cache_data(ttl=60)
def api_get(endpoint, params=None):
    response = requests.get(f"{API_URL}{endpoint}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()

# Check backend connection and dataset availability.
try:
    health = api_get("/health")
except requests.RequestException:
    st.error("Cannot connect to FastAPI. Start the backend using: uvicorn backend:app --reload")
    st.stop()

if health["status"] != "ok":
    st.warning(
        "IPL dataset is not loaded. Add matches.csv and deliveries.csv to the data folder, "
        "then restart FastAPI."
    )
    st.stop()

try:
    seasons = ["All"] + api_get("/seasons")
    teams = api_get("/teams")
except requests.RequestException as exc:
    st.error(f"Could not load dashboard filters: {exc}")
    st.stop()

with st.sidebar:
    st.header("Dashboard Filters")
    selected_season = st.selectbox("Select IPL season", seasons)
    st.markdown("---")
    st.write("**Dataset status**")
    st.success(f"{health['matches_loaded']:,} matches rows loaded")
    st.caption(f"{health['deliveries_loaded']:,} ball-by-ball rows loaded")

params = {"season": selected_season}

try:
    summary = api_get("/summary", params=params)
    team_data = api_get("/team-performance", params=params)
    batsmen_data = api_get("/top-batsmen", params={**params, "limit": 10})
    bowlers_data = api_get("/top-bowlers", params={**params, "limit": 10})
except requests.RequestException as exc:
    st.error(f"API request failed: {exc}")
    st.stop()

# KPI cards
st.subheader(f"Overview — {selected_season}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Matches", f"{summary['matches']:,}")
c2.metric("Teams", f"{summary['teams']:,}")
c3.metric("Total Runs", f"{summary['runs']:,}")
c4.metric("Wickets", f"{summary['wickets']:,}")

st.markdown("---")

# Team performance
st.subheader("Team Performance")
team_df = pd.DataFrame(team_data)

if not team_df.empty:
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            team_df.sort_values("wins", ascending=True),
            x="wins", y="team", orientation="h",
            title="Wins by Team",
            labels={"wins": "Matches won", "team": "Team"},
            color="wins",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(
            team_df.sort_values("win_percentage", ascending=True),
            x="win_percentage", y="team", orientation="h",
            title="Team Win Percentage",
            labels={"win_percentage": "Win percentage (%)", "team": "Team"},
            color="win_percentage",
            color_continuous_scale="Teal"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        team_df.rename(columns={
            "team": "Team",
            "matches_played": "Matches Played",
            "wins": "Wins",
            "win_percentage": "Win Percentage (%)"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No team data available for this selection.")

st.markdown("---")

# Batting and bowling leaders
st.subheader(" Top Batsmen")
bat_df = pd.DataFrame(batsmen_data)
if not bat_df.empty:
    bat_display = bat_df.rename(columns={
        "player": "Player", "runs": "Runs", "balls": "Balls",
        "fours": "Fours", "sixes": "Sixes", "dismissals": "Dismissals",
        "average": "Average", "strike_rate": "Strike Rate"
    })
    st.dataframe(bat_display, use_container_width=True, hide_index=True)

    fig = px.bar(
        bat_df.head(10).sort_values("runs"),
        x="runs", y="player", orientation="h",
        title="Top 10 Batsmen by Runs",
        labels={"runs": "Runs", "player": "Player"},
        color="runs",
        color_continuous_scale="Oranges"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No batting data available.")

st.markdown("---")

st.subheader(" Top Bowlers")
bowl_df = pd.DataFrame(bowlers_data)
if not bowl_df.empty:
    bowl_display = bowl_df.rename(columns={
        "player": "Player", "runs_conceded": "Runs Conceded",
        "legal_balls": "Legal Balls", "wickets": "Wickets",
        "overs": "Overs", "economy": "Economy"
    })
    st.dataframe(bowl_display, use_container_width=True, hide_index=True)

    fig = px.bar(
        bowl_df.head(10).sort_values("wickets"),
        x="wickets", y="player", orientation="h",
        title="Top 10 Bowlers by Wickets",
        labels={"wickets": "Wickets", "player": "Player"},
        color="wickets",
        color_continuous_scale="Greens"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No bowling data available.")

st.markdown("---")

# Team comparison
st.subheader(" Compare Two Teams")
if len(teams) >= 2:
    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("First team", teams, index=0)
    with col2:
        team2_options = [team for team in teams if team != team1]
        team2 = st.selectbox("Second team", team2_options, index=0)

    if st.button("Compare Teams"):
        try:
            comparison = api_get(
                "/team-comparison",
                params={
                    "team1": team1,
                    "team2": team2,
                    "season": selected_season
                }
            )
            comparison_df = pd.DataFrame(comparison)
            comparison_df = comparison_df.rename(columns={
                "team": "Team",
                "matches_played": "Matches Played",
                "wins": "Wins"
            })
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            fig = px.bar(
                comparison_df, x="Team", y="Wins", color="Team",
                title="Wins comparison"
            )
            st.plotly_chart(fig, use_container_width=True)
        except requests.RequestException as exc:
            st.error(f"Could not compare teams: {exc}")
else:
    st.info("At least two teams are needed for comparison.")

st.caption("IPL Analytics Dashboard | Built with Streamlit, FastAPI, Pandas and Plotly")
