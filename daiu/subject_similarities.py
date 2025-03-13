import os
import os.path
import time
import requests
import json
import ast

import numpy
import pandas as pd
import duckdb
from functional import pseq, seq
from bs4 import BeautifulSoup

# Environment settings.
USE_PROD = False
ENVIRONMENT = 'PROD' if USE_PROD else 'NONPROD'

# 'Cached' files.
COLLATED_FPATH = F'{ENVIRONMENT}-collated.json'
COMBINED_FPATH = F'{ENVIRONMENT}-combined.json'

# Search results.
THRESHOLD=75
APPROACH_FPATH = F'{ENVIRONMENT}-similar-approaches.json'
OUTCOMES_FPATH = F'{ENVIRONMENT}-similar-outcomes.json'
FILTERED_EMPTIES_FPATH = F'{ENVIRONMENT}-filtered-empties.json'
SUBJECT_LOOKUP_TABLE_FPATH = F'{ENVIRONMENT}-subject-lookup.json'


global_access_token = ''


def exec_sql (q):
    return duckdb.query (q).to_df ()

def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup

def normalise_m (m):
    return round ((m - float (1)) * float (100))

def set_access_token (use_prod=False):
    credentials = load_json ('SECRETS.JSON')
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

def get_api_url (use_prod=False):
    return 'https://data.curriculum.nonprod.cortex.uts.edu.au' if not use_prod else 'https://data.curriculum.cortex.uts.edu.au'

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
            set_access_token (USE_PROD)
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

def parallel_collate_all_subjects (all_subjects_page_url, page_range, max_pages):
    def execute_request (page):
        # Sorry, I think I'm about to throw up.
        time.sleep (2)

        print (F'Current Page: {page} out of {max_pages}')
        response = make_get_request (F'{all_subjects_page_url}{page}')
        return response['subjects']

    return seq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()


def collate_all_subjects ():

    all_subjects_page_url = F'{get_api_url (USE_PROD)}/subjects?page='
    max_pages = 1 << 16

    print ('Making initial request...')
    initial_request = make_get_request (F'{all_subjects_page_url}1')
    max_pages = initial_request['_meta']['total']

    print ('Chunkifying...')
    import multiprocessing as mp

    # my nproc is 16. // 2 will return 8.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // 2

    page_range_begin = 2 # We already made a GET REQ to ?page=1
    page_list = list (range (page_range_begin, max_pages + 1))

    print ('Collating in Parallel...')
    chunks = pseq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
    all_subjects = pseq (chunks).map (lambda x: parallel_collate_all_subjects (all_subjects_page_url, x, max_pages)).reduce (lambda x, y: x + y, []).to_list ()
    all_subjects += initial_request['subjects'] # Include the initial request.

    write_json (COLLATED_FPATH, all_subjects)

    return all_subjects


def get_subjects ():
    if (not fexists (COLLATED_FPATH)):
        print (F'No saved file found, creating {COLLATED_FPATH}...')
        return collate_all_subjects ()

    return load_json (COLLATED_FPATH)

def parallel_get_similar_approach (data_group):
    subject_code = data_group['subject_definition'].get ('code', None)

    if (subject_code is None):
        return []

    print (F'\tProcessing Approac: {subject_code}')

    get_similars_url = F'{get_api_url (USE_PROD)}/subjects/{subject_code}/similar-learning-approach?threshold={THRESHOLD}'
    approach_response = make_get_request (get_similars_url, False)

    time.sleep (2)
    return [ { 'similar-to': subject_code, 'similars': approach_response.get ('similar-subjects', []) } ]

def parallel_get_similar_outcome (data_group):
    subject_code = data_group['subject_definition'].get ('code', None)

    if (subject_code is None):
        return []

    print (F'\tProcessing Outcome: {subject_code}')

    get_similars_url = F'{get_api_url (USE_PROD)}/subjects/{subject_code}/similar-learning-outcomes?threshold={THRESHOLD}'
    approach_response = make_get_request (get_similars_url, False)

    time.sleep (2)
    return [ { 'similar-to': subject_code, 'similars': approach_response.get ('similar-learning-outcomes', []) } ]

