from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="IPL Analytics API")

DATA_DIR = Path(__file__).parent / "data"

matches_df = pd.DataFrame()
deliveries_df = pd.DataFrame()


def load_data():
    global matches_df, deliveries_df

    matches_df = pd.read_csv(DATA_DIR / "matches.csv")
    deliveries_df = pd.read_csv(DATA_DIR / "deliveries.csv")

    matches_df.columns = matches_df.columns.str.strip().str.lower()
    deliveries_df.columns = deliveries_df.columns.str.strip().str.lower()

    # Convert new dataset column name to the backend name
    deliveries_df.rename(columns={"batter": "batsman"}, inplace=True)

    required_matches = {
        "id", "season", "team1", "team2", "winner"
    }

    required_deliveries = {
        "match_id", "batting_team", "bowling_team",
        "batsman", "bowler", "batsman_runs",
        "total_runs", "extra_runs", "extras_type",
        "player_dismissed", "dismissal_kind"
    }

    missing_m = required_matches - set(matches_df.columns)
    missing_d = required_deliveries - set(deliveries_df.columns)

    if missing_m or missing_d:
        raise ValueError(
            f"Missing matches columns: {missing_m}; "
            f"Missing deliveries columns: {missing_d}"
        )

    matches_df["season"] = matches_df["season"].astype(str)

    for col in ["team1", "team2", "winner"]:
        matches_df[col] = matches_df[col].fillna("").astype(str)

    for col in ["batsman_runs", "total_runs", "extra_runs"]:
        deliveries_df[col] = pd.to_numeric(
            deliveries_df[col], errors="coerce"
        ).fillna(0)

    deliveries_df["extras_type"] = (
        deliveries_df["extras_type"].fillna("").str.lower()
    )

    deliveries_df["player_dismissed"] = (
        deliveries_df["player_dismissed"].fillna("")
    )

    deliveries_df["dismissal_kind"] = (
        deliveries_df["dismissal_kind"].fillna("").str.lower()
    )


@app.on_event("startup")
def startup():
    try:
        load_data()
        print("IPL datasets loaded successfully!")
        print("Matches:", len(matches_df))
        print("Deliveries:", len(deliveries_df))
    except Exception as e:
        print("Dataset loading error:", e)


def ensure_data():
    if matches_df.empty or deliveries_df.empty:
        raise HTTPException(
            status_code=503,
            detail="IPL dataset not loaded"
        )


def filter_matches(season="All"):
    ensure_data()

    df = matches_df.copy()

    if season != "All":
        df = df[df["season"] == str(season)]

    return df


def get_deliveries(match_ids):
    return deliveries_df[
        deliveries_df["match_id"].isin(match_ids)
    ].copy()


@app.get("/")
def home():
    return {
        "message": "IPL Analytics API is running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok" if not matches_df.empty and not deliveries_df.empty else "data_not_loaded",
        "matches_loaded": len(matches_df),
        "deliveries_loaded": len(deliveries_df)
    }


@app.get("/seasons")
def get_seasons():
    ensure_data()
    return sorted(matches_df["season"].unique().tolist())


@app.get("/teams")
def get_teams():
    ensure_data()

    teams = (
        set(matches_df["team1"]) |
        set(matches_df["team2"])
    )

    teams.discard("")
    return sorted(teams)


@app.get("/summary")
def summary(season: str = "All"):
    m = filter_matches(season)

    d = get_deliveries(m["id"])

    dismissals = d[
        (d["player_dismissed"] != "") &
        (~d["dismissal_kind"].isin([
            "retired hurt", "obstructing the field"
        ]))
    ]

    teams = set(m["team1"]) | set(m["team2"])
    teams.discard("")

    return {
        "matches": int(m["id"].nunique()),
        "teams": len(teams),
        "runs": int(d["total_runs"].sum()),
        "wickets": len(dismissals),
        "seasons": int(matches_df["season"].nunique())
    }


