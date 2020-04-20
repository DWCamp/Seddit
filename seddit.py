"""
seddit.py

Executes a Seddit search

@author Daniel Campman
@version 4/19/20
"""

import argparse
import json

import praw
import utils
import searchCache

CONFIG_FILE = "config.json"

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
    with open(CONFIG_FILE, 'r') as fp:
        config = json.load(fp)

    parser = argparse.ArgumentParser(description=config["description"])

    parser.add_argument('subreddit', type=str, help='Defines the subreddit being searched.')

    parser.add_argument('-st',
                        '--search-terms',
                        type=str,
                        default=None,
                        help='The path to a CSV file containing a list of search terms.')

    parser.add_argument('-a',
                        '--all',
                        action="store_true",
                        help="Refreshes all enabled feeds and then performs a search on every post stored in the "
                             "subreddit's cache.")

    parser.add_argument('-c',
                        '--config',
                        type=str,
                        help="Supplies an additional configuration file for this execution. This file does not need to "
                             "define all required values. Any values that are defined will override the default "
                             "configuration.")

    parser.add_argument('--feeds',
                        nargs='*',
                        choices=['hot', 'new', 'top'],
                        help="Performs a refresh on a specific list of feeds instead of the feeds enabled in the "
                             "config file. If this list is empty, the regularly enabled feeds will be checked.")

    parser.add_argument('-f',
                        '--force',
                        action="store_true",
                        help="Forces a refresh of the subreddit's cache, regardless of age. Note: this will only "
                             "affect the feeds that would normally be searched. It will not affect disabled feeds "
                             "and if combined with the `--feeds` argument, it will only refresh a subset of feeds.")

    parser.add_argument('-g',
                        '--graph',
                        action="store_true",
                        help='After printing the results to the console, a bar graph is displayed. This requires '
                             'matplotlib.')

    parser.add_argument('-l',
                        '--feed-limit',
                        type=int,
                        default=None,
                        help='Sets the limit on the number of entries to return from each feed being searched on a '
                             'subreddit. This defaults to "None", which will fetch as many entries as the Reddit API '
                             'will allow (around 1000). This could take a while, so for shorter run times consider '
                             'reducing this value to 50 or 100.')

    parser.add_argument('-nf',
                        '--no-filter',
                        action="store_true",
                        help='Disables filtering of common words from general noun search.')

    parser.add_argument('-th',
                        '--threshold',
                        type=int,
                        default=None,
                        help='Sets the threshold for search, below which a result will be ignored. Defaults to {} '
                             'for general search and 0 when using a search term file'.format(config["threshold"]))

    parser.add_argument('--version',
                        action="version",
                        version=config["version"])

    args = parser.parse_args()

    # Overwrite default config values if present
    if args.config:
        with open(args.config, 'r') as fp:
            data = json.load(fp)
            for attr in data:
                if attr not in config:  # Throw error if file has foreign key
                    raise ValueError("Found unrecognized key `{}` in config file `{}`".format(attr, args.config))
                config[attr] = data[attr]

    # Set script values based on arguments and config values
    parse_all = args.all
    csv_path = args.search_terms
    feed_limit = args.feed_limit
    feeds = args.feeds if args.feeds else config["enabled_feeds"]
    force = True if args.force else False
    sub_name = args.subreddit
    word_filter_path = None if args.no_filter else config["filtered_words_file"]
    if args.threshold:  # If argument passed, use it for threshold
        threshold = args.threshold
    else:  # Otherwise set it to 0 for term search and DEFAULT THRESHOLD for proper noun search
        threshold = 0 if args.search_terms else config["threshold"]

    # ============================================================= Load data
    print("---------------------------------------")

    # Load from cache if cache is valid
    cache = searchCache.read_from_cache(config["cache_file_path"], sub_name)
    reddit = praw.Reddit(client_id=config["client_id"],
                         client_secret=config["client_secret"],
                         user_agent=config["user_agent"])

    # Refresh all feeds enabled in config.json
    updated = False  # Track whether any feed was updated
    if "hot" in feeds:
        updated_hot = cache.refresh_feed(reddit, "hot", ttl=config["cache_hot_ttl"], feed_limit=feed_limit, force=force)
        updated = updated or updated_hot
    if "new" in feeds:
        updated_new = cache.refresh_feed(reddit, "new", ttl=config["cache_new_ttl"], feed_limit=feed_limit, force=force)
        updated = updated or updated_new
    if "top" in feeds:
        updated_top = cache.refresh_feed(reddit, "top", ttl=config["cache_top_ttl"], feed_limit=feed_limit, force=force)
        updated = updated or updated_top

    if updated:
        cache.save(config["cache_file_path"])  # After refreshing, save cache
    else:
        print("Loaded values from cache")

    titles = cache.titles(feed_name_list=None if parse_all else feeds)  # Extract title list from cache

    # ========================================================= Perform search
    print("---------------------------------------")

    if csv_path:  # Run name search if csv path defined
        names = utils.ingest_csv(csv_path)  # Ingest name list
        result_dictionary = utils.name_search(titles, names)
    else:
        common_words = utils.ingest_csv(word_filter_path)[0] if word_filter_path else None
        result_dictionary = utils.proper_noun_search(titles, common_words)

    # Remove entries that don't meet a threshold
    if threshold is not None:
        # Filter non-notable entries
        result_dictionary = utils.filtered_dict(result_dictionary, threshold)

    sorted_tuples = utils.sorted_dict(result_dictionary)

    # ========================================================== Display Findings

    # Print rankings to stdout
    print("Popularity score:\n")
    for name, count in sorted_tuples:
        print("{} - {}".format(name, count))

    # Create bar chart
    sorted_tuples = sorted_tuples[:config["rank_cutoff"]]  # Trim results list

    # Present graph if requested
    if args.graph:
        utils.show_bar_chart(sorted_tuples, "Top {} Results for /r/{}".format(len(sorted_tuples), sub_name))
