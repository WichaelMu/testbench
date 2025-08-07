import os
import asyncio
import json
import gzip
import shutil
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from botocore.config import Config
from botocore.exceptions import ClientError
from dateutil import parser
from datetime import datetime, timezone, timedelta
from dap.api import DAPClient
from dap.dap_types import Credentials, Format, IncrementalQuery

from ulid import monotonic as ulid

async def fetch ():
    client_id     = 'check the secrets'
    client_secret = 'check the secrets'

    credentials = Credentials.create (
        client_id     = client_id,
        client_secret = client_secret
    )

    async with DAPClient('https://api-gateway.instructure.com', credentials) as session:
        logging.info ('DAPClient successful')

        query = IncrementalQuery (
            format=Format.JSONL,
            mode=None,
            since=parser.isoparse ('2025-08-06T04:07:48Z'),
            until=None,
        )

        logging.info ('query successful')

        await session.download_table_data (
            'canvas', 'context_module_progressions', query, '/tmp/canvas_poller_out', decompress=False
        )

        print ('Done!')

if (__name__ == '__main__'):
    asyncio.run (fetch ())
