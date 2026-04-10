import asyncio
import aiohttp

import boto3

import copy

import itertools

import orjson

import logging
import os
import re

import sys

from botocore.config import Config
from botocore.exceptions import ClientError

from bs4 import BeautifulSoup

from collections import defaultdict

from concurrent.futures import ThreadPoolExecutor

from datetime import datetime

from functools import reduce

from requests_oauth2client import OAuth2Client
from requests_oauth2client import OAuth2ClientCredentialsAuth
from requests_oauth2client import ApiClient

import dscore as dsc
import log_event_module as lem
from functional import pseq

ITEM_LIMIT = int (os.environ.get ('ITEM_LIMIT', 64))

PROGRAM_NAME = 'opensearch-full-load'

not_processable_courses = []
not_processable_subjects = []
not_processable_substructures = []

def is_processable (thing):
    if thing is None:
        return False

    if isinstance (thing, (bool, int, float)):
        return True

    if isinstance (thing, str):
        return len (thing) > 0

    if isinstance (thing, dict):
        return len (thing) > 0 and any (is_processable (v) for v in thing.values ())

    if isinstance (thing, (list, set)):
        return len (thing) > 0 and any (is_processable (v) for v in thing)

    return False

def matches_course_code_format (dict):
    code = dict['code']
    if (not is_processable (code)):
        lem.exception ('deer oh deer. this code is not processable :(')
        global not_processable_courses
        not_processable_courses.append (dict)
        return False

    match re.match (r'^C[0-9]{5}$', code):
        case None:
            lem.warning (f"it is with profound regret that {dict['code']} is declared to be a course code of no validity whatsoever, thereby consigning the course to utter obliteration and nonexistence")
            return False
        case _:
            return True

def matches_subject_code_format (dict):
    code = dict['code']
    if (not is_processable (code)):
        lem.exception ('deer oh deer. this code is not processable :(')
        global not_processable_subjects
        not_processable_subjects.append (dict)
        return False

    match re.match (r'^[0-9]{5,6}$', code):
        case None:
            lem.warning (f"it is with profound regret that {dict['code']} is declared to be a subject code of no validity whatsoever, thereby consigning the subject to utter obliteration and nonexistence")
            return False
        case _:
            return True

def matches_substructure_code_format (dict):
    code = dict['code']
    if (not is_processable (code)):
        lem.exception ('deer oh deer. this code is not processable :(')
        global not_processable_substructures
        not_processable_substructures.append (dict)
        return False

    match re.match (r'^(MAJ|SMJ|STM|CBK)[0-9]{5}$', code):
        case None:
            lem.warning (f"it is with profound regret that {dict['code']} is declared to be a substructure code of no validity whatsoever, thereby consigning the substructure to utter obliteration and nonexistence")
            return False
        case _:
            return True

def bulk_download (api, entity_name, page = 1, limit = ITEM_LIMIT):
    try:
        # &sort=sys_created_on,sys_id
        lem.info (f"sending request=/{entity_name}?page={page}&limit={limit}&sort=sys_created_on,sys_id")
        response = api.get (f"/{entity_name}?page={page}&limit={limit}&sort=sys_created_on,sys_id")
        lem.info (f"response={response}")
        
        response = orjson.loads (response.text)

    except Exception as x:
        lem.error (f"encountered error: {x}")

        return (False, {})

    cleansed_response = []

    try:
        match entity_name:
            case 'courses':
                cleansed_response = list (filter (matches_course_code_format, response['data']))
            case 'subjects':
                cleansed_response = list (filter (matches_subject_code_format, response['data']))
            case 'areas_of_study':
                cleansed_response = list (filter (matches_substructure_code_format, response['data']))
            case _:
                lem.warning (f'entity type of {entity_name} is unsupported; returning unfiltered results')
                cleansed_response = response['data']

    except Exception as e:
        lem.error (F"encountered during filtering. error: {x}")
        lem.error (F"attempting to skip and continue processing...")

    return (response['meta']['hasNext'], cleansed_response)

def get_secret_envar_name ():
    return 'SECRET_NAME'

def get_os_endpoint_url_envar_name ():
    return 'OPENSEARCH_ENDPOINT_URL'

def get_bedrock_model_id_envar ():
    return 'BEDROCK_MODEL_ID'

def get_bedrock_model_region_envar ():
    return 'BEDROCK_MODEL_REGION'

def render_error_with_message (error_message, status_code = '500'):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/orjson'
        },
        'level': 'ERROR',
        'message': error_message
    }

