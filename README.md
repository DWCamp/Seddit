# Seddit v0.4.1
A Python Script for counting the number of instances a collection of terms get used in post titles on different subreddits. 
It can either search through all words to find the most common proper nouns or can take in a text file containing a list of specific terms to look for and show their frequencies.
As it performs each search, it stores every post it sees in a cache file, allowing it over time to amass a database of posts on a subreddit.

## Installation

1. Download and extract the zip file.
2. Make sure you have PRAW installed by running `pip install praw`. [Here is a link](https://www.reddit.com/prefs/apps) to the webpage for acquiring a Client ID and secret
3. Create a duplicate of `config.json`.example` named `config.json` in the project's root directory and replace the sample values with those needed for your script 

## Quickstart

### Search

Seddit uses PRAW to search the hot, top, and or new feed for a given subreddit and collect all of the posts.
After the list of post titles is collected, it will be scanned for frequently used capitalized words.
Common English words (defined by a csv file) will be discarded.
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

(Output truncated for brevity)

### Graphing

In addition to having the results printed to the console, Seddit can also generate a bar graph for each of the words.

**Note:** To generate these graphs, you must have matplotlib installed. 

### Search terms

If the objective is to compare the relative frequency of a known list of words, a search for only that specific set can be performed instead.
Tiles will be compiled like before, but this time only the specific terms will be searched for. 
Unlike proper nouns, these terms are case insensitive and a term can be multiple words long. 
Additionally, multiple search terms can be grouped together, like if there are multiple phrases that mean the same thing (e.g. "New York City" and "NYC")
When multiple terms are used, the first term is considered the "official" name for console output and graphs.
These words can be fed in through the command line using a csv file, where every row is a term and each additional name in a row separated by a single comma.

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
Because of this, every time you search a subreddit, the results are saved to a cache. 
Over time, this cache will no longer be accurate to the subreddit feeds, so after an amount of time the cache will expire and the search will be run again.
However, when the search is re-run, the old data isn't thrown away. 
All post details are stored in a central collection, with each feed being merely a list of the post IDs. 
As each feed is refreshed over time, the total number of posts catalogued will slowly grow.
This allows the script to circumvent the Reddit API's limitation of 1000 posts per search and provide a large 
collection of data

### words.csv

Included in the directory is a file called `words.csv`. 
This is a small list of the 250 most popular English words (plus a few more). 
It helps filter out words whose frequency in titles isn't interesting. 
This filtering can be disabled or modified.
If a different file is used, it should be a file containing all of the words on a single line, separated only by commas.
The path to this file can be set in the `config.json` file.

## Examples

#### Performing a basic search

```
python seddit.py funny
```

#### Creating a graph

```
python seddit.py all -g
```

## Configuration

While Seddit offers many command line arguments for modifying its function, many parameters are not available at the command line.
This simplifies the help screen and makes important commands more visible, but at the cost of configuration.
To get around that, Seddit uses a `config.json` file to define several important values that can't be reached by arguments.
This file can be modified to change the default behavior between runs. 
Additionally, a file containing some or all of these values can be passed in as an argument to vary the program's behavior from run to run.

#### General Parameters

* **version** - The version number of the program
* **description** - A brief description of the program

#### PRAW Configuration

* **client_secret** - Your Client Secret for the Reddit API
* **client_id** - Your Client ID for the Reddit API
* **user_agent** - PRAW User Agent. The recommended format is provided in the example file

#### Caching Configuration

* **cache_file_path** - The path to the cache file
* **cache_hot_ttl** - Cache lifetime for hot feed
* **cache_new_ttl** - Cache lifetime for new feed
* **cache_top_ttl** - Cache lifetime for top feed
* **enabled_feeds** - The list of feeds to check when searching a subreddit ('hot', 'new', or 'top')

#### Analysis Configuration

* **filtered_words_file** - The path to a CSV file containing words to filter out of noun search. The words should all be on the first line of the file. The included file contains the 250 most common words in the English language, to prevent words like 'The' and 'A' from dominating the results
* **rank_cutoff** - The highest rank to show on the graph. For all results, set to -1
* **search_terms** - Defines a default search terms file to use
* **threshold** - The frequency threshold for filtering out obscure results

#### Regex

* **ignore_regex** - Posts that match this regex string will **not** be evaluated
* **require_regex** - **Only** posts that match this regex string will be evaluated
