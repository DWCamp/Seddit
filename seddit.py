"""
A Python Script for counting the number of instances a collection of terms get used in post titles
on a given subreddit.

It can either search through all words to find the most common or can take
in a text file containing a list of specific terms to look for and show their frequencies.
As it performs each search, it stores every post it sees in a cache file, allowing it over time
to amass a database of posts on a subreddit.

@author Daniel Campman
@version 7/19/20
"""

import argparse
from configparser import ConfigParser
import os

import praw

import data
import utils
from PostCache import PostCache

DEFAULT_CONFIG_FILE = "config\\default.ini"
VERSION = "v0.6.0"
DESCRIPTION = f"Seddit {VERSION} - A Python Script for counting the number of " \
              f"instances a collection of terms get said on different subreddits"


# ============================================================================= Script

def load_config(path: str, child_files: [str] = None) -> ConfigParser:
    """
    Loads a configuration file and returns the ConfigParser containing the field values
    This Config parser accepts null fields. If the configuration file contains an
    `extends` field, those values will be used as the values for any fields not
    defined by the current file. If this file extends one of its child files, an
    inheritance loop will be formed. To avoid this, a list of children is kept.
    If a file extends one of its children, the ConfigParser will be returned with
    only the fields defined within the file.

    :param path: The path of the configuration file to load
    :param child_files: A list of the files which inherit from this file. This file
        is not allowed to extend one of these files.

    :return: A ConfigParser loaded with the settings defined by the configuration file
    """
    # Add own path to child files
    if child_files is None:
        child_files = []
    child_files.append(path)

    # Load config values
    config = ConfigParser(allow_no_value=True)
    config.read(path)

    # Check for inherited values
    if config["DEFAULT"].get("extends") and config["DEFAULT"]["extends"] not in child_files:
        child_config = load_config(config["DEFAULT"]["extends"], child_files)
        child_config.read_dict(config)  # Override parent values
        return child_config
    return config


def load_params() -> argparse.Namespace:
    """
    Reads the parameters from the command line and returns

    :return: An argparse.Namespace containing the command line arguments
    """

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument('subreddit',
                        type=str,
                        help='Defines the subreddit being searched.')

    """ Optional term lists """

    term_arg_group = parser.add_argument_group()

    term_arg_group.add_argument('-st',
                                '--search-terms',
                                help='The path to a CSV file containing a list of search terms. Only these terms will '
                                     'be searched for, and title matching will be matched case insensitive. Regex '
                                     'filtering will not be applied, nor will the frequency threshold')
    term_arg_group.add_argument('-tg',
                                '--term-groups',
                                help='The path to a CSV file containing a list of search terms. This list '
                                     'specifies which words, if seen, should be considered synonyms (e.g. '
                                     '"Philly" and "Philadelphia"). '
                                     "Note: Only unifies groups after parsing words. It won't find terms "
                                     "with multiple words.")

    """ Other arguments """

    parser.add_argument('-c',
                        '--config',
                        help="Force a refresh of the subreddit's cache, regardless of age")
    parser.add_argument('-f',
                        '--force',
                        action="store_true",
                        help="Force a refresh of the subreddit's cache, regardless of age")
    parser.add_argument('-g',
                        '--graph',
                        action="store_true",
                        help='Displays a bar graph of the most popular terms.')
    parser.add_argument('-l',
                        '--feed-limit',
                        type=int,
                        help='Sets the limit on the number of entries to return from each feed being searched on a '
                             'subreddit. If null or 0, it will fetch as many entries as the Reddit API will allow '
                             '(around 1000). This could take a while, so for shorter run times consider reducing this '
                             'value to 50 or 100.')
    parser.add_argument('-s',
                        '--scoring',
                        choices=['count', 'score'],
                        default='count',
                        help="How words are scored. The default, 'count', counts the number of posts that each word "
                             "appears, finding the most common word. 'score' adds up the scores of every post "
                             "containing the word, finding the 'most liked' word.")
    parser.add_argument('-th',
                        '--threshold',
                        type=int,
                        help=f'Discards results with a score below this value. Does not apply to search terms.')
    parser.add_argument('--version',
                        action="version",
                        version=f"Seddit {VERSION}")
    parser.add_argument('-wf',
                        '--word-filter',
                        nargs='*',
                        help="The path to a CSV file listing words to exclude from results. "
                             "If more than one path is listed, the words in all files will be filtered. "
                             "If not specified, the file specified in the default (or provided, if applicable) "
                             "configuration file will be used. "
                             "To disable filtering, use this flag with no value.")

    return parser.parse_args()


