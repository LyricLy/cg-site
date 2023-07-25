import sqlite3


db = sqlite3.connect("the.db")
db.row_factory = sqlite3.Row
num, = db.execute("SELECT MIN(num) FROM Rounds WHERE stage = 2")
subs = db.execute("SELECT * FROM Submissions WHERE round_num = ? ORDER BY position", num).fetchall()
db.execute("UPDATE Submissions SET position = NULL WHERE round_num = ?", num)
for idx, sub in enumerate(subs, start=1):
    db.execute("UPDATE Submissions SET position = ? WHERE round_num = ? AND author_id = ?", (idx, sub["round_num"], sub["author_id"]))
db.commit()
