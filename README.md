# Seddit v0.6.0
A Python Script for counting the number of instances a collection of terms get used in post titles on different subreddits. 
It can either search through all words to find the most common words or can take in a CSV file containing a list of specific terms to look for and show their frequencies.
As it performs each search, it stores every post it sees in a cache file, allowing it to amass a large collection of posts over time.

## Installation

1. Download and extract the zip file.
2. Install the packages listed in `requirements.txt`. 
This can be done automatically by running the command `pip install -r requirements.txt` inside the root directory.
3. Obtain a client secret and client ID from Reddit.
Instructions for how can be found on [Reddit's OAuth2 Wiki](https://github.com/reddit-archive/reddit/wiki/OAuth2)
4. Rename `config\example.ini` to `config\default.ini` and fill those values in where the placeholders are.
You can also change any of the default parameters. 
**Note:** In ini files, strings are not enclosed in quotes.

## Quickstart

### Search

Seddit uses PRAW to search the hot, top, and or new feed for a given subreddit and collect all of the posts.
The frequency of all words is then calculated, excluding a list of filtered words.
This filter can be used to exclude common words (e.g. the, a, an, this, etc.). 
The list of words will then be sorted by frequency and the results will be displayed on the terminal.

##### Example

```
python seddit.py kerbalspaceprogram
---------------------------------------
Checking cache...
Cache validated for hot feed
Cache validated for top feed
Loaded values from cache
---------------------------------------
Popularity score:

KSP - 119
Kerbal - 75
Mun - 61
Space - 52
Duna - 48
...
```

(Output truncated)

### Graphing

In addition to having the results printed to the console, Seddit can also generate a bar graph for each of the words.

**Note:** To generate these graphs, you must have matplotlib installed. 

### Term Groups

Term Groups can be used to group together nicknames (e.g. "Philly" and "Philadelphia") or common misspellings (e.g. "D.Va" and "DVa").
These groups are defined by a CSV file, where each row is a group and each column is a term in that group.
A default file can be defined in `config.py`, or a different one can be passed in as an argument.
When counting, each word in the group is replaced with the first term in the row.
This means that if two groups contain the same term, it will only count towards the first group.

Additionally, this mapping is done to the title as a whole, so multiple word phrases can be mapped to single words.
However, this means this first term in a group must be a single word, otherwise it will be broken up during frequency search.

##### Example

**overwatch.csv**

```
Tank,D.Va,Oria,Reinhardt,Roadhog,Sigma,Winston,Wrecking Ball,Zarya
Damage,Ashe,Bastion,Doomfist,Echo,Genji,Hanzo,Junkrat,McCree,Mei,Pharah,Reaper,Soldier: 76,Sombra,Symmetra,Torbjörn,Tracer,Widowmaker
Support,Ana,Baptiste,Brigitte,Lucio,Lúcio,Mercy,Moira,Zenyatta
```

**Program**

```
seddit.py Overwatch -tg term_groups/overwatch.csv
Checking cache for /r/Overwatch
Cached posts: 231
===============================================
================  RESULTS  ====================
===============================================

Popularity score:

1) Damage - 43
2) overwatch - 22
3) Support - 21
4) Tank - 15
5) new - 14
6) game - 12
7) potg - 11
8) think - 10
9) get - 9
10) play - 8
...
```

(Output truncated)

### Search terms

If the objective is to compare the relative frequency of a known list of words, a search for only that specific set can be performed instead.
These groups are defined by a CSV file, where each row is a group and each column is a term in that group.
A default file can be defined in `config.py`, or a different one can be passed in as an argument.
When the results are displayed, only the search terms provided will be displayed. 
Like term groups, search terms can be multiple word phrases and multiple terms can be grouped together.
Unlike term groups, however, the first term in the row can be more than one word.

##### Example

**splatoon.csv**

```
Agents,Agent
Callie,Aori,Squid Sisters
Inkling
Marie,HotaruSquid Sisters
Marina,Off the Hook
Octoling,Octo
Pearl,Off the Hook
```

**Program**

```
python seddit.py splatoon -st splatoon.csv
---------------------------------------
Checking cache...
Cache validated for hot feed
Cache validated for top feed
Loaded values from cache
---------------------------------------
Popularity score:

Inkling - 65
Octoling - 55
Callie - 55
Pearl - 48
Marina - 46
Agents - 39
Marie - 37
```

### Cache

Searches that yield lots of results produce better data, but they also take a long time.
Additionally, Reddit's API restricts searches to a maximum of 1,000 posts per feed.
To get around this, every time you search a subreddit, the results are saved to a cache. 
Eventually, this cache will expire and another search will be run, but the old posts will still be kept.
This lets the feeds stay current while the total number of posts saved grows.
Over time, the number of posts grow far beyond what can be scraped at one time.

### Word filters

A word filter is a CSV file containing strings that shouldn't be included in the results list.
Several files are included in the `filters` directory. 
The default file is `default.csv`, which can be changed in `config.py` or by a command line argument.
This filters 250 most popular English words, a few other common words, single letters, and numbers from 0-100.
Lists of the 100, 1000, and 10000 most common English words have also been included.

## Examples

#### Performing a basic search

```
python seddit.py funny
```

#### Creating a graph

Using Matplotlip, a bar chart of frequencies for the most popular words can be generated at the end of a search.
To reduce crowding, the "rank cutoff" setting in `config.py` specifies how many terms to display.
This graph is generated from the same list shown on screen, so the score threshold will apply here as well. 

```
python seddit.py TIL -g
```

## Configuration

While Seddit offers many command line arguments for modifying its function, many parameters are not available at the command line.
These parameters are stored in configuration files, which define several important values that can't be reached by arguments.
Default values are determined by `DEFAULT_CONFIG_FILE`, which is specified at the top of `seddit.py`.
The default path is `config/default.ini`
These can be overridden by extending this file or passing in a different filepath through the command line.
The available fields, their descriptions, and suggested values can be found in `config/example.ini`