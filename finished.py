import sqlite3

db = sqlite3.connect("the.db")

for name, done in db.execute("SELECT name, finished_guessing FROM Submissions INNER JOIN People ON id = author_id WHERE round_num = (SELECT MAX(num) FROM Rounds) ORDER BY name COLLATE NOCASE"):
    print(name, bool(done))
