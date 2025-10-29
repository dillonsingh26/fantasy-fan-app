# pages/02_Team_Leaderboard.py
import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


# ---- Persistent Header (replace your existing render_header with this) ----
import os
import streamlit as st

LOGO_PATH = "logo.png"     # or "assets/logo.png"
LOGO_HEIGHT = 44           # tweak size here

def render_header(active_page: str):
    """
    active_page: "overview" or "leaderboard"
    """
    st.markdown(f"""
    <style>
      .block-container {{ padding-top: 0.75rem; }}
      .ff-header {{
        background:#77B255;
        color:#fff;
        padding:12px 16px;
        border-radius: 10px;
        margin-bottom: 14px;
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:16px;
      }}
      .ff-left {{
        display:flex; align-items:center; gap:12px;
      }}
      .ff-logo {{
        display:flex; align-items:center; justify-content:center;
        height:{LOGO_HEIGHT}px; width:auto;
        padding:4px 6px; background:rgba(255,255,255,0.10);
        border-radius:10px; border:1px solid rgba(255,255,255,0.20);
      }}
      .ff-title {{ margin:0; font-size:22px; font-weight:700; line-height:1.1; }}
      .ff-sub   {{ margin:0; opacity:.95; font-size:13px; }}
      .ff-nav a, .ff-nav button {{
        margin-left:8px;
        border:1px solid rgba(255,255,255,0.25);
        background:rgba(255,255,255,0.10);
        color:#fff !important;
      }}
    </style>
    """, unsafe_allow_html=True)

    # build header HTML (logo + titles on left; nav on right)
    left_html = ""
    if os.path.exists(LOGO_PATH):
        # use <img> directly so we fully control sizing/margins
        left_html += f'<div class="ff-logo"><img src="{LOGO_PATH}" height="{LOGO_HEIGHT}" style="display:block;"></div>'

    left_html += """
      <div>
        <p class="ff-title">Fantasy Fan</p>
        <p class="ff-sub">Your lifetime game log • team leaderboards</p>
      </div>
    """

    st.markdown(
        f"""
        <div class="ff-header">
          <div class="ff-left">{left_html}</div>
          <div class="ff-nav"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # place the actual nav buttons right under the header (right-aligned feel)
    nav = st.columns([8, 1.1, 1.4])
    with nav[1]:
        try:
            st.page_link("app.py", label="🏠 Overview")
        except Exception:
            if st.button("🏠 Overview", use_container_width=True):
                try: st.switch_page("app.py")
                except Exception: pass
    with nav[2]:
        try:
            st.page_link("pages/02_Team_Leaderboard.py", label="🏆 Team Leaderboard")
        except Exception:
            if st.button("🏆 Team Leaderboard", use_container_width=True):
                try: st.switch_page("pages/02_Team_Leaderboard.py")
                except Exception: pass



# --------- DB SETUP (same env var) ---------
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DB_URL = os.getenv("DATABASE_URL")
    except Exception:
        pass
if not DB_URL:
    st.stop()

engine = create_engine(DB_URL, pool_pre_ping=True)

def q(sql, params=None):
    try:
        with engine.begin() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})
    except Exception as e:
        st.error(f"Query failed: {e}")
        return pd.DataFrame()

# --------- PAGE META ---------
st.set_page_config(page_title="Team Leaderboard", layout="centered")

render_header(active_page="leaderboard")

st.title("Team Leaderboard")
st.caption("Lifetime — ranked by total games attended for the selected team")

# --------- HELPERS ---------
@st.cache_data(ttl=300)
def teams_with_games():
    return q("""
        SELECT DISTINCT t.league, t.abbreviation, CONCAT(t.city, ' ', t.team_name) AS team_full
        FROM team t
        JOIN game_team gt ON gt.team_abbreviation = t.abbreviation AND gt.league = t.league
        JOIN game g ON g.game_id = gt.game_id
        ORDER BY t.league, t.abbreviation;
    """)

# --------- UI: League & Team pickers ---------
teams_df = teams_with_games()
if teams_df.empty:
    st.info("No teams with games found. Load game data first.")
    st.stop()

left, right = st.columns([1, 2], vertical_alignment="bottom")
with left:
    leagues = sorted(teams_df["league"].unique().tolist())
    league_pick = st.selectbox("League", leagues, index=0)
with right:
    options = teams_df[teams_df["league"] == league_pick].copy()
    options["label"] = options["abbreviation"] + " — " + options["team_full"]
    team_label = st.selectbox("Team", options["label"].tolist(), index=0)
    team_abbr = team_label.split(" — ")[0]

st.divider()

# --------- QUERY: Lifetime leaderboard (top 25 by total games) ---------
leaderboard = q("""
    WITH fan_team_games AS (
        SELECT
            a.fan_id,
            COALESCE(f.fan_name, CONCAT('Fan ', a.fan_id::text)) AS fan_name,
            g.game_id,
            g.game_date,
            gh.score AS home_score,
            ga.score AS away_score,
            gt.is_winner::int AS win_flag
        FROM attendance a
        JOIN game g        ON g.game_id = a.game_id
        JOIN game_team gt  ON gt.game_id = g.game_id                      -- selected team's side
        JOIN game_team gh  ON gh.game_id = g.game_id AND gh.home_away='HOME'
        JOIN game_team ga  ON ga.game_id = g.game_id AND ga.home_away='AWAY'
        LEFT JOIN fan f    ON f.fan_id = a.fan_id
        WHERE gt.league = :league
          AND gt.team_abbreviation = :abbr
    ),
    agg AS (
        SELECT
            fan_id,
            MAX(fan_name) AS fan_name,
            COUNT(*)      AS games,
            SUM(win_flag) AS W,
            SUM(CASE WHEN home_score = away_score THEN 1 ELSE 0 END) AS T
        FROM fan_team_games
        GROUP BY fan_id
    )
    SELECT
        fan_id,
        fan_name,
        games,
        W,
        (games - W - T) AS L,
        CASE WHEN games = 0 THEN 0 ELSE ROUND((W + 0.5*T)::numeric / games * 100, 1) END AS win_pct_num,
        TO_CHAR(CASE WHEN games = 0 THEN 0 ELSE ((W + 0.5*T)::numeric / games * 100) END, 'FM9990.0"%"') AS win_pct,
        (SELECT MAX(game_date) FROM fan_team_games ftg WHERE ftg.fan_id = agg.fan_id) AS last_attended
    FROM agg
    ORDER BY games DESC, win_pct_num DESC
    LIMIT 25;
""", {"league": league_pick, "abbr": team_abbr})

if leaderboard.empty:
    st.info("No fan attendance found for this team yet.")
else:
    out = leaderboard.copy()

# normalize column names to lowercase
out.columns = [c.lower() for c in out.columns]

# Guard against NaT
if "last_attended" in out.columns:
    out["last_attended"] = pd.to_datetime(out["last_attended"], errors="coerce").dt.date.astype("string")
    out["last_attended"] = out["last_attended"].fillna("—")

# add missing columns safely
for c in ["t"]:
    if c not in out.columns:
        out[c] = 0

# rename for display
rename_map = {
    "fan_id": "Fan ID",
    "fan_name": "Fan Name",
    "games": "Games",
    "w": "W",
    "l": "L",
    "t": "T",
    "win_pct": "Win %",
    "last_attended": "Last Attended Date",
}
display_cols = [col for col in rename_map if col in out.columns]
out = out[display_cols].rename(columns=rename_map)

st.dataframe(out, use_container_width=True, height=560)

