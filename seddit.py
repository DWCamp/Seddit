"""
NameCounter.py

@author Daniel Campman
@version 4/17/20
"""

# Libraries
import argparse
import csv
import json
import math
import os
import re as regex
import time
import praw

# Config values
from config import *

# ===== Script constants

DESCRIPTION = "A Python Script for counting the number of instances " \
              "a collection of terms get said on different subreddits"

# The 100 most common words in the english language.
# These will be ignored in the notable noun search
COMMON_NOUNS = ["a", "about", "all", "also", "and", "as", "at", "be", "because", "but", "by", "can", "come",
                "could", "day", "do", "even", "find", "first", "for", "from", "get", "give", "go", "have",
                "he", "her", "here", "him", "his", "how", "I", "if", "in", "into", "it", "its", "just", "know",
                "like", "look", "make", "man", "many", "me", "more", "my", "new", "no", "not", "now", "of", "on",
                "one", "only", "or", "other", "our", "out", "people", "say", "see", "she", "so", "some", "take",
                "tell", "than", "that", "the", "their", "them", "then", "there", "these", "they", "thing",
                "think", "this", "those", "time", "to", "two", "up", "use", "very", "want", "way", "we", "well",
                "what", "when", "which", "who", "will", "with", "would", "year", "you", "your"]


def scrape_subreddit(subreddit: praw.reddit, feed_limit: int):
    """
    Scrapes the defined subreddit for the first N posts on the top
    and hot feeds and returns a list of every title

    :param subreddit: The PRAW subreddit object to scrape
    :param feed_limit: The number of posts to scrape off the top and
                        hot feeds. Set to 'None' for maximum value
    :return: The list of titles
    """
    print("Scraping /r/{}...".format(subreddit.display_name))
    titles_set = set()

    # Scrape top posts of all time
    print("Getting top posts...")
    for submission in subreddit.top(limit=feed_limit):
        titles_set.add(submission.title)

    # Scrape hot posts
    print("Getting hot posts...")
    for submission in subreddit.hot(limit=feed_limit):
        titles_set.add(submission.title)

    return list(titles_set)


def filtered_dict(dictionary: dict, threshold, invert: bool = False):
    """
    Removes all keys from a dictionary whose value is less than a given threshold

    :param dictionary: The dictionary to filter
    :param threshold: The threshold below which to remove elements
    :param invert: Whether to invert the threshold (remove elements above threshold)
    :return: The filtered dictionary
    """
    if invert:
        return {key: value for (key, value) in dictionary.items() if value < threshold}
    return {key: value for (key, value) in dictionary.items() if value >= threshold}


def keys_ignored(dictionary: dict, remove: [str]):
    """
    Performs an in-place removal of a list of string keys from
    a given dictionary. This check is case-insensitive

    :param dictionary: The dictionary to filter
    :param remove: The keys to remove
    :return: A copy of the dictionary with all items removed
            whose key was in the list
    """
    remove = [key.lower() for key in remove]  # Make sure keys to remove are all lower
    return {key: value for (key, value) in dictionary.items() if key.lower() not in remove}


def sorted_dict(dictionary, reverse=True):
    """
    Returns the list of (key, value) tuples in a dictionary, sorted first
    by value and then by key
    :param dictionary: The dictionary to sort
    :param reverse: Whether to reverse the sort
    :return: A sorted list of (key, value) tuples
    """
    return sorted(dictionary.items(), reverse=reverse, key=lambda x: (x[1], x[0]))


def proper_noun_search(post_titles: list, threshold: int, name_list: list, filter_common: bool = True):
    """
    Finds a count of every proper noun which appears in a list of
    titles more than a certain number of times

    :param post_titles: The list of post titles
    :param threshold: Nouns which appear fewer than this many times will be
                      filtered from the results
    :param name_list: The list of names
    :param filter_common: Whether to filter common English words from the results
                            Defaults to `True`
    :returns: A list of (word: str, count: int) tuples. These tuples are sorted
                by count and then alphabetically by word
    """
    # Counter for all other proper nouns
    noun_count = {}

    # Find every proper noun in the tiles and log them
    for title in post_titles:
        results = regex.findall(r'\b[A-Z][\w]*\b', title)
        if not results:
            continue

        for noun in results:
            if noun in noun_count:
                noun_count[noun] += 1
            elif names and not any(noun in sublist for sublist in names):  # Don't record nouns already marked as names
                noun_count[noun] = 1

    # ======== Filter

    # Set notable threshold if undefined
    if threshold is not None:
        # Filter non-notable entries
        noun_count = filtered_dict(noun_count, threshold)

    if filter_common:  # Filter common words
        noun_count = keys_ignored(noun_count, COMMON_NOUNS)

    return sorted_dict(noun_count)  # Sort the dictionary but value and key


