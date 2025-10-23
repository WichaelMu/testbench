import json

import debug_utils as dbg

EMPTY_SET = { '' }

matrix = {
    # Status        : Incompatible.
    'offered'       : { 'draft' },
    'draft'         : { 'scheduled', 'offered', 'teachout' },
    'scheduled'     : { '' },
    'teachout'      : { '' },
    'onhold'        : { '' },
    'disestablished': { '' }
}

def solve (in_requested_statuses):
    uniq = set (in_requested_statuses)
    response_builder = {}

    for u in uniq:
        if (u not in matrix or matrix[u] == EMPTY_SET):
            continue

        intersect = uniq & matrix[u]
        if (len (intersect) > 0):
            dbg.dspec (F'{u} ^ {intersect}')
            response_builder[u] = [ x for x in intersect ]

    dbg.dcrit (response_builder)

def get_params ():
    master_record_status = 'offered'
    valid_master_record_statuses = { 'offered', 'draft', 'scheduled', 'teachout', 'onhold', 'disestablished' }
    # requested_master_record_status = apicom.get_param (event, 'status', default = master_record_status)
    requested_master_record_status = 'offered,draft,scheduled'

    r = list (map (lambda x: x.strip (),
            map (str, requested_master_record_status.split (','))
        ))

    dbg.dinfo (r)
    solve (r)

    fstringed = list (
        map (lambda x: { 'match': { 'master_record_status.value': x } },
            filter (lambda x: x in valid_master_record_statuses, r)
        )
    )

    dbg.dinfo (json.dumps (fstringed, indent=4))
    return fstringed

if (__name__ == '__main__'):
    dbg.RUNNING_FROM_LAMBDA = False
    get_params ()
