import sqlite3
import datetime
import sys

db = sqlite3.connect("the.db")

with open(sys.argv[1]) as f:
    spec = f.read()

db.execute("INSERT INTO Rounds (stage, spec, started_at) VALUES (1, ?, ?)", (spec, datetime.datetime.now(datetime.timezone.utc)))
db.commit()
