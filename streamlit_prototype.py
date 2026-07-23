from pymongo import MongoClient
from collections import defaultdict
import Utilities
import streamlit as st
import pandas as pd
import subprocess

subprocess.run(["node", "mongodb_prototype.js"], check=True)

print("Reached point A")

uri = st.secrets["MONGODB_URI"]

client = MongoClient(uri)

db = client["ManateeSegments"]
collection = db["TelemetryCollection"]


# title
st.set_page_config(layout="wide")
st.title("Manatee Simulation Connection")
st.write("")

# testing

client = MongoClient("mongodb+srv://segmentUser:e1FFaVUrB1gSiSY0@mongotest.dwu69.mongodb.net/?appName=MongoTest")
db = client["ManateeSegments"]
telemetry = db["TelemetryCollection"]
tlmData = telemetry.find()

print("Reached point B")

# Initialize a Dictionary of Lists instead of a List of Dictionaries
simDict = {
    "Description": [],
    "Event Name": [],
    "Session Number": [],
    "Simulation": [],
    "Timestamp": [],
    "Session ID": []
}

idList = []
sessionNumber = 0

for doc in tlmData:
    
    # Safely get sessionId, default to 'Unknown' if missing
    current_session_id = str(doc.get("sessionId", "Unknown"))
    
    # increment session number if current sessionId is not in idList
    if current_session_id not in idList:
        idList.append(current_session_id)
        sessionNumber += 1
    
    # Safely get the event name
    event_name = doc.get("name", "UnknownEvent")
    
    # player looks at an object
    if event_name == "lookingAt":
        objectText = doc.get("target", "Unknown Target")
        timeTaken = doc.get("intContent", 1000) / 1000
        description = f"Player looked at [ {objectText} ] for {timeTaken} seconds."
        
    # player completes a tutorial task
    elif event_name == "tutorialTaskCompleted":
        objectText = doc.get("textContent", "Unknown Task")
        description = f"Player completed the tutorial task [ {objectText} ]  "
        
    # player completes a scene
    elif event_name == "sceneCompleted":
        objectText = doc.get("textContent", "Unknown Scene")
        description = f"Player completed the scene [ {objectText} ].  "
        
    # player breathed air
    elif event_name == "playerBreathe":
        description = "Player breathed air."
        
    # player boat hit
    elif event_name == "playerHit":
        description = "Player was hit by a boat."
        
    # player ate seagrass
    elif event_name == "seagrassEaten":
        description = "Player ate seagrass."
        
    # multiplayer manatee huddle
    elif event_name == "huddleEnd":
        description = "Player huddled with other manatees."
    
    # player chooses a name
    elif event_name == "manateeNameSelected":
        nameSelected = doc.get("textContent", "Unknown Name")
        description = f"Player selected the name [ {nameSelected} ] for their manatee."
        
    # player touches a manatee
    elif event_name == "manateeInteraction":
        description = "Player interacted with a manatee."
        
    # placeholder in case we don't have a description
    else:
        description = "PLACEHOLDER TEXT"
    
    # Appending info directly to the Dictionary of Lists
    simDict["Description"].append(description)
    simDict["Event Name"].append(event_name)
    simDict["Session Number"].append(sessionNumber)
    simDict["Simulation"].append(str(doc.get("segmentChosen", "Unknown")))
    simDict["Timestamp"].append(str(doc.get("timestamp", "No Timestamp")))
    simDict["Session ID"].append(current_session_id)
    
print("Reached point C")
    
print("Creating DataFrame...")
# This uses the exact same Pandas parsing path as your successful test!
manateeFrame = pd.DataFrame(simDict)

print("Created DataFrame")
#st.dataframe(manateeFrame)

print("Reached point D")


# code to make this program work with Utilities

# -------------------------------------------------------
# Build sessions
# -------------------------------------------------------

sessions = defaultdict(list)

for doc in telemetry.find():
    sessions[doc["sessionId"]].append(doc)

summary_rows = []

# -------------------------------------------------------
# Process each session
# -------------------------------------------------------

for session_id, docs in sessions.items():

    # Parse the session (requires parse_session_mongodb in Utilities.py)
    s = Utilities.parse_session_mongodb(docs)

    row = {
        "Session ID": session_id,
        "Simulation": s["segment"],
    }

    # -----------------------------
    # Scene times
    # -----------------------------
    for scene, ms in s["scene_times"].items():
        row[f"{scene} - Total time (ms)"] = ms

    # -----------------------------
    # Looking-at times
    # -----------------------------
    for target, ms in s["canvas_times"].items():

        # Give Mailbox a nicer name
        if target == "Mailbox":
            row["Mail Box - Viewing time (ms)"] = ms
        else:
            row[f"{target} - Reading time (ms)"] = ms

    # -----------------------------
    # Event counts
    # -----------------------------

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

    # -----------------------------
    # Derived metrics
    # -----------------------------

    row["Chosen Names"] = ", ".join(s["names"])

    row["Total underwater time (s)"] = Utilities.underwater_time(s)

    row["Total game time (s)"] = Utilities.total_game_time(s)

    row["Postbox search time ms)"] = Utilities.postbox_search_time(s)

    summary_rows.append(row)

# -------------------------------------------------------
# Display summary table
# -------------------------------------------------------

summary_df = pd.DataFrame(summary_rows)

# sessions
st.subheader("Sessions")
st.write("Each row represents one completed player session and includes scene times, reading/viewing times, event counts, and derived metrics.")
st.write("**TIP:** You can sort the table by clicking on the column headers, filter the table by clicking the search bar in the upper-right corner, and resize the table's rows by clicking and dragging space between rows.")
st.write("")

st.dataframe(summary_df, use_container_width=True)

# Adding a bar chart
st.write("")
st.subheader("Scene Times Chart")
st.write("")

selected_session = st.selectbox(
    "Select Session",
    options=summary_df["Session ID"]
)

# Get the corresponding row
session = summary_df.loc[
    summary_df["Session ID"] == selected_session
].iloc[0]

simName = session["Simulation"]
st.write("Segment:", simName)
st.write("")

sceneTimes = session.filter(regex="Reading time \\(ms\\)|Viewing time \\(ms\\)")
sceneTimes = sceneTimes.rename_axis("Scene").reset_index(name="Time (ms)")

st.bar_chart(sceneTimes, x="Scene", y="Time (ms)", height=480)

# all data
st.write("")
st.subheader("All Data")
st.write("")

manateeFrame = pd.DataFrame(simDict)
st.dataframe(manateeFrame)