import time
import requests
import jwt

import log_event_module as lem

import dscore as dsc

import tbench_salesforce_module as tsf

def salesforce_context (correlation_id):
    salesforce_connection = tsf.sf.setup_salesforce_connection (correlation_id)
    instance_url = salesforce_connection['instance_url']
    access_token = salesforce_connection['access_token']
    api_version = tsf.sf.get_latest_api_version (instance_url, access_token)

    return {
        'InstanceUrl': instance_url,
        'AccessToken': access_token,
        'ApiVersion': api_version
    }

def get_object_rows (sf_context, **kwargs):
    sf_result = tsf.get_salesforce_records (sf_context, **kwargs)
    sf_records = sf_result['records']

    print (sf_records)
    return sf_records

def get_object_fields (sf_context, object_api_name):
    sf_result = tsf.sf.get_salesforce_object_fields (sf_context, object_api_name)
    sf_fields = sf_result['fields']

    # print (sf_fields)
    return sf_fields

def get_limits (sf_context_object):
    limits = tsf.get_sf_limits (sf_context_object)
    print (limits)

def exec ():
    sf_context = salesforce_context ('')

    get_limits (sf_context)
    return

    # r = sf.delete_all_salesforce_records (sf_context, 'Account')
    # return

    qobject = 'Account'
    fields = get_object_fields (sf_context, qobject)

    fields_to_grab = [ 'UTS_Identifier__c', 'PreferredName__pc' ]
    get_object_rows (
        sf_context,
        object_api_name = qobject,
        fields = fields,
        where_equals = {
            'UTS_Identifier__c': '30000000'
        },
        limit = 10000
    )

if (__name__ == '__main__'):
    exec ()