def name_search(post_titles: list, names: list):
    """
    Searches the titles for instances of each name and returns
    the number of instances each name was seen

    :param post_titles: The list of post titles
    :param names: The name list. Each element is a list of strings that all count
                    as instances of the primary name, which is the first element
    :returns: A list of (name: str, count: int) tuples. These tuples are sorted
                by count and then alphabetically by name
    """

    # Create the counter table
    name_count = {}
    for character in names:
        name_count[character[0]] = 0

    # Search for every character
    for name_list in names:
        name_key = name_list[0]

        # Compile character's nicknames names into a `(<A>|<B>|...)` regex string
        escaped_list = [regex.escape(name) for name in name_list]
        name_reg_str = '\\b({})\\b'.format("|".join(escaped_list))

        # Search every title for instance of character name
        for title in post_titles:
            if regex.search(name_reg_str, title, regex.IGNORECASE):
                name_count[name_key] += 1

    name_count = filtered_dict(name_count, 1)  # Filter names that weren't seen
    return sorted_dict(name_count)  # Sort the dictionary but value and key and return it


def read_from_cache(filepath: str, subreddit: str, limit_setting, ttl: int = 3600):
    """
    Fetches the list of titles from the cache.

    :param filepath: The path to the cache file
    :param subreddit: The name of the subreddit whose results were cached
                        This is always stored in lowercase
    :param limit_setting: The feed limit setting for this search
    :param ttl: The number of seconds before the cache is invalidated.
                If `None`, cache is never invalidated. Defaults to 1 hour
    :return: The list of titles from cache. If cache is invalid (expired,
                doesn't exist) `None` is returned
    """
    if not os.path.exists(filepath):
        print("Error: Could not find cache file")
        return None

    print("Checking cache...")
    with open(filepath, 'r') as fp:
        data = json.load(fp)

    cache_key = "{}:{}".format(subreddit.lower(), limit_setting)

    if cache_key not in data:
        print("Alert: Cache empty")
        return None

    data = data[cache_key]  # Isolate search settings

    # Check age of cache
    cache_time = data["time"]
    curr_time = time.time()
    if ttl is None or (cache_time + ttl) >= curr_time:
        print("Cache loaded.")
        return data["titles"]
    print("Alert: Cache expired")
    return None


def save_to_cache(filepath: str, subreddit: str, limit_setting, titlelist: list):
    """
    Saves a list of titles to the cache

    :param filepath: The path to the cache file
    :param subreddit: The subreddit being cached. This is always stored in lowercase
    :param limit_setting: The feed limit setting for this search
    :param titlelist: The list of titles
    """
    # Create cache file if one does not exist
    if not os.path.exists(filepath):
        print("Alert: Creating cache file...")
        with open(filepath, 'w') as fp:
            data = {}
            json.dump(data, fp)
    else:
        with open(filepath, 'r') as fp:
            data = json.load(fp)

    # Make sure path exists

    cache_key = "{}:{}".format(subreddit.lower(), limit_setting)
    if cache_key not in data:
        data[cache_key] = {}

    data[cache_key] = {
        "titles": titlelist,
        "time": time.time()
    }

    # Save results to cache
    with open(filepath, 'w') as fp:
        json.dump(data, fp)
        print("Results saved to cache.")


