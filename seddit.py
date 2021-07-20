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
import os
from functools import reduce
from operator import add

import praw

import data
import config
import utils
from PostCache import PostCache


# ============================================================================= Arguments


parser = argparse.ArgumentParser(description=config.description)

parser.add_argument('subreddit',
                    type=str,
                    help='Defines the subreddit being searched.')

""" Optional term lists """

term_arg_group = parser.add_argument_group()

term_arg_group.add_argument('-st',
                            '--search-terms',
                            type=str,
                            default=config.search_terms_file,
                            help='The path to a CSV file containing a list of search terms. Only these terms will '
                                 'be searched for, and title matching will be matched case insensitive. Regex '
                                 'filtering will not be applied, nor will the frequency threshold')

term_arg_group.add_argument('-tg',
                            '--term-group',
                            type=str,
                            default=config.term_group_file,
                            help='The path to a CSV file containing a list of search terms. This list '
                                 'specifies which words, if seen, should be considered synonyms (e.g. '
                                 '"Philly" and "Philadelphia"). '
                                 "Note: Only unifies groups after parsing words. It won't find terms "
                                 "with multiple words.")

""" Other arguments """

parser.add_argument('-f',
                    '--force',
                    action="store_true",
                    help="Force a refresh of the subreddit's cache, regardless of age")

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

parser.add_argument('-s',
                    '--scoring',
                    type=str,
                    choices=['count', 'score'],
                    default='count',
                    help="How words are scored. The default, 'count', counts the number of posts that each word "
                         "appears, finding the most common word. 'score' adds up the scores of every post "
                         "containing the word, finding the 'most liked' word.")

parser.add_argument('-th',
                    '--threshold',
                    type=int,
                    default=None,
                    help=f'The threshold for search, below which a result will be ignored. '
                         f'Defaults to {config.threshold} for general search and 0 when using a search term file')

parser.add_argument('--version',
                    action="version",
                    version=f"Seddit {config.version} - Cache file v{PostCache.CACHE_FORMAT_VERSION}")

parser.add_argument('-wf',
                    '--word-filter',
                    type=str,
                    nargs='*',
                    default=[config.filtered_words_file],
                    help="The path to a CSV file listing words to exclude from results. "
                         "If more than one path is listed, the words in all files will be filtered. "
                         "If not specified, the file specified in config.py will be used. "
                         "To disable filtering, leave this field blank")


# ============================================================================= Script


def main() -> None:
    """
    Main method of Seddit. Processes arguments
    """

    # ========================================================= Read arguments

    """ Set script values based on arguments and config values """

    args = parser.parse_args()

    # Whether to force each feed to update regardless of cache validity
    force = True if args.force else False
    # The path to the term group csv file
    search_term_path = args.search_terms
    # The name of the subreddit being scraped
    sub_name = args.subreddit
    # The path to the term group csv file
    term_group_path = args.term_group

    """ Read frequency threshold """
    threshold = args.threshold if args.threshold else config.threshold

    """ Read search terms from CSV """
    if search_term_path:
        search_terms = utils.ingest_csv(search_term_path)
        search_terms = reduce(add, search_terms)
    else:
        search_terms = None

    """ Read term groups from CSV """
    terms_list = utils.ingest_csv(term_group_path) if term_group_path else None
    term_group = data.TermGroup(terms_list)

    """ Read in word filter CSV files and flatten to 1D list """
    word_set = set()
    for path in args.word_filter:
        word_array = utils.ingest_csv(path)
        # Add every word in file to set
        for row in word_array:
            for word in row:
                word_set.add(word)

    filtered_words = list(word_set) if word_set else None

    # ========================================================= Load Data

    # Create PRAW reddit object
    reddit = praw.Reddit(client_id=config.client_id,
                         client_secret=config.client_secret,
                         user_agent=config.user_agent)

    # Load cache from file
    cache_path = f"{config.cache_dir_path}{os.path.sep}{sub_name.lower()}.json"
    cache = PostCache(sub_name, cache_path, reddit)

    # Refresh cache
    if cache.refresh(force=force, limit=args.feed_limit):
        cache.save()

    # ========================================================= Perform search

    scoring = args.scoring.lower()
    if scoring == "count":
        method = PostCache.COUNT
    elif scoring == "score":
        method = PostCache.SCORE
    else:
        raise ValueError(f"Unrecognized scoring method '{scoring}'")

    result_dict = cache.count_terms(searched_words=search_terms,
                                    term_group=term_group,
                                    filtered_words=filtered_words,
                                    method=method)

    """ Filter results """

    # Filter low-frequency words
    if threshold is not None:
        result_dict = utils.filtered_dict(result_dict, threshold)

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

    if args.graph:
        sorted_tuples = sorted_tuples[:config.rank_cutoff]  # Trim results list
        utils.show_bar_chart(sorted_tuples, "Top {} Results for /r/{}".format(len(sorted_tuples), sub_name))


if __name__ == "__main__":
    main()
