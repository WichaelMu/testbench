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
FACULTY_COURSE_FPATH = F'{ENVIRONMENT}-collated-faculty-courses.json'
RELATED_SUBJECTS_FPATH = F'{ENVIRONMENT}-related-subjects.json'
RESULT_PATH = F'{ENVIRONMENT}-absolution.xlsx'


def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup


def get_access_token (use_prod=False):
    client_id = ''
    client_secret = ''
    token_url = ''
    scope = ''

    if (not use_prod):
        client_id = '5tbulgc54eb6neskd0cuev396q'
        client_secret = '1h29kaqpkoe8tiokr5i3hatg2amnjrrdj02nochsv37rk1i2l16f'
        token_url = 'https://authz.nonprod.cortex.uts.edu.au/oauth2/token/'
        scope = 'data.curriculum.nonprod.cortex.uts.edu.au/curriculum:data:token'
    else:
        client_id = 's52m9vodfsmdiqb22gf8cegkq'
        client_secret = 'rpqdnq37a3vr79pbepn423vnql66beqaqt07vgq3v7rntjj96q'
        token_url = 'https://authz.cortex.uts.edu.au/oauth2/token/'
        scope = 'data.curriculum.cortex.uts.edu.au/curriculum:data:token'

    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }

    response = requests.post (token_url, data=payload)
    response.raise_for_status ()
    token_data = response.json ()

    return token_data['access_token']

def get_api_url (use_prod=False):
    return 'https://data.curriculum.nonprod.cortex.uts.edu.au' if not use_prod else 'https://data.curriculum.cortex.uts.edu.au'

def make_get_request (api_url, access_token, raise_on_error=True):
    headers = { 'Authorization': F'Bearer {access_token}' }
    response = requests.get (api_url, headers=headers)

    if (raise_on_error):
        response.raise_for_status ()

    return response.json ()

def write_json (path, data):
    with open (path, 'w') as w:
        json.dump (data, w)

def get_courses ():
    with open (COLLATED_FPATH, 'r') as courses:
        deserialised = json.load (courses)
        courses_lookup = pseq (deserialised) \
            .filter (lambda x: 'code' in x.keys ()) \
            .map (lambda x: { x['code']: x }) \
            .reduce (lambda x, y: x | y)
        return courses_lookup
    return {}

def parallel_collate_all_relatives (target_url, page_range, max_pages, access_token, response_key):
    def execute_request (page):
        # Sorry, I think I'm about to throw up.
        time.sleep (2)

        print (F'Current Page: {page} out of {max_pages}')
        response = make_get_request (F'{target_url}{page}', access_token)
        return response[response_key]

    return seq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()

def collate_all_course_subjects (courses, related_what):

    all_related_subjects = []

    # my nproc is 12. // 2 will return 6.
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

        access_token = get_access_token (USE_PROD)
        all_courses_page_url = F'{get_api_url (USE_PROD)}/courses/{course_code}/{related_what}?page='
        max_pages = 1 << 16

        # print (F'Making initial request for {course_code}...')
        initial_request = make_get_request (F'{all_courses_page_url}1', access_token)
        max_pages = initial_request['_meta']['total']

        page_list = list (range (page_range_begin, max_pages + 1))

        print (F'Collating {course_code} for {related_what} in Parallel...')
        chunks = seq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
        all_related_subjects += pseq (chunks) \
                .map (lambda x: [ { 'relative-to': course_code, 'subjects': parallel_collate_all_relatives (
                    all_courses_page_url, x, max_pages, access_token, related_what) }]) \
                .reduce (lambda x, y: x + y, []).to_list ()
        all_related_subjects += [ { 'relative-to': course_code, 'subjects': initial_request[related_what] } ]

    return all_related_subjects

