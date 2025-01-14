# Random sequence of bytes to encode cookies
secret_key = b""

# Discord app ID and client secret for OAuth2
app_id = 0
client_secret = ""

# Callback URL for OAuth2, should have path /callback
cb_url = ""

# Optional file to write logs to
log_file = None

# Base URL to Canon server
canon_url = ""

# Whether to cache the display of submissions (syntax highlighting, etc)
# Should be True in production, as pygments is slow
cache_display = True

# Discord IDs of admins
# Gives access to the admin panel, and allows you to delete other people's comments
# If set to "canon" and canon_url is set, Canon will be queried for the list of admins
admin_ids = []

# Where to link players that aren't on the server Canon filters to
invite_link = ""

# Which rounds to display certain figures for
# There should be no reason to change these from the provided values
likes_since = 1
bonus_rounds = ()
