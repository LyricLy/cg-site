import functools
import traceback
import sqlite3
import datetime
import io
import re
import os
import uuid

import bleach
import charset_normalizer
import magic
import mistune
import flask
import flask_minify
import flask_discord
from flask_discord import requires_authorization as auth
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

import config


app = flask.Flask(__name__)
flask_minify.Minify(app=app)
app.secret_key = config.secret_key
app.config |= {
    "SESSION_COOKIE_HTTPONLY": False,
    "SESSION_COOKIE_SECURE": True,
    "MAX_CONTENT_LENGTH": 32 * 1024 * 1024,
}
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
    cur = get_db().execute("SELECT MIN(num) FROM Rounds WHERE stage <> 3")
    if r := cur.fetchone()[0]:
        return flask.redirect(flask.url_for("show_round", num=r))
    else:
        return flask.redirect(flask.url_for("index"))

@app.route("/index/")
def index():
    rounds = "<ul>" + "".join(f"<li><a href='/{n}/'>round {n}</a></li>" for n, in get_db().execute("SELECT num FROM Rounds ORDER BY num")) + "</ul>"
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="code guessing" property="og:title">
    <meta content="code and guess and such." property="og:description">
    <meta content="https://cg.esolangs.gay/index/" property="og:url">
    <title>cg index</title>
  </head>
  <body>
    <p><a href="/stats/">stats</a> &bull; <a href="/info">info</a> &bull; <a href="/credits">credits</a></p>
    {rounds}
  </body>
</html>
"""

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

@app.route("/main.js")
def js():
    return flask.send_file("./main.js")

@app.route("/main.css")
def css():
    return flask.send_file("./main.css")

@app.route("/favicon.png")
def favicon():
    return flask.send_file("./favicon.png")

@app.route("/credits")
def credits():
    return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>cg - credits</title>
    {META}
    <meta content="code guessing credits" property="og:title">
    <meta content="all the people that made this happen." property="og:description">
    <meta content="https://cg.esolangs.gay/credits" property="og:url">
  </head>
  <body>
    <h1>credits and acknowledgements</h1>
    <ul>
      <li>umnikos - inital concept</li>
      <li>ubq323 - creating the original ruleset and hosting the first 5 rounds</li>
      <li>HelloBoi - helping host round 4</li>
      <li>deadbraincoral - helping host round 4</li>
      <li>sonata «pathétique» - helping host the first 5 rounds</li>
      <li>LyricLy - rule amendments, bot development, site development, and hosting round 6 and onwards</li>
      <li>RocketRace - site ideas</li>
      <li>Palaiologos - providing additional direction</li>
      <li>IFcoltransG - writing the info page</li>
      <li>the players - designing the rounds and writing the submissions</li>
    </ul>
  </body>
</html>
"""

@app.route("/info")
def info():
    with open("info.md") as f:
        m = mistune.html(f.read())
    return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>cg - info</title>
    {META}
    <meta content="code guessing info" property="og:title">
    <meta content="what is code guessing?" property="og:description">
    <meta content="https://cg.esolangs.gay/info" property="og:url">
  </head>
  <body>
    {m}
  </body>
