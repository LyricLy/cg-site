# Random sequence of bytes to encode cookies
secret_key = b""

# Discord app ID and client secret for OAuth2
app_id = 0
client_secret = ""

# Canonical base URL of the site
canonical = ""

# Optional file to write logs to
log_file = None

# Base URL to Canon server
canon_url = None

# Whether to cache the display of submissions (syntax highlighting, etc)
# Should be True in production, as pygments is slow
cache_display = True

# Discord IDs of admins
# Gives access to the admin panel, and allows you to delete other people's comments
# If set to a Discord role ID and canon_url is set, people with that role will be admins
admin_ids = []

# Where to link players that aren't on the server Canon filters to
invite_link = ""

# What the game is called
t = "code guessing"

# Abbreviation of the name
s = "cg"

# Description of the game used in meta tags
meta_desc = "a game about writing code anonymously and guessing who wrote what."

# Duration of Stage 1
stage1_days = 7

# Duration of Stage 2
stage2_days = 4

# Time between rounds
stage0_days = 3

# Which rounds to display certain figures for
# There should be no reason to change these from the provided values
likes_since = 1
bonus_rounds = ()
