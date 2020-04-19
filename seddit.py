"""
NameCounter.py

@author Daniel Campman
@version 4/17/20
"""

# Libraries
import csv
import json
import os
import re as regex
import time
import praw


def ingest_csv(csv_path: str, delimiter: str=',') -> [[str]]:
    """

    :param csv_path: The path to the csv file
    :param delimiter: The character which divides cells in the file's csv encoding. Defaults to ','
    :return: [[str]] - A list of rows, each of which is a list of the cells in that row
    """
    contents = []
    with open(csv_path, newline='') as csv_file:
        reader = csv.reader(csv_file, delimiter=delimiter)
        for row in reader:
            contents.append(list(row))
    return contents


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
    return {key: value for (key, value) in dictionary.items() if (value < threshold) == invert}


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


def proper_noun_search(post_titles: list, filter_words: [str]=None):
    """
    Finds a count of every proper noun which appears in a list of
    titles more than a certain number of times

    :param post_titles: The list of post titles
    :param filter_words: A list of words to remove from the results list
    :returns: A list of (word: str, count: int) tuples
    """
    # Counter for all other proper nouns
    noun_count = {}

    # Find every proper noun in the tiles and log them
    for title in post_titles:
        results = regex.findall(r'\b[A-Z][\w.]*\b', title)
        if not results:
            continue

        for noun in results:
            if noun in noun_count:
                noun_count[noun] += 1
            else:
                noun_count[noun] = 1

    if filter_words:  # Filter common words
        return keys_ignored(noun_count, filter_words)
    return noun_count


def name_search(post_titles: list, names: list):
    """
    Searches the titles for instances of each name and returns
    the number of instances each name was seen

    :param post_titles: The list of post titles
    :param names: The name list. Each element is a list of strings that all count
                    as instances of the primary name, which is the first element
    :returns: A list of (name: str, count: int) tuples
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

    return name_count  # Sort the dictionary but value and key and return it


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
    plt.xticks(y_pos, categories, rotation=50)
    plt.title(graph_title)
    plt.ylabel("Occurrences")
    plt.tight_layout()
    plt.show()
