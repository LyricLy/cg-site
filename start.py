import datetime
import sys

from db import connect


db = connect()

with open(sys.argv[1]) as f:
    spec = f.read()

now = datetime.datetime.now(datetime.timezone.utc)
db.execute("DELETE FROM Rounds WHERE stage = 1")
db.execute("INSERT INTO Rounds (stage, spec, started_at, stage2_at) VALUES (1, ?, ?, ?)", (spec, now, now+datetime.timedelta(days=7)))
db.commit()