def boto3_client_config ():
    config = Config (
        region_name = 'ap-southeast-2',
        signature_version = 'v4',
        retries = {
            'max_attempts': 8,
            'mode': 'standard'
        })

    return config

def get_secret (secret_name, secret_stage = None):
    try:
        secretsmanager_client = boto3.client ('secretsmanager', config = boto3_client_config ())

        kwargs = {
            'SecretId': secret_name
        }
        
        if secret_stage is not None:
            kwargs['VersionStage'] = secret_stage

        response = secretsmanager_client.get_secret_value (**kwargs)
        lem.info (f"{secret_name} secret value obtained")

    except ClientError:
        lem.exception (F"could not obtain the value in secret {secret_name}", )
        
        raise
    else:
        return orjson.loads (response['SecretString'])

def check_envars ():
    if os.environ.get (get_secret_envar_name ()) == None:
        message = "secret name is missing from the environment"
        lem.exception (message)
        return render_error_with_message (message)

    if os.environ.get (get_os_endpoint_url_envar_name ()) == None:
        message = "OpenSearch event store endpoint URL is missing"
        lem.exception (message)
        return render_error_with_message (message)

    if os.environ.get (get_bedrock_model_id_envar ()) == None:
        message = "Bedrock model ID (the BEDROCK_MODEL_ID envar) is missing from the environment"
        lem.exception (message)
        return render_error_with_message (message)

    if os.environ.get (get_bedrock_model_region_envar ()) == None:
        message = "Bedrock model ID (the BEDROCK_MODEL_REGION envar) is missing from the environment"
        lem.exception (message)
        return render_error_with_message (message)

    return None

def join_learning_outcomes (dict, top_outcome_element = 'course_learning_outcome'):
    def extract_learning_outcome_descriptions (outcome):
        # Extract the main description if it exists
        main_description = [ outcome['description'] ] if 'description' in outcome else []
        
        # Extract the description from learning_outcome_element if it exists
        element_description = [ element['description'] for element in outcome.get ('learning_outcome_element', []) if 'description' in element ]
        
        # Combine main description and element description
        return main_description + element_description
    
    # course_learning_outcome is an array of objects
    outcomes = dict.get (top_outcome_element, [])

    descriptions_list = reduce (lambda x, y: x + y, map (extract_learning_outcome_descriptions, outcomes), [])
    
    # Join the descriptions into a single string separated by spaces
    return " ".join (descriptions_list)

def cleanse_input_text (text):
    try:
        tom_yum = BeautifulSoup (text, "html.parser")

        return tom_yum.get_text ()
    except Exception as x:
        return None

def try_get_value (item_dict, key):
    if (item_dict is None):
        return None
    if (key not in item_dict):
        return None

    value = item_dict[key]

    if (isinstance (value, list)
        or isinstance (value, dict)
        or isinstance (value, str)):
        return value if len (value) > 0 else None

    return value if value is not None else None

