from seddit import *

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
