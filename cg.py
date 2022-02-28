import functools
import traceback
import sqlite3
import datetime
import io
import os
import uuid

import mistune
import flask
import flask_discord
from flask_discord import requires_authorization as auth
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

import config


app = flask.Flask(__name__)
app.secret_key = config.secret_key
if "OAUTHLIB_INSECURE_TRANSPORT" in os.environ:
    cb_url = "http://127.0.0.1:7000/callback"
else:
    cb_url = "https://cg.esolangs.gay/callback"
discord = flask_discord.DiscordOAuth2Session(app, 435756251205468160, config.client_secret, cb_url, config.bot_token)


def datetime_converter(value):
    return datetime.datetime.fromisoformat(value.decode())
sqlite3.register_converter("timestamp", datetime_converter)
def get_db():
    try:
        return flask.g._db
    except AttributeError:
        db = sqlite3.connect("the.db", detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
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
    cur = get_db().execute("SELECT MAX(num) FROM Rounds WHERE stage <> 3")
    if r := cur.fetchone()[0]:
        return flask.redirect(flask.url_for("show_round", num=r))
    else:
        return flask.redirect(flask.url_for("index"))

@app.route("/index/")
def index():
    return "<ul>" + "".join(f"<li><a href='/{n}/'>round {n}</a></li>" for n, in get_db().execute("SELECT num FROM Rounds ORDER BY num")) + "</ul>"

@app.route("/<int:num>/<name>")
def download_file(num, name):
    user_id = discord.fetch_user().id if discord.authorized else None
    f = get_db().execute("SELECT Files.content FROM Files INNER JOIN Rounds ON Rounds.num = Files.round_num "
                         "WHERE Files.round_num = ? AND Files.name = ? AND (Rounds.stage <> 1 OR Files.author_id = ?)", (num, name, user_id)).fetchone()
    if not f:
        flask.abort(404)
    return flask.send_file(io.BytesIO(f[0]), as_attachment=True, download_name=name)

@app.route("/files/<name>")
def download_file_available_for_public_access(name):
    return flask.send_from_directory("./files/", name)

def format_time(dt):
    uid = uuid.uuid4()
    return f'<span id="{uid}">{dt}</span><script>document.getElementById("{uid}").innerHTML = new Date("{dt}").toLocaleString()</script>'

def render_submissions(db, num, show_info):
    formatter = HtmlFormatter(style="monokai", linenos=True)
    entries = ""
    for author, _, submitted_at, position in db.execute("SELECT * FROM Submissions WHERE round_num = ? ORDER BY position", (num,)):
        entries += f'<h2 id="{position}">entry #{position}</h2>'
        if show_info:
            name, = db.execute("SELECT name FROM People WHERE id = ?", (author,)).fetchone()
            entries += f"<p>written by {name}<br>"
            target = db.execute("SELECT People.name FROM Targets INNER JOIN People ON People.id = Targets.target WHERE Targets.round_num = ? AND Targets.player_id = ?", (num, author)).fetchone()
            if submitted_at:
                entries += f"submitted at {format_time(submitted_at)}<br>"
            if target:
                target ,= target
                entries += f"impersonating {target}<br>"
            likes, = db.execute("SELECT COUNT(*) FROM Likes WHERE round_num = ? AND liked = ?", (num, author)).fetchone()
            if num >= 13:
                entries += "1 like</p>" if likes == 1 else f"{likes} likes</p>"
            entries += "<details><summary><strong>guesses</strong></summary><ul>"
            for guesser, guess in db.execute("SELECT People1.name, People2.name FROM Guesses "
                                             "INNER JOIN People AS People1 ON People1.id = Guesses.player_id "
                                             "INNER JOIN People AS People2 ON People2.id = Guesses.guess "
                                             "WHERE Guesses.round_num = ? AND Guesses.actual = ? ORDER BY People2.name", (num, author)):
                if guess == name:
                    o = "<strong>"
                    e = "</strong>"
                elif guess == target:
                    o = "<em>"
                    e = "</em>"
                else:
                    o = ""
                    e = ""
                entries += f"<li>{o}{guess}{e} (by {guesser})</li>"
            entries += "</ul></details><br>"
        for name, content, lang in db.execute("SELECT name, content, lang FROM Files WHERE author_id = ? AND round_num = ?", (author, num)):
            if lang is None:
                entries += f'<p><a href="/{num}/{name}">{name}</a></p>'
            else:
                entries += f'<details><summary><a href="/{num}/{name}">{name}</a></summary>'
                if lang.startswith("iframe"):
                    url = "/files/" + lang.removeprefix("iframe ")
                    entries += f'<iframe src="{url}" width="1280" height="720"></iframe>'
                elif lang == "png":
                    entries += f'<img src="/{num}/{name}">'
                else:
                    entries += highlight(content, get_lexer_by_name(lang), formatter)
                entries += "</details>"
    return entries, formatter.get_style_defs(".code")

LANGUAGES = ["py", "rs", "bf", "hs", "png", "text"]

@app.route("/<int:num>/")
def show_round(num):
    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,)).fetchone()
    if not rnd:
        flask.abort(404)
    match rnd["stage"]:
        case 1:
            if discord.authorized:
                panel = """
<form method="post" enctype="multipart/form-data">
  <input type="hidden" name="type" value="upload">
  <label for="files">upload one or more files</label>
  <input type="file" id="files" name="files" multiple><br>
  <input type="submit" value="submit">
</form>
"""
                user = discord.fetch_user()
                langs = db.execute("SELECT name, lang FROM Files WHERE round_num = ? AND author_id = ?", (num, user.id)).fetchall()
                if langs:
                    panel += '<h2>review</h2><form method="post"><input type="hidden" name="type" value="langs">'
                    for name, lang in langs:
                        panel += f'<label for="{name}"><a href="/{num}/{name}">{name}</a></label> <select name="{name}" id="{name}">'
                        for language in LANGUAGES:
                            selected = " selected"*(language == lang)
                            panel += f'<option value="{language}"{selected}>{language}</option>'
                        panel += "</select><br>"
                    panel += '<input type="submit" value="change languages"></form>'
            else:
                panel = '<form method="get" action="/login"><input type="submit" value="Login with Discord"></form>'
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>cg #{num}/1</title>
  </head>
  <body>
    <h1>code guessing, round #{num}, stage 1 (writing)</h1>
    <p>started at {format_time(rnd['started_at'])}. submit by {format_time(rnd['started_at'])+datetime.timedelta(days=7)}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
    <h2>submit</h2>
    <p>{'<br>'.join(flask.get_flashed_messages())}</p>
    {panel}
  </body>
