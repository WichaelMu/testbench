import os
import sys
import re
import time
import requests
import json
import random
import jwt
import urllib.parse

import boto3

import py_log_event_module as lem

from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceError, SalesforceResourceNotFound, SalesforceMalformedRequest
from simple_salesforce.format import format_external_id
import email_validator as ev

sys.path.append (F'{os.environ['DITLOC']}/tf-data-plane-copt/contrib/src/lambda/student_cohort_salesforce_module/')
import salesforce_module as sf
import tbench_salesforce_module as smod


OBJECT_EXISTS  = 'OBJECT_EXISTS'
OBJECT_CREATED = 'OBJECT_CREATED'
FIELD_EXISTS   = 'FIELD_EXISTS'
FIELD_CREATED  = 'FIELD_CREATED'
FIELD_FAILED   = 'FIELD_FAILED'

LOOKUP_NOT_FOUND = 'LOOKUP_NOT_FOUND'
LOOKUP_EXCEPTION = 'LOOKUP_EXCEPTION'
SALESFORCE_REQUEST_TIMEOUT_SECONDS = 30


def assert_salesforce_name (name):
    if (not isinstance (name, str)):
        raise ValueError (F'Invalid Salesforce name: {name}')

    if (re.fullmatch (R'[A-Za-z][A-Za-z0-9_]*(?:__[cr])?(?:\.[A-Za-z][A-Za-z0-9_]*(?:__[cr])?)*', name) is None):
        raise ValueError (F'Unsafe Salesforce name: {name}')

def soql_value (value):
    if (value is None):
        return 'NULL'

    if (isinstance (value, bool)):
        return 'TRUE' if value else 'FALSE'

    if (isinstance (value, int) or isinstance (value, float)):
        return str (value)

    escaped = str (value).replace ("'", "\\'")

    return F"'{escaped}'"


def build_where_clause (where_equals):
    if (where_equals is None or len (where_equals) == 0):
        return ''

    clauses = []

    for field_name, value in where_equals.items ():
        assert_salesforce_name (field_name)

        clauses.append (F'{field_name} = {soql_value (value)}')

    return F' WHERE {" AND ".join (clauses)}'

def get_salesforce_records (salesforce_context_object, object_api_name, fields = None, where_equals = None, order_by = None, limit = 20, fetch_all = False):
    assert_salesforce_name (object_api_name)

    if (fields is None):
        fields = [ 'Id', 'Name' ]

    for field in fields:
        assert_salesforce_name ( field )

    if (order_by is not None):
        assert_salesforce_name ( order_by )

    instance_url = salesforce_context_object['InstanceUrl']
    access_token = salesforce_context_object['AccessToken']
    api_version  = salesforce_context_object['ApiVersion']

    fields_soql = ', '.join (fields)

    where_clause = build_where_clause (where_equals)

    order_by_clause = ''
    if (order_by is not None):
        order_by_clause = F' ORDER BY {order_by}'

    limit_clause = ''
    if (fetch_all is False):
        limit_clause = F' LIMIT {int (limit)}'

    query = F'SELECT {fields_soql} FROM {object_api_name}{where_clause}{order_by_clause}{limit_clause}'

    encoded_query = urllib.parse.quote (query, safe = '')

    response = requests.get (
        F'{instance_url.rstrip ("/")}/services/data/{api_version}/query?q={encoded_query}',
        headers = {
            'Authorization': F'Bearer {access_token}',
            'Accept': 'application/json'
        },
        timeout = 30
    )

    if (response.status_code >= 400):
        lem.print (
            correlationId  = '',
            referenceId    = '',
            message        = F'Salesforce query failed',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = 'KALI',
            target         = 'Salesforce',
            action         = 'GET',
            resource       = object_api_name,
            elapsedTime    = lem.delta_time (),
            meta           = {
                'object:': object_api_name,
                'query:': query,
                'status:': response.status_code,
                'body:': response.text
            },
            verbosity      = lem.ERROR
        )

        response.raise_for_status ()

    data = response.json ()
    records = data.get ('records', [])

    if (fetch_all is True):
        while (data.get ('done') is False):
            next_records_url = data['nextRecordsUrl']

            response = requests.get (
                F'{instance_url.rstrip ("/")}{next_records_url}',
                headers = {
                    'Authorization': F'Bearer {access_token}',
                    'Accept': 'application/json'
                },
                timeout = 30
            )

            if (response.status_code >= 400):
                lem.print (
                    correlationId  = '',
                    referenceId    = '',
                    message        = F'Salesforce query pagination failed',
                    status         = 'FAILED',
                    tracepoint     = 'END',
                    source         = 'KALI',
                    target         = 'Salesforce',
                    action         = 'GET',
                    resource       = object_api_name,
                    elapsedTime    = lem.delta_time (),
                    meta           = {
                        'object:': object_api_name,
                        'query:': query,
                        'status:': response.status_code,
                        'body:': response.text,
                    },
                    verbosity      = lem.ERROR
                )

                response.raise_for_status ()

            data = response.json ()
            records.extend (data.get ('records', []))

    for record in records:
        record.pop ('attributes', None)

    return {
        'object': object_api_name,
        'query': query,
        'count': len (records),
        'records': records
    }

