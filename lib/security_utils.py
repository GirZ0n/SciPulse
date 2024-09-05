import os
import secrets
from typing import Dict


def check_secret_key(event: Dict) -> bool:
    return (key := event.get('key')) and key == os.getenv('AUTH_KEY')


if __name__ == '__main__':
    print(secrets.token_urlsafe(512))
