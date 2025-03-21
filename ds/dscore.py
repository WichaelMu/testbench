import os
import time
import requests
import json
import multiprocessing as mp

import pandas as pd
from functional import pseq, seq
from bs4 import BeautifulSoup

# Environment settings.
USE_PROD = False
ENVIRONMENT = 'NO_ENVIRONMENT'

COLLATED_COURSES_FPATH = F'{ENVIRONMENT}-collated-courses.json'
COLLATED_SUBJECTS_FPATH = F'{ENVIRONMENT}-collated-subjects.json'
COLLATED_FACULTY_COURSE_FPATH = F'{ENVIRONMENT}-collated-faculty-courses.json'

global_access_token = ''

def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup

def refresh_environment ():
    global COLLATED_COURSES_FPATH
    global COLLATED_SUBJECTS_FPATH
    global COLLATED_FACULTY_COURSE_FPATH

    COLLATED_COURSES_FPATH = F'{ENVIRONMENT}-collated-courses.json'
    COLLATED_SUBJECTS_FPATH = F'{ENVIRONMENT}-collated-subjects.json'
    COLLATED_FACULTY_COURSE_FPATH = F'{ENVIRONMENT}-collated-faculty-courses.json'

def get_environment ():
    global USE_PROD
    return USE_PROD

def get_wenvironment ():
    return 'PROD' if get_environment () else 'NONPROD'

def set_environment (environment):
    global USE_PROD
    global ENVIRONMENT

    match environment:
        case 'PROD' | True:
            USE_PROD = True
        case 'NONPROD' | True:
            USE_PROD = False
        case _:
            raise Exception ('what')

    ENVIRONMENT = 'PROD' if USE_PROD else 'NONPROD'
    refresh_environment ()

def set_access_token ():
    credentials = load_json ('secrets.json')
    client_id = credentials[ENVIRONMENT]['client_id']
    client_secret = credentials[ENVIRONMENT]['client_secret']
    token_url = credentials[ENVIRONMENT]['token_url']
    scope = credentials[ENVIRONMENT]['scope']

    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }

    response = requests.post (token_url, data=payload)
    response.raise_for_status ()
    token_data = response.json ()

    global global_access_token
    global_access_token = token_data['access_token']

def get_api_url ():
    return 'https://data.curriculum.nonprod.cortex.uts.edu.au' if not get_environment () else 'https://data.curriculum.cortex.uts.edu.au'

def make_get_request (api_url, raise_on_error=True):
    headers = { 'Authorization': F'Bearer {global_access_token}' }
    attempts = 1

    while True:
        response = requests.get (api_url, headers=headers)

        # if (raise_on_error):
        #     response.raise_for_status ()

        if (response.status_code == 200):
            if (attempts > 1):
                print (F'Retry successful on attempt: {attempts}')
            return response.json ()

        if (response.status_code == 403 or response.status_code == 401):
            print (F'Failed: {response.status_code}. Retrieving and setting new access token...')
            set_access_token ()
            headers = { 'Authorization': F'Bearer {global_access_token}' }

        print (F'\tEncountered {response.status_code}. Retrying {api_url}...')
        time.sleep (5)
        attempts += 1
        print (F'\tRetrying last. Attempt #: {attempts}...')

def fexists (fpath):
    return os.path.isfile (fpath)

def write_json (path, data):
    with open (path, 'w') as w:
        json.dump (data, w)

def load_json (path):
    with open (path) as f:
        print (F'Opening saved file {path}')
        return json.load (f)

def json_to_df (json, explode_on):
    json_df = pd.json_normalize (json)
    bomb_df = json_df.explode (explode_on, ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=[explode_on]), bomb_df[explode_on].apply (pd.Series) ], axis=1)

    return separated_df

def execute_parallel_requests (target_url, page_range, max_pages, extract_key, this_is_parallel = False):
    def execute_request (page):
        # Sorry, I think I'm about to throw up.
        time.sleep (2)

        print (F'Current Page: {page} out of {max_pages}')
        response = make_get_request (F'{target_url}{page}')
        return response[extract_key]

    if (this_is_parallel):
        return pseq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()
    return seq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()


def request_in_parallel (target_url, extract_key, fpath):

    max_pages = 1 << 16

    print ('Making initial request...')
    initial_request = make_get_request (F'{target_url}1')
    max_pages = initial_request['_meta']['total']

    print ('Chunkifying...')

    # my nproc is 16. // 2 will return 8.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // 2

    page_range_begin = 2 # We already made a GET REQ to ?page=1
    page_list = list (range (page_range_begin, max_pages + 1))

    print ('Collating in Parallel...')
    chunks = pseq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
    response_sequence = pseq (chunks).map (lambda x: execute_parallel_requests (target_url, x, max_pages, extract_key)).reduce (lambda x, y: x + y, []).to_list ()
    response_sequence += initial_request[extract_key] # Include the initial request.

    write_json (fpath, response_sequence)

    return response_sequence

def get_faculty_courses_lookup ():
    with open (COLLATED_FACULTY_COURSE_FPATH, 'r') as courses:
        deserialised = json.load (courses)
        courses_lookup = pseq (deserialised) \
            .filter (lambda x: 'code' in x.keys ()) \
            .map (lambda x: { x['code']: x }) \
            .reduce (lambda x, y: x | y)
        return courses_lookup
    return {}

def get_courses ():
    if (not fexists (COLLATED_COURSES_FPATH)):
        print (F'No saved file found, creating {COLLATED_COURSES_FPATH}...')
        return request_in_parallel (F'{get_api_url ()}/courses?debug_empty_arrays=true&debug_empty_strings=true&debug_null_values=true&page=', 'courses', COLLATED_COURSES_FPATH)

    return load_json (COLLATED_COURSES_FPATH)

def get_subjects ():
    if (not fexists (COLLATED_SUBJECTS_FPATH)):
        print (F'No saved file found, creating {COLLATED_SUBJECTS_FPATH}...')
        return request_in_parallel (F'{get_api_url ()}/subjects?debug_empty_arrays=true&debug_empty_strings=true&debug_null_values=true&page=', 'subjects', COLLATED_SUBJECTS_FPATH)

    return load_json (COLLATED_SUBJECTS_FPATH)

def get_faculty_courses (faculty_code):
    if (not os.path.isfile (COLLATED_FACULTY_COURSE_FPATH)):
        print (F'No saved file found, creating {COLLATED_FACULTY_COURSE_FPATH}...')
        return request_in_parallel (F'{get_api_url ()}/faculties/{faculty_code}/courses?debug_empty_arrays=true&debug_empty_strings=true&debug_null_values=true&page=', 'courses', COLLATED_FACULTY_COURSE_FPATH)

    return load_json (COLLATED_FACULTY_COURSE_FPATH)
