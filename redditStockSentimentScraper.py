# Reddit Stock Sentiment Scraper
# USAGE: wsbtickerbot.py [ Name of Subreddit to scrape comments from ] [ Sort Mode for Subreddit ] [ Number of Posts on the Subreddit to look at ] [ Update Frequency ]

# Utilizes a modified version of the VADER Sentiment Analysis
# library to classify Reddit comments and
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


def get_url(key, value, total_count):
    mention = ("mentions", "mention")[value == 1]
    if int(value / total_count * 100) == 0:
        perc_mentions = "<1"
    else:
        perc_mentions = int(value / total_count * 100)
    return "{0}:    {3}% {1}".format(key, value, mention, perc_mentions)


# Main Method
def main():
    print("\nReddit Stock Sentiment Scraper v1.1")

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
    while current_iteration < 1:  # Run an infinite loop to analyze subreddits indefinitely
        print("Starting Iteration {0}".format(current_iteration))

        # Start scraping comments, extract asset symbols and analyze people's sentiment on them
        scrape_and_analyze_sentiment(
            current_subreddit, subreddit_sort_mode, post_count)

        print("Iteration {0} finished successfully at {1}.\n".format(
            current_iteration, datetime.datetime.now()))
        current_iteration += 1  # Update iteration count
    # ----------------------- Main Loop -----------------------

def scrape_and_analyze_sentiment(current_subreddit, subreddit_sort_mode, post_count):
    stock_symbol_dictionary = {}
    return_string = ""

    current_subreddit = initialize_subreddit(current_subreddit)

    # Recieve posts from the subreddit in order determined by the 'hot' mode
    if subreddit_sort_mode == 'hot':
        incoming_posts = current_subreddit.hot(limit=post_count)
    
    # Recieve posts from the subreddit in order determined by the 'new' mode
    elif subreddit_sort_mode == 'new':
        incoming_posts = current_subreddit.new(limit=post_count)

    for count, post in enumerate(incoming_posts):
        # Sort comments on the post by recency
        post.comment_sort = 'new'

        if not post.clicked:  # If the post has not been opened yet
            # Scrape stock mentions from post titles
            stock_symbol_dictionary = build_stock_symbol_dictionary_from_body(stock_symbol_dictionary, post.title)

            # Search through all comments and replies to comments
            comment_count = 0
            comments = post.comments
            # comments.replace_more(limit=None)

            for comment in comments.list():
                comment_count += 1
                # To get around the AttributeError thrown by the "load more comments" option
                if isinstance(comment, MoreComments):
                    continue

                stock_symbol_dictionary = build_stock_symbol_dictionary_from_body(
                    stock_symbol_dictionary, comment.body)

                # Iterate through the comment's replies
                replies = comment.replies
                for reply in replies:
                    # To get around the AttributeError thrown by the "load more comments" option
                    if isinstance(reply, MoreComments):
                        continue
                    
                    stock_symbol_dictionary = build_stock_symbol_dictionary_from_body(
                        stock_symbol_dictionary, reply.body)
            
            print(
                "Scraping {0} comments from post {1} of {2}".format(comment_count, count + 1, post_count))

    return_string += "\n\nSymbol | Mentions | Bullish | Bearish | Neutral"

    total_mentions = 0
    ticker_list = []
    for key in stock_symbol_dictionary:
        total_mentions += stock_symbol_dictionary[key].total_mentions
        ticker_list.append(stock_symbol_dictionary[key])

    ticker_list = sorted(
        ticker_list, key=operator.attrgetter("total_mentions"), reverse=True)
    for ticker in ticker_list:
        Asset_Data.analyze_sentiment(ticker)

    # will break as soon as it hits a ticker with fewer than 5 mentions
    for count, ticker in enumerate(ticker_list):
        if count == 25:
            break

        url = get_url(ticker.symbol, ticker.total_mentions, total_mentions)
        # setting up formatting for table
        return_string += "\n{} | {} | {} | {}".format(url,
                                             ticker.bullish, ticker.bearish, ticker.neutral)

    print(return_string)


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

