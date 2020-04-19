import argparse
import math
import csv
import praw

from config import *
import seddit

DESCRIPTION = "A Python Script for counting the number of instances " \
              "a collection of terms get said on different subreddits"

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
    parser.add_argument('subreddit', type=str, help='The subreddit being searched')
    parser.add_argument('-n',
                        '--namefile',
                        type=str,
                        default=None,
                        help='The path to a CSV file containing a list of search terms')
    parser.add_argument('-g', '--graph', help='Display a bar graph of the results', action="store_true")
    parser.add_argument('-cf', type=str, default=CACHE_FILE_PATH, help='The path to a custom cache file')
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
        threshold = args.threshold
    else:
        threshold = 8 if feed_limit is None else math.log(feed_limit)

    # ============================================================= Load data
    print("\n---------------------------------------\n")

    # Load from cache if cache is valid
    titles = seddit.read_from_cache(cache_path, sub_name, feed_limit, ttl=cache_ttl)
    if titles is None:
        # Scrape from reddit
        print("Scraping from Reddit...")
        reddit = praw.Reddit(client_id=CLIENT_ID,
                             client_secret=CLIENT_SECRET,
                             user_agent=USER_AGENT)
        subreddit = reddit.subreddit(sub_name)
        titles = seddit.scrape_subreddit(subreddit, feed_limit)
        seddit.save_to_cache(cache_path, sub_name, feed_limit, titles)

    # ========================================================= Perform search
    print("\n---------------------------------------\n")

    if csv_path:  # Run name search if csv path defined
        # Ingest name list
        names = []
        with open(csv_path, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            for row in reader:
                names.append(list(row))

        result_dictionary = seddit.name_search(titles, names)
    else:
        result_dictionary = seddit.proper_noun_search(titles)

    # Remove entries that don't meet a threshold
    if threshold is not None:
        # Filter non-notable entries
        result_dictionary = seddit.filtered_dict(result_dictionary, threshold)

    sorted_tuples = seddit.sorted_dict(result_dictionary)

    # ========================================================== Display Findings

    # Print rankings to stdout
    print("Popularity score:\n")
    for name, count in sorted_tuples:
        print("{} - {}".format(name, count))

    # Create bar chart
    sorted_tuples = sorted_tuples[:RANK_THRESHOLD]  # Trim results list

    # Present graph if requested
    if args.graph:
        seddit.show_bar_chart(sorted_tuples, "Character Mentions on /r/" + sub_name)