def tokenise_event (item, entity_name):
    # Inspect substructure codes as hot garbage has been sighted in them
    if entity_name == 'areas_of_study':
        match item['code'][:3]:
            case 'CBK':
                lem.info (f'sys_id={item["sys_id"]} code={item["code"]} represents a choice block and is thus rendered ineffectual for the purposes of similarity search; consequently, it shall be blatantly disregarded')
                return item

            case 'MAJ' | 'SMJ' | 'STM':
                lem.info (f'sys_id={item["sys_id"]} code={item["code"]} is a valid substructure code; proceeding forthwith thusly')

            case _:
                lem.info (f'sys_id={item["sys_id"]} code={item["code"]}, whilst not a valid substructure code, shall not hinder our progress; therefore, we shall continue forthwith thusly')

    # Courses, subjects and areas of study
    if try_get_value (item, 'description') is not None:
        description = item['description']
        lem.info (f'code={item["code"]}: added description embeddings')
        description_vector = text_to_embeddings_via_bedrock (text = description)

        match description_vector:
            case list ():
                item['description_vector'] = description_vector
            case None:
                lem.warning (f'code={item["code"]} shall lamentably be bereft of any description')

    else:
        lem.warning (f'code={item["code"]} is lamentably bereft of any description; skipping')

    # Courses only
    if try_get_value (item, 'career_opportunities') is not None:
        lem.info (f'code={item["code"]}: added career_opportunities embeddings')
        career_vector = text_to_embeddings_via_bedrock (text = item['career_opportunities'])

        match career_vector:
            case list ():
                item['career_vector'] = career_vector
            case None:
                lem.warning (f'academic item code={item["code"]} shall have bleak career opportunities')

    # Courses only
    if try_get_value (item, 'course_learning_outcome') is not None:
        if len (item.get ('course_learning_outcome')) > 0:
            lem.info (f'code={item["code"]}: added course_learning_outcome embeddings')
            outcomes_vector = text_to_embeddings_via_bedrock (
                text = join_learning_outcomes (dict = item, top_outcome_element = 'course_learning_outcome'))

            match outcomes_vector:
                case list ():
                    item['outcomes_vector'] = outcomes_vector
                case None:
                  lem.warning (f'course code={item["code"]} shall regrettably be devoid of any delineated learning outcomes')

    # Subjects only
    if try_get_value (item, 'subject_learning_outcome') is not None:
        if len (item.get ('subject_learning_outcome')) > 0:
            lem.info (f'code={item["code"]}: added subject_learning_outcome embeddings')

            subject_learning_outcomes_embeddings = text_to_embeddings_via_bedrock (
                text = join_learning_outcomes (dict = item, top_outcome_element = 'subject_learning_outcome'))

            match subject_learning_outcomes_embeddings:
                case list ():
                    item['outcomes_vector'] = subject_learning_outcomes_embeddings
                case _:
                  lem.warning (f'subject code={item["code"]}: shall regrettably be devoid of any delineated learning outcomes')

    # Subjects only
    if try_get_value (item, 'learning_approach') is not None:
        if len (item.get ('learning_approach')) > 0:
            lem.info (f'code={item["code"]}: added learning_approach embeddings')

            learning_approach_embeddings = text_to_embeddings_via_bedrock (
                text = item['learning_approach'])

            match learning_approach_embeddings:
                case list ():
                    item['approach_vector'] = learning_approach_embeddings
                case _:
                  lem.warning (f'subject code={item["code"]}: shall regrettably be devoid of any meaningful learning approach')

    try:
        orjson.dumps (item)

    except Exception as x:
        lem.error (f"failed item code={item['code']}")
        lem.error (f"failed item description={item.get ('description', 'n/a')}")
        lem.error (f"failed item career_opportunities={item.get ('career_opportunities', 'n/a')}")

        lem.error (f"failed item course_learning_outcome={item.get ('course_learning_outcome', 'n/a')}")
        if 'course_learning_outcome' in item:
            text = cleanse_input_text (
                join_learning_outcomes (dict = item, top_outcome_element = 'course_learning_outcome'))
            lem.error (f"failed item course_learning_outcome_text={text}")

            lem.error (f"failed item course_learning_outcome={item.get ('subject_learning_outcome', 'n/a')}")

        if 'subject_learning_outcome' in item:
            text = cleanse_input_text (
                join_learning_outcomes (dict = item, top_outcome_element = 'subject_learning_outcome'))
            lem.error (f"failed item subject_learning_outcome_text={text}")
                        
        raise

    return item

async def tokenise_events (events, entity_name):
    with ThreadPoolExecutor (max_workers = ITEM_LIMIT) as pool:
        tasks = [
            asyncio.get_running_loop ().run_in_executor (pool, tokenise_event, event, entity_name) for event in events
        ]

        future_events = await asyncio.gather (*tasks)

        return future_events

async def consign_knn_event (event, oauth2_token, session, entity_name, headers):
    event_id = event['sys_id']
        
    opensearch_endpoint = f'https://{os.environ[get_os_endpoint_url_envar_name ()]}'
        
    event_id = event['sys_id']
            
    knn_index_endpoint = f'{opensearch_endpoint}/{entity_name}_knn/_doc/{event_id}'

    # headers['Authorization'] = f'Bearer {token}'

    # Persist the event into the KNN index first
    lem.info (f'consigning {event["code"]} with sys_id {event_id} into {entity_name}_knn')

    try:
        async with session.put (knn_index_endpoint, headers = headers, data = orjson.dumps (event)) as response:
            response.raise_for_status ()
        
            return await response.text ()

    except Exception as x:
        lem.error (render_error_with_message (x))

    return

async def consign_event (fat_event, oauth2_token, session, entity_name, headers):
    event = copy.deepcopy (fat_event)

    event_id = event['sys_id']
        
    opensearch_endpoint = f'https://{os.environ[get_os_endpoint_url_envar_name ()]}'
        
    event_id = event['sys_id']
            
    # Delete embeddings from the event to store the event in the main document index
    for key in [ 'description_vector', 'career_vector', 'outcomes_vector', 'approach_vector' ]:
        if key in event:
            del event[key]    

    index_endpoint = f'{opensearch_endpoint}/{entity_name}/_doc/{event_id}'

    lem.info (f'consigning {entity_name} {event["code"]} with sys_id {event_id}')

    try:
        async with session.put (index_endpoint, headers = headers, data = orjson.dumps (event)) as response:
            response.raise_for_status ()
        
            return await response.text ()

    except Exception as x:
        lem.error (render_error_with_message (x))

    return

