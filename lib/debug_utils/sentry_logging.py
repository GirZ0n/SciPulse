import os

import sentry_sdk


def setup_sentry_logging():
    if not (sentry_dsn := os.environ.get('SENTRY_DSN')):
        raise ValueError('SENTRY_DSN is not set')

    sentry_sdk.init(dsn=sentry_dsn)
