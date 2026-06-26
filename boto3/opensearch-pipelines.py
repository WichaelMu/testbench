import os
import sys
import json
from datetime import datetime
from functional import seq, pseq

import boto3
from botocore.config import Config

import socket

import yaml

import logging

import argv_parser as ap
from argv_parser import KCONTAINS, KENABLE, KPREFIX, KREWIND_ONLY, KSUFFIX, KQUERY_ONLY

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

def exec (event, context):
    argv = ap.parse_argv ()

    osis_client = get_osis_client ()
    list_of_pipelines = list_pipelines (osis_client)
    pipeline_details = get_pipelines (osis_client, list_of_pipelines)
    filtered_pipelines = filter_pipelines (pipeline_details, argv)

    if (KQUERY_ONLY in argv and argv[KQUERY_ONLY]):
        print_pipelines = seq (filtered_pipelines) \
            .map (lambda fp: seq (fp.items ()) \
                .filter (lambda fpd: fpd[0] != 'PipelineDefinition') \
                .to_dict ()
            ) \
            .to_list ()
        print (print_pipelines)
        return

    if (KREWIND_ONLY in argv and argv[KREWIND_ONLY]):
        topics = load_yaml (filtered_pipelines)
        for pd in topics:
            streaming_cluster_endpoint = 'boot-gkbcfaxp.c1.kafka-serverless.ap-southeast-2.amazonaws.com:9098'
            streaming_cluster_region   = 'ap-southeast-2'
            topic                      = pd['Topic']
            consumer_group             = pd['ConsumerGroup']
            pipeline_name              = pd['PipelineName']

            import kafka_rewinder as kr
            result = kr.reset_consumer_group_offsets (pipeline_name, topic, consumer_group, streaming_cluster_endpoint, streaming_cluster_region)

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

if (__name__ == "__main__"):
    exec (None, None)