def show_bar_chart(data: list, graph_title: str):
    """
    Displays a bar chart containing the data in a list of tuples

    Note: this function requires matplotlib

    :param data: The list of sorted (category, value) tuples
    :param graph_title: The title of the graph
    """

    # Check that matplotlib can be is imported
    try:
        import matplotlib.pyplot as plt
    except ImportError as ie:
        print("Error: Failed to import matplotlib. Cannot display graph")
        print(ie)
        return

    # Turn tuples into lists
    categories = [category for category, value in data]
    values = [value for category, value in data]

    # Create bar chart
    y_pos = [*range(len(categories))]
    plt.bar(y_pos, values, align='center')
    plt.xticks(y_pos, categories, rotation=40)
    plt.title(graph_title)
    plt.ylabel("Occurrences")
    plt.show()


if __name__ == "__main__":
    """
    Name counter

    Counts the instances of for several names in the top and hot feeds 
    for a subreddit then ranks them in terms of popularity

    Additionally finds all proper nouns that are not in the name list
    that occur above a certain frequency to indicate a popular term that 
    might be missing from your search list

    After this popularity data is collected, it is printed to stdout and
    the top ranking names are displayed as a bar chart
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('namefile', type=str, help='The path to a CSV file containing the search terms')
    parser.add_argument('subreddit', type=str, help='The subreddit being searched')
    parser.add_argument('-bg', '--graph', help='Display a bar graph of the results', action="store_true")
    parser.add_argument('-cf', type=str, default=CACHE_FILE_PATH, help='The path to a custom cache file')
    parser.add_argument('-pn',
                        '--noun-search',
                        help='Print a list of common, non-name proper nouns in the search results',
                        action="store_true")
    parser.add_argument('-fl', '--feed-limit', type=int, default=None, help='Sets the fetch limit for each feed')
    parser.add_argument('-t',
                        '--threshold',
                        type=int,
                        default=None,
                        help='Sets the threshold for proper noun search. Defaults to a fraction of the feed limit')
    parser.add_argument('-ttl',
                        type=int,
                        default=3600,
                        help='The age in seconds at which a cache entry expires in seconds. Defaults to 3600 (1 hour). '
                             'Pass a negative number to make cache never expire. Pass 0 to ignore cache')
    args = parser.parse_args()

    csv_path = args.namefile
    sub_name = args.subreddit
    cache_path = args.cf
    feed_limit = args.feed_limit
    cache_ttl = args.ttl if args.ttl >= 0 else None
    # Set notability threshold
    if args.threshold:
        notability_threshold = args.threshold
    else:
        notability_threshold = 8 if feed_limit is None else math.log(feed_limit)

    # ============================================================= Load data
    print("\n---------------------------------------\n")

    # Load from cache if cache is valid
    titles = read_from_cache(cache_path, sub_name, feed_limit, ttl=cache_ttl)
    if titles is None:
        # Scrape from reddit
        print("Scraping from Reddit...")
        reddit = praw.Reddit(client_id=CLIENT_ID,
                             client_secret=CLIENT_SECRET,
                             user_agent=USER_AGENT)
        subreddit = reddit.subreddit(sub_name)
        titles = scrape_subreddit(subreddit, feed_limit)
        save_to_cache(cache_path, sub_name, feed_limit, titles)

    # ========================================================= Name Search
    print("\n---------------------------------------\n")

    names = []

    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            names.append(list(row))

    sorted_tuples = name_search(titles, names)
    # Print rankings to stdout
    print("Name rankings:\n")
    for name, count in sorted_tuples:
        print("{} - {}".format(name, count))

    # ======================================================== Proper noun search

    if args.noun_search:
        print("\n---------------------------------------\n")

        noun_tuples = proper_noun_search(titles, threshold=notability_threshold, name_list=names)

        # Print nouns
        print("Notable nouns:\n")
        for noun, count in noun_tuples:
            print("{} - {}".format(noun, count))

        if not noun_tuples:  # Print placeholder if there were no nouns
            print("  None.")

    # ========================================================== Display Findings
    print("\n---------------------------------------\n")

    # Create bar chart
    sorted_tuples = sorted_tuples[:RANK_THRESHOLD]  # Trim results list

    # Present graph if requested
    if args.graph:
        show_bar_chart(sorted_tuples, "Character Mentions on /r/" + sub_name)
