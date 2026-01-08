import math
import json
import os
import logging
import boto3
import yaml
import datetime

from functional import seq, pseq

import api_common as apicom
from api_common import (
    load_yaml_s3,
    validate_pagination,
    get_secret_envar_name,
    get_secret_envar_host,
    get_envar_ENV,
    str_to_bool,
    transform_and_clean_data,
    get_secret,
    render_error_with_message,
    create_oauth2client,
    get_pagination_params,
    extract_code,
)

import dscore as dsc

PROGRAM_NAME = 'master-record-status-draft-support'

def main ():

    dsc.set_environment ('PROD')
    items = []

    if (dsc.has_generated (PROGRAM_NAME, 'cleaned-items')):
        items = dsc.load_generated (PROGRAM_NAME, 'cleaned-items')

    else:
        os_response = dsc.load_json ('courses.json')
        items = transform_and_clean_data(os_response, {})
        dsc.save_generated (PROGRAM_NAME, 'cleaned-items', items)

    draft_courses: list  = seq (items) \
        .filter (lambda x: 'master_record_status' in x.keys ()) \
        .filter (lambda x: 'value' in x['master_record_status'].keys ()) \
        .filter (lambda x: x['master_record_status']['value'] == 'draft')

    draft_statuses = seq (draft_courses) \
        .map (lambda x: x['status'])

    print (draft_statuses.to_list ())

if (__name__ == '__main__'):
    main ()
