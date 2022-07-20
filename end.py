import sqlite3
import datetime
import shutil


db = sqlite3.connect("the.db")
db.execute("UPDATE Rounds SET stage = 3, ended_at = ? WHERE stage = 2", (datetime.datetime.now(datetime.timezone.utc),))
db.commit()
shutil.copy("the.db", "once.db")