def main() -> None:
    """
    Main method of Seddit. Processes arguments, performs search, and returns the result
    """

    # ========================================================= Read input

    # Load config file
    config = load_config(DEFAULT_CONFIG_FILE)

    # Read command line arguments
    args = load_params()

    # Load config file from CLI argument
    if args.config:
        config.read(args.config)

    """ Convert arguments to local variables """

    # The name of the subreddit being scraped
    sub_name = args.subreddit

    # Whether to force each feed to update regardless of cache validity
    force = True if args.force else config["DEFAULT"].getboolean("force", fallback=False)
    # Whether to display a graph of the most popular terms
    show_graph = True if args.graph else config["DEFAULT"].getboolean("show_graph", fallback=False)
    # The post limit for refreshing feeds
    try:
        feed_limit = args.feed_limit if args.feed_limit else config["DEFAULT"].getint("feed_limit")
        if feed_limit < 0:  # Change non-positive feed limit to "None"
            feed_limit = None
    except TypeError:
        feed_limit = None  # Convert any non-number limit to None
    # Method for scoring
    scoring = args.scoring.lower()
    if scoring == "count":
        method = PostCache.COUNT
    elif scoring == "score":
        method = PostCache.SCORE
    else:
        raise ValueError(f"Unrecognized scoring method '{scoring}'")
    # Read frequency threshold
    threshold = args.threshold if args.threshold else config.getint("Filters", "threshold")

    """ Ingest CSV files """

    # Read search terms from CSV
    search_term_path = args.search_terms if args.search_terms else config["Files"]["search_terms"]
    search_terms = utils.ingest_csv(search_term_path) if search_term_path else None

    # Read term groups from CSV
    term_groups_path = args.term_groups if args.term_groups else config["Files"]["term_groups"]
    terms_list = utils.ingest_csv(term_groups_path) if term_groups_path else None
    term_groups = data.TermGroups(terms_list)

    # Read in word filter CSV files and flatten to 1D list
    word_set = set()
    if args.word_filter:
        word_filters = args.word_filter
    elif config["Files"].get("word_filters"):
        word_filters = config["Files"].get("word_filters").split(" ")
    else:
        word_filters = []

    for path in word_filters:
        word_array = utils.ingest_csv(path)
        # Add every word in file to set
        for row in word_array:
            for word in row:
                word_set.add(word.strip())

    filtered_words = list(word_set) if word_set else None

    # ========================================================= Load Data

    # Create PRAW reddit object
    reddit = praw.Reddit(client_id=config["PRAW"]["client_id"],
                         client_secret=config["PRAW"]["client_secret"],
                         user_agent=config["PRAW"]["user_agent"])

    # Load cache from file
    cache_path = f"{config['Cache']['dir_path']}{os.path.sep}{sub_name.lower()}.json"
    cache = PostCache(sub_name,
                      cache_path,
                      reddit,
                      config["Cache"].getint("ttl_hot"),
                      config["Cache"].getint("ttl_new"),
                      config["Cache"].getint("ttl_top"))

    # Refresh cache
    if cache.refresh(force=force, limit=feed_limit):
        cache.save()

    # ========================================================= Perform search

    # Perform search term result if provided, otherwise perform word count
    if search_terms:
        result_dict = cache.search_terms(search_terms,
                                         ignore_title_regex=config["Regex"]["ignore_title"],
                                         require_title_regex=config["Regex"]["require_title"],
                                         method=method)
    else:
        result_dict = cache.count_words(term_group=term_groups,
                                        ignore_title_regex=config["Regex"]["ignore_title"],
                                        require_title_regex=config["Regex"]["require_title"],
                                        method=method)

    """ Filter results """

    # Remove filtered words
    if filtered_words:
        utils.list_filter_dict(result_dict, filtered_words)

    # Filter low-frequency words if not using search terms
    if threshold is not None and not search_terms:
        result_dict = utils.value_filter_dict(result_dict, threshold)

    # Filter words by regex
    if config["Regex"]["require_word"] or config["Regex"]["ignore_word"]:
        utils.regex_filter_dict(result_dict,
                                require=config["Regex"]["require_word"],
                                remove=config["Regex"]["ignore_word"])

    """ Sort words by frequency """

    sorted_tuples = utils.sorted_dict(result_dict)

    # ========================================================== Display Findings

    """ Print rankings to stdout """

    print("===============================================")
    print("================  RESULTS  ====================")
    print("===============================================\n")

    print("Popularity score:\n")
    num = 1
    for name, count in sorted_tuples:
        print(f"{num}) {name} - {count}")
        num += 1

    """ Present graph if requested """

    if show_graph:
        sorted_tuples = sorted_tuples[:config["Filters"].getint("rank_cutoff")]  # Trim results list
        utils.show_bar_chart(sorted_tuples, "Top {} Results for /r/{}".format(len(sorted_tuples), sub_name))


if __name__ == "__main__":
    main()
