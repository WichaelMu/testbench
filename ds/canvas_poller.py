import os
import asyncio
import json
import gzip
import shutil
import logging
import boto3
import requests

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

def check_defined_tables (canvas_defined):
    terraform_defined = [
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
        "live_assessments_assessments",
        "assignments",
        "quizzes",
        "rubric_associations",
        "rubric_assessments",
        "live_assessments_submissions",
        "lti_resource_links",
        "lti_line_items",
        "accounts",
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
        "context_external_tools",
        "pseudonyms",
        "communication_channels",
        "sis_batches"
    ]

    from functional import pseq

    and_op = pseq (canvas_defined) \
        .filter (lambda x: x in terraform_defined) \
        .to_list ()

    incoming_not_in_defined = pseq (canvas_defined) \
        .filter (lambda x: x not in terraform_defined) \
        .to_list ()

    terraform_not_in_canvas = pseq (terraform_defined) \
        .filter (lambda x: x not in canvas_defined) \
        .to_list ()

    dsc.write_json ('/tmp/terraform-defined.json', terraform_defined)
    dsc.write_json ('/tmp/canvas-defined.json', canvas_defined)

    print (terraform_not_in_canvas)

async def fetch ():
    secrets       = dsc.load_json ('secrets.json')['CANVAS']
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

def meth2 ():
    secrets       = dsc.load_json ('secrets.json')['CANVAS']
    client_id     = secrets['ClientId']
    client_secret = secrets['ClientSecret']

    access_token = requests.post (
        'https://api-gateway.instructure.com/ids/auth/login',
        data = { 'grant_type': 'client_credentials' },
        auth = (client_id, client_secret)
    ).json ()['access_token']

    namespace = 'canvas'
    job_id = 'eeac3f1b-04e4-4e43-9cf3-df424403aef2'
    response = requests.get(
        F'https://api-gateway.instructure.com/dap/job/{job_id}',
        headers = {
            'Authorization': F'Bearer {access_token}',
            'Accept': '*/*'
        }
    )

    print (response.json ())

if (__name__ == '__main__'):
    meth2 ()
    # asyncio.run (fetch ())
