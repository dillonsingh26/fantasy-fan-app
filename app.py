# app.py  — Minimal personal Overview page only
import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# -------------------- DB SETUP --------------------
# Reads DATABASE_URL from .env if present
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DB_URL = os.getenv("DATABASE_URL")
    except Exception:
        pass
if not DB_URL:
    st.stop()  # require a DB URL (set via .env or environment)

engine = create_engine(DB_URL, pool_pre_ping=True)

def q(sql, params=None):
    """Safe query helper: returns DataFrame or empty DF on error."""
    try:
        with engine.begin() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()

def fan_games_one_row(fid: int) -> pd.DataFrame:
    """All rows for a fan’s attended games (one row per game, not doubled)."""
    return q("""
        SELECT g.game_id, g.league, g.season, g.game_date,
               gh.team_abbreviation AS home_team, gh.score AS home_score,
               ga.team_abbreviation AS away_team, ga.score AS away_score,
               CASE WHEN gh.is_winner THEN gh.team_abbreviation ELSE ga.team_abbreviation END AS winner
        FROM attendance a
        JOIN game g      ON g.game_id = a.game_id
        JOIN game_team gh ON gh.game_id = g.game_id AND gh.home_away = 'HOME'
        JOIN game_team ga ON ga.game_id = g.game_id AND ga.home_away = 'AWAY'
        WHERE a.fan_id = :fid
        GROUP BY g.game_id, g.league, g.season, g.game_date,
                 gh.team_abbreviation, gh.score, ga.team_abbreviation, ga.score, gh.is_winner
        ORDER BY g.game_date DESC;
    """, {"fid": int(fid)})

# --- top nav links (shows as buttons/links at the top) ---
nav = st.columns([1, 1, 8])
with nav[0]:
    st.page_link("app.py", label="🏠 Overview")
with nav[1]:
    st.page_link("pages/02_Team_Leaderboard.py", label="🏆 Team Leaderboard")
with nav[2]:
    st.page_link("pages/03_Scan_Checkin.py", label="🪪 Scan & Check-in")


# -------------------- THEME BANNER (optional) --------------------
st.set_page_config(page_title="Fantasy Fan — Homepage", layout="centered")

st.markdown("""
<style>
  .block-container { padding-top: 0.5rem; }
  .hero { background:#77B255; color:#fff; padding:24px; border-radius:0 0 14px 14px; margin-bottom:16px; }
  .hero h1 { margin:0; font-size:28px; line-height:1.2; }
  .hero p  { margin:6px 0 0 0; opacity:.95; }
  div[data-testid="metric-container"]{
      background:#ffffff;border:1px solid #e8e5da;border-radius:12px;padding:12px;
  }
</style>
<div class="hero">
  <h1>Fantasy Fan — Personal Overview</h1>
  <p>Your lifetime game log • see progress toward your next reward</p>
</div>
""", unsafe_allow_html=True)

# -------------------- SIDEBAR: PICK CURRENT FAN --------------------
st.sidebar.header("Fan")
_fans = q("""
    SELECT fan_id, COALESCE(fan_name, CONCAT('Fan ', fan_id::text)) AS name
    FROM fan
    ORDER BY fan_id
    LIMIT 5000;
""")
if _fans.empty:
    st.sidebar.warning("No fans found in database.")
    st.stop()

fan_labels = _fans.apply(lambda r: f"{int(r.fan_id)} — {r.name}", axis=1).tolist()
default_idx = 0
if "selected_fan_id" in st.session_state:
    try:
        default_idx = next(i for i, s in enumerate(fan_labels)
                           if s.startswith(f"{st.session_state['selected_fan_id']} —"))
    except StopIteration:
        default_idx = 0

fan_choice = st.sidebar.selectbox("Current fan", fan_labels, index=default_idx)
selected_fan_id = int(fan_choice.split(" — ")[0])
st.session_state["selected_fan_id"] = selected_fan_id

# -------------------- OVERVIEW (personal) --------------------
# 1) identity
fan_row = q("SELECT COALESCE(fan_name, CONCAT('Fan ', fan_id::text)) AS name FROM fan WHERE fan_id=:fid",
            {"fid": selected_fan_id})
fan_name = fan_row.iloc[0]["name"] if not fan_row.empty else f"Fan {selected_fan_id}"

# 2) lifetime games + simple points model
fg = fan_games_one_row(selected_fan_id)
points = int(fg["game_id"].nunique()) if not fg.empty else 0

thresholds = [5, 10, 20, 40]   # Bronze / Silver / Gold / Legend
next_threshold = next((t for t in thresholds if points < t), thresholds[-1])
progress = 0.0 if next_threshold == 0 else min(points / next_threshold, 1.0)
remaining = max(next_threshold - points, 0)

# 3) greeting + progress
st.markdown(f"### Hello {fan_name}!")
st.write(f"{remaining} point(s) away from your next reward")
st.progress(progress)

# lifetime metrics
c1, c2 = st.columns(2)
c1.metric("Lifetime games attended", points)
by_lg = fg.groupby("league")["game_id"].nunique().reset_index() if not fg.empty else pd.DataFrame()
if not by_lg.empty:
    summary = " • ".join(f"{r.league}: {int(r.game_id)}" for _, r in by_lg.iterrows())
