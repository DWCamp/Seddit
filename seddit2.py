"""
seddit.py

Executes a Seddit search

@author Daniel Campman
@version 4/19/20
"""

import argparse
import os

import praw

import v2
import config
import utils
from PostCache import PostCache


# ============================================================================= Arguments


parser = argparse.ArgumentParser(description=config.description)

parser.add_argument('subreddit',
                    type=str,
                    default="",
                    help='Defines the subreddit being searched.')

""" Optional term lists """

term_arg_group = parser.add_argument_group()

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
    # The name of the subreddit being scraped
    sub_name = args.subreddit
    # The path to the term group csv file
    term_group_path = args.term_group

    """ Read frequency threshold """
    threshold = args.threshold if args.threshold else config.threshold

    """ Read term groups from CSV """
    terms_list = utils.ingest_csv(term_group_path) if term_group_path else None
    term_group = v2.TermGroup(terms_list)

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
    if cache.refresh(force=force):
        cache.save()

    # ========================================================= Perform search

    scoring = args.scoring.lower()
    if scoring == "count":
        method = PostCache.COUNT
    elif scoring == "score":
        method = PostCache.SCORE
    else:
        raise ValueError(f"Unrecognized scoring method '{scoring}'")

    result_dict = cache.count_terms(term_group=term_group, filtered_words=filtered_words, method=method)

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
    for name, count in sorted_tuples:
        print("{} - {}".format(name, count))

    """ Present graph if requested """

    if args.graph:
        sorted_tuples = sorted_tuples[:config.rank_cutoff]  # Trim results list
        utils.show_bar_chart(sorted_tuples, "Top {} Results for /r/{}".format(len(sorted_tuples), sub_name))


if __name__ == "__main__":
    main()
