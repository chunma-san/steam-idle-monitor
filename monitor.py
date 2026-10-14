#!/usr/bin/env python3

import subprocess
import os
import re
from datetime import datetime

CONTAINER = os.getenv("ASF_CONTAINER", "archisteamfarm")

IDLE = "Playing selected GamesPlayedWhileIdle:"
DISCONNECT = "Disconnected from Steam!"
LOGGED_ON = "Successfully logged on"
FARMING = "Now farming"

def fmt(seconds):
    seconds = max(0, int(seconds))
    d, seconds = divmod(seconds, 86400)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    if d:
        return f"{d}d {h:02d}h {m:02d}m {s:02d}s"
    return f"{h:02d}h {m:02d}m {s:02d}s"

p = subprocess.run(
    ["docker", "logs", CONTAINER, "--since", "720h"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

events = []

for line in p.stdout.splitlines():
    m = re.match(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\|",
        line
    )
    if not m:
        continue

    ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")

    if IDLE in line:
        raw = line.split(IDLE, 1)[1].strip()
        games = [x.strip() for x in raw.split(",") if x.strip()]
        events.append((ts, "idle", games))

    elif DISCONNECT in line:
        events.append((ts, "disconnect", None))

    elif LOGGED_ON in line:
        events.append((ts, "loggedon", None))

    elif FARMING in line:
        events.append((ts, "farming", None))

if not events:
    print("No ASF activity found.")
    raise SystemExit(1)

now = datetime.now()

active = False
connected = False
current_start = None
current_games = []
total = 0.0

for ts, kind, data in events:

    if kind == "disconnect":
        if active and current_start:
            total += max(0, (ts - current_start).total_seconds())
        active = False
        connected = False
        current_start = None

    elif kind == "loggedon":
        connected = True

    elif kind == "farming":
        if active and current_start:
            total += max(0, (ts - current_start).total_seconds())
        active = False
        current_start = None

    elif kind == "idle":
        current_games = data

        # Repeated ResetGamesPlayed must NOT reset the timer.
        if connected and not active:
            active = True
            current_start = ts

if active and current_start:
    total += max(0, (now - current_start).total_seconds())
    current = (now - current_start).total_seconds()
else:
    current = 0

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("🎮 ASF GamesPlayedWhileIdle")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"{'🟢' if active else '🔴'} Status          : {'ACTIVE' if active else 'INACTIVE'}")
print(f"{'🔌' if connected else '❌'} Steam           : {'Connected' if connected else 'Disconnected'}")
print(f"🎯 Games           : {len(current_games)}")
print(f"⏱️  Total Idle      : {fmt(total)}")

if active:
    print(f"▶️  Current Session : {fmt(current)}")
    print(f"🕐 Session Started : {current_start:%Y-%m-%d %H:%M:%S}")
else:
    print("▶️  Current Session : --")

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
