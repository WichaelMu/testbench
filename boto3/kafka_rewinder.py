import socket
from kafka import KafkaConsumer
from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

from kafka import TopicPartition
from kafka.structs import OffsetAndMetadata

from kafka.sasl.oauth import AbstractTokenProvider

from functional import pseq, seq

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

def reset_consumer_group_offsets (name, topic_name, consumer_group_name, cluster_endpoint, cluster_region):
    try:
        reset_consumer_group_payload = {
            'streaming-cluster-endpoint': cluster_endpoint,
            'streaming-cluster-region':   cluster_region,
            'topic':                      topic_name,
            'consumer-group':             consumer_group_name,
            'function-name':              name
        }

        result = { name: reset_consumer_group (reset_consumer_group_payload) }
        return consumer_group_name

    except Exception as e:
        return {
            'ResetFailedError':   type (e).__name__,
            'ResetFailedMessage': str (e),
            'MSKTopicName':       topic_name,
            'MSKConsumerGroup':   consumer_group_name
        }
