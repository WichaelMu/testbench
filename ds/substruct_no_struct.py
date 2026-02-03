import ast
from functools import reduce
from typing import Any, Iterable, List, Optional, Callable

from functional import seq, pseq

import dscore as dsc
import debug_utils as dbg

PROGRAM_NAME = 'courses-with-no-struct'

def find_no_structure (nested_curriculum_structure):
    if ('curriculum_structure_container' not in nested_curriculum_structure):
        return nested_curriculum_structure
    return {}

def main ():
    dsc.set_environment ('PROD')
    dsc.set_access_token ()

    response = None
    if (not dsc.has_generated (PROGRAM_NAME, 'all-substructures')):
        target_url = F'{dsc.get_api_url ()}/substructures?page='
        response = dsc.request_in_parallel (target_url, 'substructures', PROGRAM_NAME, 'all-substructures')

    else:
        response = dsc.load_generated (PROGRAM_NAME, 'all-substructures')
        
    found_substructures = None

    if (dsc.has_generated (PROGRAM_NAME, 'found_substructures') and False):
        found_substructures = dsc.load_generated (PROGRAM_NAME, 'found_substructures')
        dbg.dinfo (F'Loaded from {dsc.get_generated_path (PROGRAM_NAME, "found_substructures")}')

    else:
        found_substructures = pseq (response) \
            .filter (lambda x: 'nested_curriculum_structure' not in x.keys ()) \
            .map (lambda x:
            {
                'substructure-code': x['code'],
                'substructure-nickname': x['nickname']
            }) \
            .to_list ()

        fq_path = dsc.save_generated (PROGRAM_NAME, 'found_substructures', found_substructures)

        dbg.dinfo (F'Saved. {fq_path}')

    output_path = dsc.get_generated_path (PROGRAM_NAME, 'viridescent', extension = '.xlsx')
    dsc.to_xlsx (found_substructures, [ 'substructure-code', 'substructure-nickname' ], output_path)

    dbg.dinfo (F'Done. {output_path}')

if (__name__ == '__main__'):
    main ()
