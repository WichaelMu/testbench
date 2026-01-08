import master_record_status_matrix as matrix

event = {
    'queryStringParameters': {
        'status': 'draft,offered'
    }
}

import api_common as apicom

result = matrix.solve (apicom, event)

print (result)
