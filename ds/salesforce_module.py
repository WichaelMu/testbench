import os
import re
import time
import requests
import json
import boto3
import jwt
import urllib.parse

import py_log_event_module as lem

from simple_salesforce import Salesforce
import email_validator as ev


OBJECT_EXISTS  = 'OBJECT_EXISTS'
OBJECT_CREATED = 'OBJECT_CREATED'
FIELD_EXISTS   = 'FIELD_EXISTS'
FIELD_CREATED  = 'FIELD_CREATED'
FIELD_FAILED   = 'FIELD_FAILED'


class StandardFieldIsNonExistent (Exception):
    pass

def get_secret_stuff ():
    secret_name = os.environ['SECRET_NAME']
    secretsmanager_client = boto3.client ('secretsmanager')
    secret_response = secretsmanager_client.get_secret_value (SecretId = secret_name)
    secret_stuff = secret_response['SecretString']
    return json.loads (secret_stuff)

def normalise_private_key (private_key):
    return private_key.replace ('\\n', '\n')

def setup_salesforce_connection (correlation_id):
    secret_stuff = get_secret_stuff ()

    login_url = secret_stuff['login_url'].rstrip ('/')
    private_key = normalise_private_key (secret_stuff['salesforce_key'])

    payload = {
        'iss': secret_stuff['consumer_key'],
        'sub': secret_stuff['salesforce_username'],
        'aud': login_url,
        'exp': int (time.time ()) + 180
    }

    assertion = jwt.encode (
        payload,
        private_key,
        algorithm = 'RS256'
    )

    response = requests.post (
        F'{login_url}/services/oauth2/token',
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        },
        timeout = 30
    )

    if (not response.ok):
        lem.print (
            correlationId  = correlation_id,
            referenceId    = correlation_id,
            message        = F'Salesforce OAuth Failed!',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = 'MSK',
            target         = 'Salesforce',
            action         = 'POST',
            resource       = login_url,
            elapsedTime    = lem.delta_time (),
            meta           = {
                'status': response.status_code,
                'body': response.text
            }
        )

    response.raise_for_status ()

    return response.json ()

def normalise_api_version_for_simple_salesforce (api_version):
    if (api_version.startswith ('v')):
        return api_version[1:]

    return api_version

def create_simple_salesforce_client (instance_url, access_token, api_version ):
    simple_salesforce_api_version = normalise_api_version_for_simple_salesforce (api_version)

    salesforce_client = Salesforce (
        instance_url = instance_url,
        session_id   = access_token,
        version      = simple_salesforce_api_version
    )

    return salesforce_client

def pascal_case (value):
    parts = re.split (R'[^A-Za-z0-9]+|_', value)

    clean_parts = []

    for part in parts:
        if (part == ''):
            continue

        clean_parts.append (part[:1].upper () + part[1:])

    return ''.join (clean_parts)

def is_email (value):
    if (not isinstance (value, str)):
        return False

    try:
        validation_result = ev.validate_email (value, check_deliverability = False)
        return True

    except ev.EmailSyntaxError as ese:
        lem.print (
            correlationId  = '',
            referenceId    = '',
            message        = F'Email validation failed.',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = lem.service_name,
            target         = 'Salesforce',
            action         = 'POST',
            resource       = 'Contact',
            elapsedTime    = lem.delta_time (),
            meta           = {
                'what': type (ese).__name__,
                'validation-message': str (ese)
            },
            verbosity      = lem.WARNING
        )

        return False

    except Exception as e:
        lem.print (
            correlationId  = '',
            referenceId    = '',
            message        = F'Email validation faced an error.',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = lem.service_name,
            target         = 'Salesforce',
            action         = 'POST',
            resource       = 'Contact',
            elapsedTime    = lem.delta_time (),
            meta           = {
                'what': type (e).__name__,
                'validation-message': str (e)
            },
            verbosity      = lem.ERROR
        )

        raise e

    return False

def salesforce_field_api_name (path, value_type):
    name = '_'.join (map (pascal_case, path))

    if (value_type == 'list'):
        return F'{name}Json__c'

    return F'{name}__c'

def salesforce_field_label (path, value_type):
    label = '.'.join (path)

    if (value_type == 'list'):
        return F'{label} JSON'

    return label

