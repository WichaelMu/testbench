import sys
import os
import pandas as pd
from functional import pseq, seq
import multiprocessing as mp

import dscore as dsc

PROGRAM_NAME = os.path.basename (__file__).split ('.')[0]
KENVIRONMENT = 'environment'
KUSE_GENERATED = 'use-generated'

def parse_argv () -> dict[str, str]:
    argv = sys.argv[1:]
    argc = len (argv)

    # print (F'argc, argv: {argc}, {argv}')

    def process_option (option, iterator):
        match option:
            case '--environment':
                iterator += 1

                return { KENVIRONMENT: argv[iterator] }, iterator

            case '--no-generated':
                print ('--no-generated is not yet supported.')
                return { KUSE_GENERATED: False }, iterator

            case '?' | '--help' | 'help' | '__HELP__':
                print ('Usage:')
                return {}, iterator

            case _:
                return {}, iterator

    options = {
        KENVIRONMENT: 'NONPROD',
        KUSE_GENERATED: True
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
            .map (lambda x: seq (dsc.execute_parallel_requests (F'{full_url}?page=', x, total_pages, extract_key, False)) \
                .map (lambda x: affix | x) \
                .to_list ()
            ) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        return responses + affixed_initial_request

    return affixed_initial_request

def get_course_subjects (base_url, course_code):
    if (dsc.has_generated (PROGRAM_NAME, F'course-subjects-{course_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'course-subjects-{course_code}')

    full_url = F'{base_url}/courses/{course_code}/subjects'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'subjects', { 'relative-to': course_code })

    dsc.save_generated (PROGRAM_NAME, F'course-subjects-{course_code}', result)
    return result

def get_course_majors (base_url, course_code):
    if (dsc.has_generated (PROGRAM_NAME, F'course-majors-{course_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'course-majors-{course_code}')

    full_url = F'{base_url}/courses/{course_code}/majors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'majors', { 'relative-to': course_code })

    dsc.save_generated (PROGRAM_NAME, F'course-majors-{course_code}', result)
    return result

def get_course_submajors (base_url, course_code):
    if (dsc.has_generated (PROGRAM_NAME, F'course-submajors-{course_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'course-submajors-{course_code}')

    full_url = F'{base_url}/courses/{course_code}/submajors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'submajors', { 'relative-to': course_code })

    dsc.save_generated (PROGRAM_NAME, F'course-submajors-{course_code}', result)
    return result

def get_course_substructures (base_url, course_code):
    if (dsc.has_generated (PROGRAM_NAME, F'course-substructures-{course_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'course-substructures-{course_code}')

    full_url = F'{base_url}/courses/{course_code}/substructures'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'substructures', { 'relative-to': course_code })

    dsc.save_generated (PROGRAM_NAME, F'course-substructures-{course_code}', result)
    return result

def get_subject_majors (base_url, subject_code):
    if (dsc.has_generated (PROGRAM_NAME, F'subject-majors-{subject_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'subject-majors-{subject_code}')

    full_url = F'{base_url}/subjects/{subject_code}/majors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'majors', { 'relative-to': subject_code })

    dsc.save_generated (PROGRAM_NAME, F'subject-majors-{subject_code}', result)
    return result

def get_subject_courses (base_url, subject_code):
    if (dsc.has_generated (PROGRAM_NAME, F'subject-courses-{subject_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'subject-courses-{subject_code}')

    full_url = F'{base_url}/subjects/{subject_code}/courses'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'courses', { 'relative-to': subject_code })

    dsc.save_generated (PROGRAM_NAME, F'subject-courses-{subject_code}', result)
    return result

def get_major_courses (base_url, major_code):
    if (dsc.has_generated (PROGRAM_NAME, F'major-courses-{major_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'major-courses-{major_code}')

    full_url = F'{base_url}/majors/{major_code}/courses'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'courses', { 'relative-to': major_code })

    dsc.save_generated (PROGRAM_NAME, F'major-courses-{major_code}', result)
    return result

def get_major_subjects (base_url, major_code):
    if (dsc.has_generated (PROGRAM_NAME, F'major-subjects-{major_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'major-subjects-{major_code}')

    full_url = F'{base_url}/majors/{major_code}/subjects'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'subjects', { 'relative-to': major_code })

    dsc.save_generated (PROGRAM_NAME, F'major-subjects-{major_code}', result)
    return result

def get_major_submajors (base_url, major_code):
    if (dsc.has_generated (PROGRAM_NAME, F'major-submajors-{major_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'major-submajors-{major_code}')

    full_url = F'{base_url}/majors/{major_code}/submajors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'submajors', { 'relative-to': major_code })

    dsc.save_generated (PROGRAM_NAME, F'major-submajors-{major_code}', result)
    return result

def get_major_streams (base_url, major_code):
    if (dsc.has_generated (PROGRAM_NAME, F'major-streams-{major_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'major-streams-{major_code}')

    full_url = F'{base_url}/majors/{major_code}/streams'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'streams', { 'relative-to': major_code })

    dsc.save_generated (PROGRAM_NAME, F'major-streams-{major_code}', result)
    return result

def get_submajor_subjects (base_url, submajor_code):
    if (dsc.has_generated (PROGRAM_NAME, F'submajor-subjects-{submajor_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'submajor-subjects-{submajor_code}')

    full_url = F'{base_url}/submajors/{submajor_code}/subjects'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'subjects', { 'relative-to': submajor_code })

    dsc.save_generated (PROGRAM_NAME, F'submajor-subjects-{submajor_code}', result)
    return result

def get_submajor_courses (base_url, submajor_code):
    if (dsc.has_generated (PROGRAM_NAME, F'submajor-courses-{submajor_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'submajor-courses-{submajor_code}')

    full_url = F'{base_url}/submajors/{submajor_code}/courses'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'courses', { 'relative-to': submajor_code })

    dsc.save_generated (PROGRAM_NAME, F'submajor-courses-{submajor_code}', result)
    return result

def get_submajor_streams (base_url, submajor_code):
    if (dsc.has_generated (PROGRAM_NAME, F'submajor-streams-{submajor_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'submajor-streams-{submajor_code}')

    full_url = F'{base_url}/submajors/{submajor_code}/streams'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'streams', { 'relative-to': submajor_code })

    dsc.save_generated (PROGRAM_NAME, F'submajor-streams-{submajor_code}', result)
    return result

def get_submajor_majors (base_url, submajor_code):
    if (dsc.has_generated (PROGRAM_NAME, F'submajor-majors-{submajor_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'submajor-majors-{submajor_code}')

    full_url = F'{base_url}/submajors/{submajor_code}/majors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'majors', { 'relative-to': submajor_code })

    dsc.save_generated (PROGRAM_NAME, F'submajor-majors-{submajor_code}', result)
    return result

def get_substructure_streams (base_url, substructure_code):
    if (dsc.has_generated (PROGRAM_NAME, F'substructure-streams-{substructure_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'substructure-streams-{substructure_code}')

    full_url = F'{base_url}/substructures/{substructure_code}/streams'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'streams', { 'relative-to': substructure_code })

    dsc.save_generated (PROGRAM_NAME, F'substructure-streams-{substructure_code}', result)
    return result

def get_substructure_submajors (base_url, substructure_code):
    if (dsc.has_generated (PROGRAM_NAME, F'substructure-submajors-{substructure_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'substructure-submajors-{substructure_code}')

    full_url = F'{base_url}/substructures/{substructure_code}/submajors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'submajors', { 'relative-to': substructure_code })

    dsc.save_generated (PROGRAM_NAME, F'substructure-submajors-{substructure_code}', result)
    return result

def get_substructure_majors (base_url, substructure_code):
    if (dsc.has_generated (PROGRAM_NAME, F'substructure-majors-{substructure_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'substructure-majors-{substructure_code}')

    full_url = F'{base_url}/substructures/{substructure_code}/majors'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'majors', { 'relative-to': substructure_code })

    dsc.save_generated (PROGRAM_NAME, F'substructure-majors-{substructure_code}', result)
    return result

def get_substructure_subjects (base_url, substructure_code):
    if (dsc.has_generated (PROGRAM_NAME, F'substructure-subjects-{substructure_code}')):
        return dsc.load_generated (PROGRAM_NAME, F'substructure-subjects-{substructure_code}')

    full_url = F'{base_url}/substructures/{substructure_code}/subjects'
    print (F'Hitting: {full_url}')
    result = make_request (full_url, 'subjects', { 'relative-to': substructure_code })

    dsc.save_generated (PROGRAM_NAME, F'substructure-subjects-{substructure_code}', result)
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

    if (not os.path.isdir (dsc.GENERATED_PARENT)):
        os.mkdir (dsc.GENERATED_PARENT)
    if (not os.path.isdir (os.path.join (dsc.GENERATED_PARENT, PROGRAM_NAME))):
        os.mkdir (os.path.join (dsc.GENERATED_PARENT, PROGRAM_NAME))

    course_codes = read_xlsx_column ('CommunicationCourses2025List.xlsx', 1, 0, None, True)
    course_codes = pseq (course_codes) \
        .filter (lambda x: is_probably_a_course_code (x)) \
        .to_list ()

    course_subjects = pseq (course_codes) \
        .map (lambda x: get_course_subjects (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    course_majors = pseq (course_codes) \
        .map (lambda x: get_course_majors (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    course_submajors = pseq (course_codes) \
        .map (lambda x: get_course_submajors (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    course_substructures = pseq (course_codes) \
        .map (lambda x: get_course_substructures (base_url, x)) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    subject_majors = pseq (course_subjects) \
        .map (lambda x: get_subject_majors (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    subject_courses = pseq (course_subjects) \
        .map (lambda x: get_subject_courses (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    major_courses = pseq (course_majors) \
        .map (lambda x: get_major_courses (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    major_subjects = pseq (course_majors) \
        .map (lambda x: get_major_subjects (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    major_submajors = pseq (course_majors) \
        .map (lambda x: get_major_submajors (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    major_streams = pseq (course_majors) \
        .map (lambda x: get_major_streams (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    submajor_subjects = pseq (course_submajors) \
        .map (lambda x: get_submajor_subjects (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    submajor_courses = pseq (course_submajors) \
        .map (lambda x: get_submajor_courses (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    submajor_streams = pseq (course_submajors) \
        .map (lambda x: get_submajor_streams (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    submajor_majors = pseq (course_submajors) \
        .map (lambda x: get_submajor_majors (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    substructure_streams = pseq (course_substructures) \
        .map (lambda x: get_substructure_streams (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    substructure_submajors = pseq (course_substructures) \
        .map (lambda x: get_substructure_submajors (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    substructure_majors = pseq (course_substructures) \
        .map (lambda x: get_substructure_majors (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    substructure_subjects = pseq (course_substructures) \
        .map (lambda x: get_substructure_subjects (base_url, x['code'])) \
        .reduce (lambda x, y: x + y, []) \
        .to_list ()

    result = course_subjects + course_majors + course_submajors + course_substructures + subject_majors + subject_courses + major_courses + major_subjects + major_submajors + major_streams + submajor_subjects + submajor_courses + submajor_streams + submajor_majors + substructure_streams + substructure_submajors + substructure_majors + substructure_subjects

    to_xlsx (result, [ 'relative-to', 'code', 'name', 'nickname' ], F'absolution-{PROGRAM_NAME}-{dsc.get_wenvironment ().lower ()}.xlsx')
    print ('Done')

if (__name__ == '__main__'):
    main ()
    sys.exit (0)
