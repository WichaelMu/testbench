import boto3

from functional import pseq, seq

import argv_parser as ap
from argv_parser import KENABLE, KCONTAINS, KPREFIX, KQUERY_ONLY, KSUFFIX, KREWIND_ONLY


def get_pipes_client ():
    pipes_client = boto3.client ('pipes')
    return pipes_client

def list_pipes (pipes_client, argv):
    name_prefix_parameter = {}
    if (len (argv[KPREFIX]) > 0):
        name_prefix_parameter = { 'NamePrefix': argv[KPREFIX] }

    list_pipes_response = pipes_client.list_pipes (
        **name_prefix_parameter
    )

    list_of_pipes = list_pipes_response['Pipes']
    return list_of_pipes

def filter_pipe_names (pipes, suffix, contains):
    return pseq (pipes) \
        .filter (lambda p: contains in p['Name']) \
        .filter (lambda p: p['Name'].endswith (suffix)) \
        .to_list ()

def describe_pipes (pipes_client, pipes):
    pipes_description = seq (pipes) \
        .map (lambda p: pipes_client.describe_pipe (Name = p['Name'])) \
        .map (lambda fp: pseq (fp.items ()) \
            .filter (lambda fpx: fpx[0] != 'ResponseMetadata') \
            .to_dict () \
        ) \
        .to_list ()

    return pipes_description

def determine_stopstart_pipe (pipes_client, pipes, argv):
    if (argv[KENABLE]):
        start_response = seq (pipes) \
            .map (lambda ps: pipes_client.start_pipe (Name = ps['Name'])) \
            .to_list ()

        return start_response

    else:
        stop_response = seq (pipes) \
            .map (lambda ps: pipes_client.stop_pipe (Name = ps['Name'])) \
            .to_list ()

        return stop_response

def rewind_pipes (pipes_client, pipes, argv):
    kafka_client = boto3.client ('kafka')
    kafka_lookup = {}

    rewind_result = []

    for p in pipes:
        pipe_name = p['Name']

        msk_parameters = p.get ('SourceParameters', {}).get ('ManagedStreamingKafkaParameters', {})
        if (len (msk_parameters) == 0):
            continue

        topic_name     = msk_parameters['TopicName']
        consumer_group = msk_parameters['ConsumerGroupID']
        msk_source     = p['Source']
        if (msk_source in kafka_lookup):
            kafka_struct     = kafka_lookup[msk_source]
            cluster_endpoint = kafka_struct['ClusterEndpoint']
            cluster_region   = kafka_struct['ClusterRegion']

        else:
            msk_bootstrap_broker = kafka_client.get_bootstrap_brokers (ClusterArn = msk_source)

            cluster_endpoint = msk_bootstrap_broker['BootstrapBrokerStringSaslIam']
            cluster_region   = msk_source.split (':')[3]

            msk_cache = {
                'ClusterEndpoint': cluster_endpoint,
                'ClusterRegion':   cluster_region
            }

            kafka_lookup[msk_source] = msk_cache

        import kafka_rewinder as kr
        rewind_result.append (kr.reset_consumer_group_offsets (pipe_name, topic_name, consumer_group, cluster_endpoint, cluster_region))

    return rewind_result

def main (argv):
    pipes_client    = get_pipes_client ()
    list_of_pipes   = list_pipes (pipes_client, argv)
    filtered_pipes  = filter_pipe_names (list_of_pipes, argv[KSUFFIX], argv[KCONTAINS])
    described_pipes = describe_pipes (pipes_client, filtered_pipes)

    if (argv[KREWIND_ONLY]):
        rewound_response = rewind_pipes (pipes_client, described_pipes, argv)
        return rewound_response

    else:
        stop_started = determine_stopstart_pipe (pipes_client, described_pipes, argv)
        return stop_started

if (__name__ == '__main__'):
    argv = ap.parse_argv ()

    exit_response = main (argv)
    print (exit_response)
