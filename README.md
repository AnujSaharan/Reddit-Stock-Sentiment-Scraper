# Reddit Stock Sentiment Scraper

 __Reddit Stock Sentiment Scraper__ utilizes a modified version of the VADER Sentiment Analysis library to classify Reddit comments from r/WallStreetBets and generate aggregate statistics.

## Instructions to Run

#### With Default Parameters

```python redditStockSentimentScraper.py```

__Default Subreddit:__ r/wallstreetbets
__Default Subreddit Sort:__ new
__Default Number of Posts to Scrape:__ 30
__Default Update Frequency:__ 3 minutes
__Default Plot Mode:__ Enabled

#### With Custom Parameters

```python redditStockSentimentScraper.py [ Name of Subreddit to scrape comments from ] [ Sort Mode for Subreddit ] [ Number of Posts on the Subreddit to look at ] [ Update Frequency ] [ Boolean to enable or disable PyPlot ]```

## Contents for environment_variables.json

Create a JSON file called environment_variables.json in the working directory of the project. This file holds the API information provided by Reddit.

```json
{
    "reddit_API": {
        "client_id": "client_id",
        "client_secret": "client_secret",
        "username": "reddit_username",
        "password": "reddit_password",
        "user_agent": "NULL"
    }
}
```
