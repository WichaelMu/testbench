import json
import logging
import base64
import debug_utils as dbg
from testdatabase import establish_connection, inject_ahegs, try_read
from debug_utils import debug, dwarn, derr, dmess, dspec, dcrit, Verbosity, Status
from bs4 import BeautifulSoup

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUNNING_FROM_LAMBDA = False;
"""True if the current version is being executed in a Lambda environment. False if this code is a local debug version."""
RET_ATTRIBUTE = '__RETURN_ATTRIBUTE__';
"""Sentinel values when retrieving attributes."""
STRICT = False;
"""True to print all AHEGS-related errors. False to treat AHEGS-related errors as None or default."""
__PAYLOAD_FILE = 'real.json'
"""The name of the payload JSON file used for debugging. Only used when !RUNNING_FROM_LAMBDA."""


def http_error(error_message):
    if (not RUNNING_FROM_LAMBDA):
        derr (error_message)

    return {
        "Error": error_message,
    }


def get_attributes_explicit(source, target, check_key, check_value, return_value, return_default):
    retval = []
    for attribute in source:
        attribute_target = attribute.get(target, None)
        if (attribute_target is not None and attribute_target[check_key] == check_value):
            retval.append(
                attribute.get(return_value, return_default)
                if return_value is not RET_ATTRIBUTE and return_default is not RET_ATTRIBUTE
                else attribute
            )
    return retval


def get_attributes(source, value_map):
    return get_attributes_explicit(source,
                                   value_map['attribute_target'],
                                   value_map['target_check'][0],
                                   value_map['target_check'][1],
                                   value_map['return_value'][0],
                                   value_map['return_value'][1]
                                   )


def sanitise_html(markup):
    if (not markup):
        return None
    return BeautifulSoup(markup, 'html.parser').get_text()


def verify_source(event, key, constant) -> bool:
    val = event.get(key, None)
    return (val and constant in val)

def source_is_pipe(lambda_body) -> bool:
    return verify_source(lambda_body, key='resourceArn', constant='arn:aws:pipes:')

def source_is_kafka(lambda_body) -> bool:
    return verify_source(lambda_body, key='eventSource', constant='aws:kafka')

def is_b64(any) -> bool:
    if (isinstance (any, str)):
        try:
            base64.b64decode(any)
        except Exception:
            return False
        return True
    return False

def deserialise(serialised) -> dict:
    dmess ('Checking if deserialisation is required.')
    if (not isinstance (serialised, str) and not isinstance (serialised, bytes)):
        dmess (F'Deserialise not necessary for {type(serialised)}...')
        return serialised
    dmess (F'Deserialise necessary on {type(serialised)}...')

    try:
        return json.loads(serialised)
    except Exception:
        return {}

def b64_decode(encoded) -> bytes:
    return base64.b64decode(encoded)

def extract_pipe_value(pipe) -> dict | None:
    dspec ('::ExtractPipeValue')

    if (not pipe):
        dwarn ('Pipe is None!')
        return None

    if (not isinstance(pipe, dict)):
        derr (F'extract_pipe_value is not handling a dict!\n\tType: {type(pipe)}\n\tValue: {pipe}')
        return None

    # The Kafka Message/s are in the Payload of the EventBridge Pipe.
    payload = pipe.get('payload', None)
    if (not payload):
        derr ('Payload is None!')
        return None

    # The Payload now contains Kafka data.
    # If the Kafka Message/s are a string, it is most likely B64-encoded.
    payload = deserialise(payload)

    # From here onwards, the Payload should be treated as Kafka Message/s.
    dmess ('Handing Payload over to ExtractKafkaValue::')
    return extract_kafka_value(payload)

