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

global_access_token = ''

def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup

def refresh_environment ():
    pass

def get_environment ():
    global USE_PROD
    return USE_PROD

def get_wenvironment ():
    return 'prod' if get_environment () else 'nonprod'

def set_environment (environment):
    global USE_PROD
    global ENVIRONMENT

    match environment.upper ():
        case 'PROD':
            USE_PROD = True
        case 'NONPROD':
            USE_PROD = False
        case _:
            ENVIRONMENT = environment
            return

    ENVIRONMENT = 'PROD' if USE_PROD else 'NONPROD'
    refresh_environment ()

def set_access_token ():
    credentials = load_json ('secrets.json')
    client_id = credentials[ENVIRONMENT]['client_id']
    client_secret = credentials[ENVIRONMENT]['client_secret']
    token_url = credentials[ENVIRONMENT]['token_url']
    scope = credentials.get (ENVIRONMENT, {}).get ('scope', {})

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

def make_post_request (api_url, payload, raise_on_error=True):

    headers = {
        'Authorization': F'Bearer {global_access_token}',
        'Content-Type': 'application/json'
    }

    attempts = 1

    while True:
        response = requests.post (api_url, headers=headers, data=json.dumps (payload))

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

GENERATED_PARENT = 'generated'
def get_generated_path (program_name, key, extension = '.json'):
    fq_key = F'{get_wenvironment ()}-{key}{extension}'
    return os.path.join (GENERATED_PARENT, program_name, fq_key)

def save_generated (program_name, key, data):
    if not os.path.exists (GENERATED_PARENT):
        os.makedirs (GENERATED_PARENT)

    base_program_dir = os.path.join (GENERATED_PARENT, program_name)
    if not os.path.exists (base_program_dir):
        os.makedirs (base_program_dir)

    generated_fq_path = get_generated_path (program_name, key)
    write_json (generated_fq_path, data)
    return generated_fq_path

def load_generated (program_name, key):

    try:
        generated_fq_path = get_generated_path (program_name, key)
        loaded = load_json (generated_fq_path)
        return loaded

    except Exception as e:
        return []

def has_generated (program_name, key):
    if (not os.path.isdir (GENERATED_PARENT)):
        return False

    program_directory = os.path.join (GENERATED_PARENT, program_name)
    if (not os.path.isdir (program_directory)):
        return False

    return fexists (get_generated_path (program_name, key))

def write_json (path, data):
    with open (path, 'w') as w:
        json.dump (data, w)

def load_json (path):
    with open (path) as f:
        # print (F'Opening saved file {path}')
        return json.load (f)

def json_to_df (json, explode_on):
    json_df = pd.json_normalize (json)
    bomb_df = json_df.explode (explode_on, ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=[explode_on]), bomb_df[explode_on].apply (pd.Series) ], axis=1)

    return separated_df

def execute_parallel_requests (target_url, page_range, max_pages, extract_key, this_is_parallel = False):
    def execute_request (page):
        # Sorry, I think I'm about to throw up.
        # time.sleep (2)

        print (F'Current Page: {page} out of {max_pages}')
        response = make_get_request (F'{target_url}{page}')
        return response[extract_key]

        print ('Skipping! {extract_key} not found!\nRequested: {target_url}{page}\n\tValid keys are {response.keys ()}')

    if (this_is_parallel):
        return pseq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()
    return seq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()


def request_in_parallel (target_url, extract_key, program_name, key, division = 1):

    max_pages = 1 << 16

    print ('Making initial request...')
    initial_request = make_get_request (F'{target_url}1')
    max_pages = initial_request['_meta']['total']

    print ('Chunkifying...')

    # my nproc is 16. // 2 will return 8.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // division

    page_range_begin = 2 # We already made a GET REQ to ?page=1
    page_list = list (range (page_range_begin, max_pages + 1))

    print ('Collating in Parallel...')
    chunks = pseq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
    response_sequence = pseq (chunks).map (lambda x: execute_parallel_requests (target_url, x, max_pages, extract_key)).reduce (lambda x, y: x + y, []).to_list ()
    response_sequence += initial_request[extract_key] # Include the initial request.

    save_generated (program_name, key, response_sequence)

    return response_sequence

def try_parse_int (i):
    try:
        ip = int (i)
        return True
    except:
        return False
    return False

def to_xlsx (in_array, columns_to_keep, fq_output_path, sheet_name='Sheet1'):
    df = pd.DataFrame.from_records (in_array) if in_array else pd.DataFrame ()
    df = df.reindex (columns = columns_to_keep)
    df.to_excel (fq_output_path, index=False, sheet_name = sheet_name)
