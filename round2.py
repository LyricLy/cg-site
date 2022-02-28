import sqlite3
import random


db = sqlite3.connect("the.db")
db.row_factory = sqlite3.Row
num, = db.execute("SELECT MIN(num) FROM Rounds WHERE stage = 1")
db.execute("UPDATE Rounds SET stage = 2 WHERE num = ?", num)
subs = db.execute("SELECT * FROM Submissions WHERE round_num = ?", num).fetchall()
random.shuffle(subs)
for idx, sub in enumerate(subs, start=1):
    db.execute("UPDATE Submissions SET position = ? WHERE round_num = ? AND author_id = ?", (idx, sub["round_num"], sub["author_id"]))
db.commit()
