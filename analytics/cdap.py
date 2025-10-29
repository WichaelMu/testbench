import os
import json
import requests
import time

from dateutil import parser
from datetime import datetime, timezone, timedelta

from dap.api import DAPClient
from dap.dap_types import Credentials, Format, IncrementalQuery
import dap.dap_error as daperror
import dap.api as dapi
import dap.dap_types as dap


BASE_URL = 'https://api-gateway.instructure.com'
INBOUND = {
  "database": "canvas",
  "tables": [
    "scores"
  ]
}

STRF_TIME = '%Y-%m-%dT%H:%M:%SZ'

async def start_incremental_download (base_url, credentials, from_date, to_date, database, table):
    output_directory = os.path.join ('/tmp', "canvas-dap-output")
    os.makedirs (output_directory, exist_ok=True)

    # print ({
    #     'output_directory': F'{output_directory = }',
    #     '/tmp': os.listdir ('/tmp'),
    #     '/tmp/canvas-dap-output': os.listdir (output_directory)
    # })

    print (F'Preparing to download from: {base_url}')

    try:
        async with DAPClient (base_url, credentials) as session:
            query = IncrementalQuery (
                format=Format.JSONL,
                mode=None,
                since=from_date,
                until=to_date
            )

            await session.download_table_data (
                database, table, query, output_directory, decompress=False
            )

    except Exception as e:
        print (F'DataFetchError (f"Failed poll canvas {e}")')

    print ('Done.')


async def main_actual ():

    secrets_json = open ('secrets.json', 'r')
    secrets = json.load (secrets_json)['NONPROD']
    secrets_json.close ()

    credentials = Credentials.create (
        client_id     = secrets['ClientId'],
        client_secret = secrets['ClientSecret']
    )

    now_iso      = datetime.now (timezone.utc)
    default_date = now_iso - timedelta (hours = 4)

    from_date = parser.isoparse (default_date.strftime (STRF_TIME)) - timedelta (days = 30)
    to_date = from_date + timedelta (minutes = 5)
    await start_incremental_download (BASE_URL, credentials, from_date, to_date, INBOUND['database'], INBOUND['tables'][0])

async def main_wait ():
    secrets_json = open ('secrets.json', 'r')
    secrets = json.load (secrets_json)['NONPROD']
    secrets_json.close ()

    credentials = {
    }

    response = requests.post (F'{BASE_URL}/ids/auth/login',
        data = { 'grant_type': 'client_credentials' },
        auth = (secrets['ClientId'], secrets['ClientSecret'])
    )

    response.raise_for_status ()
    token_data = response.json ()
    access_token = token_data['access_token']

    headers = {
        'Authorization': F'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': '*/*'
    }

    now_iso      = datetime.now (timezone.utc)
    default_date = now_iso - timedelta (days = 30)

    from_date = default_date.strftime (STRF_TIME)
    to_date = datetime.now (timezone.utc).strftime (STRF_TIME)
    payload = {
        'format': 'jsonl',
        'since': from_date,
        'until': to_date
    }

    print (payload)

    # response = requests.get (F'{BASE_URL}/dap/query/canvas/table', headers = headers)
    response = requests.post (F'{BASE_URL}/dap/query/canvas/table/{INBOUND["tables"][0]}/data', headers = headers, data = json.dumps (payload))

    rj = response.json ()
    print (rj)

    job_id = rj['id']

    time_started = datetime.now ()
    while (True):
        print (F'Polling status of {job_id}')

        get_response = requests.get (F'{BASE_URL}/dap/job/{job_id}', headers = headers)

        data = get_response.json()
        print (data)

        if (data['status'] == 'complete'):
            break

        time.sleep (1)

    time_taken = (datetime.now () - time_started).total_seconds ()

    print (F'{job_id} {INBOUND["tables"][0]} completed in {time_taken} seconds. Downloading now...')

    time_started = datetime.now ()
    credentials = Credentials.create (
        client_id     = secrets['ClientId'],
        client_secret = secrets['ClientSecret']
    )

    async with DAPClient(BASE_URL, credentials = credentials) as session:
        objects = await session.get_objects (job_id)
        resources = await session.get_resources (objects)
        paths = await session.download_resources (list (resources.values ()), '/tmp/mw-canvas-dap-output', decompress=False)
        print("Saved:", paths)


    time_taken = (datetime.now () - time_started).total_seconds ()

    print (F'{job_id} objects downloaded in {time_taken} seconds.')
    print ('Done.')


import asyncio

if (__name__ == '__main__'):
    asyncio.run (main_actual ())
    # asyncio.run (main_wait ())
