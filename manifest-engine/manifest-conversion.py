import orjson
import yaml

import manifest_engine as engine
import py_log_event_module as lem

import dscore as dsc

def load_event ():
    return dsc.load_json ('event.json')

def open_yaml (manifest_file_path):
    with open (manifest_file_path) as manifest:
          return yaml.safe_load (manifest)

    return ''

def main ():

    start_time, correlation_id = lem.init_logger ('manifest-conversion')

    lem_data = {
        'started_at': start_time,
        'correlation_id': correlation_id
    }

    manifest = open_yaml ('student.stu.ssp.compntssp.create.yaml')

    source = {
        'source': {
            'input': load_event (),
            'meta': {
                'kafka_key': lem.generate_ulid_now (),
                'kafka_topic': 'the-kafka-topic',
            }
        }
    }

    context = engine.evaluate_mapping_context (lem_data, manifest, source)

    transformed = engine.run_mapping (lem_data, context, manifest, source)

    engine.consign_to_sinks (lem_data, context, manifest, transformed)

if (__name__ == '__main__'):
    main ()
