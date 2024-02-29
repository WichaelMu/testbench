import json
import logging
import base64
from debug_utils import debug, dwarn, derr, dmess, dspec, dcrit

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUNNING_FROM_LAMBDA = False;
"""True if the current version is being executed in a Lambda environment. False if this code is a local debug version."""
RET_ATTRIBUTE = '__RETURN_ATTRIBUTE__';
"""Sentinel values when retrieving attributes."""
STRICT = False;
"""True to print all AHEGS-related errors. False to treat AHEGS-related errors as None or default."""
__PAYLOAD_FILE = 'FULL-SUITE.json'
"""The name of the payload JSON file used for debugging. Only used when !RUNNING_FROM_LAMBDA."""


def http_error(error_message, pre_exception_response = None):
    if (not RUNNING_FROM_LAMBDA):
        derr (error_message)

    return {
        "Error": error_message,
        "ResponseAtException": pre_exception_response
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


def verify_source(event, key, constant):
    val = event.get(key, None)
    if (val and constant in val):
        return event
    return False

def source_is_pipe(lambda_body):
    return verify_source(lambda_body, key='resourceArn', constant='arn:aws:pipes:')

def source_is_kafka(lambda_body):
    return verify_source(lambda_body, key='eventSource', constant='aws:kafka')

def is_b64(any) -> bool:
    if (isinstance (any, str)):
        try:
            base64.b64decode(any)
        except Exception:
            return False
        return True
    return False

def deserialise_string(serialised):
    dmess ('Checking if deserialisation is required.')
    if (not isinstance (serialised, str) and not isinstance (serialised, bytes)):
        dmess (F'Deserialise not necessary for {type(serialised)}...')
        return serialised
    dmess (F'Deserialise necessary on {type(serialised)}...')

    try:
        return json.loads(serialised)
    except Exception:
        return False

def b64_decode(encoded) -> bytes:
    return base64.b64decode(encoded)

def extract_pipe_value(pipe):
    dspec ('::ExtractPipeValue')

    if (not pipe):
        derr ('Pipe is None!')
        return []

    if (not isinstance(pipe, dict)):
        derr (F'extract_pipe_value is not handling a dict!\n\tType: {type(pipe)}\n\tValue: {pipe}')
        return []
    dmess ('Pipe is typeof(dict).')

    # The Kafka Message/s are in the Payload of the EventBridge Pipe.
    payload = pipe.get('payload', None)
    if (not payload):
        derr ('Payload is None!')
        return []
    dmess ('Payload is not None.')

    # The Payload now contains Kafka data.
    # If the Kafka Message/s are a string, it is most likely B64-encoded.
    payload = deserialise_string(payload)

    # From here onwards, the Payload should be treated as Kafka Message/s.
    dmess ('Handing Payload over to ExtractKafkaValue::')
    return extract_kafka_value(payload)

def extract_kafka_value(kafka):
    dspec ('::ExtractKafkaValue')

    # If coming from Pipe, ensure that the Kafka data is not null.
    if (not kafka):
        derr ('Kafka is None!')
        return []

    # Ensure we are not working with a string, a B64-encoded string, a list, or anything else...
    if (not isinstance (kafka, dict)):
        derr (F'extract_kafka_value is not handling a dict!\n\tType: {type(kafka)}\n\tValue:\n\t\t{kafka}')
        return []
    dmess ('Kafka is typeof(dict).')

    # We have to potentially check if the Source Is Kafka twice,
    #   in case this call came from ExtractPipeValue::
    if (not source_is_kafka(kafka)):
        derr ('Source is not Kafka!')
        return []

    # From here onwards, we are working with genuine Kafka data.
    dmess ('Source is Kafka.')

    # Topics and Messages from Kafka are within 'records'.
    #    Records is a map<str, array<KafkaMessage>>
    #        KafkaMessage contains the Kafka Topic, Kafka Partition ID, a Timestamp, and a B64-encoded Value.
    kafka_records = kafka.get('records', {})
    kafka_courses = []

    for kafka_topic, kafka_array in kafka_records.items():
        debug (F'Topic: {kafka_topic} :: Array Length: {len(kafka_array)}')
        for kafka_message in kafka_array:
            kafka_value = kafka_message.get('value', None)
            if (not kafka_value):
                dwarn (F'{kafka_topic} - KafkaValue is None! Continuing...')
                continue
            dmess ('Deserialising Kafka Message into Python Object...')

            # Some mixed answers about whether or not Pipes & Kafka automatically decode B64-encoded strings.
            # Decode if B64-encoded, otherwise leave it as raw JSON.
            kafka_value = b64_decode(kafka_value) if is_b64(kafka_value) else kafka_value
            kafka_deserialised = deserialise_string(kafka_value)
            kafka_courses.append(kafka_deserialised)

    if (RUNNING_FROM_LAMBDA):
        debug (F'Retrieved Course definition/s from Kafka!\n\tFound: {len(kafka_courses)}.\n\tValue/s:\n\t\t{kafka_courses}.')
    return kafka_courses


def execute_find_courses(message):
    debug("Finding Course definition/s in Event...")

    # If the event is straight from aws:pipes, extract Kafka data out from it.
    if (source_is_pipe(message)):
        return extract_pipe_value(message)
    # If the event is straight from aws:kafka, return it; this is what we want.
    elif (source_is_kafka(message)):
        return extract_kafka_value(message)
    else:
        dcrit (F'Failed to retrieve courses from EventBridge::Pipes and Kafka!\nMessage:\n\t{message}')
    return None

def get_courses(event):
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
        if (RUNNING_FROM_LAMBDA):
            lambda_body = json.loads(event['body'])
        else:
            lambda_body = event['body']

    if (len(lambda_body) == 0):
        derr ('Event has no body!')
        return http_error('Event has no body!')

    debug("Finding Course definition/s in Event...")

    courses = []
    for message in lambda_body:
        course_payload = execute_find_courses(message)
        if (course_payload):
            courses.append(course_payload)
    
    debug (F'Found {len(courses)} course/s! Handing courses over; map to UTS_AHEGS...')
    return courses


def map_uts_ahegs(courses):
    if (not isinstance (courses, list)):
        # We cannot continue if 'courses' is not of <class 'list'>.
        #     Something is also very wrong.
        fatal = F"Courses is not typeof(list)! Found {type(courses)}, expected <class 'list'>."
        dcrit (fatal)
        return http_error(fatal)

    if ('Error' in courses):
        return courses
    
    mapped_uts_ahegs_fields = []

    # courses: list< list<payload> > -- 2D Array. First dimension is the entire structure of courses,
    #                                   Second dimension is an array containing payloads for each
    #                                   EventBridge Pipe payload or Kafka Message batch.
    # course_group: list<payload>    -- The course definition/s for the individual payload.
    # course: map <str, T>           -- The course definition.
    #
    # "courses":
    # [
    #     [
    #         -- course_group --
    #         {course}, {course}, {course}
    #     ],
    #     [
    #         -- course_group --
    #         {course}, {course}, {course}
    #     ]
    # ]

    for course_group in courses:
        for course in course_group:
            if (not isinstance (course, dict)):
                warning = F"Course definition in CourseGroup is not typeof(dict)! Found {type(course)}, expected <class 'dict'>.\nData:\n\t{course}."
                dwarn (warning)
                continue
            # Only used for debug.
            abbr_name = course.get('abbr_name', '__NO_ABBR_NAME__')

            # Check that this course has the required keys for AHEGS.
            if (STRICT):
                key_validation = [ 'award', 'requirement', 'ai_association' ]
                for k in key_validation:
                    if (k not in course):
                        return http_error(F"{abbr_name} ({course.get('sys_id', '__NO_SYS_ID__')}) - Event::Body::Course has no [{k}]", pre_exception_response=mapped_uts_ahegs_fields)

            # Get required fields/attributes for course.
            awards = course.get('award', None);
            requirements = course.get('requirement', None);
            ai_associations = course.get('ai_association', None)

            if (STRICT and (not awards or not requirements or not ai_associations)):
                dwarn (F'{abbr_name} - Either award, requirements, or ai_associations are missing...')
                dmess (F'{abbr_name} - is None? awards: {awards is None}. requirements: {requirements is None}. ai_associations: {ai_associations is None}.')
                continue

            debug(F'{abbr_name} - Validation checks complete! Running AHEGS filtering...')

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
                return http_error(F"The Course: {course['code']} - {course['abbr_name']} has zero or more entries in award_information and requirement_description! Found award_information: {len(award_information)}, expected: 1, and requirement_description: {len(requirement_description)}, expected: 1!",
                                    pre_exception_response=mapped_uts_ahegs_fields)

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
            
            ftd = course.get('duration_ft_std', None)
            ftd_unit = try_get('duration_ft_period', 'label', source=course)

            # Accumulate relevant data as a single entry.
            mapped_uts_ahegs_fields.append(
                {
                    "HARVEST_YEAR": course.get('implementation_year', None),
                    "HARVEST_PERIOD": None,
                    "HARVEST_DATE": None,

                    "CODE": course.get('code', None),
                    "VERSION": course.get('sms_version', None),
                    "COURSENAME": course.get('name', None),

                    "ADMISSIONREQUIREMENTS": requirement_description[0] if (len(requirement_description) > 0) else None,

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
            )

            debug(F'{abbr_name} - Mapped UTS_AHEGS with CourseLoop properties.')
        
    debug(F'Mapped {len(mapped_uts_ahegs_fields)} UTS_AHEGS Fields!')
    return mapped_uts_ahegs_fields


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


def dispatch_ahegs_database(uts_ahegs):
    if ('Error' in uts_ahegs):
        return
    debug ('Establishing connection to database...')
    engine, cnx, meta = establish_connection()
    debug ('Connection to AHEGS database established.')

    for ahegs in uts_ahegs:
        inject_ahegs(engine, meta, ahegs)

    cnx.close()
    debug ('Closed connection to database.')


def lambda_handler(event, context):
    courses = get_courses(event);
    uts_ahegs = map_uts_ahegs(courses);

    return {
        "statusCode": "200",
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps (uts_ahegs),
    }

if (__name__ == '__main__'):
    print (lambda_handler(None, None))
