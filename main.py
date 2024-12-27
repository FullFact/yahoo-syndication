import os
import json
import requests
from bs4 import BeautifulSoup as bs
from slack_sdk import WebClient


slack_token = os.environ["SLACK_BOT_TOKEN"]
slack_channel_id = os.environ["SLACK_CHANNEL_ID"]
search_url = os.environ["SEARCH_URL"]


def run():
    # read previously seen links from file
    with open("data/data.json") as fh:
        seen = json.load(fh)

    # parse feed
    r = requests.get(search_url)
    soup = bs(r.text, features="html.parser")
    items_soup = soup.find_all("div", class_="NewsArticle")
    items = [
        {
            "title": item_soup.h4.a.text,
            "description": item_soup.p.text,
            "url": item_soup.h4.a["href"],
            "img_url": item_soup.img["src"],
            "img_alt": item_soup.img["alt"],

        } for item_soup in items_soup
    ]
    # reverse it, and make URLs unique
    items = list({i["url"]: i for i in items}.values())[::-1]

    # find any unseen items
    unseens = [
        item
        for item in items
        if item["url"] not in seen
    ]

    if not unseens:
        return

    # write to file
    with open("data/data.json", "w") as fh:
        json.dump(unseens + seen, fh, indent=4)

    # write previously unseen items to slack
    slack_client = WebClient(token=slack_token)
    for unseen in unseens:
        slack_client.chat_postMessage(
            channel=slack_channel_id,
            text="{}: {}".format(unseen["title"], unseen["url"]),
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "<{}|{}>\n{}".format(
                            unseen["url"],
                            unseen["title"],
                            unseen["description"]
                        ),
                    },
                },
            ]
        )


if __name__ == "__main__":
    run()
