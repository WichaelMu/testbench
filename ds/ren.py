import os
from datetime import datetime

from functional import pseq, seq

import py_log_event_module as lem
import rule_engine as ren

import cohorts_lookup_table
import dscore as dsc

PROGRAM_NAME = 'rule-engine'

def read_from_tags (tags, what):
    what += '='
    readed = pseq (tags) \
        .filter (lambda r: r[0:len (what)] == what) \
        .map (lambda r: r[len (what):]) \
        .to_list ()

    if (len (readed) == 0):
        return F'Failed to read {what}'

    return readed[0]

NO_GOOD = 'NoGood'
NOT_MAPPED = 'NOT_MAPPED'
NEVER_DATE = '3999-12-31'

def construct_data_entities (tag_lookup, event, rule):
    cohort_id = tag_lookup['Cohort']
    cohort = {
        'groupId': cohort_id,
        'groupName': cohorts_lookup_table.to_group_name (cohort_id),
        'groupDescription': tag_lookup.get ('GroupDescription', NOT_MAPPED),
        'owner': {
            'partyName':        tag_lookup.get ('PartyName', NOT_MAPPED),
            'partyId':          tag_lookup.get ('PartyId', NOT_MAPPED),
            'partyType':        tag_lookup.get ('PartyType', NOT_MAPPED),
            'partyDescription': tag_lookup.get ('PartyDescription', NOT_MAPPED)
        },
        'productVertical':   tag_lookup.get ('ProductVertical', NOT_MAPPED),
        'groupType':        tag_lookup.get ('GroupType', NOT_MAPPED),
        'sensitivityClass':  tag_lookup.get ('SensitivityClass', NOT_MAPPED),
        'status':            tag_lookup.get ('Status', NOT_MAPPED),
        'effectiveFromDate': tag_lookup.get ('EffectiveFromDate', NOT_MAPPED),
        'effectiveToDate':   tag_lookup.get ('EffectiveToDate', NEVER_DATE)
    }

    cohort_membership = {
        'studentId':         tag_lookup.get ('StudentId', NOT_MAPPED),
        'groupId':          cohort_id,
        'status':            cohort['status'],
        'effectiveFromDate': cohort['effectiveFromDate'],
        'effectiveToDate':   cohort['effectiveToDate'],
        'ruleId':            tag_lookup.get ('RuleName', ''),
        'ruleVersion':       'NOT_IMPLEMENTED',
        'sensitivityClass':  cohort['sensitivityClass'],
        'sourceSystem':      tag_lookup.get ('SourceSystem', NOT_MAPPED),
        'lastModifiedDate':  lem.iso_8601_now ()
    }

    rule = {
        'ruleId':            tag_lookup.get ('RuleName', ''),
        'ruleVersion':       'NOT_IMPLEMENTED',
        'ruleDefinition':    rule,
        'lastModifiedDate':  tag_lookup.get ('LastModifiedDate', ''),
        'lastModifiedBy':    tag_lookup.get ('LastModifiedBy', '')
    }

    return {
        'Cohort': cohort,
        'CohortMembership': cohort_membership,
        'Rule': rule
    }

def ddb_compliant (value):
    if isinstance (value, float):
        return str (value)

    if isinstance (value, dict):
        return { str (k): ddb_compliant (v) for k, v in value.items () }

    if isinstance (value, list):
        return [ ddb_compliant (v) for v in value ]

    if isinstance (value, tuple):
        return [ ddb_compliant (v) for v in value ]

    if isinstance (value, set):
        return { ddb_compliant (v) for v in value }

    if isinstance (value, (str, int, bool)) or value is None:
        return value

    raise TypeError (
        F'Unsupported type for DynamoDB serialisation: '
        F'{type (value).__name__} ({value!r})'
    )

def ddb_dispatch (dynamodb_client, partition_key, sorting_key, dynamodb_table, payload):
    table = dynamodb_client.Table (dynamodb_table)

    organised_key = {
        'PK': partition_key,
        'SK': sorting_key
    }

    try:
        ddb_row = ddb_compliant (payload)

    except TypeError as te:
        # formal error log here.
        raise te

    if not ddb_row:
        raise ValueError ('Payload items must not be empty')

    expression_parts  = []
    expression_names  = {}
    expression_values = {}

    for index, (attr_name, attr_value) in enumerate (ddb_row.items ()):
        name_token = F'#attr{index}'
        value_token = F':value{index}'

        expression_parts.append (F'{name_token} = {value_token}')
        expression_names[name_token] = attr_name
        expression_values[value_token] = attr_value

    update_expression = 'SET ' + ', '.join (expression_parts)

    response = table.update_item (
        Key                       = organised_key,
        UpdateExpression          = update_expression,
        ExpressionAttributeNames  = expression_names,
        ExpressionAttributeValues = expression_values,
        ReturnValues              = 'ALL_NEW'
    )

    return response.get ('Attributes', {})

