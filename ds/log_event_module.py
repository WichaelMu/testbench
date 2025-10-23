import json
import math
import os
from datetime import datetime
from ulid import monotonic as ulid

import logging

logger = logging.getLogger ()
logger.setLevel (logging.INFO)

import pytz
aest = pytz.timezone ('Australia/Sydney')

traces: list[dict] = []
service_name = "Default Service Name"

# This is inaccurate. Run init_logger (...) for precision.
start_time = datetime.now ().astimezone (aest)

stub = """
Use the following for copying and pasting
    lem.log (
        correlationId  = correlation_id,
        referenceId    = ref_id,
        message        = F'',
        status         = '',
        tracepoint     = '',
        source         = '',
        target         = '',
        action         = '',
        resource       = '',
        elapsedTime    = lem.delta_time ()
    )
"""

def get_dt_now ():
    return datetime.now ().astimezone (aest)

def register_starting_time ():
    global start_time
    start_time = get_dt_now ()
    return start_time

def delta_time (return_f32_deltatime = False):
    return str (get_dt_now () - start_time) if not return_f32_deltatime else (get_dt_now () - start_time).total_seconds ()

def generate_ulid_invoke_time () -> str:
    """Generates a new ULID based on the time of this function invocation."""
    return str (ulid.from_timestamp (start_time))

def generate_ulid_now () -> str:
    return str (ulid.from_timestamp (get_dt_now ()))

def set_service_name (svc_name):
    global service_name
    service_name = svc_name

def init_logger (svc_name):
    set_service_name (svc_name)
    start_time = register_starting_time ()
    universal_uniq_lexico_sortable_id = generate_ulid_invoke_time ()

    return universal_uniq_lexico_sortable_id, start_time

def iso_8601_now ():
    return iso_8601 (get_dt_now ())

def iso_8601 (when_datetime):
    return str (when_datetime.astimezone (aest).isoformat ())

def calculate_elapsed_time(start: datetime) -> int:
    return math.ceil((get_dt_now () - start).total_seconds())

def log (correlationId, referenceId, message, status, tracepoint, source, target, action, resource, elapsedTime, meta = {}):
    return {
        'correlationId': correlationId,
        'referenceId':   referenceId,
        'svc':           service_name,
        'env':           os.environ.get ('ENV', ''),
        'message':       message,
        'status':        status,
        'tracepoint':    tracepoint,
        'source':        source,
        'target':        target,
        'action':        action,
        'resource':      resource,
        'elapsedTime':   elapsedTime,
        'meta':          meta
    }

def print (correlationId, referenceId, message, status, tracepoint, source, target, action, resource, elapsedTime, meta = {}, verbosity = logging.INFO):
    log_dict = log (correlationId, referenceId, message, status, tracepoint, source, target, action, resource, elapsedTime, meta)
    json_log = json.dumps (log_dict)

    logging.log (verbosity, json_log)
