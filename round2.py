import sqlite3
import random
import datetime
import config
import requests


db = sqlite3.connect("the.db")
db.row_factory = sqlite3.Row
num, = db.execute("SELECT MIN(num) FROM Rounds WHERE stage = 1")
db.execute("UPDATE Rounds SET stage = 2, stage2_at = ? WHERE num = ?", (datetime.datetime.now(datetime.timezone.utc), *num))
subs = db.execute("SELECT * FROM Submissions WHERE round_num = ?", num).fetchall()
random.shuffle(subs)
for idx, sub in enumerate(subs, start=1):
    author = sub["author_id"]
    persona = requests.post(config.canon_url + f"/users/{author}/personas", json={"name": f"[author of #{idx}]", "sudo": True, "temp": True}).json()["id"]
    db.execute("UPDATE Submissions SET position = ?, persona = ? WHERE round_num = ? AND author_id = ?", (idx, persona, sub["round_num"], author))
db.commit()
