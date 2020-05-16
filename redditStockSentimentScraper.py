# Reddit Stock Sentiment Scraper
# USAGE: wsbtickerbot.py [ Name of Subreddit to scrape comments from ] [ Sort Mode for Subreddit ] [ Number of Posts on the Subreddit to look at ] [ Update Frequency ]

# Utilizes a modified version of the VADER Sentiment Analysis
# Library to classify Reddit comments from r/WallStreetBets and
# generate aggregate statistics

from vaderSentiment.vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import sys
import praw
import time
import json
import pprint
import operator
import datetime

from praw.models import MoreComments
sys.path.insert(0, 'vaderSentiment/vaderSentiment')


# Segment stock symbols from an entire comment
def segment_asset_symbol_from_body(comment_body, first_index_to_search):
    current_letter_count = 0
    asset_symbol = ""

    # Scan the comment letter by letter
    for current_character in comment_body[first_index_to_search:]:
        if not current_character.isalpha():
            if (current_letter_count == 0):
                return None
            # Takes care of edge cases where not all letters of the symbol are capitalized (Amd, Msft, Spy)
            return asset_symbol.upper()

        # Takes care of cases where everything is uppercase (AMD, MSFT, SPY)
        else:
            asset_symbol += current_character
            current_letter_count += 1
    return asset_symbol.upper()


def parse_section(ticker_dict, body):
    blacklist_words = [
        "YOLO", "TOS", "CEO", "CFO", "CTO", "DD", "BTFD", "WSB", "OK", "RH", "FTW", "WELS", "KNO", "FOR", "REIT", "NOW", "MODS", "HELP", "HIM", "TELL", "DLDO", "ETF", "EOY", "DCA", "TSP",
        "KYS", "FD", "TYS", "US", "USA", "IT", "ATH", "RIP", "BMW", "GDP", "MUST", "FOO", "FFF", "FFFF", "MAN", "OTM", "ITM", "SAM", "PLAY", "YOUR", "ARE", "FUK", "WEED", "MAST", "ADL", "GUNS",
        "OTM", "ATM", "ITM", "IMO", "LOL", "DOJ", "BE", "PR", "PC", "ICE", "OUT", "HERE", "ALL", "BAN", "HAD", "HAS", "ITS", "HOLD", "WEEK", "NOOB", "BTC", "SHIT", "METH", "JPOW", "FUD", "NEWS",
        "TYS", "ISIS", "PRAY", "PT", "FBI", "SEC", "GOD", "NOT", "POS", "COD", "FUCK", "TAX", "THIS", "WAS", "STD", "WAS", "HELP", "MOM", "PUT", "IRA", "FUND", "OMG", "NARC", "CIA", "BOSS",
        "AYYMD", "FOMO", "TL;DR", "EDIT", "STILL", "LGMA", "WTF", "RAW", "PM", "RUN", "FREE", "DOWN", "HARD", "THEY", "AND", "MODS", "HUG", "TITS", "FLU", "BOYS", "IMHO", "COME", "NYC", "NOW",
        "LMAO", "LMFAO", "ROFL", "EZ", "RED", "BEZOS", "TICK", "IS", "DOW", "KEEP", "CNBC", "CAN", "HAVE", "WITH", "PDT", "YOU", "DAMN", "DTE", "JEDI", "EMO", "BAG", "PPL", "PPT", "LIFE",
        "AM", "PM", "LPT", "GOAT", "FL", "CA", "IL", "PDFUA", "MACD", "HQ", "DOW", "LOSS", "PORN", "OFF", "DAYS", "WITH", "GOT", "LOST", "FTFY", "OVA", "BRO", "BUL", "BEST", "IRON", "SAY", "TARD",
        "OP", "DJIA", "PS", "AH", "TL", "DR", "JAN", "FEB", "JUL", "AUG", "FROM", "SUCK", "MAH", "IRS", "KEEP", "HEAD", "IIRC", "PONE", "WHO", "BIRD", "JUST", "BOIS", "STFU", "API", "POP",
        "SEP", "SEPT", "OCT", "NOV", "DEC", "FDA", "IV", "ER", "IPO", "RISE", "MORE", "BUYS", "JERK", "HUGE", "BURN", "SAME", "OCD", "HOW", "CDC", "KNOW", "DAY", "GAY", "SAFE", "WILL", "GET",
        "IPA", "URL", "MILF", "BUT", "SSN", "FIFA", "USD", "CPU", "AT", "ABC", "TRADE", "BBC", "NSA", "WWII", "TLDR", "PSA", "LOST", "DONT", "JUST", "OVER", "BACK", "YET", "FIX", "TOP", "TEN",
        "GG", "ELON", "ROPE", "GUH", "HOLY", "GAP", "GANG", "LONG", "INTO", "MOON", "THE", "HIV", "BULL", "BEAR", "YTD", "DIP", "BUY", "TURN", "LEAP", "FYI", "SARS", "CRAP", "EOW", "EASY", "AMA",
        "FDIC", "UFC", "LETS", "PUMP", "FAKE", "WHY", "TICKER", "TICKERS", "WUUU", "ESPN", "WON", "COCK", "YUGE", "ONLY", "FALL", "GSI", "ONE", "BABY", "BIG", "FAT", "GIVE", "FED", "WILL", "NEW", "PUTS", "EPS", "REK"
    ]

    if '$' in body:
        index = body.find('$') + 1
        word = segment_asset_symbol_from_body(body, index)

        if word and word not in blacklist_words:
            try:
                if word != "ROPE":
                    if word in ticker_dict:
                        ticker_dict[word].count += 1
                        ticker_dict[word].bodies.append(body)
                    else:
                        ticker_dict[word] = Ticker(word)
                        ticker_dict[word].count = 1
                        ticker_dict[word].bodies.append(body)
            except:
                pass

    word_list = re.sub("[^\w]", " ",  body).split()
    for count, word in enumerate(word_list):
        if word.isupper() and len(word) >= 3 and (word.upper() not in blacklist_words) and len(word) < 5 and word.isalpha():
            if word in ticker_dict:
                ticker_dict[word].count += 1
                ticker_dict[word].bodies.append(body)
            else:
                ticker_dict[word] = Ticker(word)
                ticker_dict[word].count = 1
                ticker_dict[word].bodies.append(body)
    return ticker_dict


