"""
Second version of the ranking algorithm for Seddit

Goals:
- Count titles containing words, not word instances, so that one post isn't counted twice
- A function that maps an input belonging a term group to the group name (does nothing if input does not belong to a term group)
- A scoring method which sums the scores of posts containing the term
- Pandas? Numpy?

Integration:
- Titles are provided as a large list along with either (A) a list of terms to search for (B) a list of term groups and words to filter
- Expects back a dictionary of word:score ("score" is currently the frequency)

"""
import json
import os
import re
import time

import praw


class TermGroup:

    def __init__(self, groups: [[str]], ignore_case=True):
        """
        Creates a group of synonymous terms. Titles filtered through the term group will have all instances
        of word in each term group replaced with the first element of the group.

        **Note:** Empty and single element lists are removed, since they will have no effect

        :param groups: The list of string lists. Each list is a term group. When a title is filtered, all words
            in each list will be replaced with the first element
        :param ignore_case: Ignore case for term matching (default: True)
        """
        # Filter `None` as well as <2 element lists, as these won't change anything
        groups = [group for group in groups if group is not None and len(group) > 1]

        # Create regex filter for each term group
        self.groups = {}
        for group in groups:
            # Compile all terms into a `(<A>|<B>|...)` regex string
            escaped_list = [re.escape(term) for term in group]
            flags = re.IGNORECASE if ignore_case else 0
            self.groups[group[0]] = re.compile('\\b({})\\b'.format("|".join(escaped_list)), flags)

    def sanitize(self, title: str) -> str:
        """
        Sanitizes term groups by replacing every instance of a term with string with a

        :param title: The title to sanitize
        :return: The title, with all instances of a term group replaced with the group name
        """
        for group in self.groups:
            title = self.groups[group].sub(group, title)
        return title


class Post:

    def __init__(self, post_id: str, title: str, score: int):
        """
        Represents a post on Reddit
        :param post_id: The ID
        :param title: The title of the post
        :param score: The score of the post
        """
        self.postID = post_id
        self.title = title
        self.score = score

    def __eq__(self, other):
        if isinstance(other, Post):
            return self.postID == other.postID
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.postID)

    def term_list(self, term_group: TermGroup) -> set:
        """
        Returns a set of all unique words in the post title

        :param term_group: The TermGroup object for this query
        :return: The set of words in the post title
        """
        title = term_group.sanitize(self.title)
        # Find all 'words' in the title (i.e. contiguous alphanumeric strings)
        words = re.findall(r'\b[A-Z][\w.]*\b', title.lower())

        if not words:
            return set()

        # Convert list to set to remove duplicates
        result = set()
        for word in words:
            result.add(word)

        # Return words
        return result

    def to_dict(self):
        """
        Convert Post to a dictionary
        :return: A dictionary representation of the Post's data
        """
        return {
            "postID": self.postID,
            "title": self.title,
            "score": self.score
        }


class PostCache:
    CACHE_FORMAT_VERSION = "1.1"

    def __init__(self, subreddit: str, cache_file: str, reddit: praw.reddit):
        """
        Creates a cache of posts from a subreddit.

        :param subreddit: The name of the subreddit the posts are scraped from
        :param cache_file: The path of the cache file
        """
        self.subreddit = subreddit  # The name of the subreddit
        self.feed_ages = {  # The time when feed was last refreshed
            "hot": 0.0,
            "new": 0.0,
            "top": 0.0
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
                    "version": PostCache.CACHE_FORMAT_VERSION,
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

        if data["version"] != PostCache.CACHE_FORMAT_VERSION:  # Check cache version
            raise ValueError(f"Unsupported cache version: Expected '{PostCache.CACHE_FORMAT_VERSION}', "
                             f"was '{data['version']}'")
        if data["subreddit"].lower() != self.subreddit:  # Check subreddit
            raise ValueError(f"Cache contains incorrect subreddit: Expected '{self.subreddit}', "
                             f"was '{data['subreddit']}'")

        # Convert dictionary data to Post objects and store
        for post_data in data["posts"]:
            post = Post(post_data["postID"], post_data["title"], post_data["score"])
            self.posts.add(post)

    def posts(self) -> list:
        """
        Fetches a list of every post for the given

        :return: A list of every cached Post
        """
        return list(self.posts)

    def refresh(self,
                ttl: int,
                force: bool = False):
        """
        Updates the cache for the specified feed(s) if any of the following conditions are true:
            - Feed cache is older than ttl
            - Cache is being force refreshed

        :param ttl: The ttl for this feed in seconds
        :param force: If `True`, cache will refresh even if it hasn't expired yet (Default: False)

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
                print(f"Alert: Forcing cache refresh")
            elif (feed_age + ttl) < curr_time:
                print(f"Alert: {feed_name} cache expired for /r/{self.subreddit}")
            else:
                # Cache is still fresh and will not be updated
                continue

            # === Refresh expired feed

            print(f"Alert: Refreshing '{feed_name}' feed for /r/{self.subreddit}...")
            refreshed = True

            # Get post generator
            if feed_name == "hot":
                generator = subreddit.hot()
            elif feed_name == "new":
                generator = subreddit.new()
            else:
                generator = subreddit.top()

            # Fetch posts from feed
            for submission in generator:
                self.posts.add(Post(submission.id, submission.title, submission.score))

            # Update cache age
            self.feed_ages[feed_name] = curr_time

        return refreshed

    def save(self) -> None:
        """
        Writes contents of the PostCache to a file
        """
        if not os.path.exists(self._cache_file):
            raise FileNotFoundError(f"Could not locate cache file at '{self._cache_file}'")

        # Convert cache to dict
        data = {
            "version": PostCache.CACHE_FORMAT_VERSION,
            "subreddit": self.subreddit,
            "feed_ages": self.feed_ages,
            "posts": [post.to_dict() for post in self.posts]
        }

        # Save results to file
        with open(self._cache_file, 'w') as fp:
            json.dump(data, fp)
            print(f"Subreddit '{self.subreddit}' saved to cache.")