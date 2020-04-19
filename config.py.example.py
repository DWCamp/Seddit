# PRAW Client Secret
CLIENT_SECRET = "<Reddit API Client Secret goes here>"

# PRAW Client ID
CLIENT_ID = "<Reddit API Client ID goes here"

# PRAW User Agent
USER_AGENT = "Seddit v0.1"

# Where to save the cache file
CACHE_FILE_PATH = "sedditCache.json"

# The default threshold for filtering out rare results
DEFAULT_THRESHOLD = 5

# The minimum rank to show on the graph
# For all results, set to -1
RANK_THRESHOLD = 15

# The path to a CSV file containing words to filter
# out of noun search. The words should all be on the
# first line of the file. The included file contains
# the 250 most common words in the English language,
# to prevent words like 'The' and 'A' from dominating
# the results
FILTERED_WORDS_FILE = "words.csv"