def get_url(key, value, total_count):
    mention = ("mentions", "mention")[value == 1]
    if int(value / total_count * 100) == 0:
        perc_mentions = "<1"
    else:
        perc_mentions = int(value / total_count * 100)
    return "{0}:    {3}% {1}".format(key, value, mention, perc_mentions)


def initialize_subreddit(current_subreddit):
    if current_subreddit == "":  # Default to r/wallstreetbets if no argument given
        current_subreddit = "wallstreetbets"

    # Initialize environment variables from config.json to connect to the Reddit API
    with open("environment_variables.json") as environment_variables_JSON:
        environment_variables = json.load(environment_variables_JSON)

    # ----------------------- Environment Variables -----------------------
    # Initialize a Reddit instance from Praw using the environment variables stored in environment_variables.json
    reddit_instance = praw.Reddit(
        # Reddit Client ID
        client_id=environment_variables["reddit_API"]["client_id"],
        # Reddit Client Secret
        client_secret=environment_variables["reddit_API"]["client_secret"],
        # Reddit Username
        username=environment_variables["reddit_API"]["username"],
        # Reddit Password
        password=environment_variables["reddit_API"]["password"],
        # Reddit User Agent - Unnecessary
        user_agent=environment_variables["reddit_API"]["user_agent"])
    # ----------------------- Environment Variables -----------------------

    # Intitialize an instance of a Subreddit from our Reddit Instance
    current_subreddit = reddit_instance.subreddit(current_subreddit)
    return current_subreddit


