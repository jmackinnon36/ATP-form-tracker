"""
ATP Player Form Tracker
A Streamlit app answering one question: is this player in form right now?

Data: Jeff Sackmann's tennis_atp data, via an archival mirror (CC BY-NC-SA 4.0).
Run locally with:  streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="ATP Player Form Tracker", layout="wide")

# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
# Sackmann removed his tennis_atp repo in 2026; this is an archival mirror of it.
BASE_URL = ("https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/"
            "main/atp/atp_matches_{year}.csv")
YEARS = [2024, 2025, 2026]

# Sackmann's tourney_date is the tournament start date, so several matches share
# one date. Round order lets us sort matches within a tournament correctly.
ROUND_ORDER = {"RR": 1, "R128": 2, "R64": 3, "R32": 4, "R16": 5,
               "QF": 6, "SF": 7, "BR": 8, "F": 8}


@st.cache_data  # downloads once, then reuses the result on every interaction
def load_matches(years):
    frames, failed = [], []
    for year in years:
        try:
            frames.append(pd.read_csv(BASE_URL.format(year=year)))
        except Exception as e:
            failed.append(f"{year} ({type(e).__name__}: {e})")
    if not frames:
        return None, failed
    df = pd.concat(frames, ignore_index=True)
    # Walkovers and defaults: no match was played, so they would inflate win %
    df = df[~df["score"].astype(str).str.contains("W/O|DEF", regex=True)]
    df["tourney_date"] = pd.to_datetime(df["tourney_date"].astype(str), format="%Y%m%d")
    return df, failed


def player_matches(df, player):
    """Reshape winner/loser rows into one row per match from the player's view."""
    # (name prefix, stats prefix, opponent prefix, result)
    sides = [("winner", "w", "loser", 1), ("loser", "l", "winner", 0)]
    frames = []
    for me, stat, opp, result in sides:
        m = df[df[f"{me}_name"] == player]
        frames.append(pd.DataFrame({
            "date": m["tourney_date"],
            "tournament": m["tourney_name"],
            "surface": m["surface"],
            "round": m["round"],
            "opponent": m[f"{opp}_name"],
            "opp_rank": m[f"{opp}_rank"],
            "score": m["score"],
            "won": result,
            "serve_pts": m[f"{stat}_svpt"],
            "serve_pts_won": m[f"{stat}_1stWon"] + m[f"{stat}_2ndWon"],
        }))
    out = pd.concat(frames)
    out["round_order"] = out["round"].map(ROUND_ORDER).fillna(0)
    out = out.sort_values(["date", "round_order"]).reset_index(drop=True)
    return out


df, failed_years = load_matches(YEARS)
if df is None:
    st.error("Couldn't download any match data. Reasons:\n\n" + "\n\n".join(failed_years))
    st.stop()
if failed_years:
    st.warning("Couldn't load some years:\n\n" + "\n\n".join(failed_years))

# ---------------------------------------------------------------------------
# 2. Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Controls")

# Only offer players with enough matches for a rolling window to mean anything
match_counts = pd.concat([df["winner_name"], df["loser_name"]]).value_counts()
players = sorted(match_counts[match_counts >= 20].index)
default = players.index("Jannik Sinner") if "Jannik Sinner" in players else 0

player = st.sidebar.selectbox("Player", players, index=default)
surfaces = st.sidebar.multiselect("Surface", ["Hard", "Clay", "Grass"],
                                  default=["Hard", "Clay", "Grass"])
window = st.sidebar.slider("Rolling window (matches)", 5, 30, 10)

# ---------------------------------------------------------------------------
# 3. Build the player's match history
# ---------------------------------------------------------------------------
all_matches = player_matches(df, player)
pm = all_matches[all_matches["surface"].isin(surfaces)].reset_index(drop=True)

if len(pm) < window:
    st.info("Not enough matches for this filter. Widen the surfaces or shrink the window.")
    st.stop()

pm["match_no"] = range(1, len(pm) + 1)
pm["Rolling win %"] = pm["won"].rolling(window).mean() * 100
pm["Rolling serve points won %"] = (
    pm["serve_pts_won"].rolling(window, min_periods=1).sum()
    / pm["serve_pts"].rolling(window, min_periods=1).sum() * 100
)
pm.loc[: window - 2, "Rolling serve points won %"] = None  # hide incomplete windows

# ---------------------------------------------------------------------------
# 4. Page layout
# ---------------------------------------------------------------------------
st.title("ATP Player Form Tracker")
st.caption(f"Is {player} in form? Rolling performance across "
           f"{YEARS[0]}–{YEARS[-1]}, {window}-match window.")