@app.get("/team-performance")
def team_performance(season: str = "All"):
    m = filter_matches(season)

    teams = sorted(
        (set(m["team1"]) | set(m["team2"])) - {""}
    )

    result = []

    for team in teams:
        played = m[
            (m["team1"] == team) |
            (m["team2"] == team)
        ]["id"].nunique()

        wins = (m["winner"] == team).sum()

        result.append({
            "team": team,
            "matches_played": int(played),
            "wins": int(wins),
            "win_percentage": round(
                wins / played * 100, 2
            ) if played else 0
        })

    return sorted(
        result,
        key=lambda x: x["wins"],
        reverse=True
    )


@app.get("/top-batsmen")
def top_batsmen(
    season: str = "All",
    limit: int = Query(10, ge=1, le=100)
):
    m = filter_matches(season)
    d = get_deliveries(m["id"])

    d["legal_ball_faced"] = (
        d["extras_type"] != "wides"
    )

    stats = d.groupby("batsman").agg(
        runs=("batsman_runs", "sum"),
        balls=("legal_ball_faced", "sum"),
        fours=("batsman_runs", lambda x: (x == 4).sum()),
        sixes=("batsman_runs", lambda x: (x == 6).sum())
    ).reset_index()

    not_out_kinds = [
        "run out", "retired hurt",
        "obstructing the field", "retired out"
    ]

    outs = d[
        (d["player_dismissed"] != "") &
        (~d["dismissal_kind"].isin(not_out_kinds))
    ].groupby("player_dismissed").size()

    stats["dismissals"] = (
        stats["batsman"].map(outs).fillna(0)
    )

    stats["average"] = np.where(
        stats["dismissals"] > 0,
        stats["runs"] / stats["dismissals"],
        stats["runs"]
    ).round(2)

    stats["strike_rate"] = np.where(
        stats["balls"] > 0,
        stats["runs"] / stats["balls"] * 100,
        0
    ).round(2)

    stats = stats.sort_values(
        "runs", ascending=False
    ).head(limit)

    stats.rename(
        columns={"batsman": "player"},
        inplace=True
    )

    return stats.to_dict(orient="records")


@app.get("/top-bowlers")
def top_bowlers(
    season: str = "All",
    limit: int = Query(10, ge=1, le=100)
):
    m = filter_matches(season)
    d = get_deliveries(m["id"])

    not_bowler_wickets = [
        "run out", "retired hurt",
        "obstructing the field", "retired out"
    ]

    wickets = d[
        (d["player_dismissed"] != "") &
        (~d["dismissal_kind"].isin(not_bowler_wickets))
    ].groupby("bowler").size()

    d["runs_conceded"] = d["total_runs"] - np.where(
        d["extras_type"].isin(["byes", "legbyes"]),
        d["extra_runs"], 0
    )

    d["legal_ball"] = ~d["extras_type"].isin(
        ["wides", "noballs"]
    )

    stats = d.groupby("bowler").agg(
        runs_conceded=("runs_conceded", "sum"),
        legal_balls=("legal_ball", "sum")
    ).reset_index()

    stats["wickets"] = (
        stats["bowler"].map(wickets).fillna(0)
    )

    stats["overs"] = (
        stats["legal_balls"] / 6
    ).round(2)

    stats["economy"] = np.where(
        stats["legal_balls"] > 0,
        stats["runs_conceded"] /
        (stats["legal_balls"] / 6),
        0
    ).round(2)

    stats = stats[
        stats["legal_balls"] > 0
    ].sort_values(
        "wickets", ascending=False
    ).head(limit)

    stats.rename(
        columns={"bowler": "player"},
        inplace=True
    )

    return stats.to_dict(orient="records")


@app.get("/team-comparison")
def team_comparison(
    team1: str,
    team2: str,
    season: str = "All"
):
    m = filter_matches(season)

    result = []

    for team in [team1, team2]:
        team_matches = m[
            (m["team1"] == team) |
            (m["team2"] == team)
        ]

        result.append({
            "team": team,
            "matches_played": int(
                team_matches["id"].nunique()
            ),
            "wins": int(
                (team_matches["winner"] == team).sum()
            )
        })

    return result