</html>
"""

def format_time(dt):
    return f'<strong><span class="datetime">{dt.isoformat()}</span></strong>'

def render_submission(db, formatter, row, show_info, written_by=True):
    author, num, submitted_at, position = row
    entries = ""
    if show_info:
        name, = db.execute("SELECT name FROM People WHERE id = ?", (author,)).fetchone()
        if written_by:
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
                guess = f"<strong>{guess}</strong>"
            elif guess == target:
                guess = f"<em>{guess}</em>"
            entries += f"<li>{guess} (by {guesser})</li>"
        entries += "</ul></details><br>"
    elif discord.authorized:
        checked = " checked"*bool(db.execute("SELECT NULL FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, discord.fetch_user().id, author)).fetchone())
        entries += f'<p><label>like? <input type="checkbox" class="like" like-pos="{position}"{checked}></label></p>'
    for name, content, lang in db.execute("SELECT name, content, lang FROM Files WHERE author_id = ? AND round_num = ?", (author, num)):
        name = bleach.clean(name)
        filetype = magic.from_buffer(content)
        # remove appalling attempts at guessing language
        filetype = re.sub(r"^.+? (?:source|script), |(?<=text) executable", "", filetype)
        header = f'<a href="/{num}/{name}">{name}</a> <sub><em>{filetype}</em></sub>'
        if lang is None:
            entries += f'<p>{header}</p>'
        else:
            entries += f'<details><summary>{header}</summary>'
            if lang.startswith("iframe"):
                url = "/files/" + lang.removeprefix("iframe ")
                entries += f'<iframe src="{url}" width="1280" height="720"></iframe>'
            elif lang == "png":
                entries += f'<img src="/{num}/{name}">'
            else:
                entries += highlight(str(charset_normalizer.from_bytes(content).best()), get_lexer_by_name(lang), formatter)
            entries += "</details>"
    return entries

def render_submissions(db, num, show_info):
    formatter = HtmlFormatter(style="monokai", linenos=True)
    entries = ""
    for r in db.execute("SELECT * FROM Submissions WHERE round_num = ? ORDER BY position", (num,)):
        position = r["position"]
        entries += f'<h2 id="{position}">entry #{position}</h2>'
        entries += render_submission(db, formatter, r, show_info)
    return entries, formatter.get_style_defs(".code") + ".code { tab-size: 4; }"

def rank_enumerate(xs, *, key):
    cur_idx = None
    cur_key = None
    for idx, x in enumerate(sorted(xs, key=key, reverse=True), start=1):
        if cur_key is None or key(x) < cur_key:
            cur_idx = idx
            cur_key = key(x)
        yield (cur_idx, x)

LANGUAGES = ["py", "rs", "bf", "hs", "c", "go", "zig", "d", "pony", "js", "apl", "sml", "vim", "befunge", "png", "text"]
META = """
<link rel="icon" type="image/png" href="/favicon.png">
<meta charset="utf-8">
<meta content="website" property="og:type">
<meta content="https://cg.esolangs.gay/favicon.png" property="og:image">
<meta content="Esolangs" property="og:site_name">
<script src="/main.js" defer></script>
<link rel="stylesheet" href="/main.css">
"""
LOGIN_BUTTON = '<form method="get" action="/login"><input type="submit" value="log in with discord"></form>'

@app.route("/<int:num>/")
def show_round(num):
    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,)).fetchone()
    if not rnd:
        flask.abort(404)

    top_elems = []
    if num > 1:
        top_elems.append(f'<a href="/{num-1}/">prev</a>')
    top_elems.append('<a href="/index">index</a>')
    if db.execute("SELECT * FROM Rounds WHERE num = ?", (num+1,)).fetchone():
        top_elems.append(f'<a href="/{num+1}">next</a>')
    top = " &bull; ".join(top_elems)

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
                panel = LOGIN_BUTTON
            submit_by = rnd['stage2_at'] or rnd['started_at']+datetime.timedelta(days=7)
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>cg #{num}/1</title>
    {META}
    <meta content="code guessing #{num}/1" property="og:title">
    <meta content="{rnd['spec'].splitlines()[0].replace('*', '')} submit by {submit_by.strftime('%B %d (%A)')}." property="og:description">
    <meta content="https://cg.esolangs.gay/{num}/" property="og:url">
  </head>
  <body>
    {top}
    <h1>code guessing, round #{num}, stage 1 (writing)</h1>
    <p>started at {format_time(rnd['started_at'])}. submit by {format_time(submit_by)}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
    <h2>submit</h2>
    <p>{dict(enumerate(flask.get_flashed_messages())).get(0, "")}</p>
    {panel}
  </body>
</html>
"""
        case 2:
            entries, style = render_submissions(db, num, False)
            your_id = discord.fetch_user().id if discord.authorized else None
            query = db.execute("SELECT People.id, People.name, Submissions.position FROM Submissions "
                               "INNER JOIN People ON People.id = Submissions.author_id "
                               "LEFT JOIN (Guesses INNER JOIN Submissions as Submissions2 ON Submissions2.round_num = Guesses.round_num AND Guesses.actual = Submissions2.author_id) "
                               "ON Guesses.round_num = Submissions.round_num AND Guesses.player_id = ? AND Guesses.guess = People.id "
                               "WHERE Submissions.round_num = ? ORDER BY Submissions2.position, People.name COLLATE NOCASE", (your_id, num)).fetchall()
            if discord.authorized and any(id == your_id for id, _, _ in query):
                panel = '<div id="guess-panel"><button onclick="toggleSticky()" id="sticky-button">Hide</button><h2>guess</h2><ol id="players">'
                for idx, (id, name, pos) in enumerate(query):
                    if id == your_id:
                        query.pop(idx)
                        query.insert(pos-1, (id, name, pos))
                        break
                for id, name, _ in query:
                    if id == your_id:
                        panel += f'<li data-id="{id}" class="player you">{name} (you!)</li>'
                    else:
                        panel += f'<li data-id="{id}" class="player">↕ {name}</li>'
                panel += "</ol></div>"
            else:
                panel = '<h2>players</h2><ol>'
                for _, name, _ in query:
                    panel += f'<li>{name}</li>'
                panel += "</ol>"
                if not discord.authorized:
                    panel += LOGIN_BUTTON
                else:
                    panel += "<p>you weren't a part of this round. come back next time?</p>"
            guess_by = rnd['ended_at'] or rnd['stage2_at']+datetime.timedelta(days=4)
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>cg #{num}/2</title>
    {META}
    <meta content="code guessing #{num}/2" property="og:title">
    <meta content="{len(query)} submissions received. guess by {guess_by.strftime('%B %d (%A)')}." property="og:description">
    <meta content="https://cg.esolangs.gay/{num}/" property="og:url">
    <style>{style}</style>
    <script src="https://cdn.jsdelivr.net/gh/SortableJS/Sortable@master/Sortable.min.js"></script>
  </head>
  <body>
    {top}
    <h1>code guessing, round #{num}, stage 2 (guessing)</h1>
    <p>started at {format_time(rnd['started_at'])}; stage 2 since {format_time(rnd['stage2_at'])}. guess by {format_time(guess_by)}</p>
    <h2>specification</h2>
    {mistune.html(rnd['spec'])}
    {panel}
    {entries}
  </body>