def get_similar_subjects (subjects_array):
    similar_approaches = []
    similar_outcomes = []

    if (not fexists (APPROACH_FPATH)):
        similar_approaches = pseq (subjects_array) \
            .map (lambda x: { 'subject_definition': x, 'access_token': global_access_token }) \
            .map (lambda x: parallel_get_similar_approach (x)) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        print (F'Saving to {APPROACH_FPATH}...')
        write_json (APPROACH_FPATH, similar_approaches)

    else:
        print (F'{APPROACH_FPATH} already exists. Skipping...')
        similar_approaches = load_json (APPROACH_FPATH)

    if (not fexists (OUTCOMES_FPATH)):
        similar_outcomes = pseq (subjects_array) \
            .map (lambda x: { 'subject_definition': x, 'access_token': global_access_token }) \
            .map (lambda x: parallel_get_similar_outcome (x)) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        print (F'Saving to {OUTCOMES_FPATH}...')
        write_json (OUTCOMES_FPATH, similar_outcomes)

    else:
        print (F'{OUTCOMES_FPATH} already exists. Skipping...')
        similar_outcomes = load_json (OUTCOMES_FPATH)

    return similar_approaches, similar_outcomes

def filter_empties (array, relative_key):
    return pseq (array).filter (lambda x: len (x[relative_key]) != 0).to_list ()

def json_to_df (json, explode_on):
    json_df = pd.json_normalize (json)
    bomb_df = json_df.explode (explode_on, ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=[explode_on]), bomb_df[explode_on].apply (pd.Series) ], axis=1)

    return separated_df

def ensure_dual_minimum_threshold (approaches, outcomes):
    print ('Ensuring Dual Minimum Thresholds...')
    filtered_empty_approaches = filter_empties (approaches, 'similars')
    filtered_empty_outcomes = filter_empties (outcomes, 'similars')

    print ('Loading JSON to DF...')
    approach_df = json_to_df (filtered_empty_approaches, 'similars')
    outcomes_df = json_to_df (filtered_empty_outcomes, 'similars')

    print ('Registering DFs...')
    duckdb.register ('approach_df', approach_df)
    duckdb.register ('outcomes_df', outcomes_df)

    print ('Running Both Similar Query...')
    both_similar_query = '''
    SELECT o."similar-to", o.*
        FROM outcomes_df o
    INNER JOIN approach_df a
    ON
        o."similar-to" = a."similar-to"
        AND
        o.code = a.code
    '''

    # Results in similar-to, similar-to_1 columns. They should be equal to each other
    # but i was bothered enough to write this comment instead of dropping the column.
    return exec_sql (both_similar_query)

def get_from_row (row, key, default):
    # For an unknown reason, i am very competent in finding bugs and insects
    # within the python language. even when given a default '[]' (literally),
    # the {}.get (key, default) method doesn't return '[]'. it is truly
    # remarkable that i have to write code in this way.
    # the same piece of code actually worked before, but no longer works. i
    # long for the day in which i have to rewrite every single character of
    # source code because python will have switched up their language syntax
    # so that every character is one position to the right on the azerty
    # keyboard layout. just because python felt different in 2025 and needed
    # a new change for the year of the snake. absolutely phenomenal.
    value = row.get (key, default)
    if (value is not None):
        if (isinstance (value, str)):
            return ast.literal_eval (value)

        # what the fuck? handling arrays in DFs is a lottery.
        if (isinstance (value, numpy.ndarray)):
            return list (value)
    return default

