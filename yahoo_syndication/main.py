import json
import os
import pathlib

from bs4 import BeautifulSoup as bs
from slack_sdk import WebClient
import requests

from .emailer import send_email


data_filepath = pathlib.Path(__file__).parent.resolve() / "data" / "data.json"


def read_data_file():
    # read previously seen links from file
    with open(data_filepath) as fh:
        seen = json.load(fh)
    return seen


def write_data_file(data):
    with open(data_filepath, "w") as fh:
        json.dump(data, fh, indent=4)


def parse_feed(url):
    r = requests.get(url)
    soup = bs(r.text, features="html.parser")
    items_soup = soup.find_all("div", class_="NewsArticle")[::-1]
    return [
        {
            "title": item_soup.h4.a.text,
            "description": item_soup.p.text,
            "url": item_soup.h4.a["href"],
            "img_url": item_soup.img["src"],
            "img_alt": item_soup.img["alt"],

        } for item_soup in items_soup
    ]


def send_articles_to_slack(articles, slack_token, slack_channel_id):
    slack_client = WebClient(token=slack_token)
    for article in articles:
        slack_client.chat_postMessage(
            channel=slack_channel_id,
            text=article["title"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "<{}|{}>\n{}".format(
                            article["url"],
                            article["title"],
                            article["description"]
                        ),
                    },
                },
            ]
        )


def run():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    slack_channel_id = os.environ["SLACK_CHANNEL_ID"]
    search_url = "https://uk.news.search.yahoo.com/search?p=site%3Afullfact.org&ei=UTF-8&fr2=sortBy&context=gsmcontext%3A%3Asort%3A%3Atime&fr=uh3_news_web"

    seen = read_data_file()

    feed_articles = parse_feed(search_url)

    # find any unseen articles
    unseens = [
        article
        for article in feed_articles
        if article["url"] not in seen
    ]

    if not unseens:
        # nothing new, so quit
        return

    write_data_file([u["url"] for u in unseens] + seen)

    # send previously unseen articles to slack
    send_articles_to_slack(unseens, slack_token, slack_channel_id)

    # send an email with the recently unseen articles
    send_email(unseens)


if __name__ == "__main__":
    run()