</html>
"""
        case 2:
            entries, style = render_submissions(db, num, False)
            players = "<ul>"
            for name, in db.execute("SELECT People.name FROM Submissions INNER JOIN People ON People.id = Submissions.author_id WHERE round_num = ? ORDER BY People.name", (num,)):
                players += f"<li>{name}</li>"
            players += "</ul>"
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>cg #{num}/2</title>
    <style>{style}</style>
  </head>
  <body>
    <h1>code guessing, round #{num}, stage 2 (guessing)</h1>
    <p>started at {format_time(rnd['started_at'])}; stage 2 since {format_time(rnd['stage2_at'])}. guess by {format_time(rnd['stage2_at']+datetime.timedelta(days=7))}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
    <h2>players</h2>
    {players}
    {entries}
  </body>
</html>
"""
        case 3:
            entries, style = render_submissions(db, num, True)
            counts = []
            for author, in db.execute("SELECT author_id FROM Submissions WHERE round_num = ?", (num,)):
                plus, = db.execute("SELECT COUNT(*) FROM Guesses WHERE round_num = ? AND player_id = ? AND guess = actual", (num, author)).fetchone()
                bonus, = db.execute("SELECT COUNT(*) FROM Guesses "
                                    "INNER JOIN Targets ON Targets.round_num = Guesses.round_num AND Targets.player_id = Guesses.actual "
                                    "WHERE Guesses.round_num = ? AND Guesses.actual = ? AND Guesses.guess = Targets.target", (num, author)).fetchone()
                minus, = db.execute("SELECT COUNT(*) FROM Guesses WHERE round_num = ? AND actual = ? AND guess = actual", (num, author)).fetchone()
                counts.append((author, plus, bonus, minus))
            def key(t):
                _, plus, bonus, minus = t
                return plus+bonus-minus, plus, bonus
            counts.sort(key=key, reverse=True)
            current = None
            last = None
            results = "<ol>"
            for idx, t in enumerate(counts, start=1):
                author, plus, bonus, minus = t
                if last is None or key(t) < last:
                    current = idx
                    last = key(t)
                name, = db.execute("SELECT name FROM People WHERE id = ?", (author,)).fetchone()
                bonus_s = f" ~{bonus}"*(num >= 12)
                results += f'<li value="{current}"><details><summary><strong>{name}</strong> +{plus}{bonus_s} -{minus} = {plus+bonus-minus}</summary><ol>'
                for guess, actual in db.execute("SELECT People1.name, People2.name FROM Guesses "
                                                "INNER JOIN People AS People1 ON People1.id = Guesses.guess "
                                                "INNER JOIN People AS People2 ON People2.id = Guesses.actual "
                                                "INNER JOIN Submissions ON Submissions.round_num = Guesses.round_num AND Submissions.author_id = Guesses.actual "
                                                "WHERE Guesses.round_num = ? AND Guesses.player_id = ? ORDER BY Submissions.position", (num, author)):
                    if guess == actual:
                        results += f"<li><strong>{actual}</strong></li>"
                    else:
                        results += f"<li>{guess} (was {actual})</li>"
                results += "</ol></details></li>"
            results += "</ol>"
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>cg #{num}</title>
    <style>{style}</style>
  </head>
  <body>
    <h1>code guessing, round #{num} (completed)</h1>
    <p>started at {format_time(rnd['started_at'])}; stage 2 at {format_time(rnd['stage2_at'])}; ended at {format_time(rnd['ended_at'])}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
    <h2>results</h2>
    {results}
    {entries}
  </body>
