import sys
import boto3
import socket

from functional import pseq, seq

import py_msk_serverless_data_streaming_client as kem
from typing import Dict

from kafka import TopicPartition
from kafka.structs import OffsetAndMetadata
from kafka import KafkaConsumer

from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
from kafka.sasl.oauth import AbstractTokenProvider

import dscore as dsc

PROGRAM_NAME = 'lambda-trigger-laziness'
class MSKTokenProvider (AbstractTokenProvider):
    def __init__(self, region):
        self.region = region

    def token (self):
        token, _ = MSKAuthTokenProvider.generate_auth_token (self.region)
        return token

def reset_consumer_group (data):
    streaming_cluster_endpoint = data['streaming-cluster-endpoint']
    streaming_cluster_region   = data['streaming-cluster-region']
    topic                      = data['topic']
    consumer_group             = data['consumer-group']
    function_name              = data.get ('function-name', 'consumer-group-resetter')

    consumer = KafkaConsumer (
        bootstrap_servers         = streaming_cluster_endpoint,
        security_protocol         = 'SASL_SSL',
        sasl_mechanism            = 'OAUTHBEARER',
        sasl_oauth_token_provider = MSKTokenProvider (streaming_cluster_region),
        group_id                  = consumer_group,
        enable_auto_commit        = False,
        client_id                 = F'{function_name}.{socket.gethostname ()}',
        request_timeout_ms        = 30000,
    )

    try:
        partitions = consumer.partitions_for_topic (topic)

        if not partitions:
            raise ValueError (F'Topic not found or no partitions visible: {topic}')

        topic_partitions = [
            TopicPartition (topic, partition_id)
            for partition_id in sorted (partitions)
        ]

        earliest_offsets = consumer.beginning_offsets (topic_partitions)

        offsets_to_commit = {
            tp: OffsetAndMetadata (earliest_offsets[tp], '', -1)
            for tp in topic_partitions
        }

        consumer.commit (offsets=offsets_to_commit)

        return { F'{tp.topic}:{tp.partition}': earliest_offsets[tp] for tp in topic_partitions }

    finally:
        consumer.close (autocommit=False)

def reset_associated_offsets (source_mapping_details, ingestor_functions_lookup):
    result = {}
    for smd in source_mapping_details:
        function_arn = smd['FunctionArn']
        function_envars = pseq (ingestor_functions_lookup) \
            .filter (lambda f: f['FunctionArn'] == function_arn) \
            .map (lambda f: f['Environment']['Variables']) \
            .to_list ()[0]

        import os
        streaming_cluster_endpoint = function_envars.get ('STREAMING_CLUSTER_ENDPOINT', os.environ['STREAMING_CLUSTER_ENDPOINT'])
        streaming_cluster_region   = function_envars.get ('STREAMING_CLUSTER_REGION', 'ap-southeast-2')
        topic                      = smd['Topics'][0]
        consumer_group             = smd['AmazonManagedKafkaEventSourceConfig']['ConsumerGroupId']
        function_name              = function_name_from_arn (smd['FunctionArn'])

        reset_consumer_group_payload = {
            'streaming-cluster-endpoint': streaming_cluster_endpoint,
            'streaming-cluster-region':   streaming_cluster_region,
            'topic':                      topic,
            'consumer-group':             consumer_group,
            'function-name':              function_name
        }

        print (reset_consumer_group)

        result |= { function_name_from_arn (smd['FunctionArn']): reset_consumer_group (reset_consumer_group_payload) }

    return { 'reset': result }

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
                FunctionName = func['FunctionName'],
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

    if (not dsc.has_generated (PROGRAM_NAME, event_source_map_key_cache)):
        event_source_mappings = list_event_source_mappings (lambda_client, ingestor_functions)
        dsc.save_generated (PROGRAM_NAME, event_source_map_key_cache, event_source_mappings)

    else:
        event_source_mappings = dsc.load_generated (PROGRAM_NAME, event_source_map_key_cache)

    if (not dsc.has_generated (PROGRAM_NAME, event_source_details_key_cache)):
        source_mapping_details = get_event_source_mappings (lambda_client, event_source_mappings)
        dsc.save_generated (PROGRAM_NAME, event_source_details_key_cache, event_source_mappings)

    else:
        source_mapping_details = dsc.load_generated (PROGRAM_NAME, event_source_details_key_cache)

    result = None

    if (argv.get (KREWIND_ONLY, False)):
        result = reset_associated_offsets (source_mapping_details, ingestor_functions)

    else:
        updated_event_source_mappings = update_event_source_mappings (lambda_client, source_mapping_details, argv[KENABLE])
        result = updated_event_source_mappings

    print (result)

KENABLE = 'enable'
KPREFIX = 'prefix'
KSUFFIX = 'suffix'
KCONTAINS = 'contains'
KREWIND_ONLY = 'rewind-only'

def parse_argv ():
    argv = sys.argv[1:]
    argc = len (argv)

    # print (F'argc, argv: {argc}, {argv}')

    def process_option (option, iterator):
        match option:
            case '--enable':
                iterator += 1

                if (argv[iterator].lower () == 'yes' or argv[iterator].lower () == 'true'):
                    result = True
                elif (argv[iterator].lower () == 'no' or argv[iterator].lower () == 'false'):
                    result = False
                else:
                    print ('--enable must be [ yes | no | true | false ]')
                    sys.exit (1)

                return { KENABLE: result }, iterator

            case '--prefix':
                iterator += 1

                return { KPREFIX: argv[iterator] }, iterator

            case '--suffix':
                iterator += 1

                return { KSUFFIX: argv[iterator] }, iterator

            case '--contains':
                iterator += 1

                return { KCONTAINS: argv[iterator] }, iterator

            case '--rewind-only':
                iterator += 1

                if (argv[iterator].lower () == 'yes' or argv[iterator].lower () == 'true'):
                    result = True
                elif (argv[iterator].lower () == 'no' or argv[iterator].lower () == 'false'):
                    result = False
                else:
                    print ('--rewind-only must be [ yes | no | true | false ]')
                    sys.exit (1)

                return { KREWIND_ONLY: argv[iterator] }, iterator

            case '?' | '--help' | 'help' | '__HELP__':
                print ('--enable true | false --prefix PREFIX --suffix SUFFIX')
                sys.exit (0)
                return {}, iterator

            case _:
                return {}, iterator

    options = {
        KPREFIX: '',
        KSUFFIX: '',
        KCONTAINS: ''
    }

    iterator = 0
    while (iterator < argc):
        try:

            option, iterator = process_option (argv[iterator], iterator)
            options = options | option

            iterator += 1

        except IndexError:

            print (F'Option {iterator + 1} ({argv[iterator]}) requires a parameter.')
            process_option ('?', 0)
            sys.exit (1)

    # print (options)

    errors_exist = False
    if (KENABLE not in options and KREWIND_ONLY not in options):
        print (F'One of --enable or --rewind-only is required')
        errors_exist = True

    if (options[KPREFIX] == '' and options[KSUFFIX] == '' and options[KCONTAINS] == ''):
        print (F'One of --prefix, --suffix, or --contains must be present')
        errors_exist = True

    if (errors_exist):
        sys.exit (1)

    return options

if (__name__ == '__main__'):
    argv = parse_argv ()

    main (argv)
