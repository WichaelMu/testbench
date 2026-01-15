import ast
from typing import Any, Iterable, List, Optional, Callable

from functional import seq, pseq

import dscore as dsc
import debug_utils as dbg

PROGRAM_NAME = 'courses-with-cbk'

def main ():
    dsc.set_environment ('NONPROD')
    dsc.set_access_token ()

    response = None
    if (not dsc.has_generated (PROGRAM_NAME, 'all-courses')):
        target_url = F'{dsc.get_api_url ()}/courses?page='
        response = dsc.request_in_parallel (target_url, 'courses', PROGRAM_NAME, 'all-courses')

    else:
        response = dsc.load_generated (PROGRAM_NAME, 'all-courses')
        
    distilled_children = None

    if (dsc.has_generated (PROGRAM_NAME, 'distilled_children')):
        distilled_children = dsc.load_generated (PROGRAM_NAME, 'distilled_children')
        dbg.dinfo (F'Loaded from {dsc.get_generated_path (PROGRAM_NAME, "distilled_children")}')

    else:
        distilled_children = pseq (response) \
            .filter (lambda x: 'nested_curriculum_structure' in x.keys ()) \
            .map (lambda x:
            {
                'course-code': x['code'],
                'with-cbk': seq (curriculum_distil_children (x['nested_curriculum_structure'])) \
                    .filter (lambda k: 'description' in k.keys ()) \
                    .filter (lambda k: k['description'] is not None and 'CBK' in k['description']) \
                    .map (lambda k: k['description']).to_list ()
            }) \
            .filter (lambda x: len (x['with-cbk']) > 0) \
            .to_list ()

        fq_path = dsc.save_generated (PROGRAM_NAME, 'distilled_children', distilled_children)

        dbg.dinfo (F'Done. {fq_path}')

    output_path = dsc.get_generated_path (PROGRAM_NAME, 'absolution', extension = '.xlsx')
    dsc.to_xlsx (distilled_children, [ 'course-code', 'with-cbk' ], output_path)

#-------------------------------------------------------------------------------
# Lib

def curriculum_distil_children (nested_curriculum_structure, *, unwrap: bool = True):
    """
    Traverse the wrapped structure and return a list of dicts:
      {
        "order": <container.order or first relationship.order>,
        "credit_points": <container.credit_points>,
        "vertical_grouping": <container.vertical_grouping or {}>,
        "children": [ <child_record entries for this container> ]
      }

    Works with AttrWrapper-wrapped values and plain dicts.
    Set unwrap = True to convert wrapped values to builtin Python types
    using ast.literal_eval where needed.
    """

    # attribute-or-dict getter
    get: Callable[[Any, str], Optional[Any]] = lambda obj, name: (
        getattr (obj, name) if hasattr (obj, name) else (obj.get (name) if isinstance (obj, dict) else None)
    )

    def to_builtin (value):
        if not unwrap:
            return value

        match value:
            case list () as lst:

                return [ to_builtin (x) for x in lst ]

            case _ if type (value).__name__ == 'AttrWrapper':
                # Try to unwrap via its textual representation
                try:
                    # __repr__ on AttrWrapper returns the underlying dict's repr
                    parsed = ast.literal_eval (repr (value))

                    return to_builtin (parsed)
                except Exception:
                    # If parsing fails, return as-is
                    return value
            case _:
                return value

    def distil_vertical_grouping (container):
        r = get (container, 'vertical_grouping') or {}

        match r:
            case False:
                return r

            case _:
                return {
                    'label': r['label'],
                    'value': r['value'],
                    'sys_id': r['sys_id'],
                }

    def distil_offspring (offspring):
        r = get (offspring, 'child_record')

        return {
            'class_name': r['class_name'],
            'code': r['code'],
            'credit_points': r['credit_points'],
            'implementation_year': r['implementation_year'],
            'name': r['name'],
            'nickname': r['nickname'],
            'sys_id': r['sys_id'],
            'status': {
                'active': r['status']['active'],
            },
        }
        
    def child_records_of (container):
        rels = get (container, 'curriculum_structure_relationship')

        match rels:
            case list () as lst:
                return [ distil_offspring (r) for r in lst if get (r, 'child_record') is not None ]

            case _:
                return []

    def container_order (container):
        # Prefer the container's own order
        cont_ord = get (container, 'order')

        if cont_ord is not None:
            return cont_ord

        # Fallback to the first non-None relationship order
        rels = get (container, 'curriculum_structure_relationship')

        match rels:
            case list () as lst:
                for r in lst:
                    o = get (r, 'order')

                    if o is not None:
                        return o
                return None

            case _:
                return None

    def iter_containers (node, seen):
        containers = get (node, 'curriculum_structure_container')

        match containers:
            case list () as lst:
                for c in lst:
                    oid = id (c)

                    if oid in seen:
                        continue

                    new_seen = seen | {oid}

                    yield c

                    # Recurse into subcontainers
                    yield from iter_containers (c, new_seen)

            case _:
                return

    def make_group (container):
        children = child_records_of (container)

        if not children:
            return None

        credit_points = get (container, 'credit_points')
        description = get (container, 'description')
        title = get (container, 'title')
        vertical_grouping = distil_vertical_grouping (container)
        ord_val = container_order (container)

        return {
            'order': to_builtin (ord_val),
            'title': to_builtin (title),
            'description': to_builtin (description),
            'credit_points': to_builtin (credit_points),
            'vertical_grouping': to_builtin (vertical_grouping),
            'children': [to_builtin (cr) for cr in children],
        }

    groups = (make_group (c) for c in iter_containers (nested_curriculum_structure, set ()))

    return [ g for g in groups if g is not None ]

if (__name__ == '__main__'):
    main ()