def extract_kafka_value(kafka) -> dict | None:
    dspec ('::ExtractKafkaValue')

    # If coming from Pipe, ensure that the Kafka data is not null.
    if (not kafka):
        dwarn ('Kafka is None!')
        return None

    # Ensure we are not working with a string, a B64-encoded string, a list, or anything else...
    if (not isinstance (kafka, dict)):
        derr (F'extract_kafka_value is not handling a dict!\n\tType: {type(kafka)}\n\tValue:\n\t\t{kafka}')
        return None

    # We have to potentially check if the Source Is Kafka twice,
    #   in case this call came from ExtractPipeValue::
    if (not source_is_kafka(kafka)):
        derr ('Source is not Kafka!')
        return None

    # From here onwards, we are working with genuine Kafka data.
    dmess ('Source is Kafka.')

    kafka_value = kafka.get('value', None)
    if (not kafka_value):
        dwarn (F'{kafka_value} - KafkaValue is None! Returning None...')
        return None
    dmess ('Deserialising Kafka Message into Python Object...')

    # Some mixed answers about whether or not Pipes & Kafka automatically decode B64-encoded strings.
    # Decode if B64-encoded, otherwise leave it as raw JSON.
    kafka_value = b64_decode(kafka_value) if is_b64(kafka_value) else kafka_value
    kafka_deserialised = deserialise(kafka_value)

    if (RUNNING_FROM_LAMBDA):
        debug (F'Retrieved Course definition from Kafka!.')
    return kafka_deserialised


def execute_find_courses(payload) -> dict | None:
    debug("Finding Course definition/s in Message...")

    # If the event is straight from aws:kafka, return it; this is what we want.
    if (source_is_kafka(payload)):
        return extract_kafka_value(payload)
    # If the event is straight from aws:pipes, extract Kafka data out from it.
    elif (source_is_pipe(payload)):
        return extract_pipe_value(payload)
    else:
        dcrit (F'Failed to retrieve courses from EventBridge::Pipes or MSK::Kafka!\nPayload:\n\t{payload}')
    return None

def get_courses(event, ref_id) -> dict | None:
    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "EXTRACT_COURSE_DEFINITION",
        tracemessage = "Extracting course definition from EventBridge Pipes & Kafka.",
        status       = Status.START,
        action       = "READ",
    )

    # Mandatory Print to CloudWatch. ###############################################
    debug (F'\tMandatory Print to CloudWatch.\n\n{event}')
    ################################################################################

    debug ("Finding ['body'] in event...")

    # If a local deployment, we have a custom JSON course file.
    if (not RUNNING_FROM_LAMBDA):
        f = open(__PAYLOAD_FILE)
        event = json.load(f)

    lambda_body = {}

    if ('body' in event):
        if (RUNNING_FROM_LAMBDA and not isinstance (event, dict)):
            lambda_body = json.loads(event['body'])
        else:
            lambda_body = event['body']

    if (len(lambda_body) == 0):
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "EXTRACT_COURSE_DEFINITION",
            tracemessage = "Event has no body!",
            status       = Status.FAILURE,
            action       = "READ",
            verbosity    = Verbosity.ERROR
        )
        return http_error('Event has no body!')

    course_payload = execute_find_courses(lambda_body)
    if (course_payload and len(course_payload) > 0):
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "EXTRACT_COURSE_DEFINITION",
            tracemessage = F"Course definition found! Handing course over to UTS_AHEGS mapping.",
            status       = Status.SUCCESS,
            action       = "READ",
        )
        return course_payload

    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "EXTRACT_COURSE_DEFINITION",
        tracemessage = "Could not find course definition in Payload! Review event in Mandatory Print to CloudWatch.",
        status       = Status.FAILURE,
        action       = "READ",
        verbosity    = Verbosity.ERROR
    )
    return None


