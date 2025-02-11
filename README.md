# cg-site

The official implementation of [code guessing](https://codeguessing.gay).

## Steps to host
- Ensure Python 3.10 or higher is installed
- Install packages from `requirements.txt`
- Copy `config_stub.py` to `config.py` and fill it out:
    - Use some method such as `secrets.token_bytes` to generate random bytes for `secret_key`
    - Make an application in the [Discord Developer Portal](https://discord.com/developers/applications/)
        - Copy the application ID for `app_id`
        - Copy the client secret for `client_secret`
        - Add a redirect in `OAuth2 -> General` of the form `https://my.site/callback`
    - Set `log_file` to a filename
    - Set `canonical` to the canonical base URL of the server (like `"https://my.site"`)
    - (Optional) Set `canon_url` to the URL to your Canon server (see below)
    - Add the IDs of people allowed to use the admin panel to `admin_ids`, or set `admin_ids = "canon"` to use the same set as Canon if `canon_url` is set
- Create a SQLite database called `the.db` and run `schema.sql` in it
- Serve the WSGI application `cg:app` with `gunicorn` or similar

## Canon
A running [Canon](https://github.com/LyricLy/Canon) server is required for the following features:
- Commenting under anonymous names
- Getting notifications from comments
- Blocking anyone not in a certain server from submitting entries
- Sending you a notification when everyone has pressed the "finished" button during stage 2
- Acting as a Discord bot providing the `!anon` and `!cg` commands

To run Canon, clone the repository, copy `config_stub.py` to `config.py` and fill it out:
- Set `log_file` to a filename
- Set `token` to a Discord bot token (perhaps the one of the application made earlier). Without doing this, anonymous personas will still work, but Discord-specific features will not
- Set `guild_id` to the ID of the Discord server being played on (only if `token` is set)
- Add your ID to `admin_ids` or set it to a role ID (only if `token` is set)
- Set `cg_url` to the canonical URL of your code guessing server

It is a Flask application just like `cg-site`, and can be run in the same way. **Do not** expose the server to the Internet! It should only be accessible from the machine that `cg-site` is running on.
Once Canon is running, be sure to set `canon_url` in `cg-site`'s config to the URL it is exposed under, without a trailing slash.
