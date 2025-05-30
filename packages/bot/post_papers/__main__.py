import logging
import operator
import os
import time
from typing import List

import feedparser
from feedparser import FeedParserDict
from slack_sdk import WebClient

from wrappers import find_channels_with_app, send_message
from paper_post import PaperPost


TAG_WHITELIST = ('cs.HC', 'cs.AI', 'cs.CY', 'cs.SE', 'cs.LG', 'cs.CL', 'cs.IR', 'cs.PL')


def _fetch_papers_from_arxiv_tag(subject: str) -> List[FeedParserDict]:
    parsed_feed = feedparser.parse(f'https://rss.arxiv.org/rss/{subject}')
    return [item for item in parsed_feed['items'] if item['arxiv_announce_type'] not in ('replace', 'replace-cross')]


def fetch_arxiv_papers() -> List[FeedParserDict]:
    cs_cy_papers = _fetch_papers_from_arxiv_tag('cs.CY')
    logging.debug(f'Fetched {len(cs_cy_papers)} CS.CY papers')

    cs_hc_papers = _fetch_papers_from_arxiv_tag('cs.HC')
    logging.debug(f'Fetched {len(cs_hc_papers)} CS.HC papers')

    unfiltered_arxiv_papers = cs_cy_papers + cs_hc_papers
    logging.debug(f'Fetched {len(unfiltered_arxiv_papers)} unfiltered papers')

    unique_arxiv_papers = list({paper['link']: paper for paper in unfiltered_arxiv_papers}.values())
    logging.debug(f'Fetched {len(unique_arxiv_papers)} unique papers')

    return [
        paper
        for paper in unique_arxiv_papers
        if all(map(lambda tag: tag in TAG_WHITELIST, set(map(operator.itemgetter('term'), paper['tags']))))
    ]


def main():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    arxiv_papers = fetch_arxiv_papers()
    logging.info(f'Fetched {arxiv_papers} arxiv papers')

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
                text=f"An error occurred while posting {paper_post.link}",
            )

            time.sleep(1)  # Better to sleep for 1 second to avoid spamming Slack

        logging.info(f'Posting to {channel} completed')


if __name__ == '__main__':
    main()
