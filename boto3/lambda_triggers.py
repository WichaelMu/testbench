import boto3

from functional import pseq, seq

import dscore as dsc

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

def filter_function_names (lambda_functions, prefix, suffix):
    return pseq (lambda_functions) \
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

def main ():
    lambda_client = get_lambda_client ()

    if (not dsc.has_generated (PROGRAM_NAME, 'ingestor-functions')):
        lambda_functions = list_functions (lambda_client)
        ingestor_functions = filter_function_names (lambda_functions, '', 'events_ingestor')

        dsc.save_generated (PROGRAM_NAME, 'ingestor-functions', ingestor_functions)

    else:
        ingestor_functions = dsc.load_generated (PROGRAM_NAME, 'ingestor-functions')

    event_source_mappings = list_event_source_mappings (lambda_client, ingestor_functions)
    source_mapping_details = get_event_source_mappings (lambda_client, event_source_mappings)
    print (source_mapping_details)

if (__name__ == '__main__'):
    main ()
