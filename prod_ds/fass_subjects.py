import pandas as pd
import numpy as np
from pandasql import sqldf
import os
import os.path
import openpyxl
import duckdb
import requests
import json
import time
import multiprocessing as mp
from functional import pseq, seq
from bs4 import BeautifulSoup

USE_PROD=True

ENVIRONMENT = 'PROD' if USE_PROD else 'NONPROD'

COLLATED_FPATH = F'{ENVIRONMENT}-collated.json'
COLLATED_SUBJECTS_FPATH = F'{ENVIRONMENT}-collated-subjects.json'
SUBJECT_LOOKUP_TABLE_FPATH = F'{ENVIRONMENT}-subject-lookup.json'
FACULTY_COURSE_FPATH = F'{ENVIRONMENT}-collated-faculty-courses.json'
RELATED_SUBJECTS_FPATH = F'{ENVIRONMENT}-related-subjects.json'
EXPANDED_SUBJECTS_FPATH = F'{ENVIRONMENT}-expanded-subjects.json'
RESULT_PATH = F'{ENVIRONMENT}-absolution.xlsx'

global_access_token = ''

def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup

def set_access_token (use_prod=False):
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

def get_courses ():
    with open (FACULTY_COURSE_FPATH, 'r') as courses:
        deserialised = json.load (courses)
        courses_lookup = pseq (deserialised) \
            .filter (lambda x: 'code' in x.keys ()) \
            .map (lambda x: { x['code']: x }) \
            .reduce (lambda x, y: x | y)
        return courses_lookup
    return {}

def parallel_execute_requests (target_url, page_range, max_pages, response_key):
    def execute_request (page):
        # Sorry, I think I'm about to throw up.
        time.sleep (2)

        print (F'Current Page: {page} out of {max_pages}')
        response = make_get_request (F'{target_url}{page}')
        return response[response_key]

    return seq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()

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

    write_json (COLLATED_SUBJECTS_FPATH, all_subjects)

    return all_subjects

def get_subjects ():
    if (not fexists (COLLATED_SUBJECTS_FPATH)):
        print (F'No saved file found, creating {COLLATED_FPATH}...')
        return collate_all_subjects ()

    return load_json (COLLATED_SUBJECTS_FPATH)

def collate_all_course_whats (courses, related_what):

    all_related_whats = []

    # my nproc is 16. // 2 will return 8.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // 2

    page_range_begin = 2 # We already made a GET REQ to ?page=1

    for course in courses:

        if (isinstance (course, list)):
            print (course)
            print (len (course))
        course_code = course.get ('code', None)
        if (course_code is None):
            continue

        all_courses_page_url = F'{get_api_url (USE_PROD)}/courses/{course_code}/{related_what}?page='
        max_pages = 1 << 16

        # print (F'Making initial request for {course_code}...')
        initial_request = make_get_request (F'{all_courses_page_url}1')
        max_pages = initial_request['_meta']['total']

        page_list = list (range (page_range_begin, max_pages + 1))

        print (F'Collating {course_code} for {related_what} in Parallel...')
        chunks = seq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
        all_related_whats += seq (chunks) \
                .map (lambda x: [ { 'relative-to': course_code, 'subjects': parallel_execute_requests (
                    all_courses_page_url, x, max_pages, related_what) }]) \
                .reduce (lambda x, y: x + y, []).to_list ()
        all_related_whats += [ { 'relative-to': course_code, 'subjects': initial_request[related_what] } ]

    return all_related_whats

