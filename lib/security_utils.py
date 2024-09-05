import json
import os
import secrets
from typing import Dict, Optional

from slack_sdk.signature import SignatureVerifier
from urllib.parse import parse_qs


def handle_slack_request(event: Dict) -> Optional[Dict]:
    verifier = SignatureVerifier(os.environ["SLACK_SIGNING_SECRET"])

    body = event['http']['body']
    headers = event['http']['headers']

    if not verifier.is_valid_request(body, headers):
        return None

    return json.loads(parse_qs(body)['payload'][0])


def check_secret_key(event: Dict) -> bool:
    return (key := event.get('key')) and key == os.getenv('AUTH_KEY')


if __name__ == '__main__':
    print(secrets.token_urlsafe(512))