</html>
"""

@app.route("/<int:num>/", methods=["POST"])
@auth
def take(num):
    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,)).fetchone()
    if not rnd:
        flask.abort(404)
    user = discord.fetch_user()
    if "user" not in discord.bot_request(f"/guilds/346530916832903169/members/{user.id}"):
        flask.abort(403)
    db.execute("INSERT OR REPLACE INTO People VALUES (?, ?)", (user.id, user.username))
    try:
        match (flask.request.form["type"], rnd["stage"]):
            case ("upload", 1):
                files = [x for x in flask.request.files.getlist("files") if x]
                if not files:
                    return flask.flash("submit at least one file")
                db.execute("INSERT OR REPLACE INTO Submissions VALUES (?, ?, ?, NULL)", (user.id, num, datetime.datetime.now(datetime.timezone.utc)))
                db.execute("DELETE FROM Files WHERE round_num = ? AND author_id = ?", (num, user.id))
                for file in files:
                    try:
                        guess = min(get_lexer_for_filename(file.filename).aliases, key=len)
                    except ClassNotFound:
                        guess = "png" if file.filename.endswith(".png") else "text"
                    db.execute("INSERT INTO Files VALUES (?, ?, ?, ?, ?)", (file.filename, user.id, num, file.read(), guess))
            case ("langs", 1):
                for key, value in flask.request.form.items():
                    if key != "type":
                        db.execute("UPDATE Files SET lang = ? WHERE round_num = ? AND name = ?", (value, num, key))
            case 2:
                pass
            case _:
                flask.abort(400)
    except Exception as e:
        traceback.print_exception(e)
    else:
        flask.flash("submitted successfully")
        db.commit()
    finally:
        return flask.redirect(flask.url_for("show_round", num=num))

@app.route("/callback")
def callback():
    discord.callback()
    return flask.redirect(flask.url_for("root"))

@app.route("/login")
def login():
    return discord.create_session(["identify"])

@app.errorhandler(404)
def not_found(e):
    return 'page not found :(<br><a href="/">go home</a>'