async def consign_events (events, oauth2_token, entity_name, headers):
    async with aiohttp.ClientSession () as session:
        tasks = map (lambda event: consign_event (event, oauth2_token, session, entity_name, headers), events)
        knn_tasks = map (lambda event: consign_knn_event (event, oauth2_token, session, entity_name, headers), events)

        all_tasks = itertools.chain (tasks, knn_tasks)

        await asyncio.gather (*all_tasks)

async def event_dispatcher (events, entity_name, headers):
    async with aiohttp.ClientSession () as session:
        # oauth2_token = await get_oauth2_token (session)
        oauth2_token = None

        await consign_events (events, oauth2_token, entity_name, headers)

def purge_index (entity_name):
    lem.info (f'purging the {entity_name} index')
    opensearch_client = ApiClient (f'https://{os.environ[get_os_endpoint_url_envar_name ()]}')

    opensearch_client.post (f'/{entity_name}/_delete_by_query',
                           headers = {
                               'Content-Type': 'application/orjson; charset=utf-8'
                           },
                           data = orjson.dumps ({
                               'query': {
                                   'match_all': {}
                               }
                           }))

    lem.info (f'/{entity_name} index purged')
        
    return

def authorise ():
        secret_name = 'nonprod/curriculum/vendor/courseloop/endpoints/inbound/oidc/client'

        cl_secret = get_secret (secret_name)

        token_endpoint = cl_secret['oauth2_token_endpoint']

        oauth2client = OAuth2Client (
            token_endpoint = token_endpoint,

            auth = (
                cl_secret['client_id'],
                cl_secret['client_secret']),

            scope = cl_secret['scope']
        )

        cl_endpoint = cl_secret['endpoint']

        lem.info ("obtaining OAuth2 token")
        lem.info (f"CL endpoint={cl_endpoint}")

        cl_api = ApiClient (
            cl_endpoint,
            auth = OAuth2ClientCredentialsAuth (oauth2client)
        )

        lem.info ("obtained OAuth2 token")

        return cl_api

def lambda_handler (event, context):
    check_envars ()
    
    try:
        cl_api = authorise ()

        entity_names = [
            'courses',
            'subjects',
            'areas_of_study'
        ]

        # Create a new event loop to ingest, transform and dispatch events asyncronously
        loop = asyncio.new_event_loop ()

        asyncio.set_event_loop (loop)

        for entity_name in entity_names:
            purge_index (entity_name)
            purge_index (f'{entity_name}_knn')

            lem.info (f"processing entity={entity_name}")

            has_next_flag = True
            page = 1

            receiver = []
            total_event_count = 0

            while has_next_flag == True:
                has_next_flag, events = bulk_download (cl_api, entity_name, page)

                page += 1

                future_events = asyncio.run (tokenise_events (events, entity_name))

                lem.info (f'gathered {len (future_events)} events')

                total_event_count += len (future_events)
                total_event_count += len (events)
                receiver += events

                loop.run_until_complete (event_dispatcher (events = future_events,
                                                           entity_name = entity_name,
                                                           headers = {
                                                               'Content-Type': 'application/orjson; charset=utf-8'
                                                           }))

            lem.info (f'{entity_name} summary: {total_event_count} academic items furnished into OpenSearch')

            dsc.save_generated (PROGRAM_NAME, F'{entity_name}-receiver', receiver)

        loop.close ()

    except Exception as error:
        lem.exception (error)
        raise
    
    return {
        'statusCode': '200',

        'headers': {
            'Content-Type': 'application/orjson'
        }
    }

if (__name__ == '__main__'):
    correlation_id, start_time = lem.init_logger ('opensearch-full-load')

    envars = dsc.load_json ('secrets.json')['OPENSEARCH']['NONPROD']
    os.environ.update (envars)

    lambda_handler ({}, {})

    dsc.save_generated (PROGRAM_NAME, 'unprocessable-courses', not_processable_courses)
    dsc.save_generated (PROGRAM_NAME, 'unprocessable-subjects', not_processable_subjects)
    dsc.save_generated (PROGRAM_NAME, 'unprocessable-substructures', not_processable_substructures)
