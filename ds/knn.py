import os
import sys
import math
import json

import boto3
from functional import pseq, seq
from opensearchpy import OpenSearch, RequestsHttpConnection
from bs4 import BeautifulSoup

import dscore as dsc


KENVIRONMENT = 'environment'
KINBOUND_STRING = 'inbound-string'
KCOUNT_LIMIT = 'count-limit'
KKNN_THRESHOLD = 'knn-threshold'
KWHAT = 'what'
KSEARCH_VECTOR = 'search-vector'
KUSE_LEGACY = 'use-legacy'
KDEBUG_QUERY = 'debug-query'


def parse_argv ():
    argv = sys.argv[1:]
    argc = len (argv)

    # print (F'argc, argv: {argc}, {argv}')

    def process_option (option, iterator):
        match option:

            case '--inbound-string':
                iterator += 1
                return { KINBOUND_STRING: argv[iterator] }, iterator

            case '--environment':
                iterator += 1

                if (argv[iterator] not in [ 'NONPROD', 'PROD' ]):
                    print ('Option --environment must be either NONPROD or PROD! Defaulting instead.')
                    return {}, iterator - 1

                return { KENVIRONMENT: argv[iterator] }, iterator

            case '--what':
                iterator += 1

                if (argv[iterator] not in [ 'courses', 'subjects', 'areas_of_study' ]):
                    print ('Option --what must be one of courses, subjects, or areas_of_study')
                    return {}, iterator - 1

                return { KWHAT: argv[iterator] }, iterator

            case '--count-limit':
                iterator += 1

                if (dsc.try_parse_int (argv[iterator])):
                    sanitised_argv = abs (int (argv[iterator]))
                    return { KCOUNT_LIMIT: sanitised_argv }, iterator

                print ('Option --count-limit is not a valid number! Defaulting instead.')
                return {}, iterator - 1

            case '--knn-threshold':
                iterator += 1

                if (dsc.try_parse_int (argv[iterator])):
                    sanitised_argv = int (argv[iterator]) + 1
                    return { KKNN_THRESHOLD: sanitised_argv }, iterator

                print ('Option --knn-threshold is not a valid number! Defaulting instead.')
                return {}, iterator - 1

            case '--search-vector':
                iterator += 1

                if (argv[iterator] not in [ 'description_vector', 'outcomes_vector', 'career_vector' ]):
                    print ('Option --search-vector must be one of description_vector, outcomes_vector, or career_vector')
                    return {}, iterator - 1

                return { KSEARCH_VECTOR: argv[iterator] }, iterator

            case '--use-legacy':
                iterator += 1

                return { KUSE_LEGACY, True }, iterator

            case '--debug-query':
                iterator += 1

                return { KDEBUG_QUERY, True }, iterator

            case '?' | '--help' | 'help' | '__HELP__':
                print ('\nOptions:\n\t--environment ENV\n\t--inbound-string "YOUR_STRING"\n\t--what ACADEMIC_ITEM\n\t--count-limit 0 <= 10000\n\t--knn-threshold 0F <= 1F\n')
                return {}, iterator

            case _:
                return {}, iterator

    options = {
        KENVIRONMENT: 'NONPROD',
        KINBOUND_STRING: 'the meaning of life',
        KWHAT: 'courses',
        KCOUNT_LIMIT: 20,
        KKNN_THRESHOLD: float (.75),
        KUSE_LEGACY: False,
        KDEBUG_QUERY: False
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
    return options

def sanitise (markup) -> str:
    if (not markup):
        return ""
    return BeautifulSoup (markup, 'html.parser').get_text ()

def text_to_bedrock (text, bedrock_arn, dimensions=1024):
    payload = {
        "body": {
            "text": text,
            "dimensions": dimensions
        }
    }

    if (isinstance (text, str) and len (text) == 0):
        print  ("api_common.text_to_bedrock (text, dimensions) - Paramater 'text' is empty.")

    bedrock_return_value = invoke_lambda (
        lambda_function_name = bedrock_arn,
        payload              = payload
    )

    return bedrock_return_value

def is_invalid (value, check_length:bool=True) -> bool:
    if (value is None):
        return True
    if (check_length and (isinstance (value, str) or isinstance (value, list) or isinstance (value, dict))):
        return len (value) == 0
    return False

def invoke_lambda (ulid:str = "", lambda_function_name: str = "", invocation_type: str = "RequestResponse", payload: dict = {}, other_invoke_parameters:dict={}) -> dict:
    if (is_invalid (lambda_function_name)):
        raise TypeError (F"'lambda_function_arn_envar' must be specified!")

    lambda_invoke_params = {
        "FunctionName": lambda_function_name,
        "InvocationType": invocation_type,
        "Payload": json.dumps (payload),
        **other_invoke_parameters
    }

    log_message = { "ulid": ulid, "parameters": lambda_invoke_params }
    # print (F"api_common.invoke_lambda ({ulid}, {lambda_function_name}, {invocation_type}, {payload}, {other_invoke_parameters}) - Invoking Lambda: {log_message}")

    # Invoke Lambda.
    lambda_client   = boto3.client ("lambda")
    lambda_response = lambda_client.invoke (**lambda_invoke_params)

    try:
        # Some odd behaviour here... don't use `bedrock_return_value.get ("Payload", ...)`!
        # Immediately after using `["Payload"]`, run `.read ()` and `.decode("utf-8")`.
        # The StreamingBody will not work in *any* other case.
        lambda_return_payload = lambda_response["Payload"]
        utf8_payload          = lambda_return_payload.read ().decode ("utf-8")

        # Vectors for text embeddings are huge, do not log them
        # logging.debug (F"api_common.invoke_lambda (...) - Invoked Lambda response: {utf8_payload}")
        return json.loads (utf8_payload)

    except Exception as e:
        # Errors will need to be handled in the calling function.
        print (F"Encountered error while reading and decoding Lambda invocation response!\n\t{e}")
        return { "ulid": ulid, "Error": e}

def transform_and_clean_data_knn (raw_knn_response, options):
    useful_response_part = raw_knn_response["hits"]["hits"]

    if (len (useful_response_part) == 0):
        return 0, []

    ai_definition = seq (useful_response_part) \
        .map (lambda h: h["inner_hits"]["latest"]["hits"]["hits"]) \
        .reduce (lambda h1, h2: h1 + h2, []) \
        .map (lambda s: s["_source"])

    confidence = seq (useful_response_part) \
        .map (lambda m: { "M": m["_score"] })

    highest_midi_chlorian_count = max (seq (confidence).map (lambda m: m["M"]).to_list ())

    knn_with_confidence = seq (ai_definition.zip (confidence)) \
        .map (lambda p: { **p[1], **p[0] }) \
        .to_list ()

    debug_empty_arrays  = options[KDEBUG_QUERY]
    debug_empty_strings = options[KDEBUG_QUERY]
    debug_null_values   = options[KDEBUG_QUERY]

    sanitised_fields = []
    for source in knn_with_confidence:
        def clean_data (data):
            if isinstance (data, list):
                return [
                    clean_data (subitem)
                    for subitem in data
                    if (subitem is not None or debug_null_values)
                    and (subitem != [] or debug_empty_arrays)
                    and (subitem != "" or debug_empty_strings)
                ]
            elif isinstance (data, dict):
                return {
                    key: clean_data (value)
                    for key, value in data.items ()
                    if (value is not None or debug_null_values)
                    and (value != [] or debug_empty_arrays)
                    and (value != "" or debug_empty_strings)
                }
            else:
                return data

        cleaned_item = clean_data (source)
        sanitised_fields.append (cleaned_item)

    return highest_midi_chlorian_count, sanitised_fields

def get_similar_things_legacy (options):
    inbound_string = options[KINBOUND_STRING]
    what = options[KWHAT]
    count_limit = options[KCOUNT_LIMIT]
    knn_threshold = options[KKNN_THRESHOLD]

    similar_things_url = F'{dsc.get_api_url ()}/similar-things'
    search_payload = {
        'what': what,
        'k': count_limit,
        'text': inbound_string,
        'dimensions': 1024
    }

    similar_things = dsc.make_post_request (similar_things_url, search_payload, raise_on_error=False)

    if ('things' not in similar_things):
        print (F'--inbound-string: {inbound_string} is not similar to any --what {what}')
        sys.exit (0)

    things = similar_things['things']

    stripped_similars = pseq (things) \
        .filter (lambda x: 'code' in x.keys ()) \
        .filter (lambda x: 'name' in x.keys ()) \
        .filter (lambda x: 'description' in x.keys ()) \
        .map (lambda x: {
            'Code': x['code'],
            'Name': x['name'],
            'Description': x['description']
        }) \
        .to_list ()

    # print ('Writing similars to out-knn.json...')
    # dsc.write_json ('out-knn.json', stripped_similars)

    # print ('Done.')
    print (json.dumps (stripped_similars))

def get_similar_things_new (options):
    envars = dsc.load_json ('secrets.json')['ENVARS']
    opensearch_client = OpenSearch (
        hosts            = [ { 'host': envars['OPENSEARCH_ENDPOINT_URL'], 'port': 443 } ],
        use_ssl          = True,
        verify_certs     = True,
        connection_class = RequestsHttpConnection,
    )

    sanitised = sanitise (options[KINBOUND_STRING])
    vectorised = text_to_bedrock (sanitised, envars['BEDROCK_LAMBDA_ARN']).get ('vector', [])

    k = options[KCOUNT_LIMIT]
    knn_os_query = {
        "size": k,
        "query": {
            "knn": {
                "description_vector": {
                    "vector": vectorised,
                    "k": k,
                    "filter": {
                        "bool": {
                            "must": [
                                { "match": { "status.label": "Approved" } },
                                { "match": { "status.value": "Active" } }
                            ]
                        }
                    }
                }
            }
        },
        "sort": [
            { "_score": { "order": "desc" } },
            { "version_approved.keyword": "desc" }
        ],
        "collapse": {
            "field": "code.keyword",
            "inner_hits": {
                "name": "latest",
                "size": 1,
                "sort": [
                    { "version_approved.keyword": "desc" }
                ]
            }
        }
    }

    knn_os_response_description = opensearch_client.search (index=F'{options[KWHAT]}_knn', body=json.dumps (knn_os_query))
    max_midi_chlorians, knn_description = transform_and_clean_data_knn (knn_os_response_description, options)

    stripped_similars = pseq (knn_description) \
        .filter (lambda x: 'code' in x.keys ()) \
        .filter (lambda x: 'name' in x.keys ()) \
        .filter (lambda x: 'description' in x.keys ()) \
        .filter (lambda x: 'M' in x.keys ()) \
        .map (lambda x: {
            'Name': x['name'],
            'Code': x['code'],
            'M': x['M'],
            'Description': sanitise (x['description'])
        }) \
        .to_list ()

    print (json.dumps (stripped_similars))

def get_similar_things (options):

    if (options[KUSE_LEGACY]):
        get_similar_things_legacy (options)

    else: # New and improved :)
        get_similar_things_new (options)

def main ():
    options = parse_argv ()

    dsc.set_environment (options[KENVIRONMENT])
    # print (F'ENVIRONMENT: {dsc.get_wenvironment ()}')
    dsc.set_access_token ()

    get_similar_things (options)

if (__name__ == '__main__'):
    main ()
    sys.exit (0)
