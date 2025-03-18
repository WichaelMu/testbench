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

import dscore as dsc

# 'Cached' files.
COMBINED_FPATH = F'{ENVIRONMENT}-combined.json'

# Search results.
THRESHOLD=75
APPROACH_FPATH = F'{ENVIRONMENT}-similar-approaches.json'
OUTCOMES_FPATH = F'{ENVIRONMENT}-similar-outcomes.json'
FILTERED_EMPTIES_FPATH = F'{ENVIRONMENT}-filtered-empties.json'
SUBJECT_LOOKUP_TABLE_FPATH = F'{ENVIRONMENT}-subject-lookup.json'


def exec_sql (q):
    return duckdb.query (q).to_df ()

def normalise_m (m):
    return round ((m - float (1)) * float (100))


def get_api_url (use_prod=False):
    return 'https://data.curriculum.nonprod.cortex.uts.edu.au' if not use_prod else 'https://data.curriculum.cortex.uts.edu.au'

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
        subject_offering_lookup = subject_lookup_table[row['similar-to']].get ('subject_offering', [])

        # Similar.
        assessment_types_similar = get_from_row (row, 'assessments', [])
        subject_offering_similar = get_from_row (row, 'subject_offering', [])

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

        # Lookup.
        subject_assessment_types = ''
        subject_location_codes = ''
        subject_mode_label = ''
        subject_mode_value = ''

        # Similar.
        similar_assessment_types = ''
        similar_location_codes = ''
        similar_mode_label = ''
        similar_mode_value = ''

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

        if (len (subject_offering_lookup) > 0):
            # Locations.
            seq_locations_lookup = seq (subject_offering_lookup)\
                .filter (lambda x: 'location' in x.keys ()) \
                .filter (lambda x: 'label' in x['location'].keys ()) \
                .map (lambda x: [ x['location']['label'] ]) \
                .map (lambda x: ', '.join (x))

            useq_locations_lookup = list (set (seq_locations_lookup.to_list ()))
            subject_location_codes = ', '.join (useq_locations_lookup)

            # Mode Label & Mode Value.

        if (len (subject_offering_similar) > 0):
            # Locations.
            seq_locations_similar = seq (subject_offering_similar)\
                .filter (lambda x: 'location' in x.keys ()) \
                .filter (lambda x: 'label' in x['location'].keys ()) \
                .map (lambda x: [ x['location']['label'] ]) \
                .map (lambda x: ', '.join (x))

            useq_locations_similar = list (set (seq_locations_similar.to_list ()))
            similar_location_codes = ', '.join (useq_locations_similar)

            # Mode Label & Mode Value.
            seq_locations_similar = seq (subject_offering_similar)\
                .filter (lambda x: 'mode' in x.keys ()) \
                .filter (lambda x: 'label' in x['mode'].keys ()) \
                .filter (lambda x: 'value' in x['mode'].keys ()) \
                .map (lambda x: { 'label': x['mode']['label'], 'value': x['mode']['value'] }) \
                .to_list ()

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
    subjects = dsc.get_subjects ()
    print (len (subjects))

    # Generate files for similarities.
    similar_approahces, similar_outcomes = get_similar_subjects (subjects)

    # Ensure a structure where both approaches and outcomes codes meet the threshold.
    minimum_thresholds = ensure_dual_minimum_threshold (similar_approahces, similar_outcomes)

    # Open similarity files for csv conversion.
    final_result, final_result_path = to_csv (subjects, minimum_thresholds)

if (__name__ == '__main__'):
    main ()