def expand_substructures (related_whats):

    if (os.path.isfile (EXPANDED_SUBJECTS_FPATH)):
        return load_json (EXPANDED_SUBJECTS_FPATH)

    def parallel_expand (substructure_group):
        relative_to = substructure_group['relative-to']
        substructure_code = substructure_group['substructure-code']
        subjects_in_substructure_url = F'{get_api_url (USE_PROD)}/substructures/{substructure_code}/subjects?page='

        initial_request = make_get_request (F'{subjects_in_substructure_url}1')
        max_pages = initial_request['_meta']['total']

        # my nproc is 16. // 2 will return 8.
        # you can try increaasing this, but i have nothing left to throw up.
        nproc = mp.cpu_count () // 2

        page_range_begin = 2 # We already made a GET REQ to ?page=1
        page_list = list (range (page_range_begin, max_pages + 1))

        print (F'Expanding {substructure_code} in Parallel...')
        chunks = seq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
        all_subjects = pseq (chunks) \
            .map (lambda x: [ { 'relative-to': relative_to, 'subjects': parallel_execute_requests (subjects_in_substructure_url, x, max_pages, 'subjects') } ]) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()
        all_subjects += [ { 'relative-to': relative_to, 'subjects': initial_request['subjects'] } ]

        return all_subjects

    print ('Filtering Valids...')
    non_empties = pseq (related_whats) \
        .filter (lambda x: 'relative-to' in x.keys ()) \
        .filter (lambda x: 'subjects' in x.keys ()) \
        .filter (lambda x: len (x['subjects']) > 0)

    print ('Extracing Codes...')
    substructure_group = pseq (non_empties) \
        .map (lambda x: [
            { 'relative-to': x['relative-to'], 'substructure_codes':
                seq (x['subjects']) \
                    .filter (lambda x: 'class_name' in x.keys ()) \
                    .filter (lambda x: x['class_name'] == 'Substructures') \
                    .filter (lambda x: 'code' in x.keys ()) \
                    .map (lambda x: x['code']) \
                    .to_list ()
            }
        ]) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    print ('Reorganising Codes...')
    reorganised_substructure_group = []
    for i in substructure_group:
        relative_to = i['relative-to']
        value = pseq (i['substructure_codes']) \
            .map (lambda x: [ { 'relative-to': relative_to, 'substructure-code': x } ]) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        if (len (value) > 0):
            reorganised_substructure_group.append (value)

    print ('Running Substructure > Subjects...')
    expanded = seq (reorganised_substructure_group) \
        .reduce (lambda x, y: x + y, []) \
        .map (lambda x: parallel_expand (x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    print (F'Writing Expanded to {EXPANDED_SUBJECTS_FPATH}...')
    write_json (EXPANDED_SUBJECTS_FPATH, expanded)

    return expanded

def collate_all_faculty_courses (faculty_code):

    all_courses_page_url = F'{get_api_url (USE_PROD)}/faculties/{faculty_code}/courses?page='
    max_pages = 1 << 16

    print ('Making initial request...')
    initial_request = make_get_request (F'{all_courses_page_url}1')
    max_pages = initial_request['_meta']['total']
    print (max_pages)

    print ('chunkifying...')

    # my nproc is 16. // 2 will return 8.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // 2

    page_range_begin = 2 # We already made a GET REQ to ?page=1
    page_list = list (range (page_range_begin, max_pages + 1))

    print ('Collating in Parallel...')
    chunks = pseq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
    all_courses = pseq (chunks).map (lambda x: parallel_execute_requests (all_courses_page_url, x, max_pages, 'courses')).reduce (lambda x, y: x + y, []).to_list ()
    all_courses += initial_request['courses']

    write_json (FACULTY_COURSE_FPATH, all_courses)
    return all_courses

def get_related_whats (courses, what):
    try:

        # Make file.
        if (not os.path.isfile (RELATED_SUBJECTS_FPATH)):
            print (F'No saved file found, creating {RELATED_SUBJECTS_FPATH}...')
            return_value = []

            return_value = pseq (what) \
                    .map (lambda x: collate_all_course_whats (courses, x)) \
                    .reduce (lambda x, y: x + y, []) \
                    .to_list ()

            write_json (RELATED_SUBJECTS_FPATH, return_value)
            return return_value


        with open (RELATED_SUBJECTS_FPATH) as subs:
            print (F'Opening saved file {RELATED_SUBJECTS_FPATH}')
            return json.load (subs)

    except Exception as E:

        raise E

def get_faculty_courses (faculty_code):
    try:

        # Make file.
        if (not os.path.isfile (FACULTY_COURSE_FPATH)):
            print (F'No saved file found, creating {FACULTY_COURSE_FPATH}...')
            return collate_all_faculty_courses (faculty_code)

        with open (FACULTY_COURSE_FPATH) as subs:
            print (F'Opening saved file {FACULTY_COURSE_FPATH}')
            return json.load (subs)

    except Exception as E:

        raise E

def to_csv ():

    subject_lookup_table = {}
    if (not fexists (SUBJECT_LOOKUP_TABLE_FPATH)):
        print ('Creating Subject Lookup Table....')

        subject_lookup_table = pseq (get_subjects ()) \
            .filter (lambda x: 'code' in x.keys ()) \
            .map (lambda x: { x['code']: x }) \
            .reduce (lambda x, y: x | y)

        write_json (SUBJECT_LOOKUP_TABLE_FPATH, subject_lookup_table)
    else:

        print ('Loading Subject Lookup Table...')
        subject_lookup_table = load_json (SUBJECT_LOOKUP_TABLE_FPATH)

    print ('Loading Relatives')
    related_subjects = []
    with open (RELATED_SUBJECTS_FPATH, 'r') as r:
        related_subjects = json.load (r)

    print ('Loading Expanded')
    expanded_subjects = []
    with open (EXPANDED_SUBJECTS_FPATH, 'r') as e:
        expanded_subjects = json.load (e)

    print ('Adding Related and Expanded...')
    active_subjects_group = related_subjects + expanded_subjects

    print ('Filtering Empties...')
    filtered_empties = pseq (active_subjects_group).filter (lambda x: len (x['subjects']) != 0).to_list ()
    non_empties = pseq (active_subjects_group).filter (lambda x: len (x['subjects']) == 0).to_list ()
    
    print ('Exploding Similars...')
    j_df = pd.json_normalize (filtered_empties)
    bomb_df = j_df.explode ('subjects', ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=['subjects']), bomb_df['subjects'].apply (pd.Series) ], axis=1)

    print ('Creating Subject Lookup Table....')
    courses_lookup = get_courses ()

    print ('Assigning Main DataFrame...')

    final_result = pd.DataFrame (columns = [
        'subject_code', 'subject_name', 'subject_subclass', 'subject_study_level',
        'relative_subject_code', 'relative_subject_name', 'relative_subject_subclass', 'relative_subject_study_level'])

    print (separated_df.columns)
    for idx, row in separated_df.iterrows ():
        rows = [[
            # Relative Subject.
            courses_lookup[row['relative-to']]['code'],
            courses_lookup[row['relative-to']]['name'],
            remove_html_elements (courses_lookup[row['relative-to']].get ('subclass', {}).get ('label', '')),
            courses_lookup[row['relative-to']].get ('study_level_ref', {}).get ('value', ''),

            # Similar Subject.
            row['code'],
            row['name'],
            row['subclass'].get ('label', ''),
            subject_lookup_table.get (row['code'], {}).get ('study_level_ref', {}).get ('value', '')
        ]]

        transient_df = pd.DataFrame (rows, columns=final_result.columns)
        final_result = pd.concat([ final_result, transient_df ], ignore_index=True)

    print (F'Saving result to {RESULT_PATH}...')
    final_result.to_excel (RESULT_PATH, index=False)

    return final_result, RESULT_PATH


def main ():

    print (F'ENVIRONMENT: {ENVIRONMENT}')
    set_access_token (USE_PROD)

    # Use file from previous run.
    # Or, generate file from API call.
    faculty_courses = get_faculty_courses ("G")
    print (len (faculty_courses))

    related_whats = get_related_whats (faculty_courses, what = [ 'subjects', 'majors', 'submajors', 'streams' ])
    print (len (related_whats))

    expanded_whats = expand_substructures (related_whats)

    # Open similarity files for csv conversion.
    final_result, final_result_path = to_csv ()

if (__name__ == '__main__'):
    main ()