def delete_all_salesforce_records (salesforce_context_object, object_api_name):
    sf_result = get_salesforce_records (
        salesforce_context_object,
        object_api_name,
        fields = [ 'Id' ],
        fetch_all = True
    )

    records = sf_result['records']
    record_count = sf_result['count']
    results = []

    if (record_count > 0):
        confirmation = input (
            F'{object_api_name} has {record_count} records. '
            F'Type {record_count} to delete all of them: '
        )

        if (confirmation != str (record_count)):
            raise ValueError ('Record count did not match; no records were deleted.')

        salesforce_client = create_simple_salesforce_client (
            salesforce_context_object['InstanceUrl'],
            salesforce_context_object['AccessToken'],
            salesforce_context_object['ApiVersion']
        )

        salesforce_object = get_simple_salesforce_object (
            salesforce_client.bulk,
            object_api_name
        )

        try:
            results = list (salesforce_object.delete (
                records,
                batch_size = 10000,
                use_serial = True
            ))

        except SalesforceError as error:
            lem.print (
                correlationId  = '',
                referenceId    = '',
                message        = 'Salesforce bulk delete failed',
                status         = 'FAILED',
                tracepoint     = 'END',
                source         = 'KALI',
                target         = 'Salesforce',
                action         = 'DELETE',
                resource       = object_api_name,
                elapsedTime    = lem.delta_time (),
                meta           = {
                    'object:': object_api_name,
                    'count:': record_count
                },
                raised_exception = error,
                verbosity      = lem.ERROR
            )

            raise

    deleted_count = sum (1 for result in results if result.get ('success') is True)

    return {
        'object': object_api_name,
        'count': record_count,
        'deleted_count': deleted_count,
        'success': deleted_count == record_count,
        'results': results
    }

def normalise_ordered_dict (obj):
    if (isinstance (obj, dict)):
        return {
            key: normalise_ordered_dict (value)
            for key, value in obj.items ()
        }

    if (isinstance (obj, list)):
        return list (map (normalise_ordered_dict, obj))

    if (isinstance (obj, tuple)):
        return tuple (map (normalise_ordered_dict, obj))

    return obj

def get_sf_limits (sf_context_object):
    instance_url = sf_context_object['InstanceUrl']
    access_token = sf_context_object['AccessToken']
    api_version  = sf_context_object['ApiVersion']

    sf_client = sf.create_simple_salesforce_client (
        instance_url,
        access_token,
        api_version
    )

    limits = sf_client.limits ()

    bulk = limits['DailyBulkApiBatches']

    return {
        'Maximum': bulk['Max'],
        'Remaining': bulk['Remaining'],
        'Consumed': bulk['Max'] - bulk['Remaining'],
        'DailyApiRequests': normalise_ordered_dict (limits['DailyApiRequests'])
    }
