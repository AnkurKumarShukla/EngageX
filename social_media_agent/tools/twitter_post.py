import tweepy
import os
#load env
from dotenv import load_dotenv
load_dotenv()



def post_to_twitter(content: str) -> str:
    """Tool to post content to Twitter using v2 API."""
    return "This is a test tweet from FastAPI!==========>  \n"+content

    # try:
    #     # Authenticate with v2 API (Bearer Token)
    #     client = tweepy.Client(
    #         bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
    #         consumer_key=os.getenv("TWITTER_API_KEY"),
    #         consumer_secret=os.getenv("TWITTER_API_SECRET_KEY"),
    #         access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    #         access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    #     )

    #     # Post Tweet
    #     tweet = client.create_tweet(text=content)

    #     # print(f"Posted successfully! Tweet URL: https://twitter.com/user/status/{tweet.data['id']}")
    #     return f"Posted successfully! Tweet URL: https://twitter.com/user/status/{tweet.data['id']}"
    # except Exception as e:
    #     return f"Failed to post to Twitter: {str(e)}"


# print(post_to_twitter("tweet about my latest give away . who so every post goes viral will get shoes "))