</html>
"""
        case 3:
            entries, style = render_submissions(db, num, True)
            lb = db.execute("""
            SELECT name, author_id,
                   (SELECT COUNT(*) FROM Guesses WHERE player_id = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num),
                   (SELECT COUNT(*) FROM Guesses
                    INNER JOIN Targets ON Targets.round_num = Guesses.round_num AND Targets.player_id = actual
                    WHERE actual = author_id AND guess = Targets.target AND Guesses.round_num = Submissions.round_num),
                   (SELECT COUNT(*) FROM Guesses WHERE guess = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num)
            FROM Submissions INNER JOIN People ON id = author_id WHERE round_num = ?""", (num,))
            results = "<ol>"
            for idx, t in rank_enumerate(lb, key=lambda t: (t[2]+t[3]-t[4], t[2], t[3])):
                name, author, plus, bonus, minus = t
                bonus_s = f" ~{bonus}"*(num in (12, 13))
                results += f'<li value="{idx}"><details><summary><strong>{name}</strong> +{plus}{bonus_s} -{minus} = {plus+bonus-minus}</summary><ol>'
                for guess, actual, pos in db.execute("SELECT People1.name, People2.name, Submissions.position FROM Guesses "
                                                "INNER JOIN People AS People1 ON People1.id = Guesses.guess "
                                                "INNER JOIN People AS People2 ON People2.id = Guesses.actual "
                                                "INNER JOIN Submissions ON Submissions.round_num = Guesses.round_num AND Submissions.author_id = Guesses.actual "
                                                "WHERE Guesses.round_num = ? AND Guesses.player_id = ? ORDER BY Submissions.position", (num, author)):
                    if guess == actual:
                        results += f'<li value="{pos}"><strong>{actual}</strong></li>'
                    else:
                        results += f'<li value="{pos}">{guess} (was {actual})</li>'
                results += "</ol></details></li>"
            results += "</ol>"
            return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="code guessing #{num}" property="og:title">
    <meta content="round concluded." property="og:description">
    <meta content="https://cg.esolangs.gay/{num}/" property="og:url">
    <title>cg #{num}</title>
    <style>{style}</style>
  </head>
  <body>
    {top}
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
    form = flask.request.form
    if "user" not in discord.bot_request(f"/guilds/346530916832903169/members/{user.id}"):
        flask.abort(403)
    if user.id != 356107472269869058:
        db.execute("INSERT OR REPLACE INTO People VALUES (?, ?)", (user.id, user.username))
    try:
        match (form["type"], rnd["stage"]):
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
                    b = file.read()
                    if len(b) > 64*1024:
                        guess = None
                    db.execute("INSERT INTO Files VALUES (?, ?, ?, ?, ?)", (file.filename, user.id, num, b, guess))
            case ("langs", 1):
                for key, value in form.items():
                    if key == "type":
                        continue
                    if value not in LANGUAGES:
                        flask.abort(400)
                    db.execute("UPDATE Files SET lang = ? WHERE round_num = ? AND name = ?", (value, num, key))
            case ("guess", 2):
                db.execute("DELETE FROM Guesses WHERE round_num = ? AND player_id = ?", (num, user.id))
                for position, guess in enumerate(form.getlist("guess"), start=1):
                    if int(guess) != user.id:
                        db.execute("INSERT INTO Guesses SELECT ?, ?, ?, author_id FROM Submissions WHERE round_num = ? AND position = ?", (num, user.id, int(guess), num, position))
            case ("like", 2):
                id, = db.execute("SELECT author_id FROM Submissions WHERE round_num = ? AND position = ?", (num, int(form["position"]))).fetchone()
                if form["checked"] == "true":
                    db.execute("INSERT OR IGNORE INTO Likes VALUES (?, ?, ?)", (num, user.id, id))
                else:
                    db.execute("DELETE FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, user.id, id))
            case _:
                flask.abort(400)
    except Exception as e:
        traceback.print_exception(e)
    else:
        flask.flash("submitted successfully")
        db.commit()
    finally:
        db.rollback()
        return flask.redirect(flask.url_for("show_round", num=num))

@app.route("/stats/")
def stats():
    db = get_db()
    lb = db.execute("""
    WITH Finished AS (SELECT num FROM Rounds WHERE stage = 3)
    SELECT name, (SELECT COUNT(*) FROM Guesses WHERE player_id = id AND guess = actual AND round_num IN Finished),
                 (SELECT COUNT(*) FROM Guesses INNER JOIN Targets ON Targets.round_num = Guesses.round_num AND Targets.player_id = actual WHERE actual = id AND guess = Targets.target AND Guesses.round_num IN Finished),
                 (SELECT COUNT(*) FROM Guesses WHERE guess = id AND guess = actual AND round_num IN Finished),
                 (SELECT COUNT(*) FROM Submissions WHERE author_id = id AND round_num IN Finished)
    FROM People""")
    rows = ["rank", "player", "gain", "loss", "bonus", "total", "~total", "played", "avg score", "avg gain", "avg loss"]
    table = "<thead><tr>"
    for row in rows:
        table += f'<th scope="col">{row}</th>'
    table += "</tr></thead>"
    e = list(rank_enumerate(lb, key=lambda t: t[1]+t[2]-t[3]))
    for rank, (name, plus, bonus, minus, played) in e:
        if not played:
            continue
        values = [
            rank,
            f'<a href="/stats/{name}">{name}</a>',
            plus,
            minus,
            bonus,
            plus+bonus-minus,
            plus-minus,
            played,
            f"{(plus+bonus-minus)/played:.3f}",
            f"{plus/played:.3f}",
            f"{minus/played:.3f}",
        ]
        table += "<tr>"
        for value in values:
            table += f"<td>{value}</td>"
        table += "</tr>"
    match [tuple(x[1]) for x in e if x[0] == 1]:
        case [(name, score, _, _, _)]:
            desc = f"{name} leads with {score} points."
        case [(_, score, _, _, _), *xs]:
            desc = f"{len(xs)+1} people lead with {score} points."
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="code guessing stats" property="og:title">
    <meta content="{desc}" property="og:description">
    <meta content="https://cg.esolangs.gay/stats/" property="og:url">
    <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@master/sortable.min.js"></script>
    <title>cg stats</title>
    <style>th, td {{ border: 1px solid; padding: 4px; }} table {{ border-collapse: collapse; }}</style>
  </head>
  <body>
    <h1>code guessing stats</h1>
    <p>welcome. more coming soon!</p>
    <h2>leaderboard</h2>
    <table class="sortable">{table}</table>
  </body>
</html>
"""