def scrape_and_analyze_sentiment(current_subreddit, subreddit_sort_mode, post_count):
    ticker_dict = {}
    text = ""

    current_subreddit = initialize_subreddit(current_subreddit)

    if subreddit_sort_mode == 'hot':
        new_posts = current_subreddit.hot(limit=post_count)
    else:
        new_posts = current_subreddit.new(limit=post_count)

    for count, post in enumerate(new_posts):
        post.comment_sort = 'new'

        if not post.clicked:
            ticker_dict = parse_section(ticker_dict, post.title)

            # search through all comments and replies to comments
            comment_count = 0
            comments = post.comments
            # comments.replace_more(limit=None)

            for comment in comments.list():
                comment_count += 1
                # without this, would throw AttributeError since the instance in this represents the "load more comments" option
                if isinstance(comment, MoreComments):
                    continue

                ticker_dict = parse_section(ticker_dict, comment.body)

                # iterate through the comment's replies
                replies = comment.replies
                for rep in replies:
                    # without this, would throw AttributeError since the instance in this represents the "load more comments" option
                    if isinstance(rep, MoreComments):
                        continue
                    ticker_dict = parse_section(ticker_dict, rep.body)
            # update the progress count
            print(
                "Scraping {0} comments from post {1} of {2}".format(comment_count, count + 1, post_count))

    text += "\n\nSymbol | Mentions | Bullish | Bearish | Neutral"

    total_mentions = 0
    ticker_list = []
    for key in ticker_dict:
        total_mentions += ticker_dict[key].count
        ticker_list.append(ticker_dict[key])

    ticker_list = sorted(
        ticker_list, key=operator.attrgetter("count"), reverse=True)
    for ticker in ticker_list:
        Ticker.analyze_sentiment(ticker)

    # will break as soon as it hits a ticker with fewer than 5 mentions
    for count, ticker in enumerate(ticker_list):
        if count == 25:
            break

        url = get_url(ticker.ticker, ticker.count, total_mentions)
        # setting up formatting for table
        text += "\n{} | {} | {} | {}".format(url,
                                             ticker.bullish, ticker.bearish, ticker.neutral)

    print(text)


class Ticker:
    def __init__(self, ticker):
        self.ticker = ticker
        self.count = 0
        self.bodies = []
        self.pos_count = 0
        self.neg_count = 0
        self.bullish = 0
        self.bearish = 0
        self.neutral = 0
        self.sentiment = 0  # 0 is neutral

    def analyze_sentiment(self):
        analyzer = SentimentIntensityAnalyzer()
        neutral_count = 0
        for text in self.bodies:
            sentiment = analyzer.polarity_scores(text)
            if (sentiment["compound"] > .005) or (sentiment["pos"] > abs(sentiment["neg"])):
                self.pos_count += 1
            elif (sentiment["compound"] < -.005) or (abs(sentiment["neg"]) > sentiment["pos"]):
                self.neg_count += 1
            else:
                neutral_count += 1

        self.bullish = int(self.pos_count / len(self.bodies) * 100)
        self.bearish = int(self.neg_count / len(self.bodies) * 100)
        self.neutral = int(neutral_count / len(self.bodies) * 100)

        # Entry point for the program
if __name__ == "__main__":
    print("\nReddit Stock Sentiment Scraper v1.0")

    # ----------------------- Subreddit Parameters -----------------------
    # Subreddit to scrape from
    current_subreddit = "wallstreetbets"  # Default to r/wallstreetbets
    if len(sys.argv) > 1:
        current_subreddit = str(sys.argv[1])

    # New - Scrape most recent posts first, Hot - Sort 'hottest' post on the subreddit
    subreddit_sort_mode = "new"  # Default to sort by 'new'
    if len(sys.argv) > 2:
        subreddit_sort_mode = str(sys.argv[2])

    # Total number of posts to scrape
    post_count = 30  # Default to 30 posts
    if len(sys.argv) > 3:
        post_count = int(sys.argv[3])

    # Total number of posts to scrape
    update_frequency = 180  # Default to 3 minutes
    if len(sys.argv) > 4:
        update_frequency = int(sys.argv[4])

    # ----------------------- Subreddit Parameters -----------------------

    # ----------------------- Print information to Terminal -----------------------
    print("\nSubreddit: r/{0}".format(current_subreddit))
    print("Subreddit Sort Mode: '{0}'".format(subreddit_sort_mode))
    print("Scraping {0} most recent posts".format(post_count))
    print("Running analysis with a {0} second timeout between iterations\n".format(
        update_frequency))
    # ----------------------- Print information to Terminal -----------------------

    # ----------------------- Main Loop -----------------------
    current_iteration = 0
    while True:  # Run an infinite loop to analyze subreddits indefinitely
        print("Starting Iteration {0}".format(current_iteration))

        # Start scraping comments, extract asset symbols and analyze people's sentiment on them
        scrape_and_analyze_sentiment(
            current_subreddit, subreddit_sort_mode, post_count)

        print("Iteration {0} finished successfully at {1}.\n".format(
            current_iteration, datetime.datetime.now()))
        current_iteration += 1  # Update iteration count
    # ----------------------- Main Loop -----------------------
