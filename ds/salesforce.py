import time
import requests
import jwt

import log_event_module as lem

import dscore as dsc

import salesforce_module as sf

def salesforce_context (correlation_id):
    salesforce_connection = sf.setup_salesforce_connection (correlation_id)
    instance_url = salesforce_connection['instance_url']
    access_token = salesforce_connection['access_token']
    api_version = sf.get_latest_api_version (instance_url, access_token)

    return {
        'InstanceUrl': instance_url,
        'AccessToken': access_token,
        'ApiVersion': api_version
    }

def get_object_rows (sf_context, **kwargs):
    sf_result = sf.get_salesforce_records (sf_context, **kwargs)
    sf_records = sf_result['records']

    print (sf_records)
    return sf_records

def get_object_fields (sf_context, object_api_name):
    sf_result = sf.get_salesforce_object_fields (sf_context, object_api_name)
    sf_fields = sf_result['fields']

    # print (sf_fields)
    return sf_fields

def exec ():
    sf_context = salesforce_context ('')

    qobject = 'Party__c'
    fields = get_object_fields (sf_context, qobject)

    # fields_to_grab = [ 'Name', 'Email__c' ]
    get_object_rows (
        sf_context,
        object_api_name = qobject,
        fields = fields,
        where_equals = {
            'StudentId__c': '28092020'
        },
    )

if (__name__ == '__main__'):
    exec ()
