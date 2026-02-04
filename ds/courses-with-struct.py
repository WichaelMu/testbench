import ast
from functools import reduce
from typing import Any, Iterable, List, Optional, Callable

from functional import seq, pseq

import dscore as dsc
import debug_utils as dbg

PROGRAM_NAME = 'courses-with-struct'

def get_recursively_relationship (relationship, current):
    result = []


    result += seq (relationship) \
        .map (lambda x: {
            **current,
            'code':     x['child_record']['code'],
            'name':     x['child_record']['name'],
            'nickname': x['child_record']['nickname']
        }) \
        .to_list ()

    result += seq (relationship) \
        .filter (lambda x: 'curriculum_structure_relationship' in x.keys ()) \
        .map (lambda x: get_recursively_relationship (x['curriculum_structure_relationship'])) \
        .to_list ()

    result += seq (relationship) \
        .filter (lambda x: 'curriculum_structure_container' in x.keys ()) \
        .map (lambda x: get_recursively_container (x['curriculum_structure_container'], current)) \
        .to_list ()

    return result

def get_recursively_container (container, current):
    return get_what_we_need (container, current)

def get_what_we_need (curriculum_structure_container, current):
    csr_mapped = []

    for csc in curriculum_structure_container:
        title = csc.get ('title', '')
        curriculum_structure_relationship = csc.get ('curriculum_structure_relationship', [])
        curriculum_structure_container    = csc.get ('curriculum_structure_container', [])

        grr = get_recursively_relationship (curriculum_structure_relationship, current)
        grc = get_recursively_container (curriculum_structure_container, current)

        csr_mapped += seq (grr + grc) \
            .filter (lambda x: 'code' in x.keys ()) \
            .filter (lambda x: 'name' in x.keys ()) \
            .filter (lambda x: 'nickname' in x.keys ()) \
            .map (lambda x: {
                'current':        current,
                'structure-type': title,
                'code':           x['code'],
                'name':           x['name'],
                'nickname':       x['nickname']
            }) \
            .to_list ()

    return csr_mapped

def main ():
    dsc.set_environment ('PROD')
    dsc.set_access_token ()

    response = dsc.get_all_academic_items ('courses')

    courses_with_struct = None

    if (dsc.has_generated (PROGRAM_NAME, 'courses-with-struct') and False):
        courses_with_struct = dsc.load_generated (PROGRAM_NAME, 'courses-with-struct')
        dbg.dinfo (F'Loaded from {dsc.get_generated_path (PROGRAM_NAME, "courses-with-struct")}')

    else:
        courses_with_struct = pseq (response) \
            .filter (lambda x: 'nested_curriculum_structure' in x) \
            .filter (lambda x: 'curriculum_structure_container' in x['nested_curriculum_structure'].keys ()) \
            .map (lambda x: seq (get_what_we_need (x['nested_curriculum_structure']['curriculum_structure_container'], {
                    'code': x['code'],
                    'name': x['name'],
                    'nickname': x['nickname']
                })) \
                .map (lambda k:
                {
                    'course-code':     k['current']['code'],
                    'course-name':     k['current']['name'],
                    'course-nickname': k['current']['nickname'],

                    'structure-category': k['structure-type'],

                    'structure-code':     k['code'],
                    'structure-name':     k['name'],
                    'structure-nickname': k['nickname']
                }) \
                .to_list () \
            ) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        fq_path = dsc.save_generated (PROGRAM_NAME, 'courses-with-struct', courses_with_struct)

        dbg.dinfo (F'Saved. {fq_path}')

    output_path = dsc.get_generated_path (PROGRAM_NAME, 'viridescent', extension = '.xlsx')
    dsc.to_xlsx (
        courses_with_struct,
        [ 'course-code', 'course-name', 'course-nickname', 'structure-category', 'structure-code', 'structure-name', 'structure-nickname' ],
        output_path
    )

    dbg.dinfo (F'Done. {output_path}')

if (__name__ == '__main__'):
    main ()
