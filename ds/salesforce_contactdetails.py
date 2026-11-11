import os
import sys
import json
import base64

import dscore as dsc

sys.path.append (F'{os.environ['DITLOC']}/tf-data-plane-copt/contrib/src/lambda/student_cohort_salesforce_contactdetails_connector/')
import student_cohorts_salesforce_contactdetails_connector as sconn

def flatten_msk_incoming_event (event):
    records = event['records']
    decoded = []

    for topic_partition, partition_records in records.items ():
        for record in partition_records:
            if (not isinstance (record, dict)):
                continue
            if ('topic' not in record or 'value' not in record or 'offset' not in record):
                continue

            decoded.append ({
                'Topic':          record['topic'],
                'TopicPartition': topic_partition,
                'Offset':         record['offset'],
                'Decoded':        json.loads (base64.b64decode (record['value']).decode ('utf-8'))
            })

    return decoded

def mimic_kafka_event (data):
    encoded = {
        'records': {
            'nonprod.domain.v1.student.contact_details-0': [
                {
                    'topic': 'nonprod.domain.v1.student.contact_details',
                    'offset': 0,
                    'value': base64.b64encode (json.dumps (data).encode ('utf-8'))
                }
            ]
        }
    }

    return encoded

def exec ():
    context = {}

    encoded = dsc.load_json ('inputs/salesforce/null.json')
    event   = mimic_kafka_event (encoded)

    return_value = sconn.lambda_handler (event, context)
    print (return_value)

if (__name__ == '__main__'):
    os.environ['ENV']           = 'nonprod'
    os.environ['FUNCTION_NAME'] = F'{os.environ['ENV']}_KALI_CONTACT_DETAILS_SALESFORCE_CONNECTOR'
    exec ()
