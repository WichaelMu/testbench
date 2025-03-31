import requests
import time
import json
import re

from functional import pseq, seq

UNAUTHORISED = 'UNAUTHORISED'
FORBIDDEN = 'FORBIDDEN'

ERROR_CODES = {
    401: UNAUTHORISED,
    403: FORBIDDEN
}

WERROR_CODES = {
    UNAUTHORISED: 401,
    FORBIDDEN: 403
}

def fexists (fpath):
    return os.path.isfile (fpath)

def write_json (path, data):
    with open (path, 'w') as w:
        json.dump (data, w)

def load_json (path):
    with open (path) as f:
        print (F'Opening saved file {path}')
        return json.load (f)

def get_token ():
    return ''
def get_base_url ():
    return 'https://uts.beta.instructure.com/api/v1'

def get_account_ids ():
    accounts = make_request (F'{get_base_url ()}/accounts')
    print (accounts)

    if (isinstance (accounts, str) and accounts in WERROR_CODES.keys ()):
        return []

    # Remap return value to [ $.[].id ]
    account_ids = seq (accounts) \
        .filter (lambda x: 'id' in x.keys ()) \
        .map (lambda x: x['id'])

    return account_ids.to_list ()

def dump_courses_onto_account (account_id=365):
    course_creation_payload = {
        "course": {
            "name": "MW - Full Course Pagination Testbench",
            "course_code": "AI101",
            "start_at": "2025-02-28T00:00:00Z",
            "end_at": "2025-06-30T23:59:59Z",
            "license": "private",
            "is_public": False,
            "public_syllabus": False,
            "public_description": "MW - Full Course Pagination Testbench Description"
        }
    }
    create_course_response = make_request (F'{get_base_url ()}/accounts/{account_id}/courses',
                                               method='POST',
                                               payload=course_creation_payload)
    print (create_course_response)

def make_request (api_url, raise_on_error=True, method='GET', payload={}, with_headers=False):
    headers = { 'Authorization': F'Bearer {get_token ()}' }
    attempts = 1

    while True:
        response = None
        if (method == 'GET'):
            response = requests.get (api_url, headers=headers)
        elif (method == 'POST'):
            response = requests.post (api_url, headers=headers, json=json.dumps (payload))

        # if (raise_on_error):
        #     response.raise_for_status ()

        if (response.status_code == 200):
            if (attempts > 1):
                print (F'Retry successful on attempt: {attempts}')
            
            if (with_headers):
                return response.json (), response.headers
            return response.json ()

        if (response.status_code == 403 or response.status_code == 401):
            print (F'Raise: {response.status_code} - {ERROR_CODES[response.status_code]}.')
            if (raise_on_error):
                response.raise_for_status ()
            return ERROR_CODES[response.status_code]

        print (F'\tEncountered {response.status_code}. Retrying {api_url}...')
        time.sleep (5)
        attempts += 1
        print (F'\tRetrying last. Attempt #: {attempts}...')

def get_next (headers):
    if ('link' not in headers.keys ()):
        print ('Link not found! Skipping Pagination...')
        return None

    links = headers['link'].split (',')
    raw_next_link = seq (links).filter (lambda l: 'rel="next"' in l).to_list ()
    next_link = raw_next_link[0] if (len (raw_next_link) > 0) else None

    if (next_link is None):
        print ('Link found, but no ref="next"! Skipping Pagination...')
        return None

    regex = F'^<({get_base_url ()}.*100).*'
    match = re.match (regex, next_link)
    if (match):
        return match.group (1)

    print (F'Regex failed!\n\nRegex: {regex}\nLink: {next_link}\nLink Header: {raw_next_link}')
    return None

def get_all_courses_for_account (account_id):
    result = []

    print ('Getting Page 1...')
    current_page = 1

    response, headers = make_request (F'{get_base_url ()}/accounts/{account_id}/courses?per_page=100', with_headers=True)
    next_link = get_next (headers)

    while (next_link is not None):
        current_page += 1
        print (F'Getting {next_link}...')

        response, headers = make_request (next_link, with_headers=True)
        result += response
        next_link = get_next (headers)

    return { 'account_id': account_id, 'courses': result }

def get_all_courses_for_accounts (account_ids):
    result = pseq (account_ids) \
        .map (lambda account_id: get_all_courses_for_account (account_id)) \
        .to_list ()

    print ('Writing result to absolution.json')
    write_json ('absolution.json', result)
    return result

def main ():
    account_ids = get_account_ids ()
    get_all_courses_for_accounts (account_ids)

if (__name__ == '__main__'):
    main ()
