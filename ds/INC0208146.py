import sys
import pandas as pd
from functional import pseq, seq
import multiprocessing as mp

import dscore as dsc

KENVIRONMENT = 'environment'

def parse_argv () -> dict[str, str]:
    argv = sys.argv[1:]
    argc = len (argv)

    # print (F'argc, argv: {argc}, {argv}')

    def process_option (option, iterator):
        match option:
            case '--environment':
                iterator += 1

                return { KENVIRONMENT: argv[iterator] }, iterator

            case '?' | '--help' | 'help' | '__HELP__':
                print ('Usage:')
                return {}, iterator

            case _:
                return {}, iterator

    options = {
        KENVIRONMENT: 'NONPROD'
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

def read_xlsx_column (path: str, col_number: int = 1, sheet = 0, header = None, drop_blank = False):
    if (col_number < 1):
        raise ValueError ("col_number must be 1 or greater")

    s = pd.read_excel (path, sheet_name = sheet, usecols = [ col_number - 1 ], header = header).iloc[:, 0]

    if drop_blank:
        s = s.replace ('', pd.NA).dropna()

    return s.tolist ()

def is_probably_a_course_code (course_code):
    return isinstance (course_code, str) and len (course_code) > 5 and course_code[0] == 'C'

def make_request (full_url, extract_key, affix = {}):
    initial_request = dsc.make_get_request (full_url)

    affixed_initial_request = seq (initial_request[extract_key]) \
        .map (lambda x: affix | x) \
        .to_list ()

    if ('_meta' in initial_request.keys ()):
        current_page = initial_request['_meta']['page']
        total_pages = initial_request['_meta']['total']

        page_range_begin = 2
        page_list = list (range (page_range_begin, total_pages + 1))
        nproc = mp.cpu_count ()
        chunks = seq (page_list).grouped (len (page_list) // nproc + (len (page_list) % nproc > 0)).to_list ()

        responses = seq (chunks) \
            .map (lambda x: affix | dsc.execute_parallel_requests (F'{full_url}?page=', x, total_pages, extract_key, True)) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        return responses + affixed_initial_request

    return initial_request[extract_key]

def get_course_subjects (base_url, course_code):
    full_url = F'{base_url}/courses/{course_code}/subjects'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'subjects', { 'relative-to': course_code })
    return result

def get_course_majors (base_url, course_code):
    full_url = F'{base_url}/courses/{course_code}/majors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'majors', { 'relative-to': course_code })
    return result

def get_course_submajors (base_url, course_code):
    full_url = F'{base_url}/courses/{course_code}/submajors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'submajors', { 'relative-to': course_code })
    return result

def get_course_substructures (base_url, course_code):
    full_url = F'{base_url}/courses/{course_code}/substructures'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'substructures', { 'relative-to': course_code })
    return result

def to_xlsx (in_array, columns_to_keep, fq_output_path, sheet_name='Sheet1'):
    df = pd.DataFrame.from_records (in_array) if in_array else pd.DataFrame ()
    df = df.reindex (columns = columns_to_keep)
    df.to_excel (fq_output_path, index=False, sheet_name = sheet_name)

def main ():
    options = parse_argv ()

    dsc.set_environment (options[KENVIRONMENT])
    dsc.set_access_token ()
    base_url = dsc.get_api_url ()

    course_codes = read_xlsx_column ('CommunicationCourses2025List.xlsx', 1, 0, None, True)
    course_codes = pseq (course_codes) \
        .filter (lambda x: is_probably_a_course_code (x)) \
        .to_list ()

    subjects = pseq (course_codes) \
        .map (lambda x: get_course_subjects (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    majors = pseq (course_codes) \
        .map (lambda x: get_course_majors (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    submajors = pseq (course_codes) \
        .map (lambda x: get_course_submajors (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    substructures = pseq (course_codes) \
        .map (lambda x: get_course_substructures (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    result = subjects + majors + submajors + substructures

    to_xlsx (result, [ 'relative-to', 'code', 'name', 'nickname' ], F'absolution-{dsc.get_wenvironment ().lower ()}.xlsx')
    print ('Done')

if (__name__ == '__main__'):
    main ()
    sys.exit (0)
