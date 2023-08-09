import sqlite3
import datetime
import shutil
import requests
import config


db = sqlite3.connect("the.db")
num, = db.execute("UPDATE Rounds SET stage = 3, ended_at = ? WHERE stage = 2 RETURNING num", (datetime.datetime.now(datetime.timezone.utc),)).fetchone()
for persona in db.execute("SELECT persona FROM Submissions WHERE round_num = ?", (num,)):
    db.execute("UPDATE Comments SET persona = -1, og_persona = COALESCE(og_persona, persona) WHERE persona = ?", persona)
db.commit()
shutil.copy("the.db", "once.db")
shutil.copy("the.db", "static/the.db")
with open("modify_for_public_viewing.sql") as f:
    script = f.read()
public_db = sqlite3.connect("static/the.db")
public_db.executescript(script)
if config.canon_url:
    requests.post(config.canon_url + "/personas/purge")
