import requests
from requests.auth import HTTPBasicAuth

from functional import pseq, seq

import dscore as dsc

PROGRAM_NAME = 'courseloop-ddos'

def main ():
    credentials = dsc.load_json ('secrets.json')['COURSELOOP']['UAT']
    hostname = credentials['hostname']
    username = credentials['username']
    password = credentials['password']

    page_range = [ i for i in range (1, 2588 + 1) ]

    r = pseq (page_range) \
        .peek (print) \
        .map (lambda p: requests.get (
            F'https://{hostname}/api/x_f5sl_cl/v3/user/user?cl_limit=10&cl_page={p}&cl_transaction=5fcc6fb087540f1039b8ab0a0cbb35d7',
            auth=HTTPBasicAuth(username, password),
        ).json ()) \
        .to_list ()

    dsc.save_generated (PROGRAM_NAME, 'results', r)
    print ('done')

if (__name__ == '__main__'):
    main ()
