"""
Class for caching posts from a subreddit. Loads posts from file,
fetches new ones when the cache is stale, and computes the scores
for words found in the title

@author Daniel Campman
@version 7/19/21
"""

import json
import os
import re
import time

import praw

from data import Post, TermGroups


class PostCache:
    _CACHE_FORMAT_VERSION = "2.0"
    _CACHE_CACHE = {}  # A dictionary of PostCache objects for each subreddit

    # Scoring methods
    COUNT = 0
    SCORE = 1

    def __init__(self,
                 subreddit: str,
                 cache_file: str,
                 reddit: praw.reddit,
                 hot_ttl: int = 86400,
                 new_ttl: int = 21600,
                 top_ttl: int = 2592000):
        """
        Creates a cache of posts from a subreddit. Posts will be loaded from
        a cache file. If a cache file cannot be located, an empty file
        will be created at the specified location

        :param subreddit: The name of the subreddit the posts are scraped from
        :param cache_file: The path of the cache file
        :param hot_ttl: The number of seconds before the hot feed is refreshed (Default: 24 hours)
        :param new_ttl: The number of seconds before the new feed is refreshed (Default: 6 hours)
        :param top_ttl: The number of seconds before the top feed is refreshed (Default: 30 days)
        """
        self.subreddit = subreddit  # The name of the subreddit
        self.feed_ages = {  # The time when feed was last refreshed
            "hot": 0.0,
            "new": 0.0,
            "top": 0.0
        }
        self.ttl = {
            "hot": hot_ttl,
            "new": new_ttl,
            "top": top_ttl
        }
        self.posts = set()  # A dictionary of all posts on the subreddit

        self._cache_file = cache_file  # The filepath of the cache file
        self._reddit = reddit  # praw.reddit instance

        # If no cache file found, create one
        if not os.path.exists(self._cache_file):
            print(f"Alert: No cache file found for {subreddit} at '{self._cache_file}'")
            # Create empty cache file
            with open(self._cache_file, 'w') as fp:
                data = {
                    "version": PostCache._CACHE_FORMAT_VERSION,
                    "subreddit": self.subreddit,
                    "feed_ages": self.feed_ages,
                    "posts": []
                }
                json.dump(data, fp)
                print("Created new cache file")
            return

        # If cache file exists, load it
        print(f"Checking cache for /r/{self.subreddit}")
        with open(self._cache_file, 'r') as fp:
            data = json.load(fp)

        # Validate cache file
        required_keys = ["version", "subreddit", "feed_ages", "posts"]
        for key in required_keys:
            if key not in data:  # Check that cache has all required keys
                raise ValueError(f"Cache contains no key '{key}'")

        if not validate_cache_version(PostCache._CACHE_FORMAT_VERSION, data["version"]):
            raise ValueError(f"Unsupported cache version: Expected '{PostCache._CACHE_FORMAT_VERSION}', "
                             f"was '{data['version']}'")

        if data["subreddit"].lower() != self.subreddit.lower():  # Check subreddit
            raise ValueError(f"Cache contains incorrect subreddit: Expected '{self.subreddit.lower()}', "
                             f"was '{data['subreddit'].lower()}'")

        # Convert dictionary data to Post objects and store
        for post_data in data["posts"]:
            post = Post(post_data["postID"], post_data["title"], post_data["score"])
            self.posts.add(post)
        self.feed_ages = data["feed_ages"]

        # Show cache size
        print(f"Cached posts: {len(self.posts)}")

    def count_words(self,
                    term_group: TermGroups = None,
                    ignore_title_regex: str = None,
                    require_title_regex: str = None,
                    method: str = SCORE) -> {str: int}:
        """
        Counts the frequency of every word in the titles of cached posts. A TermGroup can be used to specify
        words that should be considered one

        :param term_group: The TermGroup for the given search. If `None`, no TermGroup is used (Default: None)
                If "None", no words will be filtered (Default: None)
        :param ignore_title_regex: A regex pattern titles must NOT contain to be evaluated
        :param require_title_regex: A regex pattern titles must contain to be evaluated
        :param method: How words are scored. The default, COUNT, counts the number of posts that each word
                appears, finding the most common word. SCORE adds up the scores of every post
                containing the word, finding the 'most liked' word.

        :return: A {str:int} dictionary, whose keys are words and values are the number of titles they appeared in
        """

        # Perform search
        word_frequency = {}

        for post in self.posts:
            term_list = post.term_list(term_group,
                                       ignore_title_regex=ignore_title_regex,
                                       require_title_regex=require_title_regex)
            value = post.score if method == PostCache.SCORE else 1
            for term in term_list:
                if term in word_frequency:
                    word_frequency[term] += value
                else:
                    word_frequency[term] = value

        # Restore capitalization on term groups
        if term_group:
            word_frequency = {term_group.sanitize(word): freq for (word, freq) in word_frequency.items()}

        return word_frequency

    def search_terms(self,
                     searched_terms: [[str]],
                     method: str = SCORE,
                     ignore_title_regex: str = None,
                     require_title_regex: str = None,
                     ignore_case: bool = True) -> {str: int}:
        """
        Counts the frequency

        :param searched_terms: List of lists, with each list being a group of words/phrases
                (case-insensitive) to search for.
        :param method: How words are scored. The default, COUNT, counts the number of posts that each word
                appears, finding the most common word. SCORE adds up the scores of every post
                containing the word, finding the 'most liked' word.
        :param ignore_title_regex: A regex pattern titles must NOT contain to be evaluated
        :param require_title_regex: A regex pattern titles must contain to be evaluated
        :param ignore_case: Ignore case for term matching (default: True)

        :return: A {str:int} dictionary of how frequently words mapped to the number of titles they appeared in
        """
        # Create regex patterns
        search_patterns = {}
        for group in searched_terms:
            # Compile all terms into a `(<A>|<B>|...)` regex string
            escaped_list = [re.escape(term).strip() for term in group]
            flags = re.IGNORECASE if ignore_case else 0
            search_patterns[group[0]] = re.compile('\\b({})\\b'.format("|".join(escaped_list)), flags)

        # Add groups to frequency dict
        term_frequency = {}
        for group in search_patterns:
            term_frequency[group] = 0

        # Perform search
        for post in self.posts:
            # Skip title if it fails regex filter
            if ignore_title_regex and re.search(ignore_title_regex, post.title):
                continue
            elif require_title_regex and re.search(require_title_regex, post.title) is None:
                continue

            # Increase the score of the groups found in the title
            value = post.score if method == PostCache.SCORE else 1
            for group, pattern in search_patterns.items():
                term_frequency[group] += value if pattern.search(post.title) else 0

        # Return result
        return term_frequency

    def posts(self) -> list:
        """
        Fetches a list of every post for the given

        :return: A list of every cached Post
        """
        return list(self.posts)

    def refresh(self,
                force: bool = False,
                limit: int = None):
        """
        Updates the cache for the specified feed(s) if any of the following conditions are true:
            - Feed ttl has expired
            - Cache is being force refreshed

        :param force: If `True`, cache will refresh even if it hasn't expired yet (Default: False)
        :param limit: The feed limit for PRAW. Determines the maximum number of posts PRAW will fetch
            when refreshing the feeds. The lower the number, the faster it will refresh, but the less
            data will be collected. To collect the maximum number (~1000), set to `None` (Default: None)

        :return: Returns `True` if the feed was refreshed, `False` otherwise
        """

        curr_time = time.time()
        refreshed = False

        # Create subreddit object
        subreddit = self._reddit.subreddit(self.subreddit)

        # Refresh every feed
        for feed_name in self.feed_ages:
            feed_age = self.feed_ages[feed_name]

            # === Check if feed needs to be refreshed

            if force:
                print(f"Alert: Forcing cache refresh on {feed_name}")
            elif (feed_age + self.ttl[feed_name]) < curr_time:
                print(f"Alert: {feed_name} cache expired for /r/{self.subreddit} - "
                      f"Refreshing feed...")
            else:
                # Cache is still fresh and will not be updated
                continue

            # === Refresh expired feed
            refreshed = True

            # Get post generator
            if feed_name == "hot":
                generator = subreddit.hot(limit=limit)
            elif feed_name == "new":
                generator = subreddit.new(limit=limit)
            else:
                generator = subreddit.top(limit=limit)

            # Fetch posts from feed
            for submission in generator:
                new_post = Post(submission.id, submission.title, submission.score)
                # If post already in set, replace with more current score
                self.posts.discard(new_post)
                self.posts.add(new_post)

            # Update cache age
            self.feed_ages[feed_name] = curr_time

        # Show cache size after refresh
        print(f"Cached posts: {len(self.posts)}")
        return refreshed

    def save(self) -> None:
        """
        Writes contents of the PostCache to a file. Data in existing file is
        read in, updated, then written back, so as to preserve any fields required
        by different software versions.
        """
        if not os.path.exists(self._cache_file):
            raise FileNotFoundError(f"Could not locate cache file at '{self._cache_file}'")

        # Load data from cache file
        with open(self._cache_file, 'r') as fp:
            data = json.load(fp)

        # Update cache data
        data["feed_ages"] = self.feed_ages
        data["posts"] = [post.to_dict() for post in self.posts]

        # Save updated data to file
        with open(self._cache_file, 'w') as fp:
            json.dump(data, fp)
            print(f"Subreddit '{self.subreddit}' saved to cache.")


def validate_cache_version(seddit: str, file: str) -> bool:
    """
    Checks the version number of a cache file against the current one
    to determine if this file can be safely used.

    Version numbers are listed in the format 'X.Y.Z' (e.g. '2.4.0').

    X - Increments when a breaking change to the cache file design is made.
        If these numbers are different, the file is incompatible.
    Y - Increments when a forwards compatible change is made (e.g. the new
        version added a field, but older versions aren't looking for that field,
        so they won't notice). If Seddit's value is less than the file's,
        they are still compatible.
    Z - A change which did not effect compatibility.

    :param seddit: The version string for the Seddit application
    :param file: The version string of the cache file being read

    :return: Returns `True` if the cache file is compatible with this version of Seddit
    """
    try:
        seddit_values = seddit.split(".")
        file_values = file.split(".")

        if int(file_values[1]) < int(seddit_values[1]):  # Check that the file's Y value isn't too low
            return False
        return int(file_values[0]) == int(seddit_values[0])  # Check that X values are equal

    except Exception as e:
        raise ValueError(f"Unsupported cache version string: '{file}' \n{e}")
