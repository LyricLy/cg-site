# cg-site

A Flask site to manage the code guessing event in Esolangs.

## Steps to host
- Ensure Python 3.10 or higher is installed
- Install packages from `requirements.txt`
- Copy `config_stub.py` to `config.py` and fill it out:
    - Use some method such as `secrets.token_bytes` to generate random bytes for `secret_key`
    - Make an application in the [Discord Developer Portal](https://discord.com/developers/applications/)
        - Copy the client secret for `client_secret`
        - Add a redirect in `OAuth2 -> General` of the form `https://my.site/callback` and set `cb_url` to the same URL
    - Set `log_file` to a filename
    - (Optional) Set `canon_url` to the URL to your Canon server (see below)
    - Set `admin_id` to your Discord ID
- Create a SQLite database called `the.db` and run `schema.sql` in it
- Serve the WSGI application `cg:app` with `gunicorn` or similar

## Canon
A running [Canon](https://github.com/LyricLy/Canon) server is required for the following features:
- Commenting under anonymous names
- Getting notifications from comments
- Blocking anyone not in a certain server from submitting entries
- Sending you a notification when everyone has pressed the "finished" button during stage 2

To run Canon, clone the repository, copy `config_stub.py` to `config.py` and fill it out:
- Set `log_file` to a filename
- Set `token` to a Discord bot token. Without doing this, anonymous personas will still work, but notifications and filtering to server members will not
- Set `guild_id` to the ID of the Discord server being played on (only if `token` is set)
- Add the IDs of people allowed to moderate comments to `admin_ids` (only if `token` is set)

It is a Flask application just like `cg-site`, and can be run in the same way. **Do not** expose the server to the Internet! It should only be accessible from the machine that `cg-site` is running on.
Once Canon is running, be sure to set `canon_url` in `cg-site`'s config to the URL it is exposed under, without a trailing slash.

## Scripts
There are a variety of Python scripts included for managing the game state. Be aware that this interface is quite barebones, and you may have to manually edit the SQL database at times.
I suggest a tool like `sqlitebrowser`.

- `python start.py file` will read `file` as a Markdown specification and start a new round.
- `python round2.py` will transition from stage 1 to stage 2.
- `python finished.py` shows a list of players during stage 2, indicating which of them has pressed the button to finish guessing.
- `python reshuffle.py` reassigns position numbers after a submission has been removed.
  For example, if there are 3 entries and entry #2 is removed, running `reshuffle.py` will fill in its place by changing entry #3 to entry #2.
- `python end.py` ends a round, clears temporary personas, makes a backup of `the.db` in the `backups` directory, and copies a version of the database to `static/the.db` to be served publicly.
