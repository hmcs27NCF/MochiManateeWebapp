"""
streamlit_prototype.py

Author: Hudson Miller
Date: 07/29/2026

Description:
    This is a Streamlit app running on the Streamlit Community Cloud service. It is used to:
    - Display data collected from Mochi Manatee Simulation through a connection to MongoDB on a table
    - Let the user download the table as a .CSV file
    - Additionally display slide reading times on a bar chart
    
    Data is organized into sessions, each with their own ID, which the bar chart uses to select a session for display.
    
Dependencies:
    - Streamlit
    - Pymongo
    - Pandas
    - Utilities.py (from RefactoredManateeAnalysis, the Mochi Manatee Simulation backend)
"""

from pymongo import MongoClient
from collections import defaultdict
import Utilities
import streamlit as st
import pandas as pd


# - - - - - - - - - -
# MongoDB Connection
# - - - - - - - - - -

# Get the URI from Streamlit's encrypted secrets list. This can be found in the "Manage App" menu.
# WARNING: Do NOT put the unencrypted credentials / access link anywhere in the repository.
# It will compromise the security of the database and make you look silly.
uri = st.secrets["MONGODB_URI"]
client = MongoClient(uri)

st.set_page_config(layout="wide")
st.title("Manatee Simulation Connection")
st.write("")

# Name of the database, then the name of the collection under that database.
db = client["ManateeSegments"]
telemetry = db["TelemetryCollection"]

# - - - - - - - - - - - - - - - - - - - - - - -
# Building a Sessions Table with Utilities.py
# - - - - - - - - - - - - - - - - - - - - - - -

sessions = defaultdict(list)

for doc in telemetry.find():
    sessions[doc["sessionId"]].append(doc)

summary_rows = []

for session_id, docs in sessions.items():

    # Parse the session (requires parse_session_mongodb in Utilities.py)
    s = Utilities.parse_session_mongodb(docs)

    row = {
        "Session ID": session_id,
        "Simulation": s["segment"],
    }

    for scene, ms in s["scene_times"].items():
        row[f"{scene} - Total time (ms)"] = ms

    for target, ms in s["canvas_times"].items():
        if target == "Mailbox":
            row["Mail Box - Viewing time (ms)"] = ms
        else:
            row[f"{target} - Reading time (ms)"] = ms
            
    # Counts the number of times certain events occur.
    friendly = {
        "playerBreathe": "Number of Breaths",
        "seagrassEaten": "Number of Seagrass Eaten",
        "manateeInteraction": "Number of Manatee Interactions",
        "playerHit": "Number of Boat Hits",
        "huddleEnd": "Times Initiated Huddle",
        "tutorialTaskCompleted": "Tutorial Tasks Completed",
    }

    for event, count in s["event_counts"].items():

        column = friendly.get(event, event)
        row[column] = count

    # Metrics derived from Utilities.py.
    row["Chosen Names"] = ", ".join(s["names"])

    row["Total underwater time (s)"] = Utilities.underwater_time(s)

    row["Total game time (s)"] = Utilities.total_game_time(s)

    row["Postbox search time ms)"] = Utilities.postbox_search_time(s)

    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows)

# Option to export as a CSV file.
csv = summary_df.to_csv(index=False).encode("utf-8")

# "download_button" is from Streamlit itself. Once you know about it, letting users download things from your app is pretty simple.
st.download_button(
    label="Download CSV",
    data=csv,
    file_name="mongodb_export.csv",
    mime="text/csv",
)

# Description
st.subheader("Sessions")
st.write("Each row represents one completed player session and includes scene times, reading/viewing times, event counts, and derived metrics.")
st.write("**TIP:** You can sort the table by clicking on the column headers, filter the table by clicking the search bar in the upper-right corner, and resize the table's rows by clicking and dragging space between rows.")
st.write("")

st.dataframe(summary_df, use_container_width=True)


# - - - - - - - - - -
# Adding a Bar Chart
# - - - - - - - - - -

st.write("")
st.subheader("Scene Times Chart")
st.write("")

# A dropdown box that will let users select which session to display on the chart via Session ID.
selected_session = st.selectbox(
    "Select Session",
    options=summary_df["Session ID"]
)

# Get the corresponding row
session = summary_df.loc[
    summary_df["Session ID"] == selected_session
].iloc[0]

# Grabs the name of the segment (Eutrophication, BoatHit or Entanglement) from the "session" dataframe.
simName = session["Simulation"]
st.write("Segment:", simName)
st.write("")

# Displays only data that contains "Reading time (ms)"
sceneTimes = session.filter(regex="Reading time \\(ms\\)")
sceneTimes = sceneTimes.rename_axis("Scene").reset_index(name="Time (ms)")

st.bar_chart(sceneTimes, x="Scene", y="Time (ms)", height=480)