def collate_all_faculty_courses (faculty_code):

    access_token = get_access_token (USE_PROD)
    all_courses_page_url = F'{get_api_url (USE_PROD)}/faculties/{faculty_code}/courses?page='
    max_pages = 1 << 16

    print ('Making initial request...')
    initial_request = make_get_request (F'{all_courses_page_url}1', access_token)
    max_pages = initial_request['_meta']['total']
    print (max_pages)

    print ('Chunkifying...')

    # my nproc is 12. // 2 will return 6.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // 2

    page_range_begin = 2 # We already made a GET REQ to ?page=1
    page_list = list (range (page_range_begin, max_pages + 1))

    print ('Collating in Parallel...')
    chunks = pseq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
    all_courses = pseq (chunks).map (lambda x: parallel_collate_all_relatives (all_courses_page_url, x, max_pages, access_token, 'courses')).reduce (lambda x, y: x + y, []).to_list ()
    all_courses += initial_request['courses']

    write_json (FACULTY_COURSE_FPATH, all_courses)
    return all_courses

def get_related_subjects (courses):
    try:

        # Make file.
        if (not os.path.isfile (RELATED_SUBJECTS_FPATH)):
            print (F'No saved file found, creating {RELATED_SUBJECTS_FPATH}...')
            what = [ 'subjects', 'majors', 'submajors', 'streams' ]
            return_value = []

            return_value = seq (what) \
                    .map (lambda x: collate_all_course_subjects (courses, x)) \
                    .reduce (lambda x, y: x + y, []) \
                    .to_list ()

            write_json (RELATED_SUBJECTS_FPATH, return_value)
            return return_value


        with open (FACULTY_COURSE_FPATH) as subs:
            print (F'Opening saved file {FACULTY_COURSE_FPATH}')
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
    print ('Loading Relatives')
    related_subjects = []
    with open (RELATED_SUBJECTS_FPATH, 'r') as r:
        related_subjects = json.load (r)

    filtered_empties = pseq (related_subjects).filter (lambda x: len (x['subjects']) != 0).to_list ()
    non_empties = pseq (related_subjects).filter (lambda x: len (x['subjects']) == 0).to_list ()
    
    print ('Exploding Similars...')
    j_df = pd.json_normalize (filtered_empties)
    bomb_df = j_df.explode ('subjects', ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=['subjects']), bomb_df['subjects'].apply (pd.Series) ], axis=1)

    print ('Creating Subject Lookup Table....')
    courses_lookup = get_courses ()

    print ('Assigning Main DataFrame...')

    final_result = pd.DataFrame (columns = [
        'subject_code', 'subject_name', 'subject_subclass',
        'relative_subject_code', 'relative_subject_name', 'relative_subject_subclass'])

    print (separated_df.columns)
    for idx, row in separated_df.iterrows ():
        rows = [[
            # Relative Subject.
            courses_lookup[row['relative-to']]['code'],
            courses_lookup[row['relative-to']]['name'],
            remove_html_elements (courses_lookup[row['relative-to']].get ('subclass', {}).get ('label', '')),

            # Similar Subject.
            row['code'],
            row['name'],
            row['subclass'].get ('label', ''),
        ]]

        transient_df = pd.DataFrame (rows, columns=final_result.columns)
        final_result = pd.concat([ final_result, transient_df ], ignore_index=True)

    print (F'Saving result to {RESULT_PATH}...')
    final_result.to_excel (RESULT_PATH, index=False)

    return final_result, RESULT_PATH


def main ():

    print (F'ENVIRONMENT: {ENVIRONMENT}')

    # Use file from previous run.
    # Or, generate file from API call.
    faculty_courses = get_faculty_courses ("G")
    print (len (faculty_courses))

    related_subjects = get_related_subjects (faculty_courses)
    print (len (related_subjects))

    # Generate files for similarities.
    # similar_approahces, similar_outcomes = get_similar_subjects (subjects)

    # Open similarity files for csv conversion.
    final_result, final_result_path = to_csv ()

if (__name__ == '__main__'):
    main ()
