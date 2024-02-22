import sqlite3
import datetime
import hashlib
import os
import shutil
import requests
import config


db = sqlite3.connect("the.db")
num, = db.execute("UPDATE Rounds SET stage = 3, ended_at = ? WHERE stage = 2 RETURNING num", (datetime.datetime.now(datetime.timezone.utc),)).fetchone()
for persona in db.execute("SELECT persona FROM Submissions WHERE round_num = ?", (num,)):
    db.execute("UPDATE Comments SET persona = -1, og_persona = COALESCE(og_persona, persona) WHERE persona = ?", persona)

# tiebreak
winners = db.execute("SELECT player_id FROM Scores WHERE round_num = ? AND won ORDER BY player_id", (num,)).fetchall()
winner_idx = int.from_bytes(hashlib.sha256(str(num).encode()).digest(), "big") % len(winners)
for idx, so_called_winner in enumerate(winners):
    if idx != winner_idx:
        db.execute("INSERT INTO Tiebreaks (round_num, player_id, new_rank) VALUES (?, ?, ?)", (num, so_called_winner, 2))

db.commit()
os.makedirs("backups", exist_ok=True)
shutil.copy("the.db", f"backups/{num}.db")
shutil.copy("the.db", "static")
with open("modify_for_public_viewing.sql") as f:
    script = f.read()
public_db = sqlite3.connect("static/the.db")
public_db.executescript(script)
if config.canon_url:
    requests.post(config.canon_url + "/personas/purge")
