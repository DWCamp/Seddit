# ===================== Script details

VERSION = "v0.3.0"

DESCRIPTION = "Seddit {} - A Python Script for counting the number of instances a collection of terms get " \
              "said on different subreddits".format(VERSION)

# ===================== PRAW Credentials

# PRAW Client Secret
CLIENT_SECRET = "<Reddit API Client Secret goes here>"

# PRAW Client ID
CLIENT_ID = "<Reddit API Client ID goes here"

# PRAW User Agent. The recommended format is provided below
USER_AGENT = "<platform>:<app ID>:<version string> (by u/<Reddit username>)"

# ===================== Cache settings

# Where to save the cache file
CACHE_FILE_PATH = "sedditCache.json"

# The number of seconds before the cached "hot" feed is considered expired
CACHE_HOT_TTL = 3600  # One hour

# The number of seconds before the cached "new" feed is considered expired
CACHE_NEW_TTL = 300  # 5 minutes

# The number of seconds before the cached "top" feed is considered expired
CACHE_TOP_TTL = 2592000  # One month

# The feeds which should be scraped on every subreddit
ENABLED_FEEDS = ["hot", "top"]

# ===================== Analysis Settings

# The default threshold for filtering out rare results
DEFAULT_THRESHOLD = 5

# The path to a CSV file containing words to filter
# out of noun search. The words should all be on the
# first line of the file. The included file contains
# the 250 most common words in the English language,
# to prevent words like 'The' and 'A' from dominating
# the results
FILTERED_WORDS_FILE = "words.csv"

# The highest rank to show on the graph
# For all results, set to -1
RANK_CUTOFF = 15
