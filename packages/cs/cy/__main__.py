import os

from feedgen.feed import FeedGenerator
import feedparser

from security_utils import check_secret_key
from feed_utils import copy_channel_metadata, convert_item


def main(event, context):
    if not check_secret_key(event):
        return {'statusCode': 401}

    parsed_feed = feedparser.parse('https://rss.arxiv.org/rss/cs.CY')

    feed = FeedGenerator()
    copy_channel_metadata(parsed_feed, feed)

    for item in parsed_feed['items']:
        if item['arxiv_announce_type'] in ('replace', 'replace-cross'):
            continue

        feed.add_entry(convert_item(item, parsed_feed['channel']['published']))

    return {
        'body': feed.rss_str(pretty=True).decode(),
        'headers': {'Content-Type': 'text/xml'},
    }


if __name__ == '__main__':
    print(main({}, {'key': os.getenv('AUTH_KEY')}))
