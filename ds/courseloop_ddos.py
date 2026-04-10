import requests
from requests.auth import HTTPBasicAuth

import dscore as dsc

def main ():
    credentials = dsc.load_json ('secrets.json')['COURSELOOP']['UAT']
    hostname = credentials['hostname']
    username = credentials['username']
    password = credentials['password']

    base_url = F'https://{hostname}/api/x_f5sl_cl/v3/user/user?tx_id=2f2321e11b1bb210adfddc69b04bcb52&page=600'

    print ('making request...')
    response = requests.get (
        base_url,
        auth=HTTPBasicAuth(username, password),
    )
    print ('done!')

    print (response.text)

if (__name__ == '__main__'):
    main ()