else:
    summary = "—"
c2.metric("By league", summary)

st.divider()

# 4) previous 5 games as clickable chips (no W/L decorations by request)
st.markdown("#### Previous games")
if fg.empty:
    st.info("No games yet for this fan.")
else:
    last5 = fg.head(5).copy()  # already sorted desc by date
    def chip_label(r):
        # ex: "2024-10-30: CHA vs ATL"
        d = pd.to_datetime(r["game_date"]).date()
        return f"{d}: {r['home_team']} vs {r['away_team']}"

    cols = st.columns(min(5, len(last5)))
    for i, (_, row) in enumerate(last5.iterrows()):
        if cols[i].button(chip_label(row), key=f"chip_{int(row['game_id'])}"):
            st.session_state["open_game_id"] = int(row["game_id"])

    # If clicked, show details
    if "open_game_id" in st.session_state:
        gid = st.session_state["open_game_id"]
        det = fg[fg["game_id"] == gid].iloc[0]
        st.markdown("##### Game details")
        st.write({
            "game_id": int(det["game_id"]),
            "date": str(pd.to_datetime(det["game_date"]).date()),
            "league": det["league"],
            "home_team": f"{det['home_team']} ({int(det['home_score'])})",
            "away_team": f"{det['away_team']} ({int(det['away_score'])})",
            "winner": det["winner"]
        })

st.divider()

# 5) Record by team (all leagues), with expand-to-view games
st.markdown("#### Record by team")

if fg.empty:
    st.info("No games yet for this fan.")
else:
    # --- map abbrev -> full team name (City + Nickname) per league ---
    tm = q("""
        SELECT league, abbreviation, CONCAT(city, ' ', team_name) AS full_name
        FROM team
    """)
    abbr_name = {(r["abbreviation"], r["league"]): r["full_name"] for _, r in tm.iterrows()}

    def full_name(abbr, league):
        return abbr_name.get((abbr, league), abbr)

    # --- expand fan games to a row per team with W/L/T from that team's perspective ---
    rows = []
    for _, r in fg.iterrows():
        league = r["league"]
        # home perspective
        if int(r["home_score"]) > int(r["away_score"]):
            res_home, res_away = "W", "L"
        elif int(r["home_score"]) < int(r["away_score"]):
            res_home, res_away = "L", "W"
        else:
            res_home, res_away = "T", "T"

        rows.append({
            "game_id": int(r["game_id"]),
            "league": league,
            "game_date": r["game_date"],
            "team": r["home_team"],
            "opponent": r["away_team"],
            "result": res_home,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_score": int(r["home_score"]),
            "away_score": int(r["away_score"]),
        })
        # away perspective
        rows.append({
            "game_id": int(r["game_id"]),
            "league": league,
            "game_date": r["game_date"],
            "team": r["away_team"],
            "opponent": r["home_team"],
            "result": res_away,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "home_score": int(r["home_score"]),
            "away_score": int(r["away_score"]),
        })

    long_df = pd.DataFrame(rows)
    long_df["team_name"] = long_df.apply(lambda x: full_name(x["team"], x["league"]), axis=1)

    # --- aggregate to W/L/T per team ---
    agg = (long_df.groupby(["league", "team", "team_name"], as_index=False)
            .agg(games=("result", "count"),
                 W=("result", lambda s: (s == "W").sum()),
                 L=("result", lambda s: (s == "L").sum()),
                 T=("result", lambda s: (s == "T").sum()))
          )
    agg["win_pct"] = ((agg["W"] + 0.5 * agg["T"]) / agg["games"]).round(3)
    agg = agg.sort_values(["games", "win_pct"], ascending=[False, False])

    # display table (League, Team, W, L, T, Win%)
    display_cols = ["league", "team_name", "W", "L", "T", "win_pct", "games"]
    st.dataframe(agg[display_cols].rename(columns={
        "team_name": "team", "win_pct": "win_pct", "games": "games"
    }), use_container_width=True, height=320)

    st.markdown("#### Expand a team to view lifetime games")
    for _, row in agg.iterrows():
        title = f"{row['team_name']} — {int(row['W'])}-{int(row['L'])}-{int(row['T'])}"
        with st.expander(title):
            sub = long_df[(long_df["league"] == row["league"]) &
                          (long_df["team"] == row["team"])].copy()
            if sub.empty:
                st.info("No games for this team.")
            else:
                sub["date"] = pd.to_datetime(sub["game_date"]).dt.date.astype(str)
                sub["matchup"] = sub.apply(lambda x: f"{x['home_team']} vs {x['away_team']}", axis=1)
                sub["score"] = sub.apply(lambda x: f"{x['home_score']}-{x['away_score']}", axis=1)
                sub = sub[["date", "league", "matchup", "score", "result"]]
                st.dataframe(sub.sort_values("date", ascending=False),
                             use_container_width=True, height=260)


# 6) offers — three static promo cards
st.markdown("#### Offers")
c1, c2, c3 = st.columns(3)
c1.info("10% off concessions at MLB stadiums", icon="🏟️")
c2.info("10% off concessions at NFL stadiums", icon="🏈")
c3.info("10% off select jerseys at NBA arenas", icon="🏀")
