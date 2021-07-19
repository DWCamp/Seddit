"""
utils.py

Provides a number of functions for scraping subreddits
and determining the frequency of words used in the titles
of their posts.

@author Daniel Campman
@version 4/19/20
"""

# Libraries
import csv
import re


def ingest_csv(csv_path: str, delimiter: str=',', strip_spaces: bool=True) -> [[str]]:
    """
    Takes in a CSV file and returns a 2D list of the contents

    :param csv_path: The path to the csv file
    :param delimiter: The character which divides cells in the file's csv encoding. Defaults to ','
    :param strip_spaces: Remove any spaces from the ends of each cell. Defaults to `True`
    :return: [[str]] - A list of rows, each of which is a list of the cells in that row
    """
    contents = []
    with open(csv_path, newline='') as csv_file:
        reader = csv.reader(csv_file, delimiter=delimiter)
        for row in reader:
            if strip_spaces:
                contents.append([cell.strip() for cell in row])
            else:
                contents.append(list(row))
    return contents


def filtered_dict(dictionary: dict, threshold, invert: bool = False):
    """
    Removes all keys from a dictionary whose value is less than a given threshold

    :param dictionary: The dictionary to filter
    :param threshold: The threshold below which to remove elements
    :param invert: Whether to invert the threshold (remove elements above threshold)
    :return: The filtered dictionary
    """
    return {key: value for (key, value) in dictionary.items() if (value < threshold) == invert}


def keys_ignored(dictionary: dict, remove: [str]) -> None:
    """
    Performs an in-place removal of a list of string keys from
    a given dictionary. This check is case-insensitive

    :param dictionary: The dictionary to filter
    :param remove: The keys to remove
    """
    remove = [key.lower() for key in remove]  # Make sure keys to remove are all lower
    for word in remove:
        if word in dictionary:
            del dictionary[word]


def sorted_dict(dictionary, reverse=True):
    """
    Returns the list of (key, value) tuples in a dictionary, sorted first
    by value and then by key
    :param dictionary: The dictionary to sort
    :param reverse: Whether to reverse the sort
    :return: A sorted list of (key, value) tuples
    """
    return sorted(dictionary.items(), reverse=reverse, key=lambda x: (x[1], x[0]))


def proper_noun_search(post_titles: list, term_groups=None, filter_words: [str]=None):
    """
    Finds a count of every proper noun which appears in a list of
    titles more than a certain number of times

    :param post_titles: The list of post titles
    :param term_groups: A list of string lists, each defining a group of words that should be considered synonyms
    :param filter_words: A list of words to remove from the results list
    :returns: A list of (word: str, count: int) tuples
    """
    # Counter for all other proper nouns
    noun_count = {}
    term_groups = term_groups if term_groups else []

    # Find every proper noun in the tiles and log them
    for title in post_titles:
        results = re.findall(r'\b[A-Z][\w.]*\b', title)
        if not results:
            continue

        for noun in results:
            if noun in noun_count:
                noun_count[noun] += 1
            else:
                noun_count[noun] = 1

    # Merge the term groups
    for group in term_groups:
        group_name = group[0]
        if group_name not in noun_count:  # Add group name to noun count if not there already
            noun_count[group_name] = 0
        for term in group:  # Search the noun list for every term in the group
            matching_keys = []
            for key in noun_count:  # Check every noun against the given term
                if key.lower() == term.lower():  # If a match, flag the key
                    matching_keys.append(key)
            for key in matching_keys:  # Merge every match into the main entry
                if key != group_name:  # Don't merge if the key is the group name
                    noun_count[group_name] += noun_count[key]
                    del noun_count[key]

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
        escaped_list = [re.escape(name) for name in name_list]
        name_reg_str = '\\b({})\\b'.format("|".join(escaped_list))

        # Search every title for instance of character name
        for title in post_titles:
            if re.search(name_reg_str, title, re.IGNORECASE):
                name_count[name_key] += 1

    return name_count  # Sort the dictionary but value and key and return it


def regex_trimed(string_list: [str], ignore: str=None, require: str=None):
    """
    Takes a list of strings and returns a list containing only those that
    met the regex requirements

    :param string_list: The list of strings
    :param ignore: All elements matching this regex string will be removed
    :param require: Only elements matching this regex string will be kept
    """
    old_len = len(string_list)
    if ignore is not None:
        string_list = [string for string in string_list if not re.search(ignore, string)]
        print("Removed {} strings through ignore regex".format(old_len - len(string_list)))
    old_len = len(string_list)
    if require is not None:
        string_list = [string for string in string_list if re.search(require, string)]
        print("Removed {} strings through require regex".format(old_len - len(string_list)))
    # print(string_list[:10])  -- Show sample of approved titles
    return string_list


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