# Takes in a body of text and attemps to build a dictionary of all the stock symbols mentioned in the body
def build_stock_symbol_dictionary_from_body(stock_symbol_dictionary, body):
    # List to take care of most common false negatives
    blacklisted_word_list = [
        "YOLO", "TOS", "CEO", "CFO", "CTO", "DD", "BTFD", "WSB", "OK", "RH", "FTW", "WELS", "KNO", "FOR", "REIT", "NOW", "MODS", "HELP", "HIM", "TELL", "DLDO", "ETF", "EOY", "DCA", "TSP",
        "KYS", "FD", "TYS", "US", "USA", "IT", "ATH", "RIP", "BMW", "GDP", "MUST", "FOO", "FFF", "FFFF", "MAN", "OTM", "ITM", "SAM", "PLAY", "YOUR", "ARE", "FUK", "WEED", "MAST", "ADL", "GUNS",
        "OTM", "ATM", "ITM", "IMO", "LOL", "DOJ", "BE", "PR", "PC", "ICE", "OUT", "HERE", "ALL", "BAN", "HAD", "HAS", "ITS", "HOLD", "WEEK", "NOOB", "BTC", "SHIT", "METH", "JPOW", "FUD", "NEWS",
        "TYS", "ISIS", "PRAY", "PT", "FBI", "SEC", "GOD", "NOT", "POS", "COD", "FUCK", "TAX", "THIS", "WAS", "STD", "WAS", "HELP", "MOM", "PUT", "IRA", "FUND", "OMG", "NARC", "CIA", "BOSS",
        "AYYMD", "FOMO", "TL;DR", "EDIT", "STILL", "LGMA", "WTF", "RAW", "PM", "RUN", "FREE", "DOWN", "HARD", "THEY", "AND", "MODS", "HUG", "TITS", "FLU", "BOYS", "IMHO", "COME", "NYC", "NOW",
        "LMAO", "LMFAO", "ROFL", "EZ", "RED", "BEZOS", "TICK", "IS", "DOW", "KEEP", "CNBC", "CAN", "HAVE", "WITH", "PDT", "YOU", "DAMN", "DTE", "JEDI", "EMO", "BAG", "PPL", "PPT", "LIFE", "PMCCF",
        "AM", "PM", "LPT", "GOAT", "FL", "CA", "IL", "PDFUA", "MACD", "HQ", "DOW", "LOSS", "PORN", "OFF", "DAYS", "WITH", "GOT", "LOST", "FTFY", "OVA", "BRO", "BUL", "BEST", "IRON", "SAY", "TARD", "PPPLF", "CLO",
        "OP", "DJIA", "PS", "AH", "TL", "DR", "JAN", "FEB", "JUL", "AUG", "FROM", "SUCK", "MAH", "IRS", "KEEP", "HEAD", "IIRC", "PONE", "WHO", "BIRD", "JUST", "BOIS", "STFU", "API", "POP", "CRE", "PPP",
        "SEP", "SEPT", "OCT", "NOV", "DEC", "FDA", "IV", "ER", "IPO", "RISE", "MORE", "BUYS", "JERK", "HUGE", "BURN", "SAME", "OCD", "HOW", "CDC", "KNOW", "DAY", "GAY", "SAFE", "WILL", "GET", "S", "COVID",
        "IPA", "URL", "MILF", "BUT", "SSN", "FIFA", "USD", "CPU", "AT", "ABC", "TRADE", "BBC", "NSA", "WWII", "TLDR", "PSA", "LOST", "DONT", "JUST", "OVER", "BACK", "YET", "FIX", "TOP", "TEN", "U", "MLF", "LOW", "TALF",
        "GG", "ELON", "ROPE", "GUH", "HOLY", "GAP", "GANG", "LONG", "INTO", "MOON", "THE", "HIV", "BULL", "BEAR", "YTD", "DIP", "BUY", "TURN", "LEAP", "FYI", "SARS", "CRAP", "EOW", "EASY", "AMA", "TARP", "NY",
        "FDIC", "UFC", "LETS", "PUMP", "FAKE", "WHY", "TICKER", "TICKERS", "WUUU", "ESPN", "WON", "COCK", "YUGE", "ONLY", "FALL", "GSI", "ONE", "BABY", "BIG", "FAT", "GIVE", "FED", "WILL", "NEW", "PUTS", "EPS", "REK"
    ]

    # Takes care of cases where stocks are mentioned like '$INTC, $AMD, $MSFT' etc.
    if '$' in body:
        starting_index = body.find('$') + 1
        asset_symbol = format_and_segment_asset_symbol_from_body(body, starting_index)

        if asset_symbol and asset_symbol not in blacklisted_word_list:
            try:
                    # If this stock has already been added to the dictionary, update the count, append the comment body
                    if asset_symbol in stock_symbol_dictionary:
                        stock_symbol_dictionary[asset_symbol].total_mentions += 1
                        stock_symbol_dictionary[asset_symbol].associated_sentences.append(body)
                    # Else create and add the new Asset_Data object to the dictionary
                    else:
                        stock_symbol_dictionary[asset_symbol] = Asset_Data(asset_symbol)
                        stock_symbol_dictionary[asset_symbol].total_mentions = 1
                        stock_symbol_dictionary[asset_symbol].associated_sentences.append(body)
            except:
                pass
    
    # Regex takes care of the cases where comments could be written in superscript on Reddit using the "^" operator
    body_split_text_list = re.sub("[^\w]", " ", body).split() # Contains all the words in the comment body in a list like ['This','is','a','comment']
    
    for count, current_word in enumerate(body_split_text_list):
        # All NASDAQ symbols are 4 to 5 letters and alphanumeric - 5 letter stock names are barely ever mentioned
        # All NYSE symbols are 1 to 3 letters and alphanumeric - Some popular 1 and 2 letter names like F, V, and MA, but people tend to mention them with a $ sign
        if current_word.isupper() and len(current_word) >= 2 and (current_word.upper() not in blacklisted_word_list) and len(current_word) < 5 and current_word.isalpha():
            asset_symbol = current_word
            if asset_symbol in stock_symbol_dictionary:
                stock_symbol_dictionary[asset_symbol].total_mentions += 1
                stock_symbol_dictionary[asset_symbol].associated_sentences.append(body)
            else:
                stock_symbol_dictionary[asset_symbol] = Asset_Data(asset_symbol)
                stock_symbol_dictionary[asset_symbol].total_mentions = 1
                stock_symbol_dictionary[asset_symbol].associated_sentences.append(body)
    return stock_symbol_dictionary

