import random
import datetime
import requests

import config
from db import connect


db = connect()
num, = db.execute("SELECT MIN(num) FROM Rounds WHERE stage = 1")
now = datetime.datetime.now(datetime.timezone.utc)
db.execute("UPDATE Rounds SET stage = 2, stage2_at = ?, ended_at = ? WHERE num = ?", (now, now+datetime.timedelta(days=4), *num))
subs = db.execute("SELECT * FROM Submissions WHERE round_num = ?", num).fetchall()
random.shuffle(subs)
for idx, sub in enumerate(subs, start=1):
    author = sub["author_id"]
    if config.canon_url:
        persona = requests.post(config.canon_url + f"/users/{author}/personas", json={"name": f"[author of #{idx}]", "sudo": True, "temp": True}).json()["id"]
    else:
        persona = None
    db.execute("UPDATE Submissions SET position = ?, persona = ? WHERE round_num = ? AND author_id = ?", (idx, persona, sub["round_num"], author))
db.commit()
