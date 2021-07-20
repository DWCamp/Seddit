"""
Data classes for Seddit

TermGroup - A group of synonyms which should be counted as the same item
Post - A post on a subreddit

@author Daniel Campman
@version 7/19/20
"""
import re

import config


class TermGroup:

    def __init__(self, groups: [[str]], ignore_case=True):
        """
        Creates a group of synonymous terms. Titles filtered through the term group will have all instances
        of word in each term group replaced with the first element of the group.

        **Note:** Empty and single element lists are removed, since they will have no effect

        :param groups: The list of string lists. Each list is a term group. When a title is filtered, all words
            in each list will be replaced with the first element
        :param ignore_case: Ignore case for term matching (default: True)
        """
        self.groups = {}

        # Exit early if 'groups' is None or empty
        if not groups:
            return

        # Filter `None` as well as empty element lists, as these won't change anything
        groups = [group for group in groups if group is not None and len(group) > 0]

        # Create regex filter for each term group
        for group in groups:
            # Compile all terms into a `(<A>|<B>|...)` regex string
            escaped_list = [re.escape(term) for term in group]
            flags = re.IGNORECASE if ignore_case else 0
            self.groups[group[0]] = re.compile('\\b({})\\b'.format("|".join(escaped_list)), flags)

    def sanitize(self, title: str) -> str:
        """
        Sanitizes term groups by replacing every instance of a term with string with a

        :param title: The title to sanitize
        :return: The title, with all instances of a term group replaced with the group name
        """
        for group in self.groups:
            title = self.groups[group].sub(group, title)
        return title


class Post:

    def __init__(self, post_id: str, title: str, score: int):
        """
        Represents a post on Reddit
        :param post_id: The ID
        :param title: The title of the post
        :param score: The score of the post
        """
        self.postID = post_id
        self.title = title
        self.score = score

    def __eq__(self, other):
        if isinstance(other, Post):
            return self.postID == other.postID
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.postID)

    def term_list(self, term_group: TermGroup) -> set:
        """
        Returns a set of all unique words in the post title

        :param term_group: The TermGroup object for this query
        :return: The set of words in the post title
        """
        title = self.title

        # Check title against regex
        if config.ignore_title_regex and re.search(config.ignore_title_regex, title):
            return set()
        if config.require_title_regex and re.search(config.require_title_regex, title) is None:
            return set()

        title = term_group.sanitize(title) if term_group else title
        # Find all 'words' in the title (i.e. contiguous alphanumeric strings)
        words = re.findall(r"\b[\w.]+'?[\w.]*\b", title.lower())
        if not words:
            return set()

        # Convert list to set to remove duplicates
        result = set()
        for word in words:
            # Ignore word if it contains disallowed regex
            if config.ignore_word_regex and re.search(config.ignore_word_regex, word):
                continue
            # Ignore word if it does not contain required regex
            if config.require_word_regex and re.search(config.require_word_regex, word) is None:
                continue
            # If not blocked by regex, add word
            result.add(word)

        # Return words
        return result

    def to_dict(self):
        """
        Convert Post to a dictionary
        :return: A dictionary representation of the Post's data
        """
        return {
            "postID": self.postID,
            "title": self.title,
            "score": self.score
        }
