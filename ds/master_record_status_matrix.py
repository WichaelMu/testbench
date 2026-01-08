
EMPTY_SET = { '' }

default_matrix = {
    # Status        : Incompatible.
    'offered'       : { '' },
    'draft'         : { '' },
    'scheduled'     : { '' },
    'teachout'      : { '' },
    'onhold'        : { '' },
    'disestablished': { '' }
}

status_value_filter_mapping = {
    'offered'       : 'active',
    'draft'         : 'draft',
    'scheduled'     : 'active', # Unused. Default to active.
    'teachout'      : 'active',
    'onhold'        : 'active',
    'disestablished': 'active'
}

matrix = default_matrix.copy ()

def evaluate (in_requested_statuses):
    uniq = set (in_requested_statuses)
    response_builder = {}

    for u in uniq:
        if (u not in matrix or matrix[u] == EMPTY_SET):
            continue

        intersect = uniq & matrix[u]
        if (len (intersect) > 0):
            # dbg.dspec (F'{u} ^ {intersect}')
            response_builder[u] = [ x for x in intersect ]

    # dbg.dcrit (response_builder)
    return response_builder

def solve (apicom, event, default_status = 'offered', valid_statuses = { 'offered', 'draft', 'scheduled', 'teachout', 'onhold', 'disestablished' }):
    requested_master_record_status = apicom.get_param (event, 'status', default = default_status)

    if (requested_master_record_status == ''):
        return {}

    should_query = {}

    split = list (map (lambda x: x.strip (),
                map (str, requested_master_record_status.split (','))
            ))

    matrix_evaluation = evaluate (split)
    if (len (matrix_evaluation) > 0):
        return bad_request (matrix_evaluation)

    from functools import reduce
    fstringed = list (
        reduce (lambda x, y: x + y, map (lambda x: [
                {
                    'bool': {
                        'filter': [
                            { 'match': { 'master_record_status.value': x } },
                            { 'match': { 'status.value': status_value_filter_mapping[x] } }
                        ]
                    }
                }
            ],
            filter (lambda x: x in valid_statuses, split)
        ), [])
    )

    should_query = {
        'should': fstringed,
        'minimum_should_match': 1
    }

    return should_query

def override_matrix (**matrix_overrides):
    global matrix
    matrix |= matrix_overrides

    return matrix

def bad_request (matrix_evaluation, status_code = '400'):
    import json
    return {
        'statusCode': status_code,
        'headers': { 'Content-Type': 'application/json' },
        'body': json.dumps ({
            'message': 'Some requested ?status= are incompatible with each other!',
            'reason': matrix_evaluation
        })
    }