def to_csv (subjects, minimum_threshold):

    subject_lookup_table = {}
    if (not fexists (SUBJECT_LOOKUP_TABLE_FPATH)):
        print ('Creating Subject Lookup Table....')

        subject_lookup_table = pseq (subjects) \
            .filter (lambda x: 'code' in x.keys ()) \
            .map (lambda x: { x['code']: x }) \
            .reduce (lambda x, y: x | y)

        write_json (SUBJECT_LOOKUP_TABLE_FPATH, subject_lookup_table)
    else:

        subject_lookup_table = load_json (SUBJECT_LOOKUP_TABLE_FPATH)

    print ('Assigning Main DataFrame...')

    final_result = pd.DataFrame (columns = [
        # Relative Subject.
        'subject_cd', 'subject_name', 'subject_faculty', 'subject_description', 'subject_study_level', 'subject_location_code', 'subject_credit_points', 'subject_assessment_types',

        # Similar Subject.
        'similar_subject_cd', 'similar_subject_name', 'similar_subject_faculty', 'similar_subject_description', 'similar_subject_study_level', 'similar_subject_location_code', 'similar_subject_credit_points', 'similar_subject_assessment_types',

        # Similarity Score.
        'similarity' ])

    for idx, row in minimum_threshold.iterrows ():
        # Lookup.
        assessment_types_lookup = subject_lookup_table[row['similar-to']].get ('assessments', [])
        locations_lookup = subject_lookup_table[row['similar-to']].get ('subject_offering', [])

        # Similar.
        assessment_types_similar = get_from_row (row, 'assessments', [])
        locations_similar = get_from_row (row, 'subject_offering', [])

        # why tf is row['570012']['assessments'] a float?!?!
        # there are a few more, but why a float? and not default to []?!
        # they're all nan anyway...?
        # print (type (similar_assessment_types))
        #
        # if (isinstance (similar_assessment_types, float)):
        #     print (similar_assessment_types)
        #     print (row['assessments'])
        if (not isinstance (assessment_types_similar, list)):
            continue

        subject_assessment_types = ''
        subject_location_codes = ''
        similar_assessment_types = ''
        similar_location_codes = ''

        if (len (assessment_types_lookup) > 0):
            seq_subject_assessment_types = seq (assessment_types_lookup) \
                    .filter (lambda x: 'type' in x.keys ()) \
                    .filter (lambda x: 'label' in x['type'].keys ()) \
                    .map (lambda x: [ x['type']['label'] ]) \
                    .map (lambda x: ', '.join (x))

            subject_assessment_types = ', '.join (seq_subject_assessment_types)

        if (len (assessment_types_similar) > 0):
            seq_similar_assessment_types = seq (assessment_types_similar) \
                    .filter (lambda x: 'type' in x.keys ()) \
                    .filter (lambda x: 'label' in x['type'].keys ()) \
                    .map (lambda x: [ x['type']['label'] ]) \
                    .map (lambda x: ', '.join (x))

            similar_assessment_types = ', '.join (seq_similar_assessment_types)

        if (len (locations_lookup) > 0):
            seq_locations_lookup = seq (locations_lookup)\
                .filter (lambda x: 'location' in x.keys ()) \
                .filter (lambda x: 'label' in x['location'].keys ()) \
                .map (lambda x: [ x['location']['label'] ]) \
                .map (lambda x: ', '.join (x))

            useq_locations_lookup = list (set (seq_locations_lookup.to_list ()))
            subject_location_codes = ', '.join (useq_locations_lookup)

        if (len (locations_similar) > 0):
            seq_locations_similar = seq (locations_similar)\
                .filter (lambda x: 'location' in x.keys ()) \
                .filter (lambda x: 'label' in x['location'].keys ()) \
                .map (lambda x: [ x['location']['label'] ]) \
                .map (lambda x: ', '.join (x))

            useq_locations_similar = list (set (seq_locations_similar.to_list ()))
            similar_location_codes = ', '.join (useq_locations_similar)

        rows = [[
            # Relative Subject.
            subject_lookup_table[row['similar-to']]['code'],
            subject_lookup_table[row['similar-to']]['name'],
            subject_lookup_table[row['similar-to']].get ('parent_academic_org', {}).get ('label', ''),
            remove_html_elements (subject_lookup_table[row['similar-to']].get ('description', '')),
            subject_lookup_table[row['similar-to']].get ('study_level_ref', {}).get ('value', ''),
            subject_location_codes,
            subject_lookup_table[row['similar-to']]['credit_points'],
            subject_assessment_types,

            # Similar Subject.
            row['code'],
            row['name'],
            row['parent_academic_org'].get ('label', ''),
            remove_html_elements (row['description']),
            row['study_level_ref'].get ('value', ''),
            similar_location_codes,
            row['credit_points'],
            similar_assessment_types,

            # Similarity Score.
            F'{normalise_m (row["M"])}%'
        ]]

        transient_df = pd.DataFrame (rows, columns=final_result.columns)
        final_result = pd.concat([ final_result, transient_df ], ignore_index=True)

    output_file_path = F'{ENVIRONMENT}-absolution.xlsx'
    print (F'Saving result to {output_file_path}...')
    final_result.to_excel (output_file_path, index=False)

    return final_result, output_file_path


def main ():

    print (F'ENVIRONMENT: {ENVIRONMENT}')
    set_access_token (USE_PROD)

    # Use file from previous run.
    # Or, generate file from API call.
    subjects = get_subjects ()
    print (len (subjects))

    # Generate files for similarities.
    similar_approahces, similar_outcomes = get_similar_subjects (subjects)

    # Ensure a structure where both approaches and outcomes codes meet the threshold.
    minimum_thresholds = ensure_dual_minimum_threshold (similar_approahces, similar_outcomes)

    # Open similarity files for csv conversion.
    final_result, final_result_path = to_csv (subjects, minimum_thresholds)

if (__name__ == '__main__'):
    main ()
