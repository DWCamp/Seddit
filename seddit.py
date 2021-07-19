"""
seddit.py

Executes a Seddit search

@author Daniel Campman
@version 4/19/20
"""

import argparse
import json
from functools import reduce
from operator import add

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

    """ Optional term lists """

    term_arg_group = parser.add_argument_group()

    term_arg_group.add_argument('-st',
                                '--search-terms',
                                type=str,
                                default=config["search_terms"],
                                help='The path to a CSV file containing a list of search terms. Only these terms will '
                                     'be searched for, and title matching will be matched case insensitive.')

    term_arg_group.add_argument('-tg',
                                '--term-group',
                                type=str,
                                default=config["term-group"],
                                help='The path to a CSV file containing a list of search terms. Unlike --search-terms, '
                                     'this will still perform a regular proper noun search. However, this list '
                                     'specifies which words, if seen, should be considered synonyms (e.g. "Philly" and '
                                     '"Philadelphia"). Will also unify inconsistent capitalization for words with that '
                                     "spelling. Note: Only unifies groups after parsing words, so it won't find terms "
                                     "with multiple words.")

    """ Other arguments """

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
                             "configuration. By modifying the default values, this can also greatly simply your "
                             "command line arguments.")

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
                             'subreddit. This defaults to null, which will fetch as many entries as the Reddit API '
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

    """ Overwrite default config values if present """

    if args.config:
        with open(args.config, 'r') as fp:
            data = json.load(fp)
            for attr in data:
                if attr not in config:  # Throw error if file has foreign key
                    raise ValueError("Found unrecognized key `{}` in config file `{}`".format(attr, args.config))
                config[attr] = data[attr]

    """ Set script values based on arguments and config values """

    # `True` if word count should be performed on all posts in the subreddit, not just those in the feed
    parse_all = args.all
    # The path to the search terms csv file
    search_terms_path = args.search_terms
    # The path to the term group csv file
    term_group_path = args.term_group
    # The feed limit
    feed_limit = args.feed_limit
    # The list of feeds to scrape
    feeds = args.feeds if args.feeds else config["enabled_feeds"]
    # Whether to force each feed to update regardless of cache validity
    force = True if args.force else False
    # The name of the subreddit being scraped
    sub_name = args.subreddit
    # The path to the word filter file
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
        cache.save(config["cache_file_path"])  # If any feeds were refreshed, update cache
    else:
        print("Loaded values from cache")

    titles = cache.titles(feed_name_list=None if parse_all else feeds)  # Extract title list from cache

    # Remove any titles from the anaylsis that don't meet the regex criteria
    titles = utils.regex_trimed(titles, ignore=config["ignore_regex"], require=config["require_regex"])

    # ========================================================= Perform search
    print("---------------------------------------")

    if search_terms_path:  # Run name search if csv path defined
        names = utils.ingest_csv(search_terms_path)  # Ingest name list
        result_dictionary = utils.name_search(titles, names)
    else:  # If no search terms provided, run search for proper nouns
        """ Read term groups from CSV """
        term_groups = utils.ingest_csv(term_group_path) if term_group_path else None

        """ Read common words from CSV """
        common_words = utils.ingest_csv(word_filter_path) if word_filter_path else None
        common_words = reduce(add, common_words)  # Flatten 2D CSV to single list

        """ Perform search """
        result_dictionary = utils.proper_noun_search(titles, term_groups, common_words)

    """ Remove words that don't meet the frequency cutoff """

    if threshold is not None:
        # Filter non-notable entries
        result_dictionary = utils.filtered_dict(result_dictionary, threshold)

    sorted_tuples = utils.sorted_dict(result_dictionary)

    # ========================================================== Display Findings

    """ Print rankings to stdout """

    print("Popularity score:\n")
    for name, count in sorted_tuples:
        print("{} - {}".format(name, count))

    """ Create bar chart """

    sorted_tuples = sorted_tuples[:config["rank_cutoff"]]  # Trim results list

    """ Present graph if requested """

    if args.graph:
        utils.show_bar_chart(sorted_tuples, "Top {} Results for /r/{}".format(len(sorted_tuples), sub_name))
