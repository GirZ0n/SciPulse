import json
import logging
import os

from slack_sdk import WebClient

from slack_utils.paper_post import PaperPost
from slack_utils.wrappers import update_message
from security_utils import check_secret_key

logger = logging.getLogger(__name__)


def main(event, context):
    if not check_secret_key(event):
        return {'statusCode': 401}

    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    logger.info('Receiving interaction action')

    payload = json.loads(event['payload'])
    logger.debug(f'Payload: {event["payload"]}')

    channel = payload['container']['channel_id']
    logger.debug(f'Channel: {channel}')

    ts = payload['container']['message_ts']
    logger.debug(f'TS: {ts}')

    metadata = payload['message']['metadata']
    logger.debug(f'Metadata: {metadata}')

    action = payload['actions'][0]['action_id']
    logger.debug(f'Action: {action}')

    username = payload['user']['username']
    logger.debug(f'Username: {username}')

    logger.info(f'Reading post')
    paper_post = PaperPost.from_slack_metadata(metadata)

    logger.info('Updating state')
    paper_post.update_state(action, username)

    logger.info('Updating posts')
    update_message(
        client,
        channel=channel,
        ts=ts,
        blocks=paper_post.to_blocks(),
        metadata=paper_post.to_slack_metadata(),
    )
