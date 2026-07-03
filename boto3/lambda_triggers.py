import os
import sys
import boto3
import socket

from functional import pseq, seq

from typing import Dict

import dscore as dsc

import argv_parser as ap
from argv_parser import KCONTAINS, KENABLE, KPREFIX, KREWIND_ONLY, KSUFFIX, KQUERY_ONLY, KSTATUS_CHECK

PROGRAM_NAME = 'lambda-trigger-laziness'

def get_lambda_client ():
    lambda_client = boto3.client ('lambda')
    return lambda_client

def list_functions (lambda_client):
    lambda_list_functions_response = lambda_client.list_functions ()
    lambda_functions = lambda_list_functions_response['Functions']

    while (lambda_list_functions_response.get ('NextMarker', '') != ''):
        lambda_list_functions_response = lambda_client.list_functions (
            Marker = lambda_list_functions_response['NextMarker']
        )

        lambda_functions += lambda_list_functions_response['Functions']

    return lambda_functions

def filter_function_names (lambda_functions, prefix, suffix, contains):
    return pseq (lambda_functions) \
        .filter (lambda f: contains in f['FunctionName']) \
        .filter (lambda f: f['FunctionName'].startswith (prefix)) \
        .filter (lambda f: f['FunctionName'].endswith (suffix)) \
        .to_list ()

def list_event_source_mappings (lambda_client, lambda_functions):
    def get_individual_source_mapping (lambda_function):
        event_source_mappings_response = lambda_client.list_event_source_mappings (FunctionName = lambda_function['FunctionName'])
        event_source_mappings = event_source_mappings_response['EventSourceMappings']

        while (event_source_mappings_response.get ('NextMarker', '') != ''):
            event_source_mappings_response = lambda_client.list_event_source_mappings (
                FunctionName = lambda_function['FunctionName'],
                Marker = event_source_mappings_response['NextMarker']
            )

            event_source_mappings += event_source_mappings_response['EventSourceMappings']

        return event_source_mappings

    event_sources = seq (lambda_functions) \
            .map (lambda func: get_individual_source_mapping (func)) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

    return event_sources

def get_event_source_mappings (lambda_client, event_source_mappings):
    uuids = pseq (event_source_mappings).map (lambda esm: esm['UUID']).to_list ()
    event_source_mapping_responses = seq (uuids) \
        .map (lambda uuid: lambda_client.get_event_source_mapping (UUID = uuid)) \
        .to_list ()

    return event_source_mapping_responses

def function_name_from_arn (arn):
    return arn.split (':')[-1]

def update_event_source_mappings (lambda_client, event_source_mappings, should_enable):
    def exec (esm):
        try:
            return lambda_client.update_event_source_mapping (
                UUID = esm['UUID'],
                FunctionName = function_name_from_arn (esm['FunctionArn']),
                Enabled = should_enable
            )
        except Exception as riue:
            return {
                'Error': riue,
                'Failed': F'{esm['FunctionArn']} is likely in use. Skipping...'
            }

    update_response = seq (event_source_mappings) \
        .map (lambda esm: exec (esm)) \
        .map (lambda esm: esm['FunctionArn']) \
        .to_list ()

    return update_response

def main (argv):
    lambda_client = get_lambda_client ()

    if (not dsc.has_generated (PROGRAM_NAME, 'lambda-functions')):
        lambda_functions = list_functions (lambda_client)
        dsc.save_generated (PROGRAM_NAME, 'lambda-functions', lambda_functions)

    else:
        lambda_functions = dsc.load_generated (PROGRAM_NAME, 'lambda-functions')

    request_key_cache = F'ingestor-{argv[KPREFIX]}-{argv[KSUFFIX]}-{argv[KCONTAINS]}'
    event_source_map_key_cache = F'event-source-mappings-{argv[KPREFIX]}-{argv[KSUFFIX]}-{argv[KCONTAINS]}'
    event_source_details_key_cache = F'event-source-details-{argv[KPREFIX]}-{argv[KSUFFIX]}-{argv[KCONTAINS]}'

    if (not dsc.has_generated (PROGRAM_NAME, request_key_cache)):
        ingestor_functions = filter_function_names (lambda_functions, argv[KPREFIX], argv[KSUFFIX], argv[KCONTAINS])
        dsc.save_generated (PROGRAM_NAME, request_key_cache, ingestor_functions)

    else:
        ingestor_functions = dsc.load_generated (PROGRAM_NAME, request_key_cache)

    if (argv[KQUERY_ONLY]):
        print (pseq (ingestor_functions).map (lambda x: x['FunctionName']).to_list ())
        return

    if (not dsc.has_generated (PROGRAM_NAME, event_source_map_key_cache) or argv[KSTATUS_CHECK]):
        event_source_mappings = list_event_source_mappings (lambda_client, ingestor_functions)
        dsc.save_generated (PROGRAM_NAME, event_source_map_key_cache, event_source_mappings)

    else:
        event_source_mappings = dsc.load_generated (PROGRAM_NAME, event_source_map_key_cache)

    if (argv[KSTATUS_CHECK]):
        print (pseq (event_source_mappings).map (lambda e: { function_name_from_arn (e['FunctionArn']): e['State'] }).to_list ())
        return

    if (not dsc.has_generated (PROGRAM_NAME, event_source_details_key_cache)):
        source_mapping_details = get_event_source_mappings (lambda_client, event_source_mappings)
        dsc.save_generated (PROGRAM_NAME, event_source_details_key_cache, event_source_mappings)

    else:
        source_mapping_details = dsc.load_generated (PROGRAM_NAME, event_source_details_key_cache)

    if (argv.get (KREWIND_ONLY, False)):
        result = []

        for smd in source_mapping_details:
            function_arn = smd['FunctionArn']
            function_envars = pseq (ingestor_functions) \
                .filter (lambda f: f['FunctionArn'] == function_arn) \
                .map (lambda f: f['Environment']['Variables']) \
                .to_list ()[0]

            streaming_cluster_endpoint = function_envars.get ('STREAMING_CLUSTER_ENDPOINT', os.environ.get ('STREAMING_CLUSTER_ENDPOINT', None))
            streaming_cluster_region   = function_envars.get ('STREAMING_CLUSTER_REGION', 'ap-southeast-2')
            topic                      = smd['Topics'][0]
            consumer_group             = smd['AmazonManagedKafkaEventSourceConfig']['ConsumerGroupId']
            function_name              = function_name_from_arn (function_arn)

            import kafka_rewinder as kr
            result.append (kr.reset_consumer_group_offsets (function_name, topic, consumer_group, streaming_cluster_endpoint, streaming_cluster_region))

        print (result)

    else:
        updated_event_source_mappings = update_event_source_mappings (lambda_client, source_mapping_details, argv[KENABLE])

        print_result = pseq (updated_event_source_mappings) \
            .map (lambda x: function_name_from_arn (x)) \
            .to_list ()

        print (print_result)

if (__name__ == '__main__'):
    argv = ap.parse_argv ()

    main (argv)
