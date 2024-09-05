from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from feedparser import FeedParserDict


def copy_channel_metadata(original: FeedParserDict, new: FeedGenerator):
    new.title(original['channel']['title'])
    new.link(href=original['channel']['link'])
    new.description(original['channel']['description'])
    new.language(original['channel']['language'])
    new.lastBuildDate(original['channel']['updated'])
    new.managingEditor(original['channel']['author'])
    new.pubDate(original['channel']['published'])


def convert_item(original: FeedParserDict, date: str) -> FeedEntry:
    entry = FeedEntry()

    entry.title(original['title'])
    entry.link(href=original['link'])
    entry.description('\n')
    entry.guid(original['guid'])
    entry.pubDate(date)

    entry.category(
        [
            {
                'term': tag['term'],
                'scheme': tag['scheme'] if tag['scheme'] is not None else None,
                'label': tag['label'] if tag['label'] is not None else tag['term'],
            }
            for tag in original['tags']
        ]
    )

    return entry
