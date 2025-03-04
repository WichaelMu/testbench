import pandas as pd
import numpy as np
from pandasql import sqldf
import os
import os.path
import openpyxl
import duckdb
import requests
import json
from functional import pseq
from bs4 import BeautifulSoup

USE_PROD=True

ENVIRONMENT = 'PROD' if USE_PROD else 'NONPROD'
FILE_PATH = F'{ENVIRONMENT}-collated.json'

THRESHOLD=75
SIMILAR_APPROACHES_PATH = F'{ENVIRONMENT}-similar-approaches.json'
SIMILAR_OUTCOMES_PATH = F'{ENVIRONMENT}-similar-outcomes.json'

def sql(query):
    return duckdb.query(query).to_df()

def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup

def normalise_m (m):
    return round ((m - float(1)) * float (100))

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

def collate_all_subjects ():
    access_token = get_access_token (USE_PROD)
    all_subjects_page_url = F'{get_api_url (USE_PROD)}/subjects?page='
    max_pages = 1 << 16
    current_page = 1

    all_subjects = []

    while (current_page <= max_pages):
        print (F'Current Page: {current_page} out of {max_pages}')

        response = make_get_request (F'{all_subjects_page_url}{current_page}', access_token)
        max_pages = response['_meta']['total']
        current_page += 1

        all_subjects += response['subjects']

    write_json (FILE_PATH, all_subjects)

    return all_subjects


def get_subjects ():
    try:

        # Make file.
        if (not os.path.isfile (FILE_PATH)):
            print (F'No saved file found, creating {FILE_PATH}...')
            collate_all_subjects ()

        with open (FILE_PATH) as subs:
            print (F'Opening saved file {FILE_PATH}')
            return json.load (subs)

    except Exception as E:

        raise E

def parallel_get_similar_approach (data_group):
    subject_code = data_group['subject_definition'].get ('code', None)

    if (subject_code is None):
        return []

    print (F'\tProcessing Approac: {subject_code}')

    get_similars_url = F'{get_api_url (USE_PROD)}/subjects/{subject_code}/similar-learning-approach?threshold={THRESHOLD}'
    approach_response = make_get_request (get_similars_url, data_group['access_token'], False)

    return [ { 'similar-to': subject_code, 'similars': approach_response.get ('similar-subjects', []) } ]

def parallel_get_similar_outcome (data_group):
    subject_code = data_group['subject_definition'].get ('code', None)

    if (subject_code is None):
        return []

    print (F'\tProcessing Outcome: {subject_code}')

    get_similars_url = F'{get_api_url (USE_PROD)}/subjects/{subject_code}/similar-learning-outcomes?threshold={THRESHOLD}'
    approach_response = make_get_request (get_similars_url, data_group['access_token'], False)

    return [ { 'similar-to': subject_code, 'similars': approach_response.get ('similar-learning-outcomes', []) } ]

def get_similar_subjects (subjects_array):
    access_token = get_access_token (USE_PROD)

    similar_approaches = pseq (subjects_array) \
        .map (lambda x: { 'subject_definition': x, 'access_token': access_token }) \
        .map (lambda x: parallel_get_similar_approach (x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    similar_outcomes = pseq (subjects_array) \
        .map (lambda x: { 'subject_definition': x, 'access_token': access_token }) \
        .map (lambda x: parallel_get_similar_outcome (x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    print (F'Saving to {SIMILAR_APPROACHES_PATH}...')
    write_json (SIMILAR_APPROACHES_PATH, similar_approaches)

    print (F'Saving to {SIMILAR_OUTCOMES_PATH}...')
    write_json (SIMILAR_OUTCOMES_PATH, similar_outcomes)

    return similar_approaches, similar_outcomes

def to_csv ():
    print ('Loading Saved Similars...')
    with open(SIMILAR_APPROACHES_PATH, 'r') as f1, open(SIMILAR_OUTCOMES_PATH, 'r') as f2:
        data1 = json.load (f1)
        data2 = json.load (f2)

    print ('Combining Similars...')
    combined_data = data1 + data2

    filtered_empties = pseq (combined_data).filter (lambda x: len (x['similars']) != 0).to_list ()
    
    print ('Exploding Similars...')
    j_df = pd.json_normalize (filtered_empties)
    bomb_df = j_df.explode ('similars', ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=['similars']), bomb_df['similars'].apply (pd.Series) ], axis=1)

    print ('Creating Subject Lookup Table....')
    subjects = get_subjects ()
    code_organised_subjects = pseq (subjects) \
        .filter (lambda x: 'code' in x.keys ()) \
        .map (lambda x: { x['code']: x }) \
        .reduce (lambda x, y: x | y)

    print ('Assigning Main DataFrame...')

    final_result = pd.DataFrame (columns = [
        'subject_cd', 'subject_name', 'subject_faculty', 'subject_description',
        'similar_subject_cd', 'similar_subject_name', 'similar_subject_faculty', 'similar_subject_description', 'similar_subject_study_level',
        'similarity' ])

    for idx, row in separated_df.iterrows ():
        rows = [[
            # Relative Subject.
            code_organised_subjects[row['similar-to']]['code'],
            code_organised_subjects[row['similar-to']]['name'],
            code_organised_subjects[row['similar-to']].get ('parent_academic_org', {}).get ('label', ''),
            remove_html_elements (code_organised_subjects[row['similar-to']].get ('description', '')),

            # Similar Subject.
            row['code'],
            row['name'],
            row['parent_academic_org'].get ('label', ''),
            remove_html_elements (row['description']),
            row['study_level_ref'].get ('value', ''),

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

    # Use file from previous run.
    # Or, generate file from API call.
    subjects = get_subjects ()
    print (len (subjects))

    # Generate files for similarities.
    similar_approahces, similar_outcomes = get_similar_subjects (subjects)

    # Open similarity files for csv conversion.
    final_result, final_result_path = to_csv ()

if (__name__ == '__main__'):
    main ()
