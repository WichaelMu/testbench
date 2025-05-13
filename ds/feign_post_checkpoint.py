import os
import sys
import requests

import dscore as dsc

def get_secret_stuff ():
    secret_stuff = dsc.load_json ('feign_post_checkpoint_secrets.json')['NONPROD']

    client_id = secret_stuff['client_id']
    client_secret = secret_stuff['client_secret']
    endpoint = secret_stuff['endpoint']
    oidc_token_endpoint = secret_stuff['oidc_token_endpoint']

    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }

    response = requests.post (oidc_token_endpoint, data=payload)
    response.raise_for_status ()
    token_data = response.json ()

    retval = token_data['access_token']
    print (retval)
    return retval

def main ():
    access_token = get_secret_stuff ()

    target_url = 'https://uts-test.t1cloud.com/T1Default/CiAnywhere/Web/UTS-TEST/Api/WS/v1/SystemVariable/Save'

    payload = {
        'ParameterName': 'EVT_LAST_MOD_SSP',
        'Value': '2025-02-04T06:02:49+11:00'
    }

    headers = {
        'Authorization': F'Bearer: {access_token}',
        'Accept':        'application/json',
        'Content-Type':  'application/json'
    }

    response = requests.post (target_url, headers=headers, data=payload)
    # response.raise_for_status ()

    print (response.json ())

if (__name__ == '__main__'):
    main ();
    sys.exit (0)