# Formats and segment stock symbols from the comment body. Returns asset symbols in upper case.
def format_and_segment_asset_symbol_from_body(comment_body, starting_index):
    current_letter_count = 0
    asset_symbol = ""

    # Scan the comment letter by letter
    for current_character in comment_body[starting_index:]:
        if not current_character.isalpha(): 
            # If the first letter is not uppercase, it is likely not a stock symbol
            if (current_letter_count == 0):
                return None
            # Takes care of edge cases where not all letters of the symbol are capitalized (Amd, Msft, Spy)
            return asset_symbol.upper()

        # Takes care of cases where everything is uppercase (AMD, MSFT, SPY)
        else:
            asset_symbol += current_character
            current_letter_count += 1
    return asset_symbol.upper() # Return stock symbol (AMD, MSFT, SPY)

# Class to store details of a particular asset
# TODO: JSONify this
class Asset_Data:
    def __init__(self, stock_symbol):
        self.symbol = stock_symbol  # String - Stock Symbol - AMD/MSFT/SPY
        self.total_mentions = 0 # Integer - Total number of times the symbol was mentioned
        self.associated_sentences = [] # List of all associated sentences for the symbol to be analyzed for sentiment
        self.positive_comment_count = 0 # Total number of positive sentences
        self.negative_comment_count = 0 # Total number of negative sentences
        self.bullish = 0 # Percent of bullish mentions
        self.bearish = 0  # Percent of bearish mentions
        self.neutral = 0 # # Percent of neutral mentions
        self.sentiment = 0  # 0 is neutral

    def analyze_sentiment(self):
        # Instantiate a VADER instance
        sentiment_analyzer_instance = SentimentIntensityAnalyzer()
        
        neutral_comment_count = 0
        # Analyze each associated comment
        for current_comment in self.associated_sentences:
            sentiment = sentiment_analyzer_instance.polarity_scores(current_comment)
            if (sentiment["compound"] > .005) or (sentiment["pos"] > abs(sentiment["neg"])):
                self.positive_comment_count += 1
            elif (sentiment["compound"] < -.005) or (abs(sentiment["neg"]) > sentiment["pos"]):
                self.negative_comment_count += 1
            else:
                neutral_comment_count += 1
        
        # Store what percentage of comments are bullish/bearish/neutral
        self.bullish = int(self.positive_comment_count / len(self.associated_sentences) * 100)
        self.bearish = int(self.negative_comment_count / len(self.associated_sentences) * 100)
        self.neutral = int(neutral_comment_count / len(self.associated_sentences) * 100)

# Entry point for the program
if __name__ == "__main__":
    main()

