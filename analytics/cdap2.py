import time
import asyncio
import requests
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from dateutil import parser

from dap.api import DAPClient
from dap.dap_types import Credentials

BASE_URL = 'https://api-gateway.instructure.com'
OUT_GENERATED_PATH = '/tmp/mw-canvas-dap-out'
INBOUND = {
    'database': 'canvas',
    'tables': [ 'pseudonyms' ]
}

class Stopwatch:
    """Static stopwatch usable anywhere in your process."""
    _starts = {}
    _records = defaultdict (list)

    @classmethod
    def start (cls, key = "default"):
        t = time.perf_counter ()
        cls._starts[key] = t
        return t

    @classmethod
    def time (cls, key = "default"):
        try:
            return time.perf_counter () - cls._starts[key]
        except KeyError:
            raise RuntimeError (F'Stopwatch.start () has not been called for key "{key}"')

    @classmethod
    def stop (cls, key = "default", *, reset = True, record = True):
        elapsed = cls.time (key)

        if record:
            cls._records[key].append (elapsed)
        if reset:
            cls._starts.pop (key, None)

        return elapsed

    @classmethod
    def print (cls, *, latest_only = False):
        if not cls._records:
            return '(no recorded timers)'

        if latest_only:
            lines = [ F'{k} took {runs[-1]:.6f} seconds.' for k, runs in cls._records.items () if runs ]
            return "\n".join (lines) if lines else '(no recorded timers)'

        lines = []
        for k, runs in cls._records.items():
            n = len (runs)
            total = sum (runs)
            last = runs[-1]
            avg = total / n
            lines.append (F'{k}: n={n}, last={last:.6f}s, avg={avg:.6f}s, total={total:.6f}s')
        return "\n".join (lines)

def get_client_stuff (environment):
    secrets = open ('secrets.json', 'r')
    secrets_json = json.load (secrets)
    secret_stuff = secrets_json[environment]

    auth_stuff = (secret_stuff['ClientId'], secret_stuff['ClientSecret'])
    return auth_stuff

def get_canvas_auth (environment):
    print ('get_canvas_auth ()')
    Stopwatch.start ('get_canvas_auth ()')

    auth_url = F'{BASE_URL}/ids/auth/login'
    data_stuff = { 'grant_type': 'client_credentials' }
    auth_stuff = get_client_stuff (environment)

    response = requests.post (auth_url, data = data_stuff, auth = auth_stuff)
    response.raise_for_status ()

    access_token = response.json ()['access_token']

    Stopwatch.stop ('get_canvas_auth ()')

    return access_token

def get_time_windows ():
    now_iso      = datetime.now (timezone.utc)
    default_date = now_iso - timedelta (days = 30)

    from_date = default_date.strftime ('%Y-%m-%dT%H:%M:%SZ')
    to_date   = None

    return from_date, to_date

def canvas_create_job (jwt, table, from_date, to_date = None, database = 'canvas'):
    print ('canvas_create_job')
    Stopwatch.start ('canvas_create_job ()')

    create_job_url = F'{BASE_URL}/dap/query/{database}/table/{table}/data'
    headers = { 'Authorization': F'Bearer {jwt}' }
    data = json.dumps ({
        'format': 'jsonl',
        'since': from_date,
        'until': to_date
    })

    response = requests.post (create_job_url, headers = headers, data = data)
    response.raise_for_status ()

    Stopwatch.stop ('canvas_create_job ()')
    return response.json ()['id']

def wait_for_job_completion (jwt, job_id, slumber_seconds = 1):
    print ('wait_for_job_completion ()')
    Stopwatch.start ('wait_for_job_completion ()')

    get_status_url = F'{BASE_URL}/dap/job/{job_id}'
    headers = { 'Authorization': F'Bearer {jwt}', 'Accept': '*/*' }

    iterations = 0
    MAX_ITERATIONS = 1 + (4 * 3600) / slumber_seconds

    while (iterations < MAX_ITERATIONS):
        response = requests.get (get_status_url, headers = headers)
        response.raise_for_status ()

        response_json = response.json ()

        if (response_json['status'] == 'complete'):
            break

        time.sleep (slumber_seconds)
        iterations += 1
        print (response_json)
        print (F'\t{iterations = }')

    Stopwatch.stop ('wait_for_job_completion ()')
    return iterations

async def download_generated_objects (job_id, environment):
    print ('download_generated_objects ()')
    Stopwatch.start ('download_generated_objects ()')

    client_stuff = get_client_stuff (environment)
    credentials = Credentials.create (client_id = client_stuff[0], client_secret = client_stuff[1])

    async with DAPClient (BASE_URL, credentials = credentials) as session:
        objects   = await session.get_objects (job_id)
        resources = await session.get_resources (objects)
        paths     = await session.download_resources (list (resources.values ()), OUT_GENERATED_PATH, decompress = False)

    Stopwatch.stop ('download_generated_objects ()')

async def main ():
    print ('Start')
    environment = 'NONPROD'
    jwt = get_canvas_auth (environment)
    from_date, to_date = get_time_windows ()
    job_id = canvas_create_job (jwt, INBOUND['tables'][0], from_date, to_date, INBOUND['database'])
    wait_for_job_completion (jwt, job_id, slumber_seconds = 1)
    await download_generated_objects (job_id, environment)

    print ('')
    print (Stopwatch.print ())

    pass

if (__name__ == '__main__'):
    asyncio.run (main ())
