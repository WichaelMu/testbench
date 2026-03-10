
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
    'offered'       : 'asdf',
    'draft'         : 'draft',
    'scheduled'     : 'active', # Unused. Default to active.
    'teachout'      : 'active',
    'onhold'        : 'active',
    'disestablished': 'active'
}

matrix = default_matrix.copy ()

def evaluate_master_record_status_compatibility (in_requested_statuses):
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

def solve (apicom, event, default_status = 'offered', valid_statuses = { 'offered', 'draft', 'scheduled', 'teachout', 'onhold', 'disestablished' }, valid_revisions = { 'active', 'draft', 'archived' }, default_revision_status = 'active', factor_status = True, factor_mrs = True):
    requested_master_record_status = apicom.get_param (event, 'status', default = default_status)
    requested_revision_status      = apicom.get_param (event, 'revision_status', default = default_revision_status)

    # Let the matrix continue without specifying ?status=master_record_status or ?revision_status=revision_status
    if (requested_master_record_status == ''):
        requested_master_record_status = default_status
    if (requested_revision_status == ''):
        requested_revision_status = default_revision_status

    should_query = {}

    master_record_status_split = list (map (lambda x: x.strip (),
        map (str, requested_master_record_status.split (','))
    ))

    revision_status_split = list (map (lambda x: x.strip (),
        map (str, requested_revision_status.split (','))
    ))

    matrix_evaluation = evaluate_master_record_status_compatibility (master_record_status_split)
    if (len (matrix_evaluation) > 0):
        return bad_request (matrix_evaluation)

    status_query = list (
        map (lambda m: { 'match': { 'master_record_status.value': m } },
             filter (lambda m: m in valid_statuses, master_record_status_split)
        )
    )

    revision_query = list (
        map (lambda r: { 'match': { 'status.value': r } },
             filter (lambda r: r in valid_revisions, revision_status_split)
        )
    )

    import itertools
    cartesian_product = itertools.product (status_query, revision_query)

    fstringed = list (
        map (lambda f: {
            'bool': {
                'filter': f
            }
        }, cartesian_product)
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
