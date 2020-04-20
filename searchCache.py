"""
searchCache.py

Stores the results of a seddit search for caching and cumulative search

@author Daniel Campman
@version 4/19/20
"""

import json
import os
import time
import praw

CACHE_FORMAT_VERSION = "1.0"


class SearchCache:

    def __init__(self, subreddit: str):
        """
        Creates a bank of search results from a subreddit.

        :param subreddit: The name of the subreddit these results come from
        """
        self.subreddit = subreddit  # The name of the subreddit
        self._all_posts = {}        # Create a dictionary for storing the data of every post ever seen
        self.feeds = {              # Create a dictionary for caching each feed
            "hot": {
                "time": time.time(),
                "none_feed_limit": False,
                "posts": []
            },
            "new": {
                "time": time.time(),
                "none_feed_limit": False,
                "posts": []
            },
            "top": {
                "time": time.time(),
                "none_feed_limit": False,
                "posts": []
            }
        }

    def to_dict(self) -> dict:
        """
        Returns the results of the search as a JSON dictionary in this format:

        - subreddit : The name of the subreddit
        - all_posts: A dictionary of every post ever cached for this subreddit.
            The keys are the ID of every post and the values are dictionaries:
            - Score : The score of the post
            - Title : The title of the post
        - feeds : A dictionary of the different feeds
            - hot : A dictionary of posts in the 'hot' feed
                - time: The POSIX timestamp of when the feed was fetched
                - none_feed_limit: Boolean, `true` if the search was performed with a `None` feed limit
                - posts: A list of the IDs for every post in the feed
            - new : A dictionary of posts in the 'new' feed. Same structure as 'hot'
            - top : A dictionary of posts in the 'top' feed. Same structure as 'hot'

        :return: A dictionary
        """
        return {
            "subreddit": self.subreddit,
            "all_posts": self._all_posts,
            "feeds": self.feeds
        }

    def titles(self, feed_name_list: str=None):
        """
        Returns a list of every title across all feeds. If a post
        appeared in more than one feed, only one copy is returned

        :param feed_name_list: The list of feeds to search across. If `None`,
                               the results for all_posts will be returned
        :return: A list of every post title across the given feeds
        """
        if feed_name_list is None:  # If list is none, return all_posts
            return [post["Title"] for post in self._all_posts.values()]

        unique_ids = set()  # Use a set to guarantee no posts get repeated
        for feed_name in feed_name_list:  # For every feed, add their posts to the set
            unique_ids.update(self.feeds[feed_name]["posts"])
        return [self._all_posts[post_id]["Title"] for post_id in unique_ids]

    def refresh_feed(self,
                     reddit: praw.reddit,
                     feed_name: str,
                     ttl: int,
                     feed_limit: int=None,
                     force: bool=False) -> bool:
        """
        Updates the cache for the `top` field if it fails any of the following criteria:
            - The cache is older the ttl
            - The number of items in the cache is lower than the feed_limit

        :param reddit: The signed-in PRAW instance
        :param feed_name: The name of the feed to update
        :param ttl: The ttl for this feed
        :param feed_limit: The minimum number of items required for this feed
        :param force: Whether to force a cache refresh
        :return: Returns `True` if the feed was refreshed, `False` otherwise
        """
        feed_name = feed_name.lower()  # Feed name is case insensitive
        feed = self.feeds[feed_name]

        # Checks every criteria for a cache to be invalid. If any fail, it prints the
        # reason for the refresh and then exits the clause. If it reaches 'else', then
        # the cache passes all criteria and the function returns without refreshing
        curr_time = time.time()
        if force:  # Force refresh
            print("Alert: Forcing cache refresh")
        elif (feed["time"] + ttl) < curr_time:  # Cache is expired
            print("Alert: {} cache expired".format(feed_name))
        elif feed_limit is None and not feed["none_feed_limit"]:  # Feed limit changed to None
            print("Alert: Feed limit for {} changed to 'None'".format(feed_name))
        elif not feed["none_feed_limit"] and len(feed["posts"]) < feed_limit:  # Cache has too few entries
            print("Alert: {} cache has fewer than {} entries".format(feed_name, feed_limit))
        else:
            print("Cache validated for {} feed".format(feed_name))
            return False  # Return false to indicate the feed was not refreshed

        # Get post generator
        subreddit = reddit.subreddit(self.subreddit)
        if feed_name == "hot":
            generator = subreddit.hot(limit=feed_limit)
        elif feed_name == "new":
            generator = subreddit.new(limit=feed_limit)
        else:
            generator = subreddit.top(limit=feed_limit)

        print("Getting {} posts...".format(feed_name))
        posts = [post for post in generator]          # Fetch all the posts
        self.__log_posts(posts, feed)                 # Log the new posts
        feed["time"] = curr_time                      # Record the time posts were fetched
        feed["none_feed_limit"] = feed_limit is None  # Set the none_feed_limit flag

        return True  # Return true to indicate the feed was refreshed

    def save(self, file_path: str) -> None:
        """
        Saves data to a cache file

        :param file_path: The path to the cache file
        """
        save_to_cache(file_path, self)

    def __log_posts(self, post_list: list, feed: dict):
        """
        Records a list of posts to a given feed. If post_list is None,
        the feed is emptied and no posts are added to all_posts

        :param post_list: The list of reddit posts to convert
        :param feed: The dictionary of the feed these posts belong to
        """
        feed["posts"] = []  # Blank out post list
        if post_list is None:  # Escape if list is None
            return
        post_dict = {}
        for post in post_list:
            feed["posts"].append(post.id)  # Add post ids to list
            post_dict[post.id] = {         # Add post info to cache
                "Score": post.score,
                "Title": post.title
            }
        self._all_posts.update(post_dict)  # Add posts to cumulative dictionary


