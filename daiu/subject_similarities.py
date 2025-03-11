import pandas as pd
import os
import os.path
import time
import requests
import json
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


def remove_html_elements (markup):
    if (isinstance (markup, str)):
        return BeautifulSoup (markup, 'html.parser').get_text ()
    return markup

def normalise_m (m):
    return round ((m - float (1)) * float (100))

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

    while True:
        response = requests.get (api_url, headers=headers)

        # if (raise_on_error):
        #     response.raise_for_status ()

        if (response.status_code == 200):
            return response.json ()

        print (F'\tEncountered {response.status_code}. Retrying {api_url}...')
        time.sleep (5)
        print (F'\tRetrying last...')

def fexists (fpath):
    return os.path.isfile (fpath)

def write_json (path, data):
    with open (path, 'w') as w:
        json.dump (data, w)

def load_json (path):
    with open (path) as f:
        print (F'Opening saved file {path}')
        return json.load (f)

def parallel_collate_all_subjects (all_subjects_page_url, page_range, max_pages, access_token):
    def execute_request (page):
        # Sorry, I think I'm about to throw up.
        time.sleep (2)

        print (F'Current Page: {page} out of {max_pages}')
        response = make_get_request (F'{all_subjects_page_url}{page}', access_token)
        return response['subjects']

    return seq (page_range).map (lambda p: execute_request (p)).reduce (lambda x, y: x + y, []).to_list ()


def collate_all_subjects ():

    access_token = get_access_token (USE_PROD)
    all_subjects_page_url = F'{get_api_url (USE_PROD)}/subjects?page='
    max_pages = 1 << 16

    print ('Making initial request...')
    initial_request = make_get_request (F'{all_subjects_page_url}1', access_token)
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
    all_subjects = pseq (chunks).map (lambda x: parallel_collate_all_subjects (all_subjects_page_url, x, max_pages, access_token)).reduce (lambda x, y: x + y, []).to_list ()

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
    approach_response = make_get_request (get_similars_url, data_group['access_token'], False)

    time.sleep (2)
    return [ { 'similar-to': subject_code, 'similars': approach_response.get ('similar-subjects', []) } ]

def parallel_get_similar_outcome (data_group):
    subject_code = data_group['subject_definition'].get ('code', None)

    if (subject_code is None):
        return []

    print (F'\tProcessing Outcome: {subject_code}')

    get_similars_url = F'{get_api_url (USE_PROD)}/subjects/{subject_code}/similar-learning-outcomes?threshold={THRESHOLD}'
    approach_response = make_get_request (get_similars_url, data_group['access_token'], False)

    time.sleep (2)
    return [ { 'similar-to': subject_code, 'similars': approach_response.get ('similar-learning-outcomes', []) } ]

def get_similar_subjects (subjects_array):
    access_token = get_access_token (USE_PROD)
    similar_approaches = []
    similar_outcomes = []

    if (not fexists (APPROACH_FPATH)):
        similar_approaches = pseq (subjects_array) \
            .map (lambda x: { 'subject_definition': x, 'access_token': access_token }) \
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
            .map (lambda x: { 'subject_definition': x, 'access_token': access_token }) \
            .map (lambda x: parallel_get_similar_outcome (x)) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        print (F'Saving to {OUTCOMES_FPATH}...')
        write_json (OUTCOMES_FPATH, similar_outcomes)

    else:
        print (F'{OUTCOMES_FPATH} already exists. Skipping...')
        similar_outcomes = load_json (OUTCOMES_FPATH)

    return similar_approaches, similar_outcomes

def to_csv ():

    combined_data = []

    # Combining Similars takes time, so let's save it if we're running frequently.
    if (not fexists (COMBINED_FPATH)):
        print ('Loading Saved Similars...')
        with open(APPROACH_FPATH, 'r') as f1, open(OUTCOMES_FPATH, 'r') as f2:
            data1 = json.load (f1)
            data2 = json.load (f2)

        print ('Combining Similars...')
        combined_data = data1 + data2

        print (F'Saving Combined to {COMBINED_FPATH}...')
        write_json (COMBINED_FPATH, combined_data)

    else:
        print (F'Loading Combined from {COMBINED_FPATH}...')
        combined_data = load_json (COMBINED_FPATH)

    filtered_empties = pseq (combined_data).filter (lambda x: len (x['similars']) != 0).to_list ()
    
    print ('Exploding Similars...')
    j_df = pd.json_normalize (filtered_empties)
    bomb_df = j_df.explode ('similars', ignore_index=True)
    separated_df = pd.concat ([ bomb_df.drop (columns=['similars']), bomb_df['similars'].apply (pd.Series) ], axis=1)

    print ('Creating Subject Lookup Table....')
    subjects = get_subjects ()
    subject_lookup_table = pseq (subjects) \
        .filter (lambda x: 'code' in x.keys ()) \
        .map (lambda x: { x['code']: x }) \
        .reduce (lambda x, y: x | y)

    print ('Assigning Main DataFrame...')

    final_result = pd.DataFrame (columns = [
        # Relative Subject.
        'subject_cd', 'subject_name', 'subject_faculty', 'subject_description', 'subject_credit_points', 'subject_assessment_types',

        # Similar Subject.
        'similar_subject_cd', 'similar_subject_name', 'similar_subject_faculty', 'similar_subject_description', 'similar_subject_study_level', 'similar_subject_credit_points', 'similar_subject_assessment_types',

        # Similarity Score.
        'similarity' ])

    for idx, row in separated_df.iterrows ():
        assessment_types_lookup = subject_lookup_table[row['similar-to']].get ('assessments', [])
        assessment_types_similar = row.get ('assessments', [])

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
        similar_assessment_types = ''

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

        rows = [[
            # Relative Subject.
            subject_lookup_table[row['similar-to']]['code'],
            subject_lookup_table[row['similar-to']]['name'],
            subject_lookup_table[row['similar-to']].get ('parent_academic_org', {}).get ('label', ''),
            remove_html_elements (subject_lookup_table[row['similar-to']].get ('description', '')),
            subject_lookup_table[row['similar-to']]['credit_points'],
            subject_assessment_types,

            # Similar Subject.
            row['code'],
            row['name'],
            row['parent_academic_org'].get ('label', ''),
            remove_html_elements (row['description']),
            row['study_level_ref'].get ('value', ''),
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
