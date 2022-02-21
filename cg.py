import functools
import sqlite3
import datetime
import io

import mistune
import flask
import flask_discord
from flask_discord import requires_authorization as auth
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

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
    f = get_db().execute("SELECT content FROM Files WHERE round_num = ? AND name = ?", (num, name)).fetchone()
    if not f:
        flask.abort(404)
    return flask.send_file(io.BytesIO(f[0]), as_attachment=True, download_name=name)

@app.route("/files/<name>")
def download_file_available_for_public_access(name):
    return flask.send_from_directory("./files/", name)

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
                entries += f"submitted at {submitted_at}<br>"
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
                else:
                    entries += highlight(content, get_lexer_by_name(lang), formatter)
                entries += "</details>"
    return entries, formatter.get_style_defs(".code")

@app.route("/<int:num>/")
def show_round(num):
    db = get_db()
    cur = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,))
    if not (rnd := cur.fetchone()):
        flask.abort(404)
    match rnd["stage"]:
        case 1:
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>cg #{num}/1</title>
  </head>
  <body>
    <h1>code guessing, round #{num}, stage 1 (writing)</h1>
    <p>started at {rnd['started_at']}. submit by {rnd['started_at']+datetime.timedelta(days=7)}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
  </body>
</html>
"""
        case 2:
            entries, style = render_submissions(db, num, False)
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
    <p>started at {rnd['started_at']}; stage 2 since {rnd['stage2_at']}. guess by {rnd['stage2_at']+datetime.timedelta(days=7)}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
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
    <p>started at {rnd['started_at']}; stage 2 at {rnd['stage2_at']}; ended at {rnd['ended_at']}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
    <h2>results</h2>
    {results}
    {entries}
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
