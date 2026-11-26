import dscore as dsc
import py_log_event_module as lem


BATCH_SIZE = 2

def sybil_shuffle (batch_payload, external_id_field, sf_context_object):
    batches = []
    next_batch_by_external_id = {}

    for record in batch_payload:
        external_id = ( record['object'], str (record['payload'][external_id_field]) )

        batch_index = next_batch_by_external_id.get (external_id, 0)

        while (batch_index < len (batches) and len (batches[batch_index]) >= BATCH_SIZE):
            batch_index += 1

        if (batch_index == len (batches)):
            batches.append ([])

        batches[batch_index].append (record)

        next_batch_by_external_id[external_id] = batch_index + 1

    return batches

def create_payload (obj, id_field, id_value):
    return {
        'object': obj,
        'external_id_field': id_field,
        'payload': { id_field: id_value }
    }

primary_object = 'account'
primary_id_field = 'UTS_Identifier__c'

a = create_payload (primary_object, primary_id_field, 'a')
b = create_payload (primary_object, primary_id_field, 'b')
a2 = create_payload (primary_object, primary_id_field, 'a')
c = create_payload (primary_object, primary_id_field, 'c')
c2 = create_payload (primary_object, primary_id_field, 'c')
b2 = create_payload (primary_object, primary_id_field, 'b')

r = [ a, b, a2, c, c2, b2 ]
result = sybil_shuffle (r, primary_id_field, {})
print (result)
