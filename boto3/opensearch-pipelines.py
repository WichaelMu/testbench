import sys
import json
from datetime import datetime
from functional import seq, pseq

import boto3
from botocore.config import Config

import socket
from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
from kafka.sasl.oauth import AbstractTokenProvider

import yaml

import logging

logger = logging.getLogger ()
logger.setLevel (logging.INFO)


def get_osis_client ():
    config = Config (
       retries = {
          'max_attempts': 10,
          'mode': 'standard'
       }
    )

    osis = boto3.client ('osis', config = config)

    return osis

def list_pipelines (osis_client):
    pipelines_paginator = osis_client.list_pipelines (MaxResults = 50)
    pipelines_iterator = pipelines_paginator['Pipelines']
    pipelines_accumulator = pipelines_iterator

    while ('NextToken' in pipelines_iterator and len (pipelines_iterator['NextToken']) > 0):
        pipelines_iterator = osis_client.list_pipelines (
            MaxResults = 50,
            NextToken = pipelines_iterator['NextToken']
        )

        pipelines_accumulator += pipelines_iterator['Pipelines']

    pipeline_details = seq (pipelines_accumulator) \
        .filter (lambda x: 'PipelineName' in x) \
        .filter (lambda x: 'Status' in x) \
        .map (lambda x: {
            'PipelineName': x['PipelineName'],
            'PipelineStatus': x['Status'],
        }) \
        .to_list ()

    return pipeline_details

def get_pipelines (osis_client, list_of_pipelines):
    result_accumulator = seq (list_of_pipelines) \
        .map (lambda lop: osis_client.get_pipeline (PipelineName = lop['PipelineName'])) \
        .map (lambda p: p['Pipeline']) \
        .map (lambda x: {
            'PipelineName': x['PipelineName'],
            'PipelineStatus': x['Status'],
            'PipelineDefinition': x['PipelineConfigurationBody']
        }) \
        .to_list ()

    return result_accumulator

def filter_pipelines (pipeline_details, argv):
    return pseq (pipeline_details) \
        .filter (lambda x: argv[KCONTAINS] in x['PipelineName']) \
        .filter (lambda x: x['PipelineName'].startswith (argv[KPREFIX])) \
        .filter (lambda x: x['PipelineName'].endswith (argv[KSUFFIX])) \
        .to_list ()

def load_yaml (pipeline_details):
    kafka_sources = []
    for pd in pipeline_details:
        definition = yaml.safe_load (pd['PipelineDefinition'])
        del definition['version']

        source = list (definition.values ())

        kafka_details = pseq (source) \
            .filter (lambda x: 'source' in x.keys ()) \
            .filter (lambda x: 'kafka' in x['source'].keys ()) \
            .filter (lambda x: 'topics' in x['source']['kafka'].keys ()) \
            .map (lambda x: x['source']['kafka']['topics']) \
            .reduce (lambda x, y: x + y, []) \
            .to_list ()

        kafka_sources += pseq (kafka_details) \
            .map (lambda x: {
                'PipelineName': pd['PipelineName'],
                'Topic': x['name'],
                'ConsumerGroup': x['group_id']
            }) \
            .to_list ()

    print (kafka_sources)
    return kafka_sources

class MSKTokenProvider (AbstractTokenProvider):
    def __init__(self, region):
        self.region = region

    def token (self):
        token, _ = MSKAuthTokenProvider.generate_auth_token (self.region)
        return token

def reset_consumer_group (data):
    streaming_cluster_endpoint = data['streaming-cluster-endpoint']
    streaming_cluster_region   = data['streaming-cluster-region']
    topic                      = data['topic']
    consumer_group             = data['consumer-group']
    function_name              = data.get ('function-name', 'consumer-group-resetter')

    consumer = KafkaConsumer (
        bootstrap_servers         = streaming_cluster_endpoint,
        security_protocol         = 'SASL_SSL',
        sasl_mechanism            = 'OAUTHBEARER',
        sasl_oauth_token_provider = MSKTokenProvider (streaming_cluster_region),
        group_id                  = consumer_group,
        enable_auto_commit        = False,
        client_id                 = F'{function_name}.{socket.gethostname ()}',
        request_timeout_ms        = 30000,
    )

    try:
        partitions = consumer.partitions_for_topic (topic)

        if not partitions:
            raise ValueError (F'Topic not found or no partitions visible: {topic}')

        topic_partitions = [
            TopicPartition (topic, partition_id)
            for partition_id in sorted (partitions)
        ]

        earliest_offsets = consumer.beginning_offsets (topic_partitions)

        offsets_to_commit = {
            tp: OffsetAndMetadata (earliest_offsets[tp], '', -1)
            for tp in topic_partitions
        }

        consumer.commit (offsets=offsets_to_commit)

        return { F'{tp.topic}:{tp.partition}': earliest_offsets[tp] for tp in topic_partitions }

    finally:
        consumer.close (autocommit=False)

