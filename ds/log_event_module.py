import sys
import json
import logging
import math
import os
import pytz

import logging

from datetime import datetime
from ulid import monotonic as ulid

aest = pytz.timezone ('Australia/Sydney')

traces: list[dict] = []
service_name = "Default Service Name"
logger_instance = None

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

def delta_time (return_f32_deltatime = True):
    return str (get_dt_now () - start_time) if not return_f32_deltatime else (get_dt_now () - start_time).total_seconds ()

def generate_ulid_invoke_time () -> str:
    """Generates a new ULID based on the time of this function invocation."""
    return str (ulid.from_timestamp (start_time))

def generate_ulid_now () -> str:
    return str (ulid.from_timestamp (get_dt_now ()))

def set_service_name (svc_name):
    global service_name
    service_name = svc_name

def init_logger (svc_name, log_verbosity = logging.INFO, logging_overrides = {}):
    set_service_name (svc_name)
    start_time = register_starting_time ()
    universal_uniq_lexico_sortable_id = generate_ulid_invoke_time ()

    default_log_settings = {
        # Take full control over the default Lambda logging config?
        'takeover': True,

        # Otherwise, propagate our instance's settings?
        'propagate': True,

        # Modify root handlers as well?
        'override-existing-config': False
    }

    merged_settings = default_log_settings | logging_overrides

    global logger_instance
    logger_instance = logging.getLogger (svc_name)
    logger_instance.propagate = merged_settings['propagate']

    logging.basicConfig (level = log_verbosity, force = merged_settings['takeover'])

    if (merged_settings['override-existing-config']):
        root = logging.getLogger ()
        root.setLevel (log_verbosity)

        if root.handlers:
            for h in root.handlers:
                h.setLevel (log_verbosity)

    return universal_uniq_lexico_sortable_id, start_time

def iso_8601_now ():
    return iso_8601 (get_dt_now ())

def iso_8601 (when_datetime):
    return str (when_datetime.astimezone (aest).isoformat ())

def calculate_elapsed_time(start: datetime) -> int:
    return math.ceil((get_dt_now () - start).total_seconds())

def get_callsite (depth):
    zeroed = depth - 1
    if (zeroed < 1):
        zeroed = 1

    frame = sys._getframe (zeroed)
    return {
        'source-file': os.path.basename (frame.f_code.co_filename),
        'function': frame.f_code.co_name,
        'line': frame.f_lineno
    }

def log (correlationId, referenceId, message, status, tracepoint, source, target, action, resource, elapsedTime, meta = {}):
    log_entry = {
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

    traces.append (log_entry)
    return log_entry

def print (correlationId, referenceId, message, status, tracepoint, source, target, action, resource, elapsedTime, meta = {}, verbosity = logging.INFO, callsite_depth = 3):
    meta['callsite'] = get_callsite (callsite_depth)

    log_dict = log (correlationId, referenceId, message, status, tracepoint, source, target, action, resource, elapsedTime, meta)
    json_log = json.dumps (log_dict)

    if (logger_instance is None):
        logging.log (verbosity, json_log)
    else:
        logger_instance.log (verbosity, json_log)

def info (w):
    verbosity = logging.INFO
    callsite = get_callsite (3)

    if (logger_instance is None):
        logging.log (verbosity, w)
    else:
        logger_instance.log (verbosity, F'{callsite["function"]}:{callsite["line"]} - {w}')

def warning (w):
    verbosity = logging.WARNING
    callsite = get_callsite (3)

    if (logger_instance is None):
        logging.log (verbosity, w)
    else:
        logger_instance.log (verbosity, F'{callsite["function"]}:{callsite["line"]} - {w}')

def error (w):
    verbosity = logging.ERROR
    callsite = get_callsite (3)

    if (logger_instance is None):
        logging.log (verbosity, w)
    else:
        logger_instance.log (verbosity, F'{callsite["function"]}:{callsite["line"]} - {w}')

def exception (w):
    verbosity = logging.FATAL
    callsite = get_callsite (3)

    if (logger_instance is None):
        logging.log (verbosity, w)
    else:
        logger_instance.log (verbosity, F'{callsite["function"]}:{callsite["line"]} - {w}')
