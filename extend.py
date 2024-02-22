import datetime
import sqlite3
import sys

def parse_delta(s):
    count = int(s[:-1])
    unit = s[-1]
    if unit == "d":
        return datetime.timedelta(days=count)
    elif unit == "h":
        return datetime.timedelta(hours=count)
    else:
        raise ValueError(f"unknown time unit '{unit}'")

t = parse_delta(sys.argv[1])

def datetime_converter(value):
    return datetime.datetime.fromisoformat(value.decode())
sqlite3.register_converter("timestamp", datetime_converter)
db = sqlite3.connect("the.db", detect_types=sqlite3.PARSE_DECLTYPES)
db.row_factory = sqlite3.Row

num, stage, stage2_at, ended_at = db.execute("SELECT num, stage, stage2_at, ended_at FROM Rounds WHERE stage = 1 OR stage = 2").fetchone()
if stage == 1:
    stage2_at += t
elif stage == 2:
    ended_at += t
db.execute("UPDATE Rounds SET stage2_at = ?, ended_at = ? WHERE num = ?", (stage2_at, ended_at, num))
db.commit()
