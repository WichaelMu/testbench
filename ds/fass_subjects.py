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

import dscore as dsc

SUBJECT_LOOKUP_TABLE_FPATH = F'{ENVIRONMENT}-subject-lookup.json'
RELATED_SUBJECTS_FPATH = F'{ENVIRONMENT}-related-subjects.json'
EXPANDED_SUBJECTS_FPATH = F'{ENVIRONMENT}-expanded-subjects.json'
RESULT_PATH = F'{ENVIRONMENT}-absolution.xlsx'

FACULTY_TO_RUN_AGAINST = 'A'


def collate_all_course_whats (courses, related_what):

    all_related_whats = []

    # my nproc is 16. // 2 will return 8.
    # you can try increaasing this, but i have nothing left to throw up.
    nproc = mp.cpu_count () // 2

    page_range_begin = 2 # We already made a GET REQ to ?page=1

    course_counter = 0
    course_total = len (courses)

    for course in courses:
        course_counter += 1

        if (isinstance (course, list)):
            print (course)
            print (len (course))
        course_code = course.get ('code', None)
        if (course_code is None):
            continue

        print (F'Processing Course {course_counter} of {course_total}')

        all_courses_page_url = F'{dsc.get_api_url ()}/courses/{course_code}/{related_what}?page='
        max_pages = 1 << 16

        # print (F'Making initial request for {course_code}...')
        initial_request = dsc.make_get_request (F'{all_courses_page_url}1')
        max_pages = initial_request['_meta']['total']

        page_list = list (range (page_range_begin, max_pages + 1))

        print (F'Collating {course_code} for {related_what} in Parallel...')
        chunks = seq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
        all_related_whats += seq (chunks) \
                .map (lambda x: [ { 'relative-to': course_code, 'subjects': dsc.execute_parallel_requests (
                    all_courses_page_url, x, max_pages, related_what) }]) \
                .reduce (lambda x, y: x + y, []).to_list ()
        all_related_whats += [ { 'relative-to': course_code, 'subjects': initial_request[related_what] } ]

    return all_related_whats

def expand_substructures (related_whats):

    if (os.path.isfile (EXPANDED_SUBJECTS_FPATH)):
        return dsc.load_json (EXPANDED_SUBJECTS_FPATH)

    def parallel_expand (substructure_group):
        relative_to = substructure_group['relative-to']
        substructure_code = substructure_group['substructure-code']
        subjects_in_substructure_url = F'{dsc.get_api_url ()}/substructures/{substructure_code}/subjects?page='

        initial_request = dsc.make_get_request (F'{subjects_in_substructure_url}1')
        max_pages = initial_request['_meta']['total']

        # my nproc is 16. // 2 will return 8.
        # you can try increaasing this, but i have nothing left to throw up.
        nproc = mp.cpu_count () // 2

        page_range_begin = 2 # We already made a GET REQ to ?page=1
        page_list = list (range (page_range_begin, max_pages + 1))

        print (F'Expanding {substructure_code} in Parallel...')
        chunks = seq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()
        all_subjects = seq (chunks) \
            .map (lambda x: [ { 'relative-to': relative_to, 'subjects': dsc.execute_parallel_requests (subjects_in_substructure_url, x, max_pages, 'subjects') } ]) \
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
    expanded = pseq (reorganised_substructure_group) \
        .reduce (lambda x, y: x + y, []) \
        .map (lambda x: parallel_expand (x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    print (F'Writing Expanded to {EXPANDED_SUBJECTS_FPATH}...')
    dsc.write_json (EXPANDED_SUBJECTS_FPATH, expanded)

    return expanded


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

            dsc.write_json (RELATED_SUBJECTS_FPATH, return_value)
            return return_value


        with open (RELATED_SUBJECTS_FPATH) as subs:
            print (F'Opening saved file {RELATED_SUBJECTS_FPATH}')
            return json.load (subs)

    except Exception as E:

        raise E


def to_csv ():

    subject_lookup_table = {}
    if (not dsc.fexists (SUBJECT_LOOKUP_TABLE_FPATH)):
        print ('Creating Subject Lookup Table....')

        subject_lookup_table = pseq (dsc.get_subjects ()) \
            .filter (lambda x: 'code' in x.keys ()) \
            .map (lambda x: { x['code']: x }) \
            .reduce (lambda x, y: x | y)

        dsc.write_json (SUBJECT_LOOKUP_TABLE_FPATH, subject_lookup_table)
    else:

        print ('Loading Subject Lookup Table...')
        subject_lookup_table = dsc.load_json (SUBJECT_LOOKUP_TABLE_FPATH)

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
    separated_df = dsc.json_to_df (filtered_empties, 'subjects')

    print ('Creating Subject Lookup Table....')
    courses_lookup = dsc.get_faculty_courses_lookup ()

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
            dsc.remove_html_elements (courses_lookup[row['relative-to']].get ('subclass', {}).get ('label', '')),
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

    dsc.set_environment ('PROD')
    print (F'ENVIRONMENT: {ENVIRONMENT}')
    dsc.set_access_token ()

    # Use file from previous run.
    # Or, generate file from API call.
    faculty_courses = dsc.get_faculty_courses (FACULTY_TO_RUN_AGAINST)
    print (len (faculty_courses))

    related_whats = get_related_whats (faculty_courses, what = [ 'subjects', 'majors', 'submajors', 'streams' ])
    print (len (related_whats))

    expanded_whats = expand_substructures (related_whats)

    # Open similarity files for csv conversion.
    final_result, final_result_path = to_csv ()

if (__name__ == '__main__'):
    main ()
