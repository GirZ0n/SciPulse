import logging
import operator
import os
import time
from typing import List

import feedparser
from feedparser import FeedParserDict
from slack_sdk import WebClient

from slack_utils.wrappers import find_channels_with_app, send_message
from slack_utils.paper_post import PaperPost


def fetch_cs_cy_papers() -> List[FeedParserDict]:
    parsed_feed = feedparser.parse('https://rss.arxiv.org/rss/cs.CY')
    return [item for item in parsed_feed['items'] if item['arxiv_announce_type'] not in ('replace', 'replace-cross')]


def fetch_cs_hc_papers() -> List[FeedParserDict]:
    parsed_feed = feedparser.parse('https://rss.arxiv.org/rss/cs.HC')

    return [
        item
        for item in parsed_feed['items']
        if not (
            item['arxiv_announce_type'] in ('replace', 'replace-cross')
            or 'cs.CY' in set(map(operator.itemgetter('term'), item['tags']))
        )
    ]


def main():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    logging.info('Fetching papers')

    cs_cy_papers = fetch_cs_cy_papers()
    logging.debug(f'Fetched {len(cs_cy_papers)} CS.CY papers')

    cs_hc_papers = fetch_cs_hc_papers()
    logging.debug(f'Fetched {len(cs_hc_papers)} CS.HC papers')

    arxiv_papers = cs_cy_papers + cs_hc_papers
    logging.debug(f'Fetched {len(arxiv_papers)} papers')

    channels = find_channels_with_app(client)
    logging.debug(f'Found {len(channels)} channels where the app is a member')

    for channel in channels:
        logging.debug(f'Posting to {channel}')

        if not arxiv_papers:
            send_message(
                client,
                channel=channel,
                text=f'There are no papers for {time.strftime("%d-%m-%Y")} :chipi-chipi-chapa-chapa:',
            )

            continue

        thread_ts = send_message(client, channel=channel, text=f'Papers for {time.strftime("%d-%m-%Y")}')
        logging.debug(f'TS: {thread_ts}')

        for arxiv_paper in arxiv_papers:
            paper_post = PaperPost.from_arxiv(arxiv_paper)

            logging.debug(f'Posting: {paper_post.link}')
            send_message(
                client,
                channel=channel,
                thread_ts=thread_ts,
                blocks=paper_post.to_blocks(),
                metadata=paper_post.to_slack_metadata(),
            )

            time.sleep(1)  # Better to sleep for 1 second to avoid spamming Slack

        logging.info(f'Posting to {channel} completed')


if __name__ == '__main__':
    main()