@app.route("/stats/<player>")
def user_stats(player):
    db = get_db()
    s = ""
    sc = 0
    formatter = HtmlFormatter(style="monokai", linenos=True)
    for r in db.execute("SELECT Submissions.* FROM Submissions INNER JOIN Rounds ON num = round_num INNER JOIN People ON name = ? WHERE stage = 3 AND author_id = id ORDER BY round_num", (player,)):
        position = r["position"]
        num = r["round_num"]
        s += f'<h2 id="{num}"><a href="/{num}/#{position}">round #{num}</a></h2>'
        s += render_submission(db, formatter, r, True, written_by=False)
        sc += 1
    if not sc:
        flask.abort(404)
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="{player}'s code guessing stats" property="og:title">
    <meta content="see their {sc} awesome entries" property="og:description">
    <meta content="https://cg.esolangs.gay/stats/{player}" property="og:url">
    <title>cg - {player}</title>
    <style>{formatter.get_style_defs(".code")}</style>
  </head>
  <body>
    <h1>{player}'s stats</h1>
    <h2>entries</h2>
    {s}
  </body>
</html>
"""

@app.route("/callback")
def callback():
    discord.callback()
    return flask.redirect(flask.url_for("root"))

@app.route("/login")
def login():
    return discord.create_session(["identify"])

@app.errorhandler(404)
def not_found(e):
    return 'page not found :(<br><a href="/">go home</a>', 404