def ddb_construct_student_root (dtags, event):
    student_id = dtags.get ('StudentId', NOT_MAPPED)

    pk = F'STUDENT#{student_id}'
    sk = F'0#RECORD#00000000'

    return pk, sk, student_id

def ddb_construct_cohort_root (dtags, event):
    group_id = dtags.get ('Cohort', NOT_MAPPED)

    pk = F'COHORT#{group_id}'
    sk = F'0#RECORD#00000000'

    return pk, sk

def ddb_construct_membership_edge (dtags, event):
    student_id = dtags.get ('StudentId', NOT_MAPPED)
    cohort_id   = dtags.get ('Cohort', NOT_MAPPED)
    yyyymmdd   = dtags.get ('LastModifiedDate', NOT_MAPPED)
    yyyymmdd   = datetime.fromisoformat (yyyymmdd).strftime ('%Y%m%d')

    pk = F'STUDENT#{student_id}'
    sk = F'COHORT#{cohort_id}#FROM#{yyyymmdd}'

    gsi1pk = F'COHORT#{cohort_id}'
    gsi1sk = F'FROM#{yyyymmdd}#STUDENT#{student_id}'
    gsi2pk = F'COHORT'
    gsi2sk = F'COHORT#{cohort_id}'

    gsi = {
        'GSI1PK': gsi1pk,
        'GSI1SK': gsi1sk,
        'GSI2PK': gsi2pk,
        'GSI2SK': gsi2sk
    }

    return pk, sk, gsi

def ddb_construct_rule_definition (dtags, event):
    rule_id = dtags.get ('RuleName', NOT_MAPPED)
    rule_id = rule_id.rsplit("/", 1)[-1].split(".", 1)[0]
    rule_version = 0 # NOT_IMPLEMENTED
    padded_rule_version = F'{rule_version:06}'

    pk = F'RULE#{rule_id}'
    sk = F'RULE#{padded_rule_version}'
    
    return pk, sk

def persist (dtags, event, rule, dynamodb_table):
    import boto3

    constructed = construct_data_entities (dtags, event, rule)

    dynamodb_region = 'ap-southeast-2'
    dynamodb = boto3.resource ('dynamodb', region_name = dynamodb_region)

    sr_pk, sr_sk, sr_sid = ddb_construct_student_root (dtags, event)
    cr_pk, cr_sk         = ddb_construct_cohort_root (dtags, event)
    me_pk, me_sk, gsi    = ddb_construct_membership_edge (dtags, event)
    ru_pk, ru_sk         = ddb_construct_rule_definition (dtags, event)

    student_root_response    = ddb_dispatch (dynamodb, sr_pk, sr_sk, dynamodb_table, { 'studentId': sr_sid })
    cohort_root_response     = ddb_dispatch (dynamodb, cr_pk, cr_sk, dynamodb_table, constructed['Cohort'])
    membership_edge_response = ddb_dispatch (dynamodb, me_pk, me_sk, dynamodb_table, constructed['CohortMembership'] | gsi)
    rule_response            = ddb_dispatch (dynamodb, ru_pk, ru_sk, dynamodb_table, constructed['Rule'])

    return {
        'constructed-data-entities': constructed,
        'dynamodb-key-fields': {
            'student-root': {
                'PK': sr_pk,
                'SK': sr_sk,
                'StudenId': sr_sid
            },
            'cohort-root': {
                'PK': cr_pk,
                'SK': cr_sk
            },
            'membership-edge': {
                'PK': me_pk,
                'SK': me_sk,
                'GSI': gsi
            },
            'rule-definition': {
                'PK': ru_pk,
                'SK': ru_sk
            }
        }
    }

def persist_results (tags, event, rule):
    dtags = ren.construct_tags (tags)

    data_entities = pseq (dtags) \
        .filter (lambda test_tags: 'NoGood' not in test_tags.keys ()) \
        .map (lambda good_tags: persist (good_tags, event, rule, 'nonprod_student_cohorts')) \
        .to_list ()

    dsc.save_generated (PROGRAM_NAME, 'ddb-responses', data_entities)
    print (data_entities)

def main ():
    event = dsc.load_json ('rules/input.json')
    result = ren.run_rule_engine (event)

    tags = result['tags']

    persist_results (tags, event, result['rules'])

if (__name__ == '__main__'):
    main ()
