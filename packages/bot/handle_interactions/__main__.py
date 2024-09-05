import json
import logging
import os
from typing import Dict
import traceback

from slack_sdk import WebClient

from paper_post import PaperPost
from wrappers import update_message, send_ephemeral_message, send_message
from security_utils import handle_slack_request


def change_paper_status(client: WebClient, payload: Dict):
    channel = payload['container']['channel_id']
    logging.debug(f'Channel: {channel}')

    ts = payload['container']['message_ts']
    logging.debug(f'TS: {ts}')

    metadata = payload['message']['metadata']
    logging.debug(f'Metadata: {metadata}')

    action = payload['actions'][0]['action_id']
    logging.debug(f'Action: {action}')

    username = payload['user']['username']
    logging.debug(f'Username: {username}')

    logging.info(f'Reading post')
    paper_post = PaperPost.from_slack_metadata(metadata)

    logging.info('Updating state')
    paper_post.update_state(action, username)

    logging.info('Updating posts')
    update_message(
        client,
        channel=channel,
        ts=ts,
        blocks=paper_post.to_blocks(),
        metadata=paper_post.to_slack_metadata(),
        text=f"An error occurred while posting {paper_post.link}",
    )


def main(request):
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    logging.info('Verifying request')

    payload = handle_slack_request(request)
    if payload is None:
        logging.info('Request verifying failed')
        return {'statusCode': 401}

    logging.debug(f'Payload: {payload}')

    try:
        change_paper_status(client, payload)
    except Exception:
        send_ephemeral_message(
            client,
            text=traceback.format_exc(),
            user=payload['user']['id'],
            channel=payload['container']['channel_id'],
            thread_ts=payload['container']['thread_ts'],
        )
