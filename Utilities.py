import csv
from collections import defaultdict

#Structural log types (sceneChange, sceneCompleted, lookingAt, manateeNameSelected)
# are handled explicitly below. Everything else falls through the last elif and is
# auto-counted as an event, so a new Unity event needs no changes in here

#The on-land boat scenes are always the first and last scene of a session, so
# underwater_time excludes them by position rather than by name. If a mid-session
# surface scene ever gets added, that's the assumption to revisit

def _to_int(v):

    try:
        return int(v)
    except (TypeError, ValueError):
        return 0

def parse_session(path):

    #Reads one session CSV a single time and pulls out everything at once
    scene_times = {}
    canvas_times = defaultdict(int)
    canvas_scene = {}
    event_counts = defaultdict(int)
    names = []
    segment = ""
    lobby_end = None
    mailbox_seen = None
    first_scene = None
    last_scene = None
    pending = []

    with open(path, newline = "") as f:
        reader = csv.DictReader(f)  #Header based, so column order can't bite us
        for row in reader:
            kind = row.get("name", "") or ""
            text = (row.get("textContent", "") or "").replace(";", "")
            seg = row.get("segmentChosen", "") or ""
            if seg and not segment:
                segment = seg

            if kind in ("sceneChange", "sceneCompleted"):
                scene_times[text] = _to_int(row.get("intContent") )
                #Scene events fire when a scene ENDS, so anything looked at since
                # the last one belongs to this scene
                for target in pending:
                    canvas_scene.setdefault(target, text)
                pending = []
                if first_scene is None:
                    first_scene = text
                last_scene = text   #Keeps updating, ends on the final scene
                if kind == "sceneCompleted" and text == "9 - MultiplayerLobby":
                    lobby_end = _to_int(row.get("time") )

            elif kind == "lookingAt":
                if row.get("intContent") not in (None, "", "null"):
                    canvas_times[text] += _to_int(row.get("intContent") )
                pending.append(text)
                if text == "Mailbox" and mailbox_seen is None:
                    mailbox_seen = _to_int(row.get("time") )

            elif kind == "manateeNameSelected":
                names.append(text)

            elif kind:  #Anything non-blank that isn't structural is a countable event
                event_counts[kind] += 1

    return {
        "segment": segment,
        "scene_times": scene_times,
        "canvas_times": dict(canvas_times),
        "canvas_scene": canvas_scene,   #{target: scene it was looked at in}
        "event_counts": dict(event_counts),
        "names": names,
        "first_scene": first_scene,
        "last_scene": last_scene,
        "_lobby_end": lobby_end,
        "_mailbox_seen": mailbox_seen,
    }

def underwater_time(session):

    boundary = {session["first_scene"], session["last_scene"]}
    return sum(t for name, t in session["scene_times"].items() if name not in boundary)

def total_game_time(session):

    return sum(session["scene_times"].values() )

def postbox_search_time(session):

    lobby, mailbox = session["_lobby_end"], session["_mailbox_seen"]
    if lobby is None or mailbox is None:
        return None
    return round(lobby - mailbox, 0)

# ==========================================================
# MongoDB version of parse_session()
# ==========================================================

def parse_session_mongodb(docs):

    scene_times = {}
    canvas_times = defaultdict(int)
    canvas_scene = {}
    event_counts = defaultdict(int)
    names = []

    segment = ""
    lobby_end = None
    mailbox_seen = None
    first_scene = None
    last_scene = None

    pending = []

    # Keep events in chronological order
    docs = sorted(docs, key=lambda d: d.get("time", 0))

    for row in docs:

        kind = row.get("name", "") or ""

        # lookingAt stores the object name in "target"
        if kind == "lookingAt":
            text = row.get("target", "") or ""
        else:
            text = row.get("textContent", "") or ""

        text = text.replace(";", "")

        seg = row.get("segmentChosen", "") or ""
        if seg and not segment:
            segment = seg

        #
        # Scene events
        #
        if kind in ("sceneChange", "sceneCompleted"):

            # Scene duration is already stored in intContent
            scene_times[text] = _to_int(row.get("intContent"))

            # Associate pending lookingAt events with this scene
            for target in pending:
                canvas_scene.setdefault(target, text)
            pending = []

            if first_scene is None:
                first_scene = text

            last_scene = text

            if kind == "sceneCompleted" and text == "9 - MultiplayerLobby":
                lobby_end = _to_int(row.get("time"))

        #
        # Looking at slides / objects
        #
        elif kind == "lookingAt":

            if row.get("intContent") not in (None, "", "null"):
                canvas_times[text] += _to_int(row.get("intContent"))

            pending.append(text)

            if text == "Mailbox" and mailbox_seen is None:
                mailbox_seen = _to_int(row.get("time"))

        #
        # Manatee names
        #
        elif kind == "manateeNameSelected":

            names.append(text)

        #
        # Everything else gets counted
        #
        elif kind:

            event_counts[kind] += 1

    return {
        "segment": segment,
        "scene_times": scene_times,
        "canvas_times": dict(canvas_times),
        "canvas_scene": canvas_scene,
        "event_counts": dict(event_counts),
        "names": names,
        "first_scene": first_scene,
        "last_scene": last_scene,
        "_lobby_end": lobby_end,
        "_mailbox_seen": mailbox_seen,
    }