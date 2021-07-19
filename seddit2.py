"""
seddit.py

Executes a Seddit search

@author Daniel Campman
@version 4/19/20
"""

import json
import os

import praw

import v2

CONFIG_FILE = "config.py"


def main():
    # Read config file
    with open(CONFIG_FILE, 'r') as fp:
        config = json.load(fp)

    # Create PRAW reddit object
    reddit = praw.Reddit(client_id=config["client_id"],
                         client_secret=config["client_secret"],
                         user_agent=config["user_agent"])
    subreddit = "Rainbow6"

    cache_path = f"{config['cache_dir_path']}{os.path.sep}{subreddit.lower()}.json"

    cache = v2.PostCache(subreddit, cache_path, reddit)
    cache.refresh()
    cache.save()

    print("done.")


if __name__ == "__main__":
    main()
