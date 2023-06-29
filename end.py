import sqlite3
import datetime
import shutil
import requests
import config


db = sqlite3.connect("the.db")
num, = db.execute("UPDATE Rounds SET stage = 3, ended_at = ? WHERE stage = 2 RETURNING num", (datetime.datetime.now(datetime.timezone.utc),)).fetchone()
for persona in db.execute("SELECT persona FROM Submissions WHERE round_num = ?", (num,)):
    db.execute("UPDATE Comments SET persona = -1, og_persona = IIF(og_persona IS NULL, persona, og_persona) WHERE persona = ?", persona)
db.commit()
shutil.copy("the.db", "once.db")
shutil.copy("the.db", "/static/the.db")
public_db = sqlite3.connect("/static/the.db")
public_db.execute("DROP TABLE Likes")
public_db.execute("DROP TABLE Comments")
requests.post(config.canon_url + "/personas/purge")