def map_uts_ahegs(course, ref_id) -> tuple[dict, dict]:
    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "MAP_UTS_AHEGS",
        tracemessage = "Mapping course to UTS_AHEGS format.",
        status       = Status.START,
        action       = "MAP",
    )

    if ('Error' in course):
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "MAP_UTS_AHEGS",
            tracemessage = "The course definition contains error/s. Aborting UTS_AHEGS mapping.",
            status       = Status.FAILURE,
            action       = "MAP",
            verbosity    = Verbosity.ERROR
        )
        return course

    if (not isinstance (course, dict)):
        error_message = F"Course definition in CourseGroup is not typeof(dict)! Found {type(course)}, expected <class 'dict'>.\nData:\n\t{course}."
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "MAP_UTS_AHEGS",
            tracemessage = error_message,
            status       = Status.FAILURE,
            action       = "MAP",
            verbosity    = Verbosity.ERROR
        )
        return http_error(error_message), {}

    # Only used for debug.
    abbr_name = course.get('abbr_name', '__NO_ABBR_NAME__')

    # Check that this course has the required keys for AHEGS.
    if (STRICT):
        key_validation = [ 'award', 'requirement', 'ai_association' ]
        for k in key_validation:
            if (k not in course):
                return http_error(F"{abbr_name} ({course.get('sys_id', '__NO_SYS_ID__')}) - Event::Body::Course has no [{k}]"), {}

    # Get required fields/attributes for course.
    awards = course.get('award', None);
    requirements = course.get('requirement', None);
    ai_associations = course.get('ai_association', None)

    if (STRICT and (not awards or not requirements or not ai_associations)):
        dwarn (F'{abbr_name} - Either award, requirements, or ai_associations are missing...')
        dmess (F'{abbr_name} - is None? awards: {awards is None}. requirements: {requirements is None}. ai_associations: {ai_associations is None}.')

    # Search for 'award_type' in awards.
    award_information = get_attributes(awards, {
                                            'attribute_target': 'award_type',
                                            'target_check': ('value', 'award_level'),
                                            'return_value': ('award_information', '__NO_AWARD_INFORMATION__')
                                            })
    debug(F'{abbr_name} - Received Award Information. Found: {len(award_information)}.')

    # Search for 'type' in requirements.
    requirement_description = get_attributes(requirements, {
                                            'attribute_target': 'type',
                                            'target_check': ('value', 'admission'),
                                            'return_value': ('description', '__NO_REQUIREMENT_DESCRIPTION__')
                                            })
    debug(F'{abbr_name} - Received Requirement Description. Found: {len(requirement_description)}.')

    # Assert that there is exactly one occurence of award_information and requirement_description.
    if (STRICT and not RUNNING_FROM_LAMBDA and len(award_information) != 1 and len(requirement_description) != 1):
        return http_error(F"The Course: {course['code']} - {course['abbr_name']} has zero or more entries in award_information and requirement_description! Found award_information: {len(award_information)}, expected: 1, and requirement_description: {len(requirement_description)}, expected: 1!"), {}

    if (STRICT):
        debug(F'{abbr_name} - Assert passed! Looking for ai_associations...')

    # Find all ai_associations that match.
    ai_associations_match = get_attributes(ai_associations, {
                                            'attribute_target': 'association_type',
                                            'target_check': ('value', 'articulated_course'),
                                            'return_value': ( 'description', '__NO_ARTICULATION_DESCRIPTION__' )
                                            }) if ai_associations else None
    if (ai_associations_match):
        debug(F'{abbr_name} - Search for matching ai_associations complete! Found: {len(ai_associations_match)}')
    
    ftd             = course.get('duration_ft_std', None)
    ftd_unit        = try_get('duration_ft_period', 'label', source=course)
    course_code     = course.get('code', None)
    course_version  = course.get('sms_version', None)
    harvest_year    = course.get('implementation_year', None)
    updated_by      = course.get('sys_updated_by', None)
    course_metadata = dbg.trace_meta(
                            code = course_code,
                            version = course_version,
                            harv_year = harvest_year,
                            epoch = "0",
                            updated_by = updated_by
                       )

    # Accumulate relevant data as a single entry.
    mapped_uts_ahegs_fields = {
        "HARVEST_YEAR": harvest_year,
        "HARVEST_PERIOD": None,
        "HARVEST_DATE": None,

        "CODE": course_code,
        "VERSION": course_version,
        "COURSENAME": course.get('name', None),

        "ADMISSIONREQUIREMENTS": sanitise_html(requirement_description[0]) if (len(requirement_description) > 0) else None,

        "MINIMUMDURATION": None,
        "INDUSTRIALTRAINING": course.get('summary', None),
        "OVERSEASSTUDY": course.get('features', None),
        "COURSESTRUCTURE1": course.get('structure', None),

        "ARTICULATION": ai_associations_match[0] if (ai_associations_match and len(ai_associations_match) > 0) else None,
        "FURTHERSTUDY": course.get('pathways', None),
        "PROFESSIONALRECOGNITION": course.get('professional_recognition', None),
        "LEVELOFAWARD": award_information[0] if (len(award_information) > 0) else None,
        "HONOURS": None,
        "LOADEFTSL": None,

        "FULLTIMEDURATION": ftd,
        "FULLTIMEDURATIONUNIT": ftd_unit,
        "PARTTIMEDURATION": course.get('duration_pt_std', None),
        "PARTTIMEDURATIONUNIT": try_get('duration_pt_period', 'label', source=course)
    }

    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "MAP_UTS_AHEGS",
        tracemessage = F"Mapped {abbr_name} UTS_AHEGS with CourseLoop properties.",
        status       = Status.SUCCESS,
        action       = "MAP",
        metadata     = course_metadata
    )
        
    return mapped_uts_ahegs_fields, course_metadata


