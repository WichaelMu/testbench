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

import dscore as dsc

from ulid import monotonic as ulid

STRF_TIME = '%Y-%m-%dT%H:%M:%SZ'

DATABASE = 'canvas'
TABLE    = 'sis_batches'

def get_from_date ():
    now_iso = datetime.now (timezone.utc)
    default_date = now_iso - timedelta (days = 30)
    from_date = parser.isoparse (default_date.strftime (STRF_TIME))
    return from_date

def check_defined_tables (incoming_tables):
    defined = [
        "content_participation_counts",
        "courses",
        "users",
        "content_participations",
        "context_module_progressions",
        "context_modules",
        "content_tags",
        "master_courses_master_content_tags",
        "master_courses_child_content_tags",
        "learning_outcome_results",
        "learning_outcome_question_results",
        "learning_outcomes",
        "assessment_questions",
        "live_assessment_assessments",
        "assignments",
        "quizzes",
        "rubric_associations",
        "rubric_assessments",
        "live_assessments_submissions",
        "lti_resource_links",
        "lti_line_items",
        "accounts",
        "context_external_tools",
        "quiz_submissions",
        "score_statistics",
        "scores",
        "assignment_groups",
        "enrollments",
        "grading_periods",
        "submissions",
        "attachments",
        "attachment_associations",
        "canvadocs_association_contexts",
        "conversation_messages",
        "groups",
        "media_objects",
        "lti_results",
        "originality_reports",
        "submission_comments",
        "pseudonyms",
        "communication_channels",
        "sis_batches"
    ]

    from functional import pseq

    and_op = pseq (incoming_tables) \
        .filter (lambda x: x in defined) \
        .to_list ()

    incoming_not_in_defined = pseq (incoming_tables) \
        .filter (lambda x: x not in defined) \
        .to_list ()

    defined_not_in_incoming = pseq (defined) \
        .filter (lambda x: x not in incoming_tables) \
        .to_list ()

    print (F'length defined: {len (defined)}')
    print (F'length incoming: {len (incoming_tables)}')


    print (F'length and_op: {len (and_op)}')

    print (defined_not_in_incoming)

async def fetch ():
    secrets = dsc.load_json ('secrets.json')['CANVAS']
    client_id     = secrets['ClientId']
    client_secret = secrets['ClientSecret']

    credentials = Credentials.create (
        client_id     = client_id,
        client_secret = client_secret
    )

    try:
        logging.info ('making DAPClient')
        async with DAPClient('https://api-gateway.instructure.com', credentials) as session:
            logging.info ('building IncrementalQuery')

            query = IncrementalQuery (
                format  = Format.JSONL,
                mode    = None,
                since   = get_from_date (),
                until   = None,
            )

            logging.info ('downloading table data')

            # await session.download_table_data (
            #     DATABASE, TABLE, query, '/tmp/canvas_poller_out', decompress=False
            # )

            tables = await session.get_tables (DATABASE)

            check_defined_tables (tables)

            logging.info ('what')

            print ('Done!')

    except RuntimeError as ee:
        print ('w')
        print (ee)

    except Exception as e:
        print ('error')
        print (e)

if (__name__ == '__main__'):
    asyncio.run (fetch ())