def reset_associated_offsets (pipeline_data):
    result = {}
    for pd in pipeline_data:
        import os
        streaming_cluster_endpoint = 'boot-gkbcfaxp.c1.kafka-serverless.ap-southeast-2.amazonaws.com:9098'
        streaming_cluster_region   = 'ap-southeast-2'
        topic                      = pd['Topic']
        consumer_group             = pd['ConsumerGroup']
        pipeline_name              = pd['PipelineName']

        reset_consumer_group_payload = {
            'streaming-cluster-endpoint': streaming_cluster_endpoint,
            'streaming-cluster-region':   streaming_cluster_region,
            'topic':                      topic,
            'consumer-group':             consumer_group,
            'function-name':              pipeline_name
        }

        print (reset_consumer_group_payload)

        result |= { pipeline_name: reset_consumer_group (reset_consumer_group_payload) }

    return { 'reset': result }

def exec (event, context):
    argv = parse_argv ()

    osis_client = get_osis_client ()
    list_of_pipelines = list_pipelines (osis_client)
    pipeline_details = get_pipelines (osis_client, list_of_pipelines)
    filtered_pipelines = filter_pipelines (pipeline_details, argv)

    if (KREWIND_ONLY in argv and argv[KREWIND_ONLY]):
        topics = load_yaml (filtered_pipelines)
        result = reset_associated_offsets (topics)
        print (result)

    elif (KENABLE in argv and argv[KENABLE]):
        start_pipelines = seq (filtered_pipelines) \
            .filter (lambda fp: fp['PipelineStatus'] in [ 'CREATE_FAILED', 'START_FAILED', 'STOPPED' ]) \
            .map (lambda fp: osis_client.start_pipeline (PipelineName = fp['PipelineName'])) \
            .map (lambda fpr: fpr['Pipeline']) \
            .map (lambda fpr: {
                'PipelineName': fpr['PipelineName'],
                'PipelineStatus': fpr['Status']
            }) \
            .to_list ()

        print (start_pipelines)

    elif (KENABLE in argv and not argv[KENABLE]):
        stop_pipelines = seq (filtered_pipelines) \
            .filter (lambda fp: fp['PipelineStatus'] in [ 'UPDATE_FAILED', 'ACTIVE' ]) \
            .map (lambda fp: osis_client.stop_pipeline (PipelineName = fp['PipelineName'])) \
            .map (lambda fpr: fpr['Pipeline']) \
            .map (lambda fpr: {
                'PipelineName': fpr['PipelineName'],
                'PipelineStatus': fpr['Status']
            }) \
            .to_list ()

        print (stop_pipelines)

KENABLE = 'enable'
KPREFIX = 'prefix'
KSUFFIX = 'suffix'
KCONTAINS = 'contains'
KREWIND_ONLY = 'rewind-only'
KQUERY_ONLY = 'query'

def parse_argv ():
    argv = sys.argv[1:]
    argc = len (argv)

    # print (F'argc, argv: {argc}, {argv}')

    def process_option (option, iterator):
        match option:
            case '--enable':
                iterator += 1

                if (argv[iterator].lower () == 'yes' or argv[iterator].lower () == 'true'):
                    result = True
                elif (argv[iterator].lower () == 'no' or argv[iterator].lower () == 'false'):
                    result = False
                else:
                    print ('--enable must be [ yes | no | true | false ]')
                    sys.exit (1)

                return { KENABLE: result }, iterator

            case '--dry' | '--query':
                iterator += 1

                return { KQUERY_ONLY: True }, iterator

            case '--prefix':
                iterator += 1

                return { KPREFIX: argv[iterator] }, iterator

            case '--suffix':
                iterator += 1

                return { KSUFFIX: argv[iterator] }, iterator

            case '--contains':
                iterator += 1

                return { KCONTAINS: argv[iterator] }, iterator

            case '--rewind-only':
                iterator += 1

                if (argv[iterator].lower () == 'yes' or argv[iterator].lower () == 'true'):
                    result = True
                elif (argv[iterator].lower () == 'no' or argv[iterator].lower () == 'false'):
                    result = False
                else:
                    print ('--rewind-only must be [ yes | no | true | false ]')
                    sys.exit (1)

                return { KREWIND_ONLY: argv[iterator] }, iterator

            case '?' | '--help' | 'help' | '__HELP__':
                print ('--enable true | false --prefix PREFIX --suffix SUFFIX')
                sys.exit (0)
                return {}, iterator

            case _:
                return {}, iterator

    options = {
        KPREFIX: '',
        KSUFFIX: '',
        KCONTAINS: '',
        KQUERY_ONLY: False
    }

    iterator = 0
    while (iterator < argc):
        try:

            option, iterator = process_option (argv[iterator], iterator)
            options = options | option

            iterator += 1

        except IndexError:

            print (F'Option {iterator + 1} ({argv[iterator]}) requires a parameter.')
            process_option ('?', 0)
            sys.exit (1)

    # print (options)

    errors_exist = False
    if (KENABLE not in options and KREWIND_ONLY not in options):
        if (not options[KQUERY_ONLY]):
            print (F'One of --enable or --rewind-only is required')
            errors_exist = True

    if (options[KPREFIX] == '' and options[KSUFFIX] == '' and options[KCONTAINS] == ''):
        print (F'One of --prefix, --suffix, or --contains must be present')
        errors_exist = True

    if (errors_exist):
        sys.exit (1)

    return options

if (__name__ == "__main__"):
    exec (None, None)
