# ATP Player Form Tracker

Interactive Streamlit app that answers one question: is this player in form right now, and against whom?

**Live app:** https://atp-form-tracker.streamlit.app/

## What it shows
- **Headline numbers:** matches, overall win % and last-10 record compared with the player's own average
- **Form trend:** rolling win % and rolling serve points won %, with an adjustable window of 5 to 30 matches
- **Opponent ranking view:** win % against top 10, 11-20, 21-50, 51-100 and 100+ opponents, with match counts
- **Surface split and recent results:** win % by surface and the ten most recent matches

## How it works
Each match is stored once as a winner row and a loser row, so the app reshapes the data into one row per match from the chosen player's point of view. Rolling serve points won % is calculated from totals across the window, so longer matches carry more weight. Walkovers and defaults are excluded because no match was played.

## Built with
Python, Streamlit, pandas and Plotly. Developed with AI-assisted coding and deployed on Streamlit Community Cloud.

## Data
Jeff Sackmann's ATP match data (CC BY-NC-SA 4.0), loaded from an archived copy after the original repository was removed. The data ends in late May 2026.

## Limitations
- Opponent quality is not accounted for in the rolling form lines, so use the opponent ranking view alongside them
- The x-axis is match order, so injury breaks do not appear as gaps
- A small-sample warning appears when a filter leaves fewer than 30 matches

## Run locally
```
pip install -r requirements.txt
python -m streamlit run app.py
```
