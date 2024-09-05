import json
import logging
import os

from slack_sdk import WebClient

from paper_post import PaperPost
from wrappers import update_message
from security_utils import check_secret_key


def main(event, context):
    if not check_secret_key(event):
        return {'statusCode': 401}

    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    logging.info('Receiving interaction action')

    payload = json.loads(event['payload'])
    logging.debug(f'Payload: {event["payload"]}')

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