last10 = pm.tail(10)
c1, c2, c3 = st.columns(3)
c1.metric("Matches", len(pm))
c2.metric(f"Overall win % ({YEARS[0]}–{YEARS[-1]})", f"{pm['won'].mean() * 100:.0f}%")
c3.metric("Last 10", f"{int(last10['won'].sum())}–{int(len(last10) - last10['won'].sum())}",
          delta=f"{(last10['won'].mean() - pm['won'].mean()) * 100:+.0f} pts vs own average")

if len(pm) < 30:
    st.warning(f"Small sample: only {len(pm)} matches with this filter, so treat the "
               "form lines and percentages with caution.")

# Form trend chart
chart_df = pm.melt(
    id_vars=["match_no", "date", "opponent", "tournament"],
    value_vars=["Rolling win %", "Rolling serve points won %"],
    var_name="Metric", value_name="Percent",
)
fig = px.line(chart_df, x="match_no", y="Percent", color="Metric",
              hover_data=["date", "tournament", "opponent"],
              color_discrete_map={"Rolling win %": "#FF6B6B",
                                  "Rolling serve points won %": "#4DA3FF"})
fig.update_layout(xaxis_title="Match number (chronological)", yaxis_title="%",
                  legend_title=None, yaxis_range=[0, 100],
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
st.plotly_chart(fig, width="stretch")

# Opponent quality: how does the player perform against different calibres of opponent?
st.subheader("Win % by opponent ranking")
RANK_BINS = [0, 10, 20, 50, 100, float("inf")]
RANK_LABELS = ["Top 10", "11–20", "21–50", "51–100", "100+"]
ranked = pm.dropna(subset=["opp_rank"]).copy()
ranked["Opponent rank"] = pd.cut(ranked["opp_rank"], bins=RANK_BINS, labels=RANK_LABELS)
by_rank = (ranked.groupby("Opponent rank", observed=False)
           .agg(matches=("won", "size"), win_pct=("won", "mean"))
           .reset_index())
by_rank["win_pct"] *= 100
by_rank["label"] = by_rank["matches"].map(lambda n: f"{n} match" + ("" if n == 1 else "es"))
fig3 = px.bar(by_rank, x="Opponent rank", y="win_pct", text="label")
fig3.update_layout(xaxis_title="Opponent ranking at the time", yaxis_title="Win %",
                   yaxis_range=[0, 105])
fig3.update_traces(textposition="outside")
st.plotly_chart(fig3, width="stretch")
st.caption("Compare the last-10 record with this view: a poor run against top-10 players "
           "means something different from a poor run against unseeded opponents. "
           f"{len(pm) - len(ranked)} matches with no opponent ranking are excluded.")

left, right = st.columns(2)

with left:
    st.subheader("Win % by surface")
    by_surface = (all_matches.groupby("surface")
                  .agg(matches=("won", "size"), win_pct=("won", "mean"))
                  .reset_index())
    by_surface["win_pct"] *= 100
    by_surface["label"] = by_surface["matches"].map(lambda n: f"{n} match" + ("" if n == 1 else "es"))
    fig2 = px.bar(by_surface, x="surface", y="win_pct", text="label")
    fig2.update_layout(xaxis_title=None, yaxis_title="Win %")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, width="stretch")

with right:
    st.subheader("Most recent matches")
    recent = pm.tail(10).iloc[::-1].copy()
    recent["Result"] = recent["won"].map({1: "W", 0: "L"})
    recent["Tournament start"] = recent["date"].dt.strftime("%d %b %Y")
    st.dataframe(
        recent[["Tournament start", "tournament", "round", "opponent", "Result", "score"]],
        hide_index=True, width="stretch",
    )

latest = df["tourney_date"].max().strftime("%d %b %Y")
st.caption(f"Data: Jeff Sackmann / tennis_atp via the tennis-sackmann-archive mirror "
           f"(CC BY-NC-SA 4.0). Latest tournament in data: {latest}.")

with st.expander("Limitations"):
    st.markdown(
        "- **Data cut-off:** the data ends at the latest tournament shown above, so "
        "'current form' means form as of that date, not today.\n"
        "- **Opponent quality in the trend chart:** the rolling lines treat all opponents "
        "equally. Use the opponent ranking chart to see the split.\n"
        "- **Match number, not time:** the x-axis is match order, so injury breaks do not "
        "show as gaps.\n"
        "- **Retirements and missing stats:** retirements count as normal results, and "
        "matches with no serve stats are skipped in the serve line. Walkovers and "
        "defaults are excluded because no match was played.\n"
        "- **Short window:** a few seasons of tour-level data is enough for form, "
        "not for a career view."
    )
