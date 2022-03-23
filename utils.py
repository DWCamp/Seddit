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


def ingest_csv(csv_path: str, delimiter: str = ',', strip_spaces: bool = True) -> [[str]]:
    """
    Takes in a CSV file and returns a 2D list of the contents

    :param csv_path: The path to the csv file
    :param delimiter: The character which divides cells in the file's csv encoding. Defaults to ','
    :param strip_spaces: Remove any spaces from the ends of each cell. Defaults to `True`
    :return: [[str]] - A list of rows, each of which is a list of the cells in that row
    """
    contents = []
    with open(csv_path, newline='', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file, delimiter=delimiter)
        for row in reader:
            if strip_spaces:
                contents.append([cell.strip() for cell in row])
            else:
                contents.append(list(row))
    return contents


def value_filter_dict(dictionary: dict, threshold, invert: bool = False):
    """
    Creates a copy of a dictionary with all elements removed whose
    value is less than a given threshold

    :param dictionary: The dictionary to filter
    :param threshold: The threshold below which to remove elements
    :param invert: Whether to invert the threshold (remove elements above threshold)

    :return: The filtered dictionary
    """
    return {key: value for (key, value) in dictionary.items() if (value < threshold) == invert}


def list_filter_dict(dictionary: dict, remove: [str]) -> {str: any}:
    """
    Performs an in-place removal of all keys from a dictionary that match
    the provided list. This check is case-insensitive

    :param dictionary: The dictionary to filter
    :param remove: The keys to remove

    :return: The filtered dictionary
    """
    remove = [key.lower() for key in remove]  # Make sure keys to remove are all lower
    for word in remove:
        if word in dictionary:
            del dictionary[word]
    return dictionary


def regex_filter_dict(dictionary: {str: any}, remove: str = None, require: str = None) -> {str: any}:
    """
    Takes a {str: Any} dictionary and removes all keys that don't meet the regex requirements

    :param dictionary: The dictionary to filter
    :param remove: All elements containing this pattern will be removed. If `None`,
            all elements will be kept (Default: None)
    :param require: All elements that do not contain this pattern will be removed.
            If `None`, all elements will be kept. (Default: None)

    :return: The filtered dictionary
    """
    # Abort if no filters
    if not remove and not require:
        return dictionary

    # Perform key filter
    for key in dictionary:
        # Remove key if it matches regex
        if remove and re.search(remove, key):
            del dictionary[key]
        # Remove key if it does not contain required regex
        elif require and re.search(require, key) is None:
            del dictionary[key]

    return dictionary


def sorted_dict(dictionary, reverse=True):
    """
    Returns the list of (key, value) tuples in a dictionary, sorted first
    by value and then by key
    :param dictionary: The dictionary to sort
    :param reverse: Whether to reverse the sort
    :return: A sorted list of (key, value) tuples
    """
    return sorted(dictionary.items(), reverse=reverse, key=lambda x: (x[1], x[0]))


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
