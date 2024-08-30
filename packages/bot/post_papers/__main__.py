import logging
import operator
import os
from typing import Optional, List

from feedgen.feed import FeedGenerator
import feedparser
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import time

from html2text import html2text as ht

from utils import copy_channel_metadata, convert_item, check_secret_key

# client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
channel_id = "C07JTPTK1RD"
logger = logging.getLogger(__name__)


def send_message(
        client: WebClient,
        *,
        message: Optional[str] = None,
        blocks: Optional[List] = None,
        thread_ts: Optional[str] = None,
) -> Optional[str]:
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks,
            thread_ts=thread_ts,
        )
        return response["message"]["ts"]
    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")
        return None


def get_cs_cy_items() -> List:
    parsed_feed = feedparser.parse('https://rss.arxiv.org/rss/cs.CY')

    return [
        item
        for item in parsed_feed['items']
        if item['arxiv_announce_type'] not in ('replace', 'replace-cross')
    ]


def get_cs_hc_items() -> List:
    parsed_feed = feedparser.parse('https://rss.arxiv.org/rss/cs.HC')

    return [
        item
        for item in parsed_feed['items']
        if not (
                item['arxiv_announce_type'] in ('replace', 'replace-cross')
                or 'cs.CY' in set(map(operator.itemgetter('term'), item['tags']))
        )
    ]


# def retrieve_parent_message_ts(client: WebClient):
#     cur_ts = str(time.time())
#
#     result = client.conversations_history(
#         channel=channel_id,
#         inclusive=True,
#         latest=cur_ts,
#         limit=1
#     )
#
#     parent_ts = result["messages"][0]["ts"]
#     return parent_ts


# def feed_item_to_message_text(item):
#     return f"""*<{item['link']}|{item['title']}>*
#
# *Abstract:* {ht(item['description'].split(' ', 5)[5], bodywidth=0)}"""


def get_paper_description_blocks(item):
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{item['title']}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Link:* {item['link']}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Abstract:*\n{ht(item['description'].split(' ', 5)[5], bodywidth=0)}"
            }
        }
    ]


actions_base = [
    {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": "Accept"
        },
        "style": "primary",
        "value": "accepted",
        "action_id": "accept"
    },
    {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": "Reject"
        },
        "style": "danger",
        "value": "rejected",
        "action_id": "reject"
    }
]

actions_active = [
    {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": "Cancel selection"
        },
        "value": "canceled",
        "action_id": "cancel"
    }
]


def feed_item_to_message_blocks_base(item):
    return get_paper_description_blocks(item) + [{
        "type": "actions",
        "elements": actions_base
    }]
    # return [
    #     {
    #         "type": "header",
    #         "text": {
    #             "type": "plain_text",
    #             "text": f"{item['title']}"
    #         }
    #     },
    #     {
    #         "type": "section",
    #         "text": {
    #             "type": "mrkdwn",
    #             "text": f"*Link:* {item['link']}"
    #         }
    #     },
    #     {
    #         "type": "section",
    #         "text": {
    #             "type": "mrkdwn",
    #             "text": f"*Abstract:*\n{ht(item['description'].split(' ', 5)[5], bodywidth=0)}"
    #         }
    #     },
    #     {
    #         "type": "actions",
    #         "elements": [
    #             {
    #                 "type": "button",
    #                 "text": {
    #                     "type": "plain_text",
    #                     "text": "Accept"
    #                 },
    #                 "style": "primary",
    #                 "value": "accept"
    #             },
    #             {
    #                 "type": "button",
    #                 "text": {
    #                     "type": "plain_text",
    #                     "text": "Reject"
    #                 },
    #                 "style": "danger",
    #                 "value": "reject"
    #             }
    #         ]
    #     }
    # ]


def feed_item_to_message_blocks_active(item, block_actions):
    username = block_actions["user"]["username"]
    action_value = block_actions["actions"][0]["value"]
    return get_paper_description_blocks(item) + [{
        "type": "divider"
    }] + [{
        "type": "context",
        "elements": [
            {
                "type": "image",
                "image_url": "https://pbs.twimg.com/profile_images/625633822235693056/lNGUneLX_400x400.jpg",
                "alt_text": "cute cat"
            },
            {
                "type": "mrkdwn",
                "text": f"@{username} has {action_value} this paper."
            }
        ]
    }] + [{
        "type": "divider"
    }] + [{
        "type": "actions",
        "elements": actions_active
    }]


def main():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    thread_ts = send_message(client, message=f'Papers feed for {time.strftime("%Y-%m-%d")}')

    cs_cy_items = get_cs_cy_items()
    cs_hc_items = get_cs_hc_items()

    items = cs_cy_items + cs_hc_items

    for item in items:
        send_message(client, blocks=feed_item_to_message_blocks_base(item), thread_ts=thread_ts)


if __name__ == '__main__':
    main()
