import sys
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

def update_event_source_mappings (lambda_client, event_source_mappings, should_enable):
    update_response = seq (event_source_mappings) \
        .map (lambda esm: lambda_client.update_event_source_mapping (
            UUID = esm['UUID'],
            FunctionName = esm['FunctionArn'].split(':')[-1],
            Enabled = should_enable
        )) \
        .to_list ()

    return update_response

def main (argv):
    lambda_client = get_lambda_client ()

    if (not dsc.has_generated (PROGRAM_NAME, 'lambda-functions')):
        lambda_functions = list_functions (lambda_client)
        dsc.save_generated (PROGRAM_NAME, 'lambda-functions', lambda_functions)

    else:
        lambda_functions = dsc.load_generated (PROGRAM_NAME, 'lambda-functions')

    ingestor_functions = filter_function_names (lambda_functions, argv[KPREFIX], argv[KSUFFIX])
    event_source_mappings = list_event_source_mappings (lambda_client, ingestor_functions)
    source_mapping_details = get_event_source_mappings (lambda_client, event_source_mappings)

    updated_event_source_mappings = update_event_source_mappings (lambda_client, source_mapping_details, argv[KENABLE])
    print (updated_event_source_mappings)

KENABLE = 'enable'
KPREFIX = 'prefix'
KSUFFIX = 'suffix'
KCONTAINS = 'contains'

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
    if (KENABLE not in options):
        print (F'--enable is required')
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
