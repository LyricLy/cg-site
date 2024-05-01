import datetime
import sqlite3

def datetime_converter(value):
    return datetime.datetime.fromisoformat(value.decode())

def datetime_adapter(value):
    return value.isoformat()

sqlite3.register_converter("timestamp", datetime_converter)
sqlite3.register_adapter(datetime.datetime, datetime_adapter)

def connect(path="the.db"):
    db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db
