import sys
import datetime
import io
import itertools
import os
import re
import random
import hashlib
import shutil
import html
import tarfile
import zipfile
import json
import logging
from collections import defaultdict
from pathlib import PurePosixPath

import bleach
import charset_normalizer
import magic
import mistune
import requests
import flask
import flask_discord
import yarl
from oauthlib import oauth2
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

import config
from db import connect


logging.basicConfig(filename=config.log_file, encoding="utf-8", format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", level=logging.INFO)
app = flask.Flask(__name__, static_url_path="")
app.secret_key = config.secret_key
app.config |= {
    "SESSION_COOKIE_HTTPONLY": False,
    "SESSION_COOKIE_SECURE": True,
    "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
    "PERMANENT_SESSION_LIFETIME": datetime.timedelta(days=365 * 5),
}
discord = flask_discord.DiscordOAuth2Session(app, config.app_id, config.client_secret, config.cb_url)
plugins = ["strikethrough", "table", "footnotes"]
markdown = mistune.create_markdown(plugins=plugins)
markdown_html = mistune.create_markdown(escape=False, plugins=plugins)
formatter = HtmlFormatter(linenos=True)
style = formatter.get_style_defs(".code")


def get_db():
    try:
        return flask.g._db
    except AttributeError:
        db = connect()
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
    cur = get_db().execute("SELECT MIN(num) FROM Rounds WHERE stage AND stage <> 3")
    if r := cur.fetchone()[0]:
        return flask.redirect(flask.url_for("show_round", num=r))
    else:
        return flask.redirect(flask.url_for("index"))

def get_title(spec):
    l = spec.split("**", 2)
    return l[1] if len(l) >= 3 else None

def get_summary(spec):
    l = spec.splitlines()
    return l[0].replace("*", "") if l else None

def join_warning(user_id):
    if user_id and not can_play(user_id):
        return f'<aside>note: you are not on <a href="{config.invite_link}">the Discord server</a>. joining it is a requirement to play.</aside>'
    return ""

@app.route("/index/")
def index():
    nums = get_db().execute("SELECT num, started_at, spec, stage FROM Rounds ORDER BY num DESC").fetchall()
    rounds = "".join(f"<li><a href='/{n}/'>round #{n}</a> ({get_title(spec)})</li>" if stage else f"<li>round #{n} at {format_time(start)}</li>" for n, start, spec, stage in nums)
    user_id = fetch_user_id()
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="{config.t}" property="og:title">
    <meta name="description" content="{config.meta_desc}">
    <meta content="{config.meta_desc}" property="og:description">
    <meta content="{config.canonical}/index/" property="og:url">
    <title>{config.t}</title>
  </head>
  <body>
    <p>
      <a href="/stats/">stats</a>
      &bull; <a href="/info">info</a>
      &bull; <a href="/credits">credits</a>
      &bull; <a href="/anon">anon settings</a>
      {f' &bull; <a href="/admin/">admin panel</a>'*is_admin(user_id)}
      {f' &bull; <a href="/logout">log out</a>'*bool(user_id)}
    </p>
    {join_warning(user_id)}
    <ul>{rounds}</ul>
  </body>
</html>
"""

@app.route("/<int:num>/<path:name>")
def download_file(num, name):
    user_id = fetch_user_id()
    f = get_db().execute("SELECT Files.content FROM Files INNER JOIN Rounds ON Rounds.num = Files.round_num "
                         "WHERE Files.round_num = ? AND Files.name = ? AND (Rounds.stage <> 1 OR Files.author_id = ?)", (num, name, user_id)).fetchone()
    if not f:
        flask.abort(404)
    resp = flask.send_file(io.BytesIO(f[0]), mimetype="application/octet-stream")
    return resp

@app.route("/files/<path:name>")
def download_file_available_for_public_access(name):
    return flask.send_from_directory("./files/", name)

def show_md(title, desc):
    with open(f"mds/{title}.md") as f:
        m = markdown(f.read())
    return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>{config.s} - {title}</title>
    {META}
    <meta content="{config.t} {title}" property="og:title">
    <meta content="{desc}" property="og:description">
    <meta content="{config.canonical}/info" property="og:url">
  </head>
  <body>
    <a href="/index/">index</a>
    {m}
  </body>
</html>
"""

@app.route("/info")
def info():
    return show_md("info", f"what is {config.t}?")

@app.route("/credits")
def credits():
    return show_md("credits", "all the people that helped make this happen.")

def external_url(lang):
    if str(lang).startswith("external"):
        return lang.removeprefix("external ")
    return None

def make_tar(num, compression=""):
    user_id = fetch_user_id()
    f = io.BytesIO()
    with tarfile.open(mode=f"w:{compression}", fileobj=f) as tar:
        for name, content, position, lang in get_db().execute(
            "SELECT name, content, position, lang FROM Files "
            "INNER JOIN Submissions ON Submissions.round_num = Files.round_num AND Submissions.author_id = Files.author_id "
            "INNER JOIN Rounds ON Rounds.num = Files.round_num "
            "WHERE Files.round_num = ? AND (stage <> 1 OR Files.author_id = ?)", (num, user_id)
        ):
            print(name, lang)
            if url := external_url(lang):
                content = requests.get(url).content
            info = tarfile.TarInfo(f"{num}/{position}/{name}")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    f.seek(0)
    return f

def list_archive(content):
    f = io.BytesIO(content)
    try:
        with tarfile.open(fileobj=f, errorlevel=2) as tar:
            return [(n, g.read()) for n in tar.getnames() if (g := tar.extractfile(n))]
    except tarfile.TarError:
        f.seek(0)
        try:
            with zipfile.ZipFile(f) as z:
                return [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
        except zipfile.BadZipFile:
            return [("???", b"cg: unable to read archive")]

@app.route("/<int:num>.tar.bz2")
def download_round_bzip2(num):
    return flask.send_file(make_tar(num, "bz2"), mimetype="application/x-bzip2")

def get_name(i):
    return bleach.clean(get_db().execute("SELECT name FROM People WHERE id = ?", (i,)).fetchone()[0])

def format_time(dt):
    return f'<time role="timer" datetime="{dt.isoformat()}">{dt.isoformat()}</time>'

def persona_name(author, persona, d={}):
    if persona == -1:
        return get_name(author) + ' <span class="verified"></span>'
    if not config.canon_url:
        return "[unknown]"
    return d.get(persona) or d.setdefault(persona, bleach.clean(requests.get(config.canon_url + f"/personas/{persona}").json()["name"]))

def name_of_user(user):
    return user.to_json()["global_name"] or user.name

def fetch_user():
    if not discord.authorized:
        return None
    try:
        return discord.fetch_user()
    except oauth2.InvalidGrantError:
        return None

def fetch_user_id():
    user = fetch_user()
    return user.id if user else None

def fetch_personas():
    user = fetch_user()
    if not user:
        return None
    base_persona = {"id": -1, "name": name_of_user(user)}
    if not config.canon_url:
        return [base_persona]
    if not hasattr(flask.g, "d"):
        flask.g.d = {}
    d = flask.g.d
    return d.get(user.id) or d.setdefault(user.id, [base_persona, *requests.get(config.canon_url + f"/users/{user.id}/personas").json()])

def is_admin(user_id):
    if not user_id:
        return False
    if isinstance(config.admin_ids, int):
        return requests.get(config.canon_url + f"/users/{user_id}/roles/{config.admin_ids}").json()
    return user_id in config.admin_ids

def pass_to_js(*args):
    s = ""
    for arg in args:
        s += html.escape(json.dumps(arg), quote=True)
        s += ","
    return s

def submission_pos_to_id(num, pos):
    db = get_db()
    return db.execute("SELECT author_id FROM Submissions WHERE round_num = ? AND position = ?", (num, pos)).fetchone()[0]

def submission_id_to_pos(num, author):
    db = get_db()
    return db.execute("SELECT position FROM Submissions WHERE round_num = ? AND author_id = ?", (num, author)).fetchone()[0]

def render_comments(db, num, parent_id):
    parent = submission_id_to_pos(num, parent_id)
    rows = db.execute("SELECT * FROM Comments WHERE round_num = ? AND parent = ?", (num, parent_id)).fetchall()
    comments = f'<details {"open"*bool(rows)}><summary><strong>comments</strong> {len(rows)}</summary><div class="comments">'
    for row in rows:
        comments += f'<div id="c{row["id"]}" class="comment"><strong>{persona_name(row["author_id"], row["persona"])}</strong>'
        if row["og_persona"]:
            comments += f'<span class="tooltip"><span class="tooltip-inner">known at the time as <strong>{persona_name(row["author_id"], row["og_persona"])}</strong></span></span>'
        extras = []
        if r := row["reply"]:
            replied, their_persona = db.execute("SELECT author_id, persona FROM Comments WHERE round_num = ? AND parent = ? AND id = ?", (num, parent_id, r)).fetchone()
            extras.append(f'<a href="#c{r}"><em>replying to <strong>{persona_name(replied, their_persona)}</strong></em></a>')
        extras.append(f'<a href="#c{row["id"]}">¶</a>')
        if user := fetch_user():
            owns = row["author_id"] == user.id
            extras.append(f'<button onclick="reply({pass_to_js(str(row["id"]), str(parent))})">reply</button>')
            if owns:
                extras.append(f'<button onclick="edit({pass_to_js(str(row["id"]), str(parent), row["unchanged_content"] or row["content"], row["persona"], row["reply"])})">edit</button>')
            if owns or is_admin(user.id):
                extras.append(f'<form method="post" action="/{num}/" class="delete-button"><input type="hidden" name="type" value="delete-comment"><input type="hidden" name="id" value="{row["id"]}"><input type="submit" value="delete"></form>')
        comments += ' ' + ' '.join(extras)
        comments += f'{markdown(row["content"])}</div><hr>'
    comments += "<h3>post a comment</h3>"
    if not (personas := fetch_personas()):
        comments += f"<p>{LOGIN_BUTTON}</p>"
    else:
        comments += f'<form method="post" action="/{num}/" id="post-{parent}"><input type="hidden" name="type" value="comment"><input type="hidden" name="parent" value="{parent}">as <select name="persona">'
        for idx, persona in enumerate(personas):
            comments += f'<option value="{persona["id"]}" {" selected"*(not idx)}>{persona["name"]}</option>'
        comments += '</select><span class="extra"></span><p><textarea class="comment-content" name="content" onkeypress="considerSubmit(event)" autocomplete="off" maxlength="1000"></textarea></p></form>'
    comments += "</div></details>"
    return comments

def lang_display(lang):
    if not lang:
        return "No display"
    if lang == "image":
        return "Image"
    if lang == "pdf":
        return "PDF"
    if lang == "archive":
        return "Archive"
    if lang.startswith("iframe"):
        return "Embedded page"
    return get_lexer_by_name(lang).name

def render_file(name, content, lang, url=None, dropdown_name=None, languages=None):
    filetype = magic.from_buffer(content)
    # remove appalling attempts at guessing language
    filetype = re.sub(r"^.+? (?:source|script(?: executable)?|program|document), |(?<=text) executable", "", filetype)

    if (ext := external_url(lang)) and url:
        url = ext
        filetype = f"external link to {yarl.URL(url).host}"
        lang = None

    file = ""
    name = bleach.clean(name)
    header_name = name if not url else f'<a href="{url}">{name}</a>'
    header = f'{header_name} <small><em>{filetype}</em></small>'
    if languages:
        header += f' <select name="{dropdown_name}">'
        for language in languages:
            selected = " selected"*(language == lang)
            header += f'<option value="{language}"{selected}>{lang_display(language)}</option>'
        header += "</select>"

    if lang is None or lang == "image" and not url:
        file += f'{header}<br>'
    else:
        file += f'<details><summary>{header}</summary>'
        if lang.startswith("iframe"):
            u = lang.removeprefix("iframe ")
            file += f'<iframe src="/files/{u}" width="1280" height="720" sandbox="allow-downloads allow-forms allow-modals allow-pointer-lock allow-presentation allow-scripts"></iframe>'
        elif lang == "image":
            file += f'<img src="{url}">'
        elif lang == "pdf":
            file += f'<object type="application/pdf" data="{url}" width="1280" height="720"></object>'
        elif lang == "archive":
            file += '<div class="comments">'
            file += render_file_contents([(n, c, guess_language(n, c)) for n, c in list_archive(content)])
            file += '</div>'
        else:
            try:
                text = content.decode()
            except UnicodeDecodeError:
                best = charset_normalizer.from_bytes(content).best()
                text = str(best) if best else "cg: couldn't decode file contents"
            file += highlight(text, get_lexer_by_name(lang), formatter)
        file += "</details>"

    return file

def root_dir(r):
    return r[0].parts[0] if len(r[0].parts) > 1 else None

def _render_file_contents(fs, url_stem, languages):
    out = ""
    fs.sort(key=lambda r: (not root_dir(r), r[0]))
    for dir_name, g in itertools.groupby(fs, root_dir):
        if dir_name:
            out += f'<details><summary>dir <strong>{dir_name}</strong></summary><div class="comments">'
            new_fs = [(path.relative_to(dir_name), *r) for path, *r in g]
            out += _render_file_contents(new_fs, url_stem, languages)
            out += '</div></details>'
        else:
            for path, full_name, content, lang in g:
                out += render_file(path.name, content, lang, url_stem + full_name if url_stem else None, full_name, languages)
    return out

def render_file_contents(fs, url_stem=None, languages=None):
    return _render_file_contents([(PurePosixPath(name), name, *r) for name, *r in fs], url_stem, languages)

def render_files(db, num, author, languages=None):
    fs = db.execute("SELECT name, content, lang FROM Files WHERE author_id = ? AND round_num = ?", (author, num)).fetchall()
    return render_file_contents(fs, f"/{num}/", languages)


def render_submission(db, row, show_info, written_by=True):
    author, num, submitted_at, cached_display, position = row
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
        if num in config.likes_since:
            entries += "1 like</p>" if likes == 1 else f"{likes} likes</p>"
        entries += "<details><summary><strong>guesses</strong></summary><ul>"
        for guesser, guess_id in sorted(db.execute("SELECT player_id, guess FROM Guesses WHERE round_num = ? AND actual = ?", (num, author)), key=lambda x: get_name(x[1])):
            guess = get_name(guess_id)
            if guess_id == author:
                guess = f"<strong>{guess}</strong>"
            if guess_id == target:
                guess = f"<em>{guess}</em>"
            entries += f"<li>{guess} (by {get_name(guesser)})</li>"
        entries += "</ul></details>"
    elif (your_id := fetch_user_id()) and db.execute("SELECT NULL FROM Submissions WHERE round_num = ? AND author_id = ?", (num, your_id)).fetchone():
        checked = " togglevalue"*bool(db.execute("SELECT NULL FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, your_id, author)).fetchone())
        entries += f'<p><button class="toggle" alt="unlike" ontoggle="onLike({position})"{checked}>like</button></p>'
    entries += render_comments(db, num, author)
    entries += "<br>"
    if not cached_display or not config.cache_display:
        cached_display = render_files(db, num, author)
        db.execute("UPDATE Submissions SET cached_display = ? WHERE round_num = ? AND author_id = ?", (cached_display, num, author))
        db.commit()
    entries += cached_display
    return entries

def render_submissions(db, num, show_info):
    entries = f'<p>you can <a id="download" href="/{num}.tar.bz2">download</a> all the entries</p>'
    for r in db.execute("SELECT author_id, round_num, submitted_at, cached_display, position FROM Submissions WHERE round_num = ? ORDER BY position", (num,)):
        position = r["position"]
        entries += f'<div class="entry"><h3 id="{position}">entry #{position}</h3>'
        entries += render_submission(db, r, show_info)
        entries += "</div>"
    return entries

def rank_enumerate(xs, *, key):
    cur_idx = None
    cur_key = None
    for idx, x in enumerate(sorted(xs, key=key, reverse=True), start=1):
        if cur_key is None or key(x) < cur_key:
            cur_idx = idx
            cur_key = key(x)
        yield (cur_idx, x)

LANGUAGES = [
    "py", "c", "rs", "js", "ts", "bf", "hs", "lua", "rb", "zig", "cpp", "go", "java", "kotlin", "groovy",
    "d", "swift", "pl", "scm", "raku", "apl", "bqn", "j", "k", "sml", "ocaml", "f#", "erlang", "dart", "pony", "ada",
    "nim", "nb", "forth", "factor", "elm", "vim", "sed", "nix", "tal", "sh", "matlab", "prolog",
    "md", "html", "css", "xml", "yaml", "toml", "json", "befunge", "image", "text", None
]
ADMIN_LANGUAGES = [*LANGUAGES, "pdf", "archive"]
META = f"""
<link rel="icon" type="image/png" href="/meta/favicon-96x96.png" sizes="96x96">
<link rel="icon" type="image/svg+xml" href="/meta/favicon.svg">
<link rel="shortcut icon" href="/meta/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/meta/apple-touch-icon.png">
<meta name="apple-mobile-web-app-title" content="{config.s}">
<link rel="manifest" href="/meta/site.webmanifest">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta content="website" property="og:type">
<meta content="{config.canonical}/meta/apple-touch-icon.png" property="og:image">
<script src="/main.js" defer></script>
<link rel="stylesheet" href="/main.css">
<link rel="stylesheet" href="/highlight.css">
"""
LOGIN_BUTTON = '<form method="get" action="/login"><input type="submit" value="log in with discord"></form>'

def score_round(num):
    return get_db().execute("SELECT rank, player_id, total, plus, bonus, minus, won FROM Scores WHERE round_num = ? ORDER BY rank", (num,))

def show_spec(rnd):
    return f"<h2>specification</h2>{markdown_html(rnd['spec'])}"

def flash():
    if m := flask.get_flashed_messages():
        return m[0]
    else:
        return ""

HELL_QUERY = """
WITH other_submissions AS (
    SELECT author_id, position
    FROM Submissions
    WHERE Submissions.round_num = ?1 AND author_id != ?2
), our_guesses AS (
    SELECT actual, guess, locked FROM Guesses WHERE round_num = ?1 AND player_id = ?2
), guesses_wo_holes AS (
    SELECT COUNT(*) FILTER (WHERE guess IS NULL) OVER (ORDER BY position) as idx1, guess, COALESCE(locked, 0) as locked
    FROM other_submissions LEFT JOIN our_guesses ON actual = author_id
), hole_fills AS (
    SELECT row_number() OVER (ORDER BY name COLLATE NOCASE) AS idx2, author_id
    FROM other_submissions INNER JOIN People ON id = author_id
    WHERE NOT EXISTS(SELECT 1 FROM our_guesses WHERE guess = author_id)
)
SELECT COALESCE(guess, hole_fills.author_id) as the_id, name, locked, finished_guessing FROM
    guesses_wo_holes
    LEFT JOIN hole_fills ON idx1 = idx2
    INNER JOIN People ON id = the_id
    INNER JOIN Submissions ON round_num = ?1 AND Submissions.author_id = the_id
"""

@app.route("/<int:num>/")
def show_round(num):
    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ? AND stage", (num,)).fetchone()
    if not rnd:
        flask.abort(404)
    user_id = fetch_user_id()

    top_elems = []
    if num > 1:
        top_elems.append(f'<a href="/{num-1}/">prev</a>')
    top_elems.append('<a href="/index/">index</a>')
    top_elems.append('<a href="/info">info</a>')
    if is_admin(user_id):
        top_elems.append(f'<a href="/admin/{num}">admin panel</a>')
    if db.execute("SELECT * FROM Rounds WHERE num = ? AND stage", (num+1,)).fetchone():
        top_elems.append(f'<a href="/{num+1}/">next</a>')
    top = " &bull; ".join(top_elems)

    match rnd["stage"]:
        case 1:
            if user_id:
                panel = """
<form method="post" enctype="multipart/form-data">
  <input type="hidden" name="type" value="upload">
  <label for="files">upload one or more files</label>
  <input type="file" id="files" name="files" multiple><br>
  <label for="dirs">and/or directories</label>
  <input type="file" id="dirs" name="files" multiple webkitdirectory><br>
  <input type="submit" value="submit">
</form>
"""
                files = render_files(db, num, user_id, LANGUAGES)
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
            submit_by = rnd['stage2_at']
            meta_desc = html.escape(f"{get_summary(rnd['spec'])} submit by {submit_by.strftime('%B %d (%A)')}.", quote=True)
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>{config.s} #{num}/1</title>
    {META}
    <meta content="{config.t} #{num}/1" property="og:title">
    <meta content="{meta_desc}" property="og:description">
    <meta content="{config.canonical}/{num}/" property="og:url">
  </head>
  <body>
    {top}
    <h1>{config.t}, round #{num}, stage 1 (writing)</h1>
    <p>started at {format_time(rnd['started_at'])}. submit by {format_time(submit_by)}</p>
    {show_spec(rnd)}
    <h2>entries</h2>
    <p>{entries}</p>
    <h2>submit</h2>
    {join_warning(user_id)}
    <p>{flash()}</p>
    {panel}
  </body>
</html>
"""
        case 2:
            entries = render_submissions(db, num, False)
            if user_id and (e := db.execute("SELECT position, finished_guessing FROM Submissions WHERE author_id = ? AND round_num = ?", (user_id, num)).fetchone()):
                entries_header = f'<h2>entries <button title="toggle showing locked entries while guessing" ontoggle="toggleHide()" id="hide-button" class="toggle" alt="🕶️🔒">👓🔒</button></h2>'
                your_pos, finished = e
                panel = f'''
<div id="guess-panel">
  <button ontoggle="toggleSticky()" id="sticky-button" class="toggle" alt="show">hide</button>
  <h2>
    guess
    <button onclick="shuffleGuesses()" title="shuffle guesses">🔀</button>
    <button title="once all players have pressed this button, guessing can end early" class="toggle" ontoggle="finish(this)" alt="unfinish"{" togglevalue"*finished}>finish</button>
  </h2>
  <ol id="players">'''
                query = db.execute(HELL_QUERY, (num, user_id)).fetchall()
                query.insert(your_pos-1, (user_id, get_name(user_id), None, None))
                for id, name, locked, finished in query:
                    events = 'onmousemove="setPlayerCursor(event)" onclick="clickPlayer(event)"'
                    if id == user_id:
                        panel += f'<li data-id="me" class="player you locked finished" {events}>{name} (you!)</li>'
                    else:
                        lock_button = f'<button title="lock guess in place" class="toggle lock-button" ontoggle="lock(this)" alt="🔒"{" togglevalue"*bool(locked)}>🔓</button>'
                        panel += f'<li data-id="{id}" class="player{" locked"*bool(locked)}{" finished"*finished}" {events}><a style="color:unset" href="/stats/{name}">{name}</a> {lock_button}</li>'
                panel += "</ol></div>"
            else:
                entries_header = '<h2>entries</h2>'
                panel = '<h2>players</h2><ol>'
                query = db.execute("SELECT name FROM Submissions INNER JOIN People ON id = author_id WHERE round_num = ? ORDER BY name COLLATE NOCASE", (num,)).fetchall()
                for name, in query:
                    panel += f'<li>{name}</li>'
                panel += "</ol>"
                if not user_id:
                    panel += LOGIN_BUTTON
                else:
                    panel += "<p>you weren't a part of this round. come back next time?</p>"
            guess_by = rnd['ended_at']
            return f"""
<!DOCTYPE html>
<html>
  <head>
    <title>{config.s} #{num}/2</title>
    {META}
    <meta content="{config.t} #{num}/2" property="og:title">
    <meta content="{len(query)} submissions received. guess by {guess_by.strftime('%B %d (%A)')}." property="og:description">
    <meta content="{config.canonical}/{num}/" property="og:url">
    <script src="https://cdn.jsdelivr.net/gh/SortableJS/Sortable@master/Sortable.min.js"></script>
  </head>
  <body>
    {top}
    <h1>{config.t}, round #{num}, stage 2 (guessing)</h1>
    <p>started at {format_time(rnd['started_at'])}; stage 2 since {format_time(rnd['stage2_at'])}. guess by {format_time(guess_by)}</p>
    {show_spec(rnd)}
    {panel}
    {entries_header}
    {entries}
  </body>
</html>
"""
        case 3:
            entries = render_submissions(db, num, True)
            results = "<ol>"
            for idx, author, total, plus, bonus, minus, won in score_round(num):
                bonus_s = f" ~{bonus}"*(num in config.bonus_rounds)
                crown = "👑 "*won
                results += f'<li value="{idx}"><details><summary>{crown}<strong>{get_name(author)}</strong> +{plus}{bonus_s} -{minus} = {total}</summary><ol>'
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
    <meta content="{config.t} #{num}" property="og:title">
    <meta content="round concluded." property="og:description">
    <meta content="{config.canonical}/{num}/" property="og:url">
    <title>{config.s} #{num}</title>
  </head>
  <body>
    {top}
    <h1>{config.t}, round #{num} (completed)</h1>
    <p>started at {format_time(rnd['started_at'])}; stage 2 at {format_time(rnd['stage2_at'])}; ended at {format_time(rnd['ended_at'])}</p>
    {show_spec(rnd)}
    <h2>results</h2>
    {results}
    <h2>entries</h2>
    {entries}
  </body>
</html>
"""

def guess_language(filename, content):
    if not content or len(content) > 64*1024:
        return None
    try:
        guess = min(get_lexer_for_filename(filename).aliases, key=len)
    except ClassNotFound:
        guess = "image" if filename.lower().endswith((".png", ".jpg", ".jpeg")) else "text"
    if guess not in LANGUAGES:
        return "text"
    return guess

def can_play(user_id):
    if not config.canon_url:
        return True
    return requests.get(config.canon_url + f"/users/{user_id}").json()["can_play"]

@app.route("/<int:num>/", methods=["POST"])
def take(num):
    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,)).fetchone()
    if not rnd:
        flask.abort(404)
    user = fetch_user()
    if not user:
        flask.abort(403)
    if not can_play(user.id):
        logging.info(f"{user.id} not on server, forbidding")
        flask.abort(403)
    db.execute("INSERT OR REPLACE INTO People VALUES (?, ?)", (user.id, name_of_user(user)))
    anchor = None
    form = flask.request.form
    try:
        match (form["type"], rnd["stage"]):
            case ("upload", 1):
                files = [x for x in flask.request.files.getlist("files") if x]
                if not files:
                    return flask.flash("submit at least one file")
                db.execute("INSERT OR REPLACE INTO Submissions (author_id, round_num, submitted_at) VALUES (?, ?, ?)", (user.id, num, datetime.datetime.now(datetime.timezone.utc)))
                db.execute("DELETE FROM Files WHERE round_num = ? AND author_id = ?", (num, user.id))
                for file in files:
                    b = file.read()
                    guess = guess_language(file.filename, b)
                    db.execute("INSERT INTO Files (name, author_id, round_num, content, lang) VALUES (?, ?, ?, ?, ?)", (file.filename, user.id, num, b, guess))
                logging.info(f"accepted files {', '.join(str(x.filename) for x in files)} from {user.id}")
            case ("langs", 1):
                for key, value in form.items():
                    if key == "type":
                        continue
                    # the pain of being str()'d
                    if value == "None":
                        value = None 
                    if value not in LANGUAGES:
                        flask.abort(400)
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
            case ("finish", 2):
                res, = db.execute("UPDATE Submissions SET finished_guessing = NOT finished_guessing WHERE round_num = ? AND author_id = ? RETURNING finished_guessing", (num, user.id)).fetchone()
                if not res:
                    logging.info(f"{user.id} unfinished guessing")
                else:
                    logging.info(f"{user.id} finished guessing")
                    all_done, = db.execute("SELECT MIN(finished_guessing) FROM Submissions WHERE round_num = ?", (num,)).fetchone()
                    if config.canon_url and all_done:
                        requests.post(config.canon_url + "/round-over", json=config.admin_ids)
            case ("like", 2):
                for pos in form.getlist("position"):
                    author_id, = db.execute("SELECT author_id FROM Submissions WHERE round_num = ? AND position = ?", (num, int(pos))).fetchone()
                    checked = db.execute("SELECT NULL FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, user.id, author_id)).fetchone()
                    if checked:
                        db.execute("DELETE FROM Likes WHERE round_num = ? AND player_id = ? AND liked = ?", (num, user.id, author_id))
                        logging.info(f"{user.id} unliked {author_id}")
                    else:
                        db.execute("INSERT OR IGNORE INTO Likes VALUES (?, ?, ?)", (num, user.id, author_id))
                        logging.info(f"{user.id} liked {author_id}")
            case ("comment", 2 | 3):
                parent = submission_pos_to_id(num, int(form["parent"]))
                persona = int(form["persona"])
                reply = int(form["reply"]) if "reply" in form else None
                unchanged_content = None
                content = form["content"]
                if persona != -1:
                    unchanged_content = content
                    content = requests.post(config.canon_url + f"/users/{user.id}/transform", json={"text": content, "persona": persona}).json()["text"]
                time = datetime.datetime.now(datetime.timezone.utc)
                if edit := form.get("edit"):
                    owner, = db.execute("SELECT author_id FROM Comments WHERE id = ?", (edit,)).fetchone()
                    if user.id != owner:
                        flask.abort(403)
                    db.execute(
                        "UPDATE Comments SET content = ?, unchanged_content = ?, edited_at = ?, reply = ?, persona = ?, og_persona = IIF(og_persona IS NULL AND ?4 != persona, persona, og_persona) WHERE id = ?",
                        (content, unchanged_content, time, reply, persona, edit),
                    )
                    anchor = f"c{edit}"
                    logging.info(f"{user.id} edited their comment {edit} (persona: {persona}, reply: {reply}): {unchanged_content} | {content}")
                else:
                    id, = db.execute(
                        "INSERT INTO Comments (round_num, parent, author_id, content, unchanged_content, posted_at, reply, persona) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
                        (num, parent, user.id, content, unchanged_content, time, reply, persona),
                    ).fetchone()
                    anchor = f"c{id}"
                    logging.info(f"{user.id} commented on {parent} (id: {id}, persona: {persona}, reply: {reply}): {unchanged_content} | {content}")
                    reply_author = None
                    if reply:
                        reply_author, = db.execute("SELECT author_id FROM Comments WHERE id = ?", (reply,)).fetchone()
                    if config.canon_url:
                        requests.post(config.canon_url + "/notify", json={"reply": reply_author, "parent": parent, "persona": persona, "user": user.id, "content": content, "url": f"{config.canonical}/{num}/#c{id}"})
            case ("delete-comment", 2 | 3):
                id = form["id"]
                owner, pos = db.execute(
                    "SELECT Comments.author_id, position FROM Comments INNER JOIN Submissions ON Submissions.round_num = Comments.round_num AND Submissions.author_id = parent WHERE id = ?",
                    (id,)
                ).fetchone()
                if user.id != owner and not is_admin(user.id):
                    flask.abort(403)
                db.execute("DELETE FROM Comments WHERE id = ?", (id,))
                anchor = str(pos)
                logging.info(f"{user.id} deleted their comment {id}")
            case _:
                flask.abort(400)
    except:
        raise
    else:
        flask.flash("submitted successfully")
        db.commit()
    finally:
        db.rollback()
        if exc := sys.exception():
            raise exc
        return flask.redirect(flask.url_for("show_round", num=num, _anchor=anchor))

def build_table(cols, rows):
    table = '<table class="sortable"><thead></tr>'
    for col in cols:
        table += f'<th scope="col">{col}</th>'
    table += "</tr></thead>"
    for row in rows:
        table += "<tr>"
        for value in row:
            table += f"<td>{value:.3f}</td>" if isinstance(value, float) else f"<td>{value}</td>"
        table += "</tr>"
    table += "</table>"
    return table

SEASON_EVERY = 10

@app.route("/stats/")
def stats():
    db = get_db()
    round_count, = db.execute("SELECT MAX(num) FROM Rounds WHERE stage = 3").fetchone()
    try:
        after_round = min(max(int(flask.request.args.get("after", ((round_count-1) // SEASON_EVERY * SEASON_EVERY) + 1)), 1), round_count)
        before_round = min(max(int(flask.request.args.get("before", round_count)), after_round), round_count)
    except ValueError:
        flask.abort(400)
    rounds = db.execute("SELECT num FROM Rounds WHERE stage = 3 AND num >= ? AND num <= ?", (after_round, before_round)).fetchall()

    top_buttons = []
    season, off = divmod(after_round - 1, SEASON_EVERY)
    if not off and before_round == min(round_count, after_round + SEASON_EVERY - 1):
        top_buttons.append(f"season {season+1}")
        for name, n in [("previous", season-1), ("next", season+1)]:
            start = n * SEASON_EVERY + 1
            end = (n+1) * SEASON_EVERY
            if 1 <= start <= round_count:
                top_buttons.append(f'<a href="?after={start}&before={min(end, round_count)}">{name} season</a>')
    if not top_buttons:
        top_buttons.append('<a href=".">latest season</a>')
    if len(rounds) != round_count:
        top_buttons.append('<a href="?after=1">all time leaderboard</a>')

    lb = defaultdict(lambda: [0]*7)
    for num, in rounds:
        players = score_round(num)
        for rank, player, total, plus, bonus, minus, won in players:
            p = lb[player]
            for i, x in enumerate((total, plus, bonus, minus, 1, won)):
                p[i] += x
    for player, count in db.execute("SELECT liked, COUNT(*) FROM Likes WHERE round_num >= ? AND round_num <= ? GROUP BY liked", (after_round, before_round)):
        lb[player][-1] += count

    bonus_col = any(n in config.bonus_rounds for n in range(after_round, before_round+1))
    like_col = before_round >= config.likes_since
    cols = [
        ("rank", "current rank in the leaderboard"),
        ("player", "discord username"),
        ("tot", "total score"),
        ("+", "points earned by guessing correctly"),
        ("-", "points lost by being guessed"),
        *[("~", "bonus points from special rules")]*bonus_col,
        ("in", "rounds played"),
        ("won", "rounds won"),
        ("tot/r", "average score per round"),
        ("+/r", "average correct guesses per round"),
        ("-/r", "average times guessed each round"),
        *[("likes", "total likes")]*like_col,
    ]
    rows = []

    e = list(rank_enumerate(lb.items(), key=lambda t: t[1][0]))
    for rank, (player, (total, plus, bonus, minus, played, won, likes)) in e:
        if not played:
            continue
        name = get_name(player)
        rows.append([
            rank,
            f'<a href="/stats/{name}">{name}</a>',
            total,
            plus,
            minus,
            *[bonus]*bonus_col,
            played,
            won,
            total / played,
            plus / played,
            minus / played,
            *[likes]*like_col,
        ])

    table = build_table([f'<span title="{y}">{x}</span>' for x, y in cols], rows)
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
    <meta content="{config.t} stats" property="og:title">
    <meta content="{desc}" property="og:description">
    <meta content="{config.canonical}/stats/" property="og:url">
    <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@master/dist/sortable.min.js"></script>
    <title>{config.s} stats</title>
  </head>
  <body>
    <a href="/index/">index</a>
    <h1>{config.t} stats</h1>
    <p>welcome. more coming soon!</p>
    <h2>leaderboard</h2>
    <form>
      from round <input name="after" type="number" value="{after_round}" min="1"> to <input name="before" type="number" value="{before_round}"> <button type="submit">go</button>
    </form>
    {' &bull; '.join(top_buttons)}
    {table}
  </body>
</html>
"""

CHUMPS = "player_id = ? AND guess = id"
SCOURGES = "player_id = id AND guess = ?"
FIND = "SELECT name, SUM(guess = actual), COUNT(*) AS count, SUM(guess = actual) * 1.0 / COUNT(*) AS ratio FROM People INNER JOIN Guesses ON {} INNER JOIN Rounds ON num = round_num WHERE stage = 3 GROUP BY id HAVING count >= 4 ORDER BY ratio DESC"

@app.route("/stats/<path:player>")
def user_stats(player):
    db = get_db()
    r = db.execute("SELECT id FROM People WHERE name = ? AND EXISTS(SELECT 1 FROM Submissions WHERE author_id = id)", (player,)).fetchone()
    if not r:
        flask.abort(404)
    player_id ,= r
    cols = ["name", "correct guesses", "games together", "ratio"]
    chumps = build_table(cols, db.execute(FIND.format(CHUMPS), (player_id,)).fetchall())
    scourges = build_table(cols, db.execute(FIND.format(SCOURGES), (player_id,)).fetchall())
    s = ""
    sc = 0
    for r in db.execute("SELECT author_id, round_num, submitted_at, cached_display, position FROM Submissions INNER JOIN Rounds ON num = round_num WHERE stage = 3 AND author_id = ? ORDER BY round_num DESC", (player_id,)):
        position = r["position"]
        num = r["round_num"]
        s += f'<h3 id="{num}"><a href="/{num}/#{position}">round #{num}</a></h3>'
        s += render_submission(db, r, True, written_by=False)
        sc += 1
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="{player}'s {config.t} stats" property="og:title">
    <meta content="see their {sc} awesome entries" property="og:description">
    <meta content="{config.canonical}/stats/{player}" property="og:url">
    <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@master/dist/sortable.min.js"></script>
    <title>{config.s} - {player}</title>
  </head>
  <body>
    <a href="/stats">all stats</a>
    <h1>{player}'s stats</h1>
    <h2>guessed the most</h2>
    {chumps}
    <h2>were guessed the most by</h2>
    {scourges}
    <h2>entries</h2>
    {s}
  </body>
</html>
"""

@app.route("/anon")
def canon_settings():
    if not config.canon_url:
        panel = "this page is not available"
    elif not (user := fetch_user_id()):
        panel = LOGIN_BUTTON
    else:
        settings = requests.get(config.canon_url + f"/users/{user}/settings").json()
        personas = requests.get(config.canon_url + f"/users/{user}/personas").json()
        panel = '<form method="POST"><input type="submit" class="hidden-submit" name="add"><h3>personas</h3><p>the names that belong to you. temporary personas will be removed and remade each round.</p><ul>'
        for persona in personas:
            end = f'<input type="submit" name="{persona["id"]}" value="delete">' if not persona["temp"] else "<em>(temp)</em>"
            panel += f'<li><strong>{bleach.clean(persona["name"])}</strong> {end}</li>'
        panel += f'<li><input name="name" type="text" size="16"> <input type="submit" name="add" value="add"> {flash()}</li></ul>'
        for setting in settings["settings"]:
            panel += f'<h3>{setting["display"].lower()} <input type="checkbox" name="{setting["name"]}"{" checked"*setting["value"]}></h3><p>{setting["blurb"].lower()}</p>'
        panel += f'<input type="submit" value="save"></form><p><sup>identifiable information (bits, lower is better): {settings["entropy"]:.2f}</sup></p>'
    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <meta content="anon settings" property="og:title">
    <meta content="configure the behaviour of {config.s} and canon in regards to anonymous posts" property="og:description">
    <meta content="{config.canonical}/anon" property="og:url">
    <title>anon settings</title>
  </head>
  <body>
    <a href="/index/">index</a>
    <h1>anon settings</h2>
    <p>here you can configure the system behind posting anonymously on this site and Discord.</p>
    {panel}
  </body>
</html>
"""

@app.route("/anon", methods=["POST"])
def change_settings():
    user = fetch_user_id()
    if not user:
        flask.abort(403)
    requests.post(config.canon_url + f"/users/{user}/settings", json=flask.request.form.to_dict())
    if "add" in flask.request.form:
        r = requests.post(config.canon_url + f"/users/{user}/personas", json={"name": flask.request.form["name"]}).json()
        if r["result"] == "taken":
            flask.flash("that name is taken or reserved")
    elif (d := next(iter(flask.request.form.keys()))).isdigit() and flask.request.form[d] == "delete":
        requests.delete(config.canon_url + f"/personas/{d}")
    return flask.redirect(flask.url_for("canon_settings"))

@app.route("/admin/")
def panel_root():
    r, = get_db().execute("SELECT MAX(num) FROM Rounds").fetchone()
    return flask.redirect(flask.url_for("panel", num=r))

@app.route("/admin/<int:num>")
def panel(num):
    user_id = fetch_user_id()
    if not is_admin(user_id):
        flask.abort(401)

    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,)).fetchone()
    if not rnd:
        flask.abort(404)

    if timefield := ["started_at", "stage2_at", "ended_at", None][rnd["stage"]]:
        extend = f'<input type="date" name="{timefield}" value="{rnd[timefield].strftime("%Y-%m-%d")}"> <input type="submit" value="extend/shorten deadline">'
    else:
        extend = ""

    entries = ""
    if rnd["stage"] > 1:
        entries += '<h2>entries</h2>'
        entries += flash()
        for author, pos in db.execute("SELECT author_id, position FROM Submissions WHERE round_num = ? ORDER BY position", (num,)):
            if rnd["stage"] == 2:
                entries += f'<h3>#{pos} <input type="submit" name="nix-{pos}" value="disqualify"></h3>'
            else:
                entries += f'<h3>#{pos}</h3>'
            entries += render_files(db, num, author, ADMIN_LANGUAGES)
        entries += '<p><input type="submit" value="update languages"></p>'

    return f"""
<!DOCTYPE html>
<html>
  <head>
    {META}
    <title>admin panel (#{num})</title>
  </head>
  <body>
    <header>
      {f'<a href="{num-1}">previous round</a>' if num > 1 else '<a></a>'}
      <h1>{f'<a href="/{num}/">round #{num}</a>' if rnd["stage"] else f'round #{num}'}</h1>
      {f'<a href="{num+1}">next round</a>' if rnd["stage"] == 3 else '<a></a>'}
    </header>
    <form method="post">
      <details>
        <summary>edit specification</summary>
        <p>
          {f"title (shown on /index/): {title}"
          if (title := get_title(rnd["spec"])) else
          "<strong>warning: specification should have a bolded section indicating the challenge in the first paragraph</strong>"}
          <br>summary (shown in link embed): {get_summary(rnd["spec"])}
        </p>
        <textarea class="comment-content" name="spec" autocomplete="off">{rnd["spec"]}</textarea>
        <input type="submit" value="save">
      </details>
      <p>{extend}</p>
      <p>{" ".join(f'<input type="submit" name="action" value="{v}">' for v in [["start round"], ["move to stage 2", "unstart round"], ["end round"], []][rnd["stage"]])}</p>
      {show_spec(rnd)}
      {entries}
    </form>
  </body>
</html>
    """

def backup(num):
    os.makedirs("backups", exist_ok=True)
    shutil.copy("the.db", f"backups/{num}.db")

@app.route("/admin/<int:num>", methods=["POST"])
def take_admin(num):
    db = get_db()
    rnd = db.execute("SELECT * FROM Rounds WHERE num = ?", (num,)).fetchone()
    if not rnd:
        flask.abort(404)
    user_id = fetch_user_id()
    if not is_admin(user_id):
        flask.abort(403)
    form = flask.request.form
    try:
        db.execute("UPDATE Rounds SET spec = ? WHERE num = ?", (form["spec"], num))
        db.execute("UPDATE Submissions SET cached_display = NULL WHERE round_num = ?", (num,))
        for key, value in form.items():
            # the pain of being str()'d
            if value == "None":
                value = None 
            if value not in ADMIN_LANGUAGES:
                continue
            db.execute("UPDATE Files SET lang = ? WHERE round_num = ? AND name = ?", (value, num, key))

        for timefield in "started_at", "stage2_at", "ended_at":
            date = form.get(timefield)
            if not date:
                continue
            new = datetime.datetime.combine(datetime.datetime.strptime(date, "%Y-%m-%d").date(), rnd[timefield].timetz())
            db.execute(f"UPDATE Rounds SET {timefield} = ? WHERE num = ?", (new, num))

        now = datetime.datetime.now(datetime.timezone.utc)
        match (form.get("action"), rnd["stage"]):
            case ("start round", 0):
                db.execute("UPDATE Rounds SET stage = 1, started_at = ?, stage2_at = ? WHERE num = ?", (now, now+datetime.timedelta(days=config.stage1_days), num))
                logging.info(f"{user_id} started round {num}")
            case ("move to stage 2", 1):
                db.execute("UPDATE Rounds SET stage = 2, stage2_at = ?, ended_at = ? WHERE num = ?", (now, now+datetime.timedelta(days=config.stage2_days), num))
                subs = db.execute("SELECT * FROM Submissions WHERE round_num = ?", (num,)).fetchall()
                random.shuffle(subs)
                for idx, sub in enumerate(subs, start=1):
                    author = sub["author_id"]
                    if config.canon_url:
                        persona = requests.post(config.canon_url + f"/users/{author}/personas", json={"name": f"[author of #{idx}]", "sudo": True, "temp": True}).json()["id"]
                    else:
                        persona = None
                    db.execute("UPDATE Submissions SET position = ?, persona = ? WHERE round_num = ? AND author_id = ?", (idx, persona, sub["round_num"], author))
                db.commit()
                logging.info(f"{user_id} moved round {num} to stage 2")
                backup(num)
            case ("unstart round", 1):
                db.execute("UPDATE Rounds SET stage = 0 WHERE num = ?", (num,))
                logging.info(f"{user_id} unstarted round {num}")
            case ("end round", 2):
                db.execute("UPDATE Rounds SET stage = 3, ended_at = ? WHERE num = ?", (now, num))
                db.execute("INSERT INTO Rounds (stage, spec, started_at) VALUES (0, '', ?)", (now+datetime.timedelta(days=config.stage0_days),))

                for persona in db.execute("SELECT persona FROM Submissions WHERE round_num = ?", (num,)):
                    db.execute("UPDATE Comments SET persona = -1, og_persona = COALESCE(og_persona, persona) WHERE persona = ?", persona)

                # tiebreak
                winners = db.execute("SELECT player_id FROM Scores WHERE round_num = ? AND won ORDER BY player_id", (num,)).fetchall()
                winner_idx = int.from_bytes(hashlib.sha256(str(num).encode()).digest(), "big") % (len(winners) or 1)
                for idx, (so_called_winner,) in enumerate(winners):
                    if idx != winner_idx:
                        db.execute("INSERT INTO Tiebreaks (round_num, player_id, new_rank) VALUES (?, ?, ?)", (num, so_called_winner, 2))

                db.commit()
                logging.info(f"{user_id} ended round {num}")
                backup(num)

                # make public copy
                shutil.copy("the.db", "static")
                with open("modify_for_public_viewing.sql") as f:
                    script = f.read()
                public_db = connect("static/the.db")
                public_db.executescript(script)

                if config.canon_url:
                    requests.post(config.canon_url + "/personas/purge")
            case (None, _):
                for key in form:
                    if not key.startswith("nix-"):
                        continue
                    pos = int(key.removeprefix("nix-"))
                    author, = db.execute("DELETE FROM Submissions WHERE round_num = ? AND position = ? RETURNING author_id", (num, pos)).fetchone()

                    subs = db.execute("SELECT * FROM Submissions WHERE round_num = ? ORDER BY position", (num,)).fetchall()
                    db.execute("UPDATE Submissions SET position = NULL WHERE round_num = ?", (num,))
                    for idx, sub in enumerate(subs, start=1):
                        if config.canon_url and (persona := sub["persona"]):
                            requests.patch(config.canon_url + f"/personas/{persona}", json={"name": f"[author of #{idx}]", "sudo": True})
                        db.execute("UPDATE Submissions SET position = ? WHERE round_num = ? AND author_id = ?", (idx, sub["round_num"], sub["author_id"]))

                    flask.flash(f"disqualified {author} ({get_name(author)})")
                    logging.info(f"{user_id} disqualified {author}")
            case _:
                flask.abort(400)
    except:
        raise
    else:
        db.commit()
    finally:
        db.rollback()
        if exc := sys.exception():
            raise exc
        return flask.redirect(flask.url_for("panel", num=num))

@app.route("/callback")
def callback():
    flask.session.permanent = True
    r = discord.callback()
    return flask.redirect(r["redirect"])

@app.route("/login")
def login():
    return discord.create_session(["identify"], data={"redirect": flask.request.referrer})

@app.route("/logout")
def logout():
    discord.revoke()
    return flask.redirect(flask.url_for("index"))

@app.errorhandler(404)
def not_found(e):
    return 'page not found :(<br><a href="/">go home</a>', 404
