import functools
import sqlite3
import datetime

import pygments
import mistune
import flask
import flask_discord
from flask_discord import requires_authorization as auth

import config


app = flask.Flask(__name__)
app.secret_key = config.secret_key
discord = flask_discord.DiscordOAuth2Session(app, 435756251205468160, config.client_secret, "http://localhost:7000/callback", config.bot_token)


def get_db():
    try:
        return flask.g._db
    except AttributeError:
        db = sqlite3.connect("the.db", detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON;")
        flask.g._db = db
        return db

@app.teardown_appcontext
def close_connection(exception):
    try:
        flask.g._db.close()
    except AttributeError:
        pass


@app.route("/")
def root():
    cur = get_db().execute("SELECT MAX(num) FROM Rounds WHERE stage <> 3;")
    if r := cur.fetchone()[0]:
        return flask.redirect(flask.url_for("show_round", num=r))
    else:
        return flask.redirect(flask.url_for("index"))

@app.route("/index/")
def index():
    return "<br>".join(f"<a href='/{n}/'>" for n, in get_db().execute("SELECT num FROM Rounds;"))

@app.route("/<int:num>/")
def show_round(num):
    cur = get_db().execute("SELECT * FROM Rounds WHERE num = ?;", (num,))
    if not (rnd := cur.fetchone()):
        flask.abort(404)
    match rnd["stage"]:
        case 1:
                return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>code guessing #{num}</title>
  </head>
  <body>
    <h1>code guessing, round #{num}, stage 1 (writing)</h1>
    <p>started at {rnd['started_at']}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
  </body>
</html>
"""
        case 2:
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>code guessing #{num}</title>
  </head>
  <body>
    <h1>code guessing, round #{num}, stage 2 (guessing)</h1>
    <p>started at {rnd['started_at']}; stage 2 since {rnd['stage2_at']}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
  </body>
</html>
"""

@app.route("/callback")
def callback():
    discord.callback()
    return flask.redirect(flask.url_for("root"))

@app.errorhandler(flask_discord.Unauthorized)
def redirect_unauthorized(e):
    return discord.create_session(["identify"])

@app.errorhandler(404)
def not_found(e):
    return 'page not found :(<br><a href="/">go home</a>'
