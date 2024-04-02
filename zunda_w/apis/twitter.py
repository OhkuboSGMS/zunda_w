import os

import tweepy


def tweet(title: str, url: str):
    """
    :param title: podcast title
    :param url: share_url
    https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
    https://github.com/tweepy/tweepy/blob/master/examples/API_v2/create_tweet.py
    :param text: 
    :return: 
    """
    client = tweepy.Client(
        consumer_key=os.environ["CONSUMER_KEY"],
        consumer_secret=os.environ["CONSUMER_SECRET"],
        access_token=os.environ["ACCESS_TOKEN"],
        access_token_secret=os.environ["ACCESS_TOKEN_SECRET"]
    )
    template = """新しいエピソードが配信されました
Listen to \"{title}\"
#ポッドキャスト #とにかくヨシ！
{url}"""

    res = client.create_tweet(text=template.format(title=title, url=url))
