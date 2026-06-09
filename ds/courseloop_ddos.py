import json
import requests
from requests.auth import HTTPBasicAuth

from functional import pseq, seq

import dscore as dsc

from stopwatch import Stopwatch

PROGRAM_NAME = 'courseloop-ddos'

def grab_next_href (links):
    for l in links:
        if ('rel' in l.keys () and l['rel'] == 'next'):
            return l['href']

    return None

def main ():
    credentials = dsc.load_json ('secrets.json')['COURSELOOP']['UAT']
    hostname = credentials['hostname']
    username = credentials['username']
    password = credentials['password']

    page_range = [ i for i in range (1, 2588 + 1) ]

    sw = Stopwatch ()

    initial_request = requests.get (
        F'https://{hostname}/api/x_f5sl_cl/v3/user/user?cl_limit=10',
        auth=HTTPBasicAuth(username, password),
    )

    mark_time = sw.mark ()
    print (F'Initial request responded in: {mark_time}')

    response = initial_request.json ()
    response_builder = response['user']

    links = response['links']
    the_next = grab_next_href (links)

    max_loop = 1 << 52
    iter_l = 0
    while (the_next != None):
        iter_l += 1
        if (iter_l == max_loop):
            break

        response = requests.get (
            F'https://{hostname}{the_next}',
            auth=HTTPBasicAuth(username, password),
        )

        delta_time = sw.lap ()
        mark_time = sw.mark ()
        print (F'{delta_time} - {the_next}')

        jresponse = response.json ()
        response_builder += jresponse['user']

        links = jresponse['links']
        the_next = grab_next_href (links)

    dsc.save_generated (PROGRAM_NAME, 'built-response', response_builder)
    print ('done')

if (__name__ == '__main__'):
    main ()
