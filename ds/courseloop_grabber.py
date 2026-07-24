import sys
import requests
import requests.auth

import dscore as dsc
import stopwatch

PROGRAM_NAME = 'courseloop-grabber'


def get_secret_stuff ():
    credentials  = dsc.load_json ('secrets.json')['COURSELOOP_API']['UAT']
    access_token = dsc.get_custom_auth (**credentials)

    authorisation_headers = { 'Authorization': F'Bearer {access_token}' }
    return authorisation_headers

def vet (response, what):
    return 'code' in response and what in response['code']

def grab_courseloop (what):
    generated_key = F'grab-courseloop-{what}'
    if (dsc.has_generated (PROGRAM_NAME, generated_key)):
        return dsc.load_generated (PROGRAM_NAME, generated_key)

    headers         = get_secret_stuff ()
    base_url        = 'https://uts-clapi.uat.courseloop.com'
    initial_request = requests.get (F'{base_url}/{what}?limit=32', headers = headers)

    response     = initial_request.json ()
    return_value = response['data']

    while (response['meta']['hasNext']):
        next = response['meta']['next']
        print (next, file = sys.stderr)
        running_request = requests.get (F'{base_url}/{next}', headers = headers)

        response = running_request.json ()
        return_value += response['data']

    dsc.save_generated (PROGRAM_NAME, generated_key, return_value)
    return return_value

def main ():
    sw = stopwatch.Stopwatch ()

    all_whats = grab_courseloop ('subjects')

    elapsed_time = sw.stop ()
    print (elapsed_time)

if (__name__ == '__main__'):
    main ()