def try_get(*args, source):
    if (not isinstance(source, dict)):
        if (STRICT):
            derr (F'source is not an instance of dict! {source}\nReturning source input instead...')
        return source

    val = source.get(args[0], None)
    if (not val):
        return val

    intptr = 1
    while (intptr < len(args)):
        val = val.get(args[intptr], None)
        if (not isinstance(val, dict)):
            return val

    return None


def dispatch_ahegs_database(uts_ahegs, course_metadata, ref_id):
    dbg.trace (
        ulid         = ref_id,
        tracepoint   = "DATABASE",
        tracemessage = "Dispatching UTS_AHEGS mapping to MS SQL database.",
        status       = Status.START,
        action       = "DISPATCH",
        metadata     = course_metadata,
    )

    if ('Error' in uts_ahegs):
        dbg.trace (
            ulid         = ref_id,
            tracepoint   = "DATABASE",
            tracemessage = "UTS_AHEGS Mapping resulted and contains errors. Aborting dispatch to database.",
            status       = Status.FAILURE,
            action       = "DISPATCH",
            metadata     = course_metadata,
            verbosity    = Verbosity.ERROR
        )
        return

    engine, cnx, meta = establish_connection(ref_id, course_metadata)

    if (engine and cnx and meta):
        inject_ahegs(engine, meta, uts_ahegs, ref_id, course_metadata)
        cnx.close()
        debug ('Closed connection to database.')


def lambda_handler(event, context):
    ref_id = dbg.generate_ulid_now()

    dbg.trace (
        ulid = ref_id,
        tracepoint="PROGRAM_EXECUTION",
        tracemessage="UTS AHEGS Mapping program begins here.",
        status = Status.START,
        action = "EXEC",
    )

    courses = get_courses(event, ref_id);
    uts_ahegs, course_metadata = map_uts_ahegs(courses, ref_id);
    dispatch_ahegs_database(uts_ahegs, course_metadata, ref_id);

    dbg.trace (
        ulid = ref_id,
        tracepoint="PROGRAM_EXECUTION",
        tracemessage="UTS AHEGS Mapping program terminates here (before returning).",
        status = Status.END,
        action = "EXEC",
        metadata = course_metadata
    )

    return {
        "statusCode": "200",
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps (uts_ahegs),
    }

if (__name__ == '__main__'):
    print (lambda_handler(None, None))

    # env ENV=dev FUNCTION_NAME="dev_post_statements_ahegs_lambda" SECRET_NAME=dev/curriculum/courseloop/endpoints/api/credentials/client OPENSEARCH_ENDPOINT_URL=search.curriculum.dev.mesh.uts.edu.au MSSQL_SECRETS=dev/curriculum/cognos/endpoints/sqlserver/verge/credentials

    # print (lambda_handler(None, None))
