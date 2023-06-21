import ctypes
import functools
import traceback
import sqlite3
import datetime
import io
import re
import subprocess
import tarfile
import os
import json
import logging
from collections import defaultdict

import bleach
import charset_normalizer
import magic
import mistune
import requests
import flask
import flask_discord
import yarl
from flask_discord import requires_authorization as auth
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

import config


logging.basicConfig(filename=config.log_file, encoding="utf-8", format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", level=logging.INFO)
app = flask.Flask(__name__, static_url_path="")
app.secret_key = config.secret_key
app.config |= {
    "SESSION_COOKIE_HTTPONLY": False,
    "SESSION_COOKIE_SECURE": True,
    "MAX_CONTENT_LENGTH": 4 * 1024 * 1024,
}
discord = flask_discord.DiscordOAuth2Session(app, 435756251205468160, config.client_secret, config.cb_url)
markdown = mistune.create_markdown(plugins=["strikethrough", "table", "footnotes"])
formatter = HtmlFormatter(style="monokai", linenos=True)


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
    nums = get_db().execute("SELECT num, ended_at, spec FROM Rounds ORDER BY num DESC").fetchall()
    last, at, _ = nums[0]
    rounds = "".join(f"<li><a href='/{n}/'>round #{n}</a> ({spec.split('**', 2)[1]})</li>" for n, _, spec in nums)
    rounds = "<ul>" + (f"<li>round {last+1} at {format_time(at+datetime.timedelta(days=3))}</li>" if at else "") + rounds + "</ul>"
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
    <p><a href="/stats/">stats</a> &bull; <a href="/info">info</a> &bull; <a href="/credits">credits</a> &bull; <a href="/anon">anon settings</a></p>
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
    return flask.send_file(io.BytesIO(f[0]), mimetype="application/octet-stream")

@app.route("/files/<name>")
def download_file_available_for_public_access(name):
    return flask.send_from_directory("./files/", name)

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
    <a href="/index">index</a>
    <h1>credits and acknowledgements</h1>
    <ul>
      <li>umnikos - inital concept</li>
      <li>ubq323 - creating the original ruleset and hosting the first 5 rounds</li>
      <li>HelloBoi, deadbraincoral - helping host round 4</li>
      <li>sonata «pathétique» - helping host the first 5 rounds</li>
      <li>LyricLy - rule amendments, bot development, site development, and hosting round 6 and onwards</li>
      <li>RocketRace, olus2000, Palaiologos - ideas and advice</li>
      <li>IFcoltransG - writing the info page</li>
      <li>the players - designing the rounds and writing the submissions</li>
    </ul>
  </body>
</html>
"""

@app.route("/info")
def info():
    with open("info.md") as f:
        m = markdown(f.read())
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
    <a href="/index">index</a>
    {m}
  </body>
</html>
"""

def make_tar(num, compression=""):
    user_id = discord.fetch_user().id if discord.authorized else None
    f = io.BytesIO()
    with tarfile.open(mode=f"w:{compression}", fileobj=f) as tar:
        for name, content, position in get_db().execute("SELECT name, content, position FROM Files "
                                                        "INNER JOIN Submissions ON Submissions.round_num = Files.round_num AND Submissions.author_id = Files.author_id "
                                                        "INNER JOIN Rounds ON Rounds.num = Files.round_num "
                                                        "WHERE Files.round_num = ? AND (stage <> 1 OR Files.author_id = ?)", (num, user_id)):
            info = tarfile.TarInfo(f"{num}/{position}/{name}")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    f.seek(0)
    return f

@app.route("/<int:num>.tar.bz2")
def download_round_bzip2(num):
    return flask.send_file(make_tar(num, "bz2"), as_attachment=True, download_name=f"{num}.tar.bz2")

@app.route("/<int:num>.tar.bz3")
def download_round_bzip3(num):
    proc = subprocess.run(["bzip3", "-e"], input=make_tar(num).getvalue(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise Exception(f"bzip3: {proc.stderr}")
    return flask.send_file(io.BytesIO(proc.stdout), as_attachment=True, download_name=f"{num}.tar.bz3")

def get_name(i):
    return bleach.clean(get_db().execute("SELECT name FROM People WHERE id = ?", (i,)).fetchone()[0])

def format_time(dt):
    return f'<strong><span class="datetime">{dt.isoformat()}</span></strong>'

def persona_name(author, persona, d={}):
    if persona == -1:
        return get_name(author) + ' <span class="verified"></span>'
    if not config.canon_url:
        return "[unknown]"
    return d.get(persona) or d.setdefault(persona, bleach.clean(requests.get(config.canon_url + f"/personas/{persona}").json()["name"]))

def fetch_personas():
    user = discord.fetch_user()
    base_persona = {"id": -1, "name": user.to_json()["global_name"]}
    if not config.canon_url:
        return [base_persona]
    if not hasattr(flask.g, "d"):
        flask.g.d = {}
    d = flask.g.d
    return d.get(user.id) or d.setdefault(user.id, [base_persona, *requests.get(config.canon_url + f"/users/{user.id}/personas").json()])

def pass_to_js(*args):
    s = ""
    for arg in args:
        s += json.dumps(arg).replace('"', '&quot;')
        s += ","
    return s

def render_comments(db, num, parent, show_info):
    rows = db.execute("SELECT * FROM Comments WHERE round_num = ? AND parent = ?", (num, parent)).fetchall()
    comments = f'<details {"open"*bool(rows)}><summary><strong>comments</strong> {len(rows)}</summary><div class="comments">'
    for row in rows:
        comments += f'<div id="c{row["id"]}" class="comment"><strong>{persona_name(row["author_id"], row["persona"])}</strong>'
        if row["og_persona"]:
            comments += f'<span class="tooltip">*<span class="tooltip-inner">known at the time as <strong>{persona_name(row["author_id"], row["og_persona"])}</strong></span></span>'
        extras = []
        if r := row["reply"]:
            replied, their_persona = db.execute("SELECT author_id, persona FROM Comments WHERE round_num = ? AND parent = ? AND id = ?", (num, parent, r)).fetchone()
            extras.append(f'<a href="#c{r}"><em>replying to <strong>{persona_name(replied, their_persona)}</strong></em></a>')
        extras.append(f'<a href="#c{row["id"]}">¶</a>')
        if discord.authorized:
            user = discord.fetch_user()
            owns = row["author_id"] == user.id
            if not owns:
                extras.append(f'<button onclick="reply({pass_to_js(str(row["id"]), str(row["parent"]))})">reply</button>')
            else:
                extras.append(f'<button onclick="edit({pass_to_js(str(row["id"]), str(row["parent"]), row["content"], row["persona"], row["reply"])})">edit</button>')
            if owns or user.id == 319753218592866315:
                extras.append(f'<form method="post" action="/{num}/" class="delete-button"><input type="hidden" name="type" value="delete-comment"><input type="hidden" name="id" value="{row["id"]}"><input type="submit" value="delete"></form>')
        comments += ' ' + ' '.join(extras)
        comments += f'{markdown(row["content"])}</div><hr>'
    comments += "<h3>post a comment</h3>"
    if not discord.authorized:
        comments += f"<p>{LOGIN_BUTTON}</p>"
    else:
        user = discord.fetch_user()
        comments += f'<form method="post" action="/{num}/" id="post-{parent}"><input type="hidden" name="type" value="comment"><input type="hidden" name="parent" value="{parent}">as <select name="persona">'
        for idx, persona in enumerate(fetch_personas()):
            comments += f'<option value="{persona["id"]}" {" selected"*(not idx)}>{persona["name"]}</option>'
        comments += '</select><span class="extra"></span><p><textarea class="comment-content" name="content" oninput="resize(this)" onkeypress="considerSubmit(event)" cols="80" autocomplete="off" maxlength="1000"></textarea> <input type="submit" value="Post"></p></form>'
    comments += "</div></details>"
    return comments


def render_files(db, num, author, lang_dropdowns=False):
    files = ""
    for name, content, hl_content, lang in db.execute("SELECT name, content, hl_content, lang FROM Files WHERE author_id = ? AND round_num = ? ORDER BY name", (author, num)):
        name = bleach.clean(name)
        if str(lang).startswith("external"):
            url = lang.removeprefix("external ")
            filetype = f"external link to {yarl.URL(url).host}"
            lang = None
        else:
            url = f"/{num}/{name}"
            filetype = magic.from_buffer(content)
            # remove appalling attempts at guessing language
            filetype = re.sub(r"^.+? (?:source|script), |(?<=text) executable", "", filetype)
        header = f'<a href="{url}">{name}</a> <small><em>{filetype}</em></small>'
        if lang_dropdowns:
            header += f' <select name="{name}" id="{name}">'
            for language in LANGUAGES:
                selected = " selected"*(LANGMAP.get(language, language) == lang)
                header += f'<option value="{language}"{selected}>{language}</option>'
            header += "</select><br>"
        if lang is None:
            files += f'{header}<br>'
        else:
            files += f'<details><summary>{header}</summary>'
            if lang.startswith("iframe"):
                url = "/files/" + lang.removeprefix("iframe ")
                files += f'<iframe src="{url}" width="1280" height="720"></iframe>'
            elif lang == "image":
                files += f'<img src="/{num}/{name}">'
            elif lang == "pdf":
                files += f'<object type="application/pdf" data="/{num}/{name}" width="1280" height="720"></object>'
            else:
                if not hl_content:
                    try:
                        text = content.decode()
                    except UnicodeDecodeError:
                        best = charset_normalizer.from_bytes(content).best()
                        text = str(best) if best else "cg: couldn't decode file contents"
                    hl_content = highlight(text, get_lexer_by_name(lang), formatter)
                    db.execute("UPDATE Files SET hl_content = ? WHERE round_num = ? AND name = ?", (hl_content, num, name))
                    db.commit()
                files += hl_content
            files += "</details>"
    return files


def render_submission(db, row, show_info, written_by=True):
    author, num, submitted_at, position = row
    entries = ""
    if show_info:
        name = get_name(author)
        if written_by:
            entries += f"<p>written by {name}<br>"
        target = db.execute("SELECT target FROM Targets WHERE round_num = ? AND player_id = ?", (num, author)).fetchone()
        if submitted_at:
            entries += f"submitted at {format_time(submitted_at)}<br>"
        if target:
            target ,= target
            entries += f"impersonating {get_name(target)}<br>"
        likes, = db.execute("SELECT COUNT(*) FROM Likes WHERE round_num = ? AND liked = ?", (num, author)).fetchone()
        if num >= 13:
            entries += "1 like</p>" if likes == 1 else f"{likes} likes</p>"
        entries += "<details><summary><strong>guesses</strong></summary><ul>"
        for guesser, guess in sorted(db.execute("SELECT player_id, guess FROM Guesses WHERE round_num = ? AND actual = ?", (num, author)), key=lambda x: get_name(x[1])):
            if guess == author:
                guess = f"<strong>{get_name(guess)}</strong>"
            elif guess == target:
                guess = f"<em>{get_name(guess)}</em>"
            else:
                guess = get_name(guess)
            entries += f"<li>{guess} (by {get_name(guesser)})</li>"
        entries += "</ul></details>"
    elif discord.authorized:
        checked = " toggleValue"*bool(db.execute("SELECT NULL FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, discord.fetch_user().id, author)).fetchone())
        entries += f'<p><button class="toggle" alt="unlike" ontoggle="onLike({position})"{checked}>like</button></p>'
    entries += render_comments(db, num, author, show_info)
    entries += "<br>"
    entries += render_files(db, num, author)
    return entries

def render_submissions(db, num, show_info):
    entries = f'<h2>entries</h2><p>you can <a id="download" href="/{num}.tar.bz2">download</a> all the entries</p>'
    for r in db.execute("SELECT author_id, round_num, submitted_at, position FROM Submissions WHERE round_num = ? ORDER BY position", (num,)):
        position = r["position"]
        entries += f'<h3 id="{position}">entry #{position}</h3>'
        entries += render_submission(db, r, show_info)
    return entries, formatter.get_style_defs(".code") + ".code { tab-size: 4; }"

def rank_enumerate(xs, *, key):
    cur_idx = None
    cur_key = None
    for idx, x in enumerate(sorted(xs, key=key, reverse=True), start=1):
        if cur_key is None or key(x) < cur_key:
            cur_idx = idx
            cur_key = key(x)
        yield (cur_idx, x)

LANGUAGES = ["py", "rs", "b", "hs", "c", "cpp", "go", "zig", "d", "raku", "pony", "js", "ts", "apl", "sml", "ml", "fs", "vim", "sh", "bf", "lua", "erl", "sed", "ada", "none", "img", "txt"]
LANGMAP = {
    "bf": "befunge",
    "b": "bf",
    "fs": "f#",
    "erl": "erlang",
    "ml": "ocaml",
    "img": "image",
    "txt": "text",
    "none": None,
}
META = """
<link rel="icon" type="image/png" href="/favicon.png">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta content="website" property="og:type">
<meta content="https://cg.esolangs.gay/favicon.png" property="og:image">
<meta content="Esolangs" property="og:site_name">
<script src="/main.js" defer></script>
<script src="https://unpkg.com/konami@1.6.3/konami.js"></script>
<link rel="stylesheet" href="/main.css">
"""
LOGIN_BUTTON = '<form method="get" action="/login"><input type="submit" value="log in with discord"></form>'

def score_round(num):
    lb = get_db().execute("""
    SELECT author_id,
           (SELECT COUNT(*) FROM Guesses WHERE player_id = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num),
           (SELECT COUNT(*) FROM Guesses
            INNER JOIN Targets ON Targets.round_num = Guesses.round_num AND Targets.player_id = actual
            WHERE actual = author_id AND guess = Targets.target AND Guesses.round_num = Submissions.round_num),
           (SELECT COUNT(*) FROM Guesses WHERE guess = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num)
    FROM Submissions WHERE round_num = ?""", (num,))
    e = rank_enumerate(((author, plus+bonus-minus, plus, bonus, minus) for author, plus, bonus, minus in lb), key=lambda t: t[1:4])
    if t := TIEBREAKS.get(num):
        l = [(t.get(d[0], r), d) for r, d in e]
        l.sort(key=lambda t: t[0])
        return l
    return e

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
    top_elems.append('<a href="/info">info</a>')
    if db.execute("SELECT * FROM Rounds WHERE num = ?", (num+1,)).fetchone():
        top_elems.append(f'<a href="/{num+1}">next</a>')
    top = " &bull; ".join(top_elems)

    match rnd["stage"]:
        case 1:
            formatter = HtmlFormatter(style="monokai", linenos=True)
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
                files = render_files(db, num, user.id, lang_dropdowns=True)
                if files:
                    panel += f"""
<h2>review</h2>
<p><a id="download" href="/{num}.tar.bz2">download all</a></p>
<form method="post">
  <input type="hidden" name="type" value="langs">
  {files}
  <input type="submit" value="change languages">
</form>
"""
            else:
                panel = LOGIN_BUTTON
            entry_count, = db.execute("SELECT COUNT(*) FROM Submissions WHERE round_num = ?", (num,)).fetchone()
            entries = f"<strong>{entry_count}</strong> entries have been received so far." if entry_count != 1 else "<strong>1</strong> entry has been received so far."
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
    <style>{formatter.get_style_defs(".code")}</style>
  </head>
  <body>
    {top}
    <h1>code guessing, round #{num}, stage 1 (writing)</h1>
    <p>started at {format_time(rnd['started_at'])}. submit by {format_time(submit_by)}</p>
    <h2>specification</h2>
    {markdown(rnd['spec'])}
    <h2>entries</h2>
    <p>{entries}</p>
    <h2>submit</h2>
    <p>{m[0] if (m := flask.get_flashed_messages()) else ""}</p>
    {panel}
  </body>
</html>
"""
        case 2:
            entries, style = render_submissions(db, num, False)
            your_id = discord.fetch_user().id if discord.authorized else None
            query = db.execute("SELECT People.id, People.name, Submissions.position, locked FROM Submissions "
                               "INNER JOIN People ON People.id = Submissions.author_id "
                               "LEFT JOIN (Guesses INNER JOIN Submissions as Submissions2 ON Submissions2.round_num = Guesses.round_num AND Guesses.actual = Submissions2.author_id) "
                               "ON Guesses.round_num = Submissions.round_num AND Guesses.player_id = ? AND Guesses.guess = People.id "
                               "WHERE Submissions.round_num = ? ORDER BY Submissions2.position, People.name COLLATE NOCASE", (your_id, num)).fetchall()
            if discord.authorized and any(id == your_id for id, _, _, _ in query):
                panel = '<div id="guess-panel"><button ontoggle="toggleSticky()" id="sticky-button" class="toggle" alt="show">hide</button><h2>guess <button onclick="shuffleGuesses()" title="shuffle guesses">🔀</button></h2><ol id="players">'
                for idx, (id, name, pos, locked) in enumerate(query):
                    if id == your_id:
                        query.pop(idx)
                        query.insert(pos-1, (id, name, pos, locked))
                        break
                for id, name, _, locked in query:
                    if id == your_id:
                        panel += f'<li data-id="me" class="player you locked">{name} (you!)</li>'
                    else:
                        lock_button = f'<button title="lock guess in place" class="toggle lock-button" ontoggle="lock(this)" alt="🔓"{" toggleValue"*bool(locked)}>🔒</button>'
                        panel += f'<li data-id="{id}" class="player{" locked"*bool(locked)}">↕ {name} {lock_button}</li>'
                panel += "</ol></div>"
            else:
                panel = '<h2>players</h2><ol>'
                for _, name, _, _ in query:
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
    {markdown(rnd['spec'])}
    {panel}
    {entries}
  </body>
</html>
"""
        case 3:
            entries, style = render_submissions(db, num, True)
            results = "<ol>"
            for idx, (author, total, plus, bonus, minus) in score_round(num):
                bonus_s = f" ~{bonus}"*(num in (12, 13))
                results += f'<li value="{idx}"><details><summary><strong>{get_name(author)}</strong> +{plus}{bonus_s} -{minus} = {total}</summary><ol>'
                for guess, actual, pos in db.execute(
                    "SELECT guess, actual, position FROM Guesses "
                    "INNER JOIN Submissions ON Submissions.round_num = Guesses.round_num AND Submissions.author_id = Guesses.actual "
                    "WHERE Guesses.round_num = ? AND Guesses.player_id = ? ORDER BY Submissions.position", (num, author)
                ):
                    if guess == actual:
                        results += f'<li value="{pos}"><strong>{get_name(actual)}</strong></li>'
                    else:
                        results += f'<li value="{pos}">{get_name(guess)} (was {get_name(actual)})</li>'
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
    {markdown(rnd['spec'])}
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
    if config.canon_url and not requests.get(config.canon_url + f"/users/{user.id}").json()["result"]:
        flask.abort(403)
    db.execute("INSERT OR REPLACE INTO People VALUES (?, ?)", (user.id, user.to_json()["global_name"]))
    anchor = None
    try:
        match (form["type"], rnd["stage"]):
            case ("upload", 1):
                files = [x for x in flask.request.files.getlist("files") if x]
                if not files:
                    return flask.flash("submit at least one file")
                db.execute("INSERT OR REPLACE INTO Submissions (author_id, round_num, submitted_at) VALUES (?, ?, ?)", (user.id, num, datetime.datetime.now(datetime.timezone.utc)))
                db.execute("DELETE FROM Files WHERE round_num = ? AND author_id = ?", (num, user.id))
                for file in files:
                    try:
                        guess = min(get_lexer_for_filename(file.filename).aliases, key=len)
                    except ClassNotFound:
                        guess = "image" if file.filename.lower().endswith((".png", ".jpg", ".jpeg")) else "text"
                    b = file.read()
                    if not b or len(b) > 64*1024:
                        guess = None
                    elif guess not in LANGUAGES:
                        guess = "text"
                    db.execute("INSERT INTO Files (name, author_id, round_num, content, lang) VALUES (?, ?, ?, ?, ?)", (file.filename, user.id, num, b, guess))
                logging.info(f"accepted files {', '.join(str(x.filename) for x in files)} from {user.id}")
            case ("langs", 1):
                for key, value in form.items():
                    if key == "type":
                        continue
                    if value not in LANGUAGES:
                        flask.abort(400)
                    value = LANGMAP.get(value, value)
                    db.execute("UPDATE Files SET lang = ? WHERE round_num = ? AND name = ?", (value, num, key))
            case ("guess", 2):
                db.execute("DELETE FROM Guesses WHERE round_num = ? AND player_id = ?", (num, user.id))
                guesses = form.getlist("guess")
                for position, guess in enumerate(guesses, start=1):
                    if guess != "me":
                        insert = guess.removesuffix("-locked")
                        locked = insert != guess
                        db.execute("INSERT INTO Guesses SELECT ?, ?, ?, author_id, ? FROM Submissions WHERE round_num = ? AND position = ?", (num, user.id, int(insert), locked, num, position))
                logging.info(f"accepted guess {guesses} from {user.id}")
            case ("like", 2):
                for pos in form.getlist("position"):
                    id, = db.execute("SELECT author_id FROM Submissions WHERE round_num = ? AND position = ?", (num, int(pos))).fetchone()
                    checked = db.execute("SELECT NULL FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, user.id, id)).fetchone()
                    if checked:
                        db.execute("DELETE FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, user.id, id))
                        logging.info(f"{user.id} unliked {id}")
                    else:
                        db.execute("INSERT OR IGNORE INTO Likes VALUES (?, ?, ?)", (num, user.id, id))
                        logging.info(f"{user.id} liked {id}")
            case ("comment", 2 | 3):
                parent = int(form["parent"])
                persona = int(form["persona"])
                reply = int(form["reply"]) if "reply" in form else None
                content = form["content"]
                if persona != -1:
                    content = requests.post(config.canon_url + f"/users/{user.id}/transform", json={"text": content, "persona": persona}).json()["text"]
                time = datetime.datetime.now(datetime.timezone.utc)
                if edit := form.get("edit"):
                    owner, = db.execute("SELECT author_id FROM Comments WHERE id = ?", (edit,)).fetchone()
                    if user.id != owner:
                        flask.abort(403)
                    db.execute("UPDATE Comments SET content = ?, edited_at = ?, reply = ?, persona = ?, og_persona = IIF(og_persona IS NULL, persona, og_persona) WHERE id = ?", (content, time, reply, persona, edit))
                    anchor = f"c{edit}"
                    logging.info(f"{user.id} edited their comment {edit} (persona: {persona}, reply: {reply}): {content}")
                else:
                    id, = db.execute(
                        "INSERT INTO Comments (round_num, parent, author_id, content, posted_at, reply, persona) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
                        (num, parent, user.id, content, time, reply, persona)
                    ).fetchone()
                    anchor = f"c{id}"
                    logging.info(f"{user.id} commented on {parent} (id: {id}, persona: {persona}, reply: {reply}): {content}")
                    msg = f"at <https://cg.esolangs.gay/{num}#c{id}>:\n{content}"
                    reply_author = None
                    if reply:
                        reply_author, = db.execute("SELECT author_id FROM Comments WHERE id = ?", (reply,)).fetchone()
                    if config.canon_url:
                        requests.post(config.canon_url + "/notify", json={"reply": reply_author, "parent": parent, "persona": persona, "user": user.id, "url": f"https://cg.esolangs.gay/{num}#c{id}"})
            case ("delete-comment", 2 | 3):
                id = form["id"]
                owner, pos = db.execute(
                    "SELECT Comments.author_id, position FROM Comments INNER JOIN Submissions ON Submissions.round_num = Comments.round_num AND Submissions.author_id = parent WHERE id = ?",
                    (id,)
                ).fetchone()
                if user.id not in (owner, 319753218592866315):
                    flask.abort(403)
                db.execute("DELETE FROM Comments WHERE id = ?", (id,))
                anchor = str(pos)
                logging.info(f"{user.id} deleted their comment {id}")
            case _:
                flask.abort(400)
    except Exception as e:
        traceback.print_exception(e)
    else:
        flask.flash("submitted successfully")
        db.commit()
    finally:
        db.rollback()
        return flask.redirect(flask.url_for("show_round", num=num, _anchor=anchor))

# TODO consider moving into DB
TIEBREAKS = {
    6: {
        241757436720054273: 2,
        354579932837445635: 2,
    },
    12: {
        345300752975003649: 1,
        319753218592866315: 2,
    },
    23: {
        156021301654454272: 2,
    },
    28: {
        356107472269869058: 2,
    },
    29: {
        521726876755165184: 2,
    },
    32: {
        166910808305958914: 2,
    },
}

@app.route("/stats/")
def stats():
    db = get_db()
    before_round = float(flask.request.args.get("round", float("inf")))
    rounds = db.execute("SELECT num FROM Rounds WHERE stage = 3 AND num <= ?", (before_round,)).fetchall()
    lb = defaultdict(lambda: [0]*8)
    for num, in rounds:
        likers, = db.execute("SELECT COUNT(DISTINCT player_id) FROM Likes WHERE round_num = ?", (num,)).fetchone()
        players = list(score_round(num))
        for rank, (player, total, plus, bonus, minus) in players:
            p = lb[player]
            for i, x in enumerate((total, plus, bonus, minus, 1, TIEBREAKS.get(num, {}).get(player, rank) == 1)):
                p[i] += x
            p[-1] += likers
    for player, count in db.execute("SELECT liked, COUNT(*) FROM Likes WHERE round_num <= ? GROUP BY liked", (before_round,)):
        lb[player][-2] += count

    cols = ["rank", "player", "tot", "+", "-", *["~"]*(before_round >= 12), "in", "won", "tot/r", "+/r", "-/r", *["likes", "pop"]*(before_round >= 13)]
    table = "<thead><tr>"
    for col in cols:
        table += f'<th scope="col">{col}</th>'
    table += "</tr></thead>"

    e = list(rank_enumerate(lb.items(), key=lambda t: t[1][0]))
    for rank, (player, (total, plus, bonus, minus, played, won, likes, likers_seen)) in e:
        if not played:
            continue
        name = get_name(player)
        values = [
            rank,
            f'<a href="/stats/{name}">{name}</a>',
            total,
            plus,
            minus,
            *[bonus]*(before_round >= 12),
            played,
            won,
            f"{total/played:.3f}",
            f"{plus/played:.3f}",
            f"{minus/played:.3f}",
            *[likes,
            f"{likes/likers_seen:.3f}" if likers_seen else -1]*(before_round >= 13),
        ]
        table += "<tr>"
        for value in values:
            table += f"<td>{value}</td>"
        table += "</tr>"
    match [tuple(x[1]) for x in e if x[0] == 1]:
        case [(name, (total, *_))]:
            desc = f"{get_name(name)} leads with {total} points."
        case [(_, (total, *_)), *xs]:
            desc = f"{len(xs)+1} people lead with {total} points."
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
    <a href="/index">index</a>
    <h1>code guessing stats</h1>
    <p>welcome. more coming soon!</p>
    <h2>leaderboard</h2>
    <form>
      as of round <input name="round" type="number" value="{len(rounds)}" min="1"> <button type="submit">go</button>
    </form>
    <table class="sortable">{table}</table>
  </body>
</html>
"""

@app.route("/stats/<player>")
def user_stats(player):
    db = get_db()
    s = ""
    sc = 0
    for r in db.execute("SELECT author_id, round_num, submitted_at, position FROM Submissions INNER JOIN Rounds ON num = round_num INNER JOIN People ON name = ? WHERE stage = 3 AND author_id = id ORDER BY round_num", (player,)):
        position = r["position"]
        num = r["round_num"]
        s += f'<h3 id="{num}"><a href="/{num}/#{position}">round #{num}</a></h3>'
        s += render_submission(db, r, True, written_by=False)
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
    <a href="/stats">all stats</a>
    <h1>{player}'s stats</h1>
    <h2>entries</h2>
    {s}
  </body>
</html>
"""

@app.route("/anon")
def canon_settings():
    if not config.canon_url:
        panel = "this page is not available"
    elif not discord.authorized:
        panel = LOGIN_BUTTON
    else:
        user = discord.fetch_user().id
        settings = requests.get(config.canon_url + f"/users/{user}/settings").json()
        personas = requests.get(config.canon_url + f"/users/{user}/personas").json()
        panel = '<form method="POST"><input type="submit" class="hidden-submit" name="add"><h3>personas</h3><p>the names that belong to you. temporary personas will be removed and remade each round.</p>'
        panel += f'<ul><li><strong>{get_name(user)}</strong></li>'
        for persona in personas:
            end = f'<input type="submit" name="{persona["id"]}" value="delete">' if not persona["temp"] else "<em>(temp)</em>"
            panel += f'<li><strong>{bleach.clean(persona["name"])}</strong> {end}</li>'
        panel += f'<li><input name="name" type="text" size="16"> <input type="submit" name="add" value="add"> {m[0] if (m := flask.get_flashed_messages()) else ""}</li></ul>'
        for setting in settings:
            panel += f'<h3>{setting["display"].lower()} <input type="checkbox" name="{setting["name"]}"{" checked"*setting["value"]}></h3><p>{setting["blurb"].lower()}</p>'
        panel += '<input type="submit" value="save"></form>'
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="anon settings" property="og:title">
    <meta content="configure the behaviour of cg and esobot in regards to anonymous posts" property="og:description">
    <meta content="https://cg.esolangs.gay/anon" property="og:url">
    <title>anon settings</title>
  </head>
  <body>
    <a href="/index">index</a>
    <h1>anon settings</h2>
    <p>here you can configure the system behind posting anonymously on cg and Esolangs.</p>
    {panel}
  </body>
</html>
"""

@app.route("/anon", methods=["POST"])
def change_settings():
    if not discord.authorized:
        flask.abort(403)
    user = discord.fetch_user().id
    requests.post(config.canon_url + f"/users/{user}/settings", json=flask.request.form.to_dict())
    if "add" in flask.request.form:
        r = requests.post(config.canon_url + f"/users/{user}/personas", json={"name": flask.request.form["name"]}).json()
        if r["result"] == "taken":
            flask.flash("that name is taken or reserved")
    elif (d := next(iter(flask.request.form.keys()))).isdigit() and flask.request.form[d] == "delete":
        requests.delete(config.canon_url + f"/personas/{d}")
    return flask.redirect(flask.url_for("canon_settings"))

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
