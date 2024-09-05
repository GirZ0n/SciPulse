import logging
from typing import List, Optional, Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def find_channels_with_app(client: WebClient) -> List[str]:
    channels = client.conversations_list(types=['public_channel', 'private_channel']).data['channels']
    return [channel['id'] for channel in channels if channel['is_member']]


def send_message(
    client: WebClient,
    *,
    channel: str,
    text: Optional[str] = None,
    blocks: Optional[List] = None,
    thread_ts: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
            thread_ts=thread_ts,
            metadata=metadata,
            unfurl_links=False,
            unfurl_media=False,
        )
        return response["message"]["ts"]
    except SlackApiError as e:
        logger.error(f"Error posting message: {repr(e)}")
        return None


def update_message(
    client: WebClient,
    *,
    channel: str,
    ts: str,
    text: Optional[str] = None,
    blocks: Optional[List] = None,
    metadata: Optional[Dict] = None,
):
    try:
        client.chat_update(
            channel=channel,
            ts=ts,
            text=text,
            blocks=blocks,
            metadata=metadata,
        )
    except SlackApiError as e:
        logger.error(f"Error posting message: {repr(e)}")


def send_ephemeral_message(
    client: WebClient,
    *,
    channel: str,
    user: str,
    text: Optional[str] = None,
    thread_ts: Optional[str] = None,
):
    try:
        client.chat_postEphemeral(channel=channel, user=user, text=text, thread_ts=thread_ts)
    except SlackApiError as e:
        logger.error(f"Error posting message: {repr(e)}")
