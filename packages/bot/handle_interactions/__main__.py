import os
from typing import Dict
import traceback

from slack_sdk import WebClient

from paper_post import PaperPost
from wrappers import update_message, send_ephemeral_message
from security_utils import handle_slack_request

import logfire

logfire.configure(service_name="Handle Interactions")
logfire.instrument_pymongo()


@logfire.instrument('Changing paper structure')
def change_paper_status(client: WebClient, payload: Dict):
    channel = payload['container']['channel_id']
    logfire.debug(f'Channel: {channel}')

    ts = payload['container']['message_ts']
    logfire.debug(f'TS: {ts}')

    metadata = payload['message']['metadata']
    logfire.debug(f'Metadata: {metadata}')

    action = payload['actions'][0]['action_id']
    logfire.debug(f'Action: {action}')

    username = payload['user']['username']
    logfire.debug(f'Username: {username}')

    logfire.info(f'Reading post')
    paper_post = PaperPost.from_slack_metadata(metadata)

    logfire.info('Updating state')
    paper_post.update_state(action, username)

    logfire.info('Updating posts')
    update_message(
        client,
        channel=channel,
        ts=ts,
        blocks=paper_post.to_blocks(),
        metadata=paper_post.to_slack_metadata(),
        text=f"An error occurred while posting {paper_post.link}",
    )


@logfire.instrument('Handling interaction')
def _main(request):
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)

    logfire.info('Verifying request')
    payload = handle_slack_request(request)
    if payload is None:
        logfire.info('Request verifying failed')
        return {'statusCode': 401}

    logfire.debug(f'Payload: {payload}')

    try:
        change_paper_status(client, payload)
    except Exception as e:
        logfire.exception(f'Error occurred while handling interaction: {e}')

        send_ephemeral_message(
            client,
            text=traceback.format_exc(),
            user=payload['user']['id'],
            channel=payload['container']['channel_id'],
            thread_ts=payload['container']['thread_ts'],
        )


# DigitalOcean can't find a main function wrapped in decorator
def main(request):
    _main(request)
