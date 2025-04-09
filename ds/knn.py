import os
import sys
import math

from functional import pseq, seq

import dscore as dsc


KENVIRONMENT = 'environment'
KINBOUND_STRING = 'inbound-string'
KCOUNT_LIMIT = 'count-limit'
KKNN_THRESHOLD = 'knn-threshold'
KWHAT = 'what'
KSEARCH_VECTOR = 'search-vector'


def parse_argv ():
    argv = os.sys.argv[1:]
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
                    return { KCOUNT_LIMIT: sanitised_argv }

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
        KKNN_THRESHOLD: float (.75)
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

    print (options)
    return options

def get_similar_things (options):
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

    print ('Writing similars to knn-out.json...')
    dsc.write_json ('knn-out.json', stripped_similars)

    print ('Done.')

def main ():
    options = parse_argv ()

    dsc.set_environment (options[KENVIRONMENT])
    print (F'ENVIRONMENT: {dsc.get_wenvironment ()}')
    dsc.set_access_token ()

    get_similar_things (options)

if (__name__ == '__main__'):
    main ()
    sys.exit (0)