def flatten_schema (schema, prefix = None):
    if (prefix is None):
        prefix = []

    fields = []

    for key, value in schema.items ():
        path = prefix + [key]

        if (isinstance (value, dict)):
            fields.extend (
                flatten_schema (
                    value,
                    path
                )
            )

            continue

        if (isinstance (value, list)):
            fields.append (
                {
                    'path': path,
                    'kind': 'list',
                    'item_schema': value[0] if (len (value) > 0) else 'string'
                }
            )

            continue

        fields.append (
            {
                'path': path,
                'kind': value
            }
        )

    return fields

def salesforce_execute_request (method, instance_url, access_token, path, body = None):
    response = requests.request (
        method,
        F'{instance_url.rstrip ("/")}{path}',
        headers = {
            'Authorization': F'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        json = body,
        timeout = 60
    )

    if (response.status_code >= 400):
        error_text = response.json ()

        if (error_text.get ('errorCode') == 'DUPLICATE_DEVELOPER_NAME'):
            return None

        lem.print (
            correlationId  = '',
            referenceId    = '',
            message        = F'Salesforce error.',
            status         = 'FAILED',
            tracepoint     = '',
            source         = '',
            target         = '',
            action         = '',
            resource       = '',
            elapsedTime    = lem.delta_time (),
            meta           = {
                'method:': method,
                'path:': path,
                'status:': response.status_code,
                'body:': error_text
            }
        )

        response.raise_for_status ()

    if (response.text.strip () == ''):
        return None

    return response.json ()

def object_exists (instance_url, access_token, object_api_name, api_version):
    response = requests.get (
        F'{instance_url.rstrip ("/")}/services/data/{api_version}/sobjects/{object_api_name}/describe',
        headers = {
            'Authorization': F'Bearer {access_token}',
            'Accept': 'application/json'
        },
        timeout = 30
    )

    if (response.status_code == 200):
        return True

    if (response.status_code == 404):
        return False

    response.raise_for_status ()

    return False

def field_exists (instance_url, access_token, object_api_name, field_api_name, api_version):
    if (not object_exists (instance_url, access_token, object_api_name, api_version)):
        return False

    description = salesforce_execute_request (
        'GET',
        instance_url,
        access_token,
        F'/services/data/{api_version}/sobjects/{object_api_name}/describe'
    )

    if (description is not None and isinstance (description, dict)):
        for field in description['fields']:
            if (field['name'] == field_api_name):
                return True

    return False

def hoomanise_salesforce_api_name (api_name):
    if (api_name == 'Name'):
        return 'Name'

    label = re.sub (R'__c$', '', api_name)

    label = re.sub (R'([a-z0-9])([A-Z])', R'\1 \2', label)

    label = label.replace ('_', ' ')

    return label.strip ()

def normalise_field_spec (field_api_name, raw_spec):
    if (isinstance (raw_spec, dict)):
        spec = dict (raw_spec)

    else:
        spec = { 'type': raw_spec }

    spec.setdefault ('api_name', field_api_name)

    spec.setdefault ('label', hoomanise_salesforce_api_name (field_api_name))

    return spec

def parse_text_length (field_type):
    match = re.fullmatch (
        R'text\s*\(\s*(\d+)\s*\)',
        field_type,
        flags = re.IGNORECASE
    )

    if (match is None):
        return None

    return int (match.group (1))


def parse_lookup_reference (field_type):
    match = re.fullmatch (R'lookup\s*\(\s*([A-Za-z0-9_]+__c)\s*\)', field_type, flags = re.IGNORECASE)

    if (match is None):
        return None

    return match.group (1)

def picklist_value_label (value):
    if (value == ''):
        return value

    return value[:1].upper () + value[1:]

def normalise_picklist_values (values, default_value = None):
    normalised = []

    for value in values:
        if (isinstance (value, dict)):
            full_name = str (value['fullName'])
            label     = str (value.get ('label', full_name))
        else:
            full_name = str (value)
            label     = str (value)

        normalised.append ({
            'fullName': full_name,
            'label': label,
            'default': full_name == default_value
        })

    return normalised

def field_metadata_from_spec (field_api_name, spec):
    field_type = str (spec.get ('type', 'text')).strip ()

    field_type_lower = field_type.lower ()

    if (field_type_lower == 'standard'):
        return None

    if (field_type_lower == 'existing_only'):
        return None

    label    = spec.get ('label', hoomanise_salesforce_api_name (field_api_name))
    required = spec.get ('required', False)

    description_parts = []

    if (spec.get ('source') is not None):
        description_parts.append (F'Source mapping: {spec["source"]}')

    if (spec.get ('notes') is not None):
        description_parts.append (str (spec['notes']))

    description = '\n'.join (description_parts)

    text_length_from_type      = parse_text_length (field_type)
    lookup_reference_from_type = parse_lookup_reference (field_type)

    if (field_type_lower == 'standard'):
        return None

    if (field_type_lower == 'string' or field_type_lower == 'text' or text_length_from_type is not None):
        metadata = {
            'label': label,
            'type': 'Text',
            'length': spec.get ('length', text_length_from_type if (text_length_from_type is not None) else 255),
            'required': required
        }

    elif (field_type_lower == 'email'):
        metadata = {
            'label': label,
            'type': 'Email',
            'required': required
        }

    elif (field_type_lower == 'date'):
        metadata = {
            'label': label,
            'type': 'Date',
            'required': required
        }

    elif (field_type_lower == 'datetime'):
        metadata = {
            'label': label,
            'type': 'DateTime',
            'required': required
        }

    elif (field_type_lower == 'numbeR'):
        metadata = {
            'label': label,
            'type': 'NumbeR',
            'precision': spec.get ('precision', 18),
            'scale': spec.get ('scale', 0),
            'required': required
        }

    elif (field_type_lower == 'boolean' or field_type_lower == 'checkbox'):
        metadata = {
            'label': label,
            'type': 'Checkbox',
            'defaultValue': str (spec.get ('default', False)).lower ()
        }

    elif (field_type_lower == 'longtext'):
        metadata = {
            'label': label,
            'type': 'LongTextArea',
            'length': spec.get ('length', (1 << 16) >> 1),
            'visibleLines': spec.get ('visible_lines', 3)
        }

    elif (field_type_lower == 'picklist'):
        values = spec.get ('values', [])

        default_value = spec.get ('default', None)

        metadata = {
            'label': label,
            'type': 'Picklist',
            'required': required,
            'valueSet': {
                'restricted': spec.get ('restricted', False),
                'valueSetDefinition': {
                    'sorted': False,
                    'value': normalise_picklist_values (values, default_value)
                }
            }
        }

    elif (field_type_lower == 'lookup' or lookup_reference_from_type is not None):
        reference_to = spec.get ('reference_to', lookup_reference_from_type)

        if (reference_to is None):
            raise ValueError (F'Lookup field {field_api_name} is missing reference_to')

        metadata = {
            'label': label,
            'type': 'Lookup',
            'referenceTo': reference_to,
            'relationshipName': spec.get ('relationship_name', re.sub (R'__c$', '', field_api_name)),
            'relationshipLabel': spec.get ('relationship_label', label),
            'deleteConstraint': spec.get ('delete_constraint', 'Restrict'),
            'required': required
        }

    else:
        raise ValueError (F'Unsupported Salesforce field type for {field_api_name}: {field_type}')

    if (spec.get ('external_id', False)):
        metadata['externalId'] = True

    if (spec.get ('unique', False)):
        metadata['unique'] = True
        metadata['caseSensitive'] = spec.get ('case_sensitive', False)

    if (description != ''):
        metadata['description'] = description
        metadata['inlineHelpText'] = description[:255]

    return metadata

def create_custom_object (instance_url, access_token, object_api_name, label, plural_label, api_version):
    if (object_exists (instance_url, access_token, object_api_name, api_version)):
        lem.info (F'Object already exists: {object_api_name}')
        return OBJECT_EXISTS

    salesforce_client = create_simple_salesforce_client (
        instance_url,
        access_token,
        api_version
    )

    sf_mdapi = salesforce_client.mdapi

    custom_object = sf_mdapi.CustomObject (
        fullName      = object_api_name,
        label         = label,
        pluralLabel   = plural_label,
        nameField     = sf_mdapi.CustomField (
            label   = 'Name',
            type    = sf_mdapi.FieldType ('Text')
        ),
        deploymentStatus = sf_mdapi.DeploymentStatus ('Deployed'),
        sharingModel = sf_mdapi.SharingModel ('ReadWrite')
    )

    result = sf_mdapi.CustomObject.create (custom_object)

    lem.info (F'Created object: {object_api_name}')
    return OBJECT_CREATED

def create_custom_field (instance_url, access_token, object_api_name, field_api_name, metadata, api_version):
    if (field_exists (instance_url, access_token, object_api_name, field_api_name, api_version)):
        lem.info (F'Field already exists: {object_api_name}.{field_api_name}')
        return FIELD_EXISTS

    body = {
        'FullName': F'{object_api_name}.{field_api_name}',
        'Metadata': metadata
    }

    try:
        result = salesforce_execute_request (
            'POST',
            instance_url,
            access_token,
            F'/services/data/{api_version}/tooling/sobjects/CustomField',
            body
        )

    except Exception as e:
        return FIELD_FAILED

    lem.info (F'Created field: {object_api_name}.{field_api_name}')
    return FIELD_CREATED

def wait_for_object (instance_url, access_token, object_api_name, api_version, timeout_seconds = 60, interval_seconds = 2):
    deadline = time.time () + timeout_seconds

    while (time.time () < deadline):
        if (object_exists (instance_url, access_token, object_api_name, api_version)):
            lem.info (F'Object is ready: {object_api_name}')
            return

        lem.info (F'Waiting for object to become available: {object_api_name}')
        time.sleep (interval_seconds)

    raise TimeoutError (F'Object was created but did not become available within {timeout_seconds} seconds: {object_api_name}')

SF_STANDARD_FIELDS = { 'Name' }
def create_object_from_schema (instance_url, access_token, object_api_name, label, plural_label, sf_schema, api_version):
    object_creation_exit_code = create_custom_object (instance_url, access_token, object_api_name, label, plural_label, api_version)

    wait_for_object (instance_url, access_token, object_api_name, api_version)

    faults = []
    field_errors_exist = False
    for field_api_name, raw_spec in sf_schema.items ():
        spec = normalise_field_spec (field_api_name, raw_spec)

        field_type = str (spec.get ('type', '')).lower ()

        # If, for some reason, a default field does not exist...
        if (field_api_name in SF_STANDARD_FIELDS or field_type == 'standard' or field_type == 'existing_only'):
            if (spec.get ('must_exist', False)):
                if (not field_exists (instance_url, access_token, object_api_name, field_api_name, api_version)):
                    raise StandardFieldIsNonExistent (F'Expected field does not exist: {object_api_name}.{field_api_name}')

        metadata = field_metadata_from_spec (field_api_name, spec)
        field_creation_exit_code = create_custom_field (instance_url, access_token, object_api_name, field_api_name, metadata, api_version)

        if (field_creation_exit_code == FIELD_FAILED):
            faults.append ({
                'object-name': object_api_name,
                'object-creation-status': object_creation_exit_code,
                'field-name': field_api_name,
                'field-creation-status': field_creation_exit_code
            })

    return object_creation_exit_code, faults

def get_salesforce_id_by_external_id (object_api_name, external_id_field, external_id_value, salesforce_context_object):
    instance_url = salesforce_context_object['InstanceUrl']
    access_token = salesforce_context_object['AccessToken']
    api_version  = salesforce_context_object['ApiVersion']

    encoded_external_id_value = urllib.parse.quote (str (external_id_value), safe = '')

    response = requests.get (
        F'{instance_url.rstrip ("/")}/services/data/{api_version}/sobjects/{object_api_name}/{external_id_field}/{encoded_external_id_value}',
        headers = {
            'Authorization': F'Bearer {access_token}',
            'Accept': 'application/json'
        },
        timeout = 30
    )

    if (response.status_code == 404):
        raise Exception (F'Salesforce parent record not found: {object_api_name}.{external_id_field}={external_id_value}')

    if (response.status_code >= 400):
        lem.print (
            correlationId  = '',
            referenceId    = '',
            message        = F'Salesforce lookup failed!.',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = 'MSK',
            target         = 'Salesforce',
            action         = 'GET',
            resource       = '{external_id_field}.{external_id_value}',
            elapsedTime    = lem.delta_time (),
            meta           = {
                'object:': object_api_name,
                'external_id_field:': external_id_field,
                'external_id_value:': external_id_value,
                'status:': response.status_code,
                'body:': response.text
            }
        )

        response.raise_for_status ()

    return response.json ()['Id']

def list_salesforce_api_versions (instance_url, access_token):
    response = requests.get (
        F'{instance_url.rstrip ("/")}/services/data/',
        headers = { 'Authorization': F'Bearer {access_token}', 'Accept': 'application/json' },
        timeout = 30
    )

    response.raise_for_status ()

    return response.json ()

def get_latest_api_version (instance_url, access_token):
    versions = list_salesforce_api_versions (instance_url, access_token)

    latest = max (
        versions,
        key=lambda version: float (version['version'])
    )

    return F'v{latest["version"]}'

def sanitise_salesforce_payload (payload):
    sanitised = {}

    for key, value in payload.items ():
        if (value is None):
            continue
        if (isinstance (value, str) and value.strip () == ''):
            continue

        sanitised[key] = value

    return sanitised

def dispatch_salesforce_record (correlation_id, object_api_name, external_id_field, payload, salesforce_context_object):
    if (external_id_field not in payload):
        raise Exception (F'Missing external ID field {external_id_field} in payload')

    instance_url = salesforce_context_object['InstanceUrl']
    access_token = salesforce_context_object['AccessToken']
    api_version  = salesforce_context_object['ApiVersion']

    external_id_value = payload[external_id_field]

    encoded_external_id_value = urllib.parse.quote (str (external_id_value), safe = '')
    salesforce_payload        = sanitise_salesforce_payload (payload)
    del salesforce_payload[external_id_field]

    response = requests.patch (
        F'{instance_url.rstrip ("/")}/services/data/{api_version}/sobjects/{object_api_name}/{external_id_field}/{encoded_external_id_value}',

        headers = {
            'Authorization': F'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },

        json    = salesforce_payload,
        timeout = 30
    )

    if (response.status_code >= 400):
        try:
            meta_body = response.json ()
        except:
            meta_body = response.text

        lem.print (
            correlationId  = correlation_id,
            referenceId    = correlation_id,
            message        = F'Failed to dispatch record to Salesforce!',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = 'MSK',
            target         = instance_url,
            action         = 'PATCH',
            resource       = object_api_name,
            elapsedTime    = lem.delta_time (),
            meta           = {
                'status:': response.status_code,
                'object:': object_api_name,
                'external-id-field:': external_id_field,
                'external-id-value:': external_id_value,
                'body:': meta_body
            },
            verbosity      = 40
        )

        response.raise_for_status ()

    return {
        'success': True,
        'object': object_api_name,
        'externalIdField': external_id_field,
        'externalIdValue': external_id_value,
        'response': response.json () if response.text.strip () != '' else 'NO_RESPONSE'
    }

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

def get_salesforce_object_fields (salesforce_context_object, object_api_name, custom_only = False, include_deprecated = False, include_metadata = False, include_reference_fields = False):
    assert_salesforce_name (object_api_name)

    instance_url = salesforce_context_object['InstanceUrl']
    access_token = salesforce_context_object['AccessToken']
    api_version  = salesforce_context_object['ApiVersion']

    response = requests.get (
        F'{instance_url.rstrip ("/")}/services/data/{api_version}/sobjects/{object_api_name}/describe',
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
            message        = F'Salesforce object describe failed',
            status         = 'FAILED',
            tracepoint     = 'END',
            source         = 'KALI',
            target         = 'Salesforce',
            action         = 'GET',
            resource       = object_api_name,
            elapsedTime    = lem.delta_time (),
            meta           = {
                'object:': object_api_name,
                'status:': response.status_code,
                'body:': response.text,
            },
            verbosity      = lem.ERROR
        )

        response.raise_for_status ()

    describe = response.json ()

    field_results = []

    for field in describe.get ('fields', []):
        if (include_deprecated is False and field.get ('deprecatedAndHidden') is True):
            continue

        if (custom_only is True and field.get ('custom') is not True):
            continue

        field_name = field['name']

        if (include_metadata is True):
            field_results.append ({
                'name': field_name,
                'label': field.get ('label'),
                'type': field.get ('type'),
                'length': field.get ('length'),
                'custom': field.get ('custom'),
                'createable': field.get ('createable'),
                'updateable': field.get ('updateable'),
                'nillable': field.get ('nillable'),
                'externalId': field.get ('externalId'),
                'unique': field.get ('unique'),
                'referenceTo': field.get ('referenceTo'),
                'relationshipName': field.get ('relationshipName')
            })

            continue

        field_results.append (field_name)

        if (include_reference_fields is True):
            relationship_name = field.get ('relationshipName')

            if (relationship_name is not None):
                field_results.append (F'{relationship_name}.Name')

    return {
        'object': object_api_name,
        'count': len (field_results),
        'fields': field_results
    }
