import gzip
from io import BytesIO
import json
import os
import pathlib

from bs4 import BeautifulSoup as bs
from slack_sdk import WebClient
import requests

from .emailer import send_email


DATA_FILEPATH = pathlib.Path(__file__).parent.resolve() / "data" / "data.json"


def read_data_file():
    """read previously seen links from file."""
    with open(DATA_FILEPATH) as fh:
        seen = json.load(fh)
    return seen


def write_data_file(data):
    with open(DATA_FILEPATH, "w") as fh:
        json.dump(data, fh, indent=4)


def get_yahoo_articles():
    # URL comes from:
    # https://uk.news.yahoo.com/robots.txt
    url = (
        "https://uk.news.yahoo.com/sitemaps/"
        "news-sitemap_articles_GB_en-GB.xml.gz"
    )
    resp = requests.get(url, stream=True)
    with gzip.open(BytesIO(resp.content), "rb") as fh:
        content = fh.read()
    soup = bs(content)
    return {
        x.find("news:title").text: x.find("loc").text
        for x in soup.find_all("url")
    }


def get_ff_articles():
    url = os.environ["YAHOO_FEED_URL"]
    resp = requests.get(url)
    soup = bs(resp.content)
    return {
        x.find("title").text: x.find("description").text
        for x in soup.find_all("item")
    }


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
                            article["description"],
                        ),
                    },
                },
            ]
        )


def run():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    slack_channel_id = os.environ["SLACK_CHANNEL_ID"]

    from_address = os.environ["FROM_ADDRESS"]
    from_pwd = os.environ["FROM_PWD"]
    to_addresses = os.environ["TO_ADDRESSES"]
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = os.environ["SMTP_PORT"]

    seen = read_data_file()

    yahoo_articles = get_yahoo_articles()
    ff_articles = get_ff_articles()
    unseens = [
        {
            "url": yahoo_articles[title],
            "title": title,
            "description": description,
        }
        for title, description in ff_articles.items()
        if title in yahoo_articles
        and yahoo_articles[title] not in seen
    ]

    if not unseens:
        # nothing new, so quit
        return

    write_data_file([u["url"] for u in unseens] + seen)

    # send previously unseen articles to slack
    send_articles_to_slack(unseens, slack_token, slack_channel_id)

    # send an email with the recently unseen articles
    send_email(
        unseens,
        from_address,
        from_pwd,
        to_addresses,
        smtp_server,
        smtp_port,
    )


if __name__ == "__main__":
    run()