def read_from_cache(file_path: str, sub_name: str) -> SearchCache:
    """
    Fetches a SearchCache object from cache

    :param file_path: The path to the cache file
    :param sub_name: The name of the subreddit whose results were cached
    :return: A SearchResult object from the cache. If there is an issue
             with the search, or the subreddit does not exist in the cache,
             the object will be empty
    """
    # Make sure cache file exists
    if not os.path.exists(file_path):
        print("Error: Could not find cache file")
        return SearchCache(sub_name)

    # Load cache data
    print("Checking cache...")
    with open(file_path, 'r') as fp:
        data = json.load(fp)

    # Validate cache
    if "version" not in data or data["version"] != CACHE_FORMAT_VERSION:
        print("Error: Unsupported cache version")
        return SearchCache(sub_name)
    if sub_name.lower() not in data["subreddits"]:
        print("Alert: Cache does not contain entry for /r/" + sub_name)
        return SearchCache(sub_name)

    # Load SearchCache from file
    sub_dict = data["subreddits"][sub_name]
    new_cache = SearchCache(sub_name)
    new_cache._all_posts = sub_dict["all_posts"]
    new_cache.feeds = sub_dict["feeds"]
    return new_cache


def save_to_cache(file_path: str, cache: SearchCache):
    """
    Saves a SearchResult to the cache

    :param file_path: The path to the cache file
    :param cache: The SearchCache object being stored
    """
    # Create cache file if one does not exist, otherwise read in existing data
    if not os.path.exists(file_path):
        print("Alert: Creating cache file...")
        with open(file_path, 'w') as fp:
            data = {
                "version": CACHE_FORMAT_VERSION,
                "subreddits": {}
            }
            json.dump(data, fp)
    else:
        with open(file_path, 'r') as fp:
            data = json.load(fp)

    data["subreddits"][cache.subreddit] = cache.to_dict()  # Update the subreddit's cache

    # Save results to file
    with open(file_path, 'w') as fp:
        json.dump(data, fp)
        print("Results saved to cache.